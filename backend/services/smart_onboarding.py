"""
MATCHO — Smart Onboarding Service
Orchestre toutes les sources pour un onboarding magique.

1. UID Register → IDE, adresse, forme juridique
2. OpenIBAN → Validation IBAN, banque, BIC
3. Gemini Flash → Analyse but social, vérification adresse, suggestions

© 2026 PEP's Swiss SA
"""

import re
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from datetime import datetime
import httpx

logger = logging.getLogger("umbra.onboarding")

from .uid_register import UIDRegisterService, CompanyResult


# ══════════════════════════════════════════════════════════
# IBAN VALIDATION SERVICE
# ══════════════════════════════════════════════════════════

@dataclass
class IBANResult:
    iban: str
    iban_formatted: str
    valid: bool
    bank_name: str = ""
    bic: str = ""
    bank_city: str = ""
    bank_zip: str = ""
    country: str = ""
    error: str = ""

    def to_dict(self):
        return asdict(self)


class IBANService:
    """Validation IBAN via OpenIBAN (gratuit, sans clé)"""

    OPENIBAN_URL = "https://openiban.com/validate"

    @staticmethod
    def format_iban(raw: str) -> str:
        clean = re.sub(r"[^A-Z0-9]", "", raw.upper())
        return " ".join([clean[i:i+4] for i in range(0, len(clean), 4)])

    @staticmethod
    def validate_structure(iban: str) -> Optional[str]:
        clean = re.sub(r"[^A-Z0-9]", "", iban.upper())
        if len(clean) < 5:
            return "IBAN trop court"
        country = clean[:2]
        if country == "CH" and len(clean) != 21:
            return f"IBAN suisse doit faire 21 caractères (reçu: {len(clean)})"
        if country == "LI" and len(clean) != 21:
            return f"IBAN liechtensteinois doit faire 21 caractères (reçu: {len(clean)})"
        rearranged = clean[4:] + clean[:4]
        numeric = ""
        for c in rearranged:
            if c.isdigit():
                numeric += c
            else:
                numeric += str(ord(c) - 55)
        if int(numeric) % 97 != 1:
            return "Checksum IBAN invalide"
        return None

    async def validate(self, iban: str) -> IBANResult:
        clean = re.sub(r"[^A-Z0-9]", "", iban.upper())
        formatted = self.format_iban(clean)
        error = self.validate_structure(clean)
        if error:
            return IBANResult(iban=clean, iban_formatted=formatted, valid=False, error=error)
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    self.OPENIBAN_URL,
                    params={"iban": clean, "getBIC": "true", "validateBankCode": "true"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    bank = data.get("bankData", {})
                    return IBANResult(
                        iban=clean, iban_formatted=formatted,
                        valid=data.get("valid", False),
                        bank_name=bank.get("name", ""),
                        bic=bank.get("bic", ""),
                        bank_city=bank.get("city", ""),
                        bank_zip=bank.get("zip", ""),
                        country=clean[:2],
                    )
        except Exception as e:
            logger.warning(f"[IBAN] Erreur validation async OpenIBAN: {e}")
        return IBANResult(iban=clean, iban_formatted=formatted, valid=True, country=clean[:2])

    def validate_sync(self, iban: str) -> IBANResult:
        clean = re.sub(r"[^A-Z0-9]", "", iban.upper())
        formatted = self.format_iban(clean)
        error = self.validate_structure(clean)
        if error:
            return IBANResult(iban=clean, iban_formatted=formatted, valid=False, error=error)
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(self.OPENIBAN_URL, params={"iban": clean, "getBIC": "true", "validateBankCode": "true"})
                if resp.status_code == 200:
                    data = resp.json()
                    bank = data.get("bankData", {})
                    return IBANResult(iban=clean, iban_formatted=formatted, valid=data.get("valid", False),
                        bank_name=bank.get("name", ""), bic=bank.get("bic", ""),
                        bank_city=bank.get("city", ""), bank_zip=bank.get("zip", ""), country=clean[:2])
        except Exception as e:
            logger.warning(f"[IBAN] Erreur validation sync OpenIBAN: {e}")
        return IBANResult(iban=clean, iban_formatted=formatted, valid=True, country=clean[:2])


# ══════════════════════════════════════════════════════════
# GEMINI FLASH ANALYSIS
# ══════════════════════════════════════════════════════════

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

ADDRESS_CHECK_PROMPT = """Tu es un assistant fiduciaire suisse. Compare ces deux adresses et réponds en JSON strict.

ADRESSE SAISIE PAR LE CLIENT:
{client_address}

ADRESSE OFFICIELLE DU REGISTRE DU COMMERCE:
{official_address}

Réponds UNIQUEMENT avec ce JSON (pas de markdown, pas de commentaire):
{{"match": true, "confidence": 95, "differences": [], "suggestion": "Les adresses correspondent.", "corrected_address": null}}
"""

PURPOSE_ANALYSIS_PROMPT = """Tu es un expert comptable fiduciaire en Suisse. Analyse ce but social extrait du registre du commerce.

SOCIÉTÉ: {company_name}
FORME JURIDIQUE: {legal_form}
CAPITAL: {capital}
BUT SOCIAL: {purpose}

Réponds UNIQUEMENT avec ce JSON (pas de markdown):
{{"sector": "...", "noga_code": "XX.XXX", "noga_description": "...", "activity_type": "commerce|services|industrie|immobilier|holding|finance|restauration|construction|santé|tech|autre", "chart_of_accounts": {{"template": "PME_Services", "specific_accounts": [{{"number": "XXXX", "name": "...", "reason": "..."}}]}}, "vat_status": {{"likely_registered": true, "reason": "...", "vat_method": "effective|taux_forfaitaire|exonéré"}}, "audit_requirement": {{"type": "ordinaire|restreinte|opting_out", "reason": "..."}}, "regulatory": ["..."], "risks": ["..."], "recommendations": ["..."]}}"""

COMPLETENESS_PROMPT = """Tu es un assistant fiduciaire. Évalue la complétude de ce dossier client pour un onboarding en Suisse.

DONNÉES: {data_json}

Réponds UNIQUEMENT en JSON:
{{"score": 75, "missing_critical": ["..."], "missing_optional": ["..."], "next_steps": ["..."], "ready_for_mandate": false}}"""


class GeminiService:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _call(self, prompt: str) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{GEMINI_API_URL}?key={self.api_key}",
                    json={"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048}},
                )
                if resp.status_code == 200:
                    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    text = re.sub(r"```json\s*", "", text)
                    text = re.sub(r"```\s*", "", text)
                    return json.loads(text.strip())
        except Exception as e:
            print(f"⚠️ Gemini error: {e}")
        return None

    async def check_address(self, client_address: str, official_address: str) -> Optional[dict]:
        return await self._call(ADDRESS_CHECK_PROMPT.format(client_address=client_address, official_address=official_address))

    async def analyze_purpose(self, company_name: str, legal_form: str, capital: str, purpose: str) -> Optional[dict]:
        return await self._call(PURPOSE_ANALYSIS_PROMPT.format(company_name=company_name, legal_form=legal_form, capital=capital, purpose=purpose))

    async def check_completeness(self, data: dict) -> Optional[dict]:
        return await self._call(COMPLETENESS_PROMPT.format(data_json=json.dumps(data, ensure_ascii=False, indent=2)))


# ══════════════════════════════════════════════════════════
# ORCHESTRATEUR
# ══════════════════════════════════════════════════════════

@dataclass
class OnboardingResult:
    company: Optional[Dict] = None
    company_alternatives: List[Dict] = field(default_factory=list)
    iban_results: List[Dict] = field(default_factory=list)
    address_check: Optional[Dict] = None
    purpose_analysis: Optional[Dict] = None
    completeness: Optional[Dict] = None
    timestamp: str = ""
    duration_ms: int = 0
    sources_used: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "company": self.company,
            "company_alternatives": self.company_alternatives,
            "iban_results": self.iban_results,
            "ai_analysis": {
                "address_check": self.address_check,
                "purpose_analysis": self.purpose_analysis,
                "completeness": self.completeness,
            },
            "meta": {"timestamp": self.timestamp, "duration_ms": self.duration_ms, "sources_used": self.sources_used},
        }


