"""
MATCHO — Zefix REST API Service
Interroge le registre du commerce suisse (Zefix) pour obtenir:
- But social (Zweck)
- Organes (CA, gérants, réviseur)
- Capital social
- Publications FOSC
- Historique des mutations

API: https://www.zefix.admin.ch/ZefixPublicREST/
Auth: Basic (inscription gratuite sur zefix.ch)

© 2026 PEP's Swiss SA
"""

import re
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from datetime import datetime, date

logger = logging.getLogger("umbra.zefix")
import httpx


ZEFIX_BASE = "https://www.zefix.admin.ch/ZefixPublicREST/api/v1"


@dataclass
class Organ:
    """Membre d'un organe (CA, direction, révision)"""
    name: str
    role: str  # "Membre du conseil d'administration", "Gérant", "Organe de révision"
    function: str = ""  # "Président", "Directeur", etc.
    signature: str = ""  # "Signature individuelle", "Signature collective à deux"
    since: str = ""
    address: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class ZefixCompany:
    """Données enrichies depuis Zefix"""
    name: str
    uid: str  # CHE-xxx.xxx.xxx
    ehraid: int = 0
    legal_seat: str = ""  # Siège légal
    canton: str = ""
    legal_form: str = ""
    status: str = ""  # "ACTIVE", "DELETED", etc.

    # Registre du commerce
    purpose: str = ""  # But social
    capital: str = ""
    capital_currency: str = "CHF"
    rc_number: str = ""  # Numéro RC cantonal

    # Organes
    organs: List[Organ] = field(default_factory=list)

    # Dates
    inscription_date: str = ""
    last_mutation_date: str = ""
    deletion_date: str = ""

    # FOSC publications
    publications: List[Dict] = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d["organs"] = [o.to_dict() for o in self.organs]
        return d

    @property
    def auditor(self) -> Optional[str]:
        for o in self.organs:
            if "révis" in o.role.lower() or "audit" in o.role.lower():
                return o.name
        return None

    @property
    def managers(self) -> List[Organ]:
        return [o for o in self.organs if "gérant" in o.role.lower() or "direct" in o.role.lower()]

    @property
    def board_members(self) -> List[Organ]:
        return [o for o in self.organs if "conseil" in o.role.lower() or "admin" in o.role.lower()]


class ZefixService:
    """
    Client pour l'API REST Zefix.

    Usage:
        svc = ZefixService(username="your_user", password="your_pass")
        company = await svc.get_company_by_uid("CHE-113.594.673")
        print(company.purpose)
        print(company.organs)
    """

    def __init__(self, username: str = "", password: str = ""):
        self.auth = (username, password) if username and password else None

    def _headers(self):
        return {"Accept": "application/json", "Content-Type": "application/json"}

    async def search(self, name: str, max_results: int = 10) -> List[Dict]:
        """Recherche par nom via Zefix REST"""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{ZEFIX_BASE}/firm/search.json",
                    json={
                        "name": name,
                        "languageKey": "fr",
                        "maxEntries": max_results,
                    },
                    headers=self._headers(),
                    auth=self.auth,
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            print(f"⚠️ Zefix search error: {e}")
        return []

    async def get_company_by_ehraid(self, ehraid: int) -> Optional[ZefixCompany]:
        """Récupère les détails complets via ehraid"""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{ZEFIX_BASE}/firm/{ehraid}.json",
                    headers=self._headers(),
                    auth=self.auth,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return self._parse_company(data)
        except Exception as e:
            print(f"⚠️ Zefix detail error: {e}")
        return None

    async def get_company_by_uid(self, uid: str) -> Optional[ZefixCompany]:
        """Recherche par UID puis récupère les détails"""
        clean = re.sub(r"[^0-9]", "", uid)
        results = await self.search(f"CHE-{clean[:3]}.{clean[3:6]}.{clean[6:9]}", max_results=1)
        if not results:
            # Try name search with UID
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        f"{ZEFIX_BASE}/firm/uid/{clean}.json",
                        headers=self._headers(),
                        auth=self.auth,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, list) and data:
                            return self._parse_company(data[0])
                        elif isinstance(data, dict):
                            return self._parse_company(data)
            except Exception as e:
                # Leçon PEP's #10 : Logger l'erreur
                logger.warning(f"[ZEFIX] Erreur recherche par nom: {e}")
        elif results:
            ehraid = results[0].get("ehraid")
            if ehraid:
                return await self.get_company_by_ehraid(ehraid)
        return None

    async def get_publications(self, ehraid: int, limit: int = 10) -> List[Dict]:
        """Récupère les publications FOSC pour une entreprise"""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{ZEFIX_BASE}/firm/{ehraid}/shabPub.json",
                    headers=self._headers(),
                    auth=self.auth,
                )
                if resp.status_code == 200:
                    pubs = resp.json()
                    return pubs[:limit] if isinstance(pubs, list) else []
        except Exception as e:
            print(f"⚠️ Zefix publications error: {e}")
        return []

    async def get_full_company(self, uid: str) -> Optional[ZefixCompany]:
        """
        Récupère TOUT: détails + organes + publications.
        C'est la méthode principale pour le Smart Onboarding.
        """
        company = await self.get_company_by_uid(uid)
        if company and company.ehraid:
            pubs = await self.get_publications(company.ehraid)
            company.publications = pubs
        return company

    def _parse_company(self, data: Dict) -> ZefixCompany:
        """Parse la réponse Zefix en objet structuré"""
        organs = []
        for person in data.get("persons", []):
            organs.append(Organ(
                name=f"{person.get('firstName', '')} {person.get('lastName', '')}".strip() or person.get("name", ""),
                role=person.get("function", {}).get("fr", "") or person.get("function", {}).get("de", ""),
                function=person.get("role", ""),
                signature=person.get("authorization", {}).get("fr", "") or person.get("authorization", {}).get("de", ""),
                since=person.get("entryDate", ""),
                address=person.get("address", ""),
            ))

        # Organe de révision
        for auditor in data.get("auditors", []):
            organs.append(Organ(
                name=auditor.get("name", ""),
                role="Organe de révision",
                function="Réviseur",
                since=auditor.get("entryDate", ""),
                address=auditor.get("address", ""),
            ))

        capital_str = ""
        cap = data.get("capital")
        if cap:
            capital_str = f"{cap.get('amount', '')} {cap.get('currency', 'CHF')}"

        return ZefixCompany(
            name=data.get("name", ""),
            uid=data.get("uid", ""),
            ehraid=data.get("ehraid", 0),
            legal_seat=data.get("legalSeat", ""),
            canton=data.get("canton", {}).get("cantonAbbreviation", "") if isinstance(data.get("canton"), dict) else data.get("canton", ""),
            legal_form=data.get("legalForm", {}).get("fr", "") if isinstance(data.get("legalForm"), dict) else data.get("legalForm", ""),
            status=data.get("status", ""),
            purpose=data.get("purpose", {}).get("fr", "") if isinstance(data.get("purpose"), dict) else data.get("purpose", ""),
            capital=capital_str,
            capital_currency=cap.get("currency", "CHF") if cap else "CHF",
            rc_number=data.get("chNr", "") or data.get("registerOfficeId", ""),
            organs=organs,
            inscription_date=data.get("inscriptionDate", ""),
            last_mutation_date=data.get("lastMutationDate", ""),
            deletion_date=data.get("deletionDate", ""),
        )


