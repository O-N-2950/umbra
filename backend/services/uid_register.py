"""
MATCHO — Service de recherche IDE/UID suisse
Interroge l'API fédérale UID Register (BFS/OFS)
+ Vérification intelligente via Gemini Flash

API: https://www.uid-wse.admin.ch/V5.0/PublicServices.svc (SOAP, gratuit, sans clé)

© 2026 PEP's Swiss SA — Tous droits réservés
"""

import re
try:
    import defusedxml.ElementTree as ET
except ImportError:
    raise ImportError("❌ FATAL: pip install defusedxml — required for secure XML parsing")
from dataclasses import dataclass, field
from typing import List, Optional
import httpx


# ══════════════════════════════════════════════════════════
# MODÈLES
# ══════════════════════════════════════════════════════════

LEGAL_FORMS = {
    "0101": "Raison individuelle",
    "0103": "Société simple",
    "0104": "Société en nom collectif",
    "0105": "Société en commandite",
    "0106": "SA (Société Anonyme)",
    "0107": "Sàrl (Société à responsabilité limitée)",
    "0108": "Société coopérative",
    "0109": "Association",
    "0110": "Fondation",
    "0111": "Succursale CH",
    "0113": "Succursale étrangère",
    "0151": "Administration fédérale",
    "0152": "Administration cantonale",
    "0153": "Administration communale",
    "0302": "Entreprise individuelle non inscrite RC",
    "0327": "Autre forme juridique",
}

CANTON_NAMES = {
    "JU": "Jura", "BE": "Berne", "VD": "Vaud", "GE": "Genève",
    "NE": "Neuchâtel", "FR": "Fribourg", "VS": "Valais",
    "ZH": "Zurich", "LU": "Lucerne", "BS": "Bâle-Ville",
    "BL": "Bâle-Campagne", "AG": "Argovie", "SO": "Soleure",
    "SG": "Saint-Gall", "GR": "Grisons", "TI": "Tessin",
    "TG": "Thurgovie", "SZ": "Schwyz", "ZG": "Zoug",
    "SH": "Schaffhouse", "AR": "Appenzell RE", "AI": "Appenzell RI",
    "GL": "Glaris", "NW": "Nidwald", "OW": "Obwald", "UR": "Uri",
}


@dataclass
class CompanyResult:
    """Résultat de recherche d'entreprise suisse"""
    # Identification
    ide: str                        # CHE-xxx.xxx.xxx
    ide_raw: str                    # CHExxxxxxxxx (sans ponctuation)
    name: str                       # Nom officiel
    legal_name: str                 # Raison sociale complète
    legal_form_code: str            # Code forme juridique
    legal_form: str                 # Forme juridique en texte
    
    # Adresse
    street: str = ""
    house_number: str = ""
    zip_code: str = ""
    town: str = ""
    canton: str = ""
    canton_name: str = ""
    country: str = "CH"
    
    # Registres
    hr_number: Optional[str] = None     # Numéro registre du commerce
    ehraid: Optional[str] = None        # EHRA ID
    estv_id: Optional[str] = None       # ID administration fiscale
    
    # Statut
    is_active: bool = True
    is_vat_registered: bool = False
    
    # Score
    match_score: int = 0                # Score de correspondance (0-100)
    
    @property
    def full_address(self) -> str:
        parts = []
        if self.street:
            addr = self.street
            if self.house_number:
                addr += f" {self.house_number}"
            parts.append(addr)
        if self.zip_code and self.town:
            parts.append(f"{self.zip_code} {self.town}")
        if self.canton:
            parts.append(self.canton)
        return ", ".join(parts)
    
    @property
    def ide_formatted(self) -> str:
        """Format CHE-xxx.xxx.xxx"""
        raw = self.ide_raw.replace("CHE", "")
        if len(raw) == 9:
            return f"CHE-{raw[:3]}.{raw[3:6]}.{raw[6:9]}"
        return self.ide
    
    @property
    def vat_number(self) -> str:
        """Numéro TVA: CHE-xxx.xxx.xxx TVA"""
        return f"{self.ide_formatted} TVA"
    
    def to_dict(self) -> dict:
        return {
            "ide": self.ide_formatted,
            "ide_raw": self.ide_raw,
            "name": self.name,
            "legal_name": self.legal_name,
            "legal_form": self.legal_form,
            "legal_form_code": self.legal_form_code,
            "address": {
                "street": self.street,
                "house_number": self.house_number,
                "zip_code": self.zip_code,
                "town": self.town,
                "canton": self.canton,
                "canton_name": self.canton_name,
                "country": self.country,
                "full": self.full_address,
            },
            "registre_commerce": self.hr_number,
            "ehraid": self.ehraid,
            "is_active": self.is_active,
            "is_vat_registered": self.is_vat_registered,
            "vat_number": self.vat_number if self.is_vat_registered else None,
            "match_score": self.match_score,
        }