class SmartOnboardingService:
    def __init__(self, gemini_api_key: str = ""):
        self.uid_service = UIDRegisterService()
        self.iban_service = IBANService()
        self.gemini = GeminiService(gemini_api_key) if gemini_api_key else None

    async def onboard(self, company_name: str, client_address: str = "",
                      ibans: List[str] = None, purpose: str = "") -> OnboardingResult:
        import time
        start = time.time()
        result = OnboardingResult(timestamp=datetime.utcnow().isoformat())
        sources = []

        # Step 1: Company lookup
        companies = await self.uid_service.search_by_name(company_name, max_results=5)
        sources.append("UID Register (OFS)")
        if companies:
            best = companies[0]
            result.company = best.to_dict()
            result.company_alternatives = [c.to_dict() for c in companies[1:]]
            # Step 2: Address check
            if client_address and self.gemini:
                official = best.full_address
                result.address_check = await self.gemini.check_address(client_address, official)
                sources.append("Gemini Flash (adresse)")
            # Step 3: Purpose analysis
            if purpose and self.gemini:
                result.purpose_analysis = await self.gemini.analyze_purpose(best.name, best.legal_form, "N/A", purpose)
                sources.append("Gemini Flash (but social)")

        # Step 4: IBAN validation
        if ibans:
            for iban in ibans:
                r = await self.iban_service.validate(iban)
                result.iban_results.append(r.to_dict())
            sources.append("OpenIBAN")

        # Step 5: Completeness
        if self.gemini:
            result.completeness = await self.gemini.check_completeness({
                "company_name": company_name,
                "ide": result.company.get("ide") if result.company else None,
                "address": client_address,
                "address_verified": result.address_check.get("match") if result.address_check else None,
                "legal_form": result.company.get("legal_form") if result.company else None,
                "ibans_count": len(result.iban_results),
                "ibans_valid": all(r.get("valid") for r in result.iban_results) if result.iban_results else False,
                "purpose_analyzed": result.purpose_analysis is not None,
            })
            sources.append("Gemini Flash (complétude)")

        result.sources_used = sources
        result.duration_ms = int((time.time() - start) * 1000)
        return result


# ══════════════════════════════════════════════════════════
# FASTAPI ROUTES
# ══════════════════════════════════════════════════════════

def create_onboarding_routes(gemini_api_key: str = ""):
    from fastapi import APIRouter, Query, Body
    from pydantic import BaseModel

    router = APIRouter(tags=["Smart Onboarding"])
    svc = SmartOnboardingService(gemini_api_key)

    class OnboardingRequest(BaseModel):
        company_name: str
        client_address: str = ""
        ibans: List[str] = []
        purpose: str = ""

    class IBANRequest(BaseModel):
        iban: str

    @router.post("/full")
    async def full_onboarding(req: OnboardingRequest):
        result = await svc.onboard(req.company_name, req.client_address, req.ibans, req.purpose)
        return result.to_dict()

    @router.get("/search")
    async def search_company(name: str = Query(..., min_length=2)):
        companies = await svc.uid_service.search_by_name(name, max_results=5)
        return {"query": name, "count": len(companies), "results": [c.to_dict() for c in companies]}

    @router.post("/validate-iban")
    async def validate_iban(req: IBANRequest):
        return (await svc.iban_service.validate(req.iban)).to_dict()

    return router