# ══════════════════════════════════════════════════════════
# FOSC MONITORING SERVICE
# ══════════════════════════════════════════════════════════

class FOSCMonitor:
    """
    Surveillance des publications FOSC pour les clients.
    Vérifie quotidiennement les nouvelles publications via Zefix.

    Usage:
        monitor = FOSCMonitor(zefix_svc)
        alerts = await monitor.check_client(ehraid=123456, last_check="2026-01-01")
    """

    ALERT_KEYWORDS = {
        "siège": "address_change",
        "transfert": "address_change",
        "domicile": "address_change",
        "capital": "capital_change",
        "augmentation": "capital_change",
        "réduction": "capital_change",
        "organe": "organ_change",
        "administrateur": "organ_change",
        "gérant": "organ_change",
        "directeur": "organ_change",
        "réviseur": "organ_change",
        "révision": "organ_change",
        "faillite": "bankruptcy",
        "liquidation": "liquidation",
        "dissolution": "liquidation",
        "raison sociale": "name_change",
        "nouvelle raison": "name_change",
    }

    def __init__(self, zefix: ZefixService):
        self.zefix = zefix

    async def check_client(self, ehraid: int, last_check: str = "") -> List[Dict]:
        """
        Vérifie les nouvelles publications FOSC pour un client.
        Retourne les alertes détectées.
        """
        pubs = await self.zefix.get_publications(ehraid, limit=20)
        alerts = []

        for pub in pubs:
            pub_date = pub.get("publicationDate", "") or pub.get("date", "")
            if last_check and pub_date and pub_date <= last_check:
                continue

            # Classify
            message = json.dumps(pub, ensure_ascii=False).lower()
            alert_type = "other"
            for keyword, atype in self.ALERT_KEYWORDS.items():
                if keyword in message:
                    alert_type = atype
                    break

            alerts.append({
                "alert_type": alert_type,
                "title": pub.get("title", "") or pub.get("message", "")[:100],
                "summary": pub.get("message", "")[:500],
                "fosc_date": pub_date,
                "fosc_reference": pub.get("registrationOfficeJournalId", ""),
                "raw_data": pub,
            })

        return alerts

    async def check_all_clients(self, clients: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Vérifie tous les clients d'une fiduciaire.
        clients = [{"id": "...", "ehraid": 123, "last_check": "2026-01-01"}, ...]
        """
        results = {}
        for c in clients:
            ehraid = c.get("ehraid")
            if not ehraid:
                continue
            alerts = await self.check_client(ehraid, c.get("last_check", ""))
            if alerts:
                results[c["id"]] = alerts
        return results