# ══════════════════════════════════════════════════════════
# SERVICE UID REGISTER
# ══════════════════════════════════════════════════════════

UID_API_URL = "https://www.uid-wse.admin.ch/V5.0/PublicServices.svc"

# Namespaces XML utilisés dans les réponses
NS = {
    "s": "http://schemas.xmlsoap.org/soap/envelope/",
    "uid": "http://www.uid.admin.ch/xmlns/uid-wse",
    "uid5": "http://www.uid.admin.ch/xmlns/uid-wse/5",
    "ech108": "http://www.ech.ch/xmlns/eCH-0108/5",
    "ech098": "http://www.ech.ch/xmlns/eCH-0098/5",
    "ech097": "http://www.ech.ch/xmlns/eCH-0097/5",
}


def _build_search_envelope(name: str) -> str:
    """Construit l'enveloppe SOAP pour la recherche par nom"""
    # Escape XML
    name_escaped = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    return f"""<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
                  xmlns:uid="http://www.uid.admin.ch/xmlns/uid-wse"
                  xmlns:uid5="http://www.uid.admin.ch/xmlns/uid-wse/5">
  <soapenv:Body>
    <uid:Search>
      <uid:searchParameters>
        <uid5:uidEntitySearchParameters>
          <uid5:organisationName>{name_escaped}</uid5:organisationName>
        </uid5:uidEntitySearchParameters>
      </uid:searchParameters>
    </uid:Search>
  </soapenv:Body>
</soapenv:Envelope>"""


def _build_getbyuid_envelope(uid_number: str) -> str:
    """Construit l'enveloppe SOAP pour la recherche par CHE"""
    # Nettoyer le numéro: garder uniquement les chiffres
    digits = re.sub(r"[^0-9]", "", uid_number.replace("CHE", "").replace("che", ""))
    
    return f"""<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
                  xmlns:uid="http://www.uid.admin.ch/xmlns/uid-wse"
                  xmlns:ech097="http://www.ech.ch/xmlns/eCH-0097/5">
  <soapenv:Body>
    <uid:GetByUID>
      <uid:uid>
        <ech097:uidOrganisationIdCategorie>CHE</ech097:uidOrganisationIdCategorie>
        <ech097:uidOrganisationId>{digits}</ech097:uidOrganisationId>
      </uid:uid>
    </uid:GetByUID>
  </soapenv:Body>
</soapenv:Envelope>"""


def _parse_company_from_xml(org_element) -> Optional[CompanyResult]:
    """Parse un élément organisation XML en CompanyResult"""
    try:
        # Chercher dans différentes structures possibles
        org = org_element
        
        # Identification
        def find_text(parent, tag_local, default=""):
            """Cherche un tag par nom local dans tous les sous-éléments"""
            for elem in parent.iter():
                if elem.tag.split("}")[-1] == tag_local and elem.text:
                    return elem.text.strip()
            return default
        
        uid_categorie = find_text(org, "uidOrganisationIdCategorie", "CHE")
        uid_id = find_text(org, "uidOrganisationId", "")
        org_name = find_text(org, "organisationName", "")
        legal_name = find_text(org, "organisationLegalName", org_name)
        legal_form_code = find_text(org, "legalForm", "")
        
        # Adresse
        street = find_text(org, "street", "")
        house_number = find_text(org, "houseNumber", "")
        zip_code = find_text(org, "swissZipCode", "")
        town = find_text(org, "town", "")
        canton = find_text(org, "cantonAbbreviation", "")
        
        # IDs additionnels
        hr_number = None
        ehraid = None
        estv_id = None
        for other_id in org.iter():
            if other_id.tag.split("}")[-1] == "OtherOrganisationId":
                cat = find_text(other_id, "organisationIdCategory", "")
                val = find_text(other_id, "organisationId", "")
                if cat == "CH.HR":
                    hr_number = val
                elif cat == "CH.EHRAID":
                    ehraid = val
                elif cat == "CH.ESTVID":
                    estv_id = val
        
        # Statut TVA
        is_vat = False
        vat_status = find_text(org, "vatStatus", "")
        if vat_status == "1":
            is_vat = True
        
        # Score
        rating_text = find_text(org, "rating", "0")
        # Le rating peut être dans l'élément parent (searchResultItem)
        
        ide_raw = f"{uid_categorie}{uid_id}"
        ide_formatted = f"{uid_categorie}-{uid_id[:3]}.{uid_id[3:6]}.{uid_id[6:9]}" if len(uid_id) == 9 else ide_raw
        
        return CompanyResult(
            ide=ide_formatted,
            ide_raw=ide_raw,
            name=org_name,
            legal_name=legal_name,
            legal_form_code=legal_form_code,
            legal_form=LEGAL_FORMS.get(legal_form_code, f"Code {legal_form_code}"),
            street=street,
            house_number=house_number,
            zip_code=zip_code,
            town=town,
            canton=canton,
            canton_name=CANTON_NAMES.get(canton, canton),
            country="CH",
            hr_number=hr_number,
            ehraid=ehraid,
            estv_id=estv_id,
            is_active=True,
            is_vat_registered=is_vat,
            match_score=int(rating_text) if rating_text.isdigit() else 0,
        )
    except Exception as e:
        print(f"⚠️ Erreur parsing XML: {e}")
        return None


class UIDRegisterService:
    """
    Service de recherche dans le registre UID suisse.
    
    API fédérale gratuite, sans clé d'authentification.
    Source: Office fédéral de la statistique (OFS/BFS)
    
    Usage:
        service = UIDRegisterService()
        results = await service.search_by_name("WW Finance Group")
        company = await service.get_by_uid("CHE-113.594.673")
    """
    
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
    
    async def search_by_name(self, name: str, max_results: int = 5) -> List[CompanyResult]:
        """
        Recherche une entreprise par nom dans le registre UID.
        
        Args:
            name: Nom de l'entreprise (partiel ou complet)
            max_results: Nombre max de résultats
        
        Returns:
            Liste de CompanyResult triée par score de correspondance
        """
        envelope = _build_search_envelope(name)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                UID_API_URL,
                content=envelope,
                headers={
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://www.uid.admin.ch/xmlns/uid-wse/IPublicServices/Search",
                },
            )
        
        if response.status_code != 200:
            print(f"⚠️ UID API erreur HTTP {response.status_code}")
            return []
        
        return self._parse_search_response(response.text, max_results)
    
    async def get_by_uid(self, uid: str) -> Optional[CompanyResult]:
        """
        Recherche une entreprise par numéro IDE/UID.
        
        Args:
            uid: Numéro CHE (formats acceptés: CHE-113.594.673, CHE113594673, 113594673)
        
        Returns:
            CompanyResult ou None si non trouvé
        """
        envelope = _build_getbyuid_envelope(uid)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                UID_API_URL,
                content=envelope,
                headers={
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://www.uid.admin.ch/xmlns/uid-wse/IPublicServices/GetByUID",
                },
            )
        
        if response.status_code != 200:
            return None
        
        results = self._parse_search_response(response.text, 1)
        return results[0] if results else None
    
    def search_by_name_sync(self, name: str, max_results: int = 5) -> List[CompanyResult]:
        """Version synchrone de search_by_name"""
        envelope = _build_search_envelope(name)
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                UID_API_URL,
                content=envelope,
                headers={
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://www.uid.admin.ch/xmlns/uid-wse/IPublicServices/Search",
                },
            )
        
        if response.status_code != 200:
            return []
        
        return self._parse_search_response(response.text, max_results)
    
    def get_by_uid_sync(self, uid: str) -> Optional[CompanyResult]:
        """Version synchrone de get_by_uid"""
        envelope = _build_getbyuid_envelope(uid)
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                UID_API_URL,
                content=envelope,
                headers={
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://www.uid.admin.ch/xmlns/uid-wse/IPublicServices/GetByUID",
                },
            )
        
        if response.status_code != 200:
            return None
        
        results = self._parse_search_response(response.text, 1)
        return results[0] if results else None
    
    def _parse_search_response(self, xml_text: str, max_results: int) -> List[CompanyResult]:
        """Parse la réponse SOAP et extrait les entreprises"""
        results = []
        
        try:
            # Protection XXE: utilise le parser sécurisé
            from security import safe_parse_xml
            root = safe_parse_xml(xml_text)
            
            # Trouver tous les éléments de résultat
            for item in root.iter():
                if item.tag.split("}")[-1] == "uidEntitySearchResultItem":
                    # Extraire le rating directement
                    rating = 0
                    for child in item:
                        if child.tag.split("}")[-1] == "rating" and child.text:
                            rating = int(child.text)
                    
                    company = _parse_company_from_xml(item)
                    if company:
                        company.match_score = rating
                        results.append(company)
                
                # GetByUID retourne un seul résultat différemment
                elif item.tag.split("}")[-1] == "GetByUIDResponse":
                    company = _parse_company_from_xml(item)
                    if company:
                        company.match_score = 100
                        results.append(company)
            
        except ET.ParseError as e:
            print(f"⚠️ Erreur parsing XML: {e}")
        
        # Trier par score décroissant et limiter
        results.sort(key=lambda x: x.match_score, reverse=True)
        return results[:max_results]


# ══════════════════════════════════════════════════════════
# API ROUTES — FastAPI
# ══════════════════════════════════════════════════════════

def create_uid_routes():
    """
    Crée les routes FastAPI pour la recherche UID.
    
    À intégrer dans main.py :
        from services.uid_register import create_uid_routes
        uid_router = create_uid_routes()
        app.include_router(uid_router, prefix="/api/uid")
    """
    from fastapi import APIRouter, Query
    
    router = APIRouter(tags=["Registre IDE/UID"])
    service = UIDRegisterService()
    
    @router.get("/search", summary="Rechercher une entreprise par nom")
    async def search_company(
        name: str = Query(..., description="Nom de l'entreprise", min_length=2),
        max_results: int = Query(5, ge=1, le=20),
    ):
        """
        Recherche dans le registre fédéral IDE/UID (OFS).
        
        Gratuit, sans clé API. Données officielles du registre du commerce suisse.
        L'utilisateur tape le nom → MATCHO pré-remplit IDE, adresse, forme juridique.
        """
        results = await service.search_by_name(name, max_results)
        
        return {
            "query": name,
            "count": len(results),
            "results": [r.to_dict() for r in results],
            "source": "uid-wse.admin.ch (Office fédéral de la statistique)",
        }
    
    @router.get("/lookup/{uid}", summary="Rechercher par numéro IDE")
    async def lookup_uid(uid: str):
        """
        Recherche une entreprise par son numéro IDE/UID (CHE-xxx.xxx.xxx).
        
        Formats acceptés: CHE-113.594.673, CHE113594673, 113594673
        """
        result = await service.get_by_uid(uid)
        
        if not result:
            return {"error": "Entreprise non trouvée", "uid": uid}
        
        return {
            "found": True,
            "company": result.to_dict(),
            "source": "uid-wse.admin.ch",
        }
    
    @router.get("/validate/{uid}", summary="Valider un numéro IDE")
    async def validate_uid(uid: str):
        """Vérifie si un numéro IDE est valide et actif"""
        result = await service.get_by_uid(uid)
        
        return {
            "uid": uid,
            "valid": result is not None,
            "active": result.is_active if result else False,
            "company_name": result.name if result else None,
        }
    
    return router


# ══════════════════════════════════════════════════════════
# TEST RAPIDE
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    service = UIDRegisterService()
    
    print("🔍 Recherche: WW Finance Group")
    print("=" * 50)
    
    results = service.search_by_name_sync("WW Finance Group")
    
    for r in results:
        print(f"\n✅ {r.name}")
        print(f"   IDE:     {r.ide_formatted}")
        print(f"   Forme:   {r.legal_form}")
        print(f"   Adresse: {r.full_address}")
        print(f"   Canton:  {r.canton_name}")
        print(f"   Score:   {r.match_score}/100")
        if r.hr_number:
            print(f"   RC:      {r.hr_number}")
