"""
UMBRA — Matching Engine
Algorithme de matching multicritères entre profils candidats et entreprises.

Score composite pondéré [0–100] :
  compétences  40%  — Jaccard + niveaux + vérification terrain
  culture      20%  — similarité cosinus vecteurs 6D
  géographie   20%  — distance réelle / rayon max
  salaire      15%  — chevauchement fourchettes ±10%
  durabilité    5%  — tension marché × stabilité historique

Filtres disqualifiants appliqués AVANT le calcul :
  - Salary incompatible (0 chevauchement même ±10%)
  - Distance > max(mobility_a, mobility_b)
  - Protection employeur actif (IDE bloqué)
  - Trust score < 2.0 (accès restreint)

© 2026 PEP's Swiss SA — UMBRA
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("umbra.matching")

# ── POIDS ─────────────────────────────────────────────────────────────────────

WEIGHT_SKILLS     = 0.40
WEIGHT_CULTURE    = 0.20
WEIGHT_GEO        = 0.20
WEIGHT_SALARY     = 0.15
WEIGHT_DURABILITY = 0.05

# Bonus niveau compétence (level 1=débutant 2=autonome 3=expert)
SKILL_LEVEL_WEIGHT = {1: 0.50, 2: 0.75, 3: 1.00}
SKILL_VERIFIED_BONUS = 0.15  # +15% si compétence vérifiée en conditions réelles

# Seuil minimum sous lequel on ne crée pas de match
MIN_SCORE_THRESHOLD = 50.0

# Score minimum pour notifier un profil en mode SHADOW
SHADOW_NOTIFY_THRESHOLD = 85.0

# Tolérance salary fit (±10%)
SALARY_TOLERANCE = 0.10


# ── DATA CLASSES ──────────────────────────────────────────────────────────────

@dataclass
class SkillEntry:
    skill_id: str
    level: int = 2          # 1=débutant 2=autonome 3=expert
    verified: bool = False  # vérifiée après embauche confirmée


@dataclass
class CultureVector:
    """Vecteur culturel 6 dimensions [0.0–1.0] calculé depuis quiz."""
    autonomie:     float = 0.5
    structure:     float = 0.5
    collaboration: float = 0.5
    remote:        float = 0.5
    croissance:    float = 0.5
    stabilite:     float = 0.5

    def as_list(self) -> list[float]:
        return [
            self.autonomie, self.structure, self.collaboration,
            self.remote, self.croissance, self.stabilite,
        ]


@dataclass
class GeoPoint:
    lat: float
    lon: float
    mobility_km: int = 50


@dataclass
class SalaryRange:
    min_chf: int
    max_chf: int
    currency: str = "CHF"


@dataclass
class ProfileInput:
    """Profil anonyme prêt pour le matching — extrait de AnonymousProfile."""
    profile_id: str
    profile_type: str       # "candidate" | "company"
    sector_id: str
    skills: list[SkillEntry]
    culture: CultureVector
    geo: GeoPoint
    salary: SalaryRange
    notice_days: int = 0
    trust_score: float = 3.0
    trust_grade: str = "standard"
    employer_block_ids: list[str] = field(default_factory=list)  # IDE bloqués
    company_ide: Optional[str] = None   # IDE de l'entreprise (pour protection candidat)
    is_shadow: bool = False  # profil en mode veille passive
    hire_rate_pct: float = 50.0  # taux d'embauche historique (pour durabilité)
    market_tension_pct: float = 50.0  # tension marché du secteur


@dataclass
class MatchScore:
    """Résultat détaillé d'un calcul de matching."""
    profile_a_id: str
    profile_b_id: str

    # Score total et sous-scores [0–100]
    total:      float = 0.0
    skills:     float = 0.0
    culture:    float = 0.0
    geo:        float = 0.0
    salary:     float = 0.0
    durability: float = 0.0

    # Détails
    distance_km:        float = 0.0
    salary_compatible:  bool = False
    matched_skill_ids:  list[str] = field(default_factory=list)
    culture_similarity: float = 0.0
    market_intel:       Optional[str] = None
    market_tension_pct: float = 0.0

    # Flags
    disqualified:       bool = False
    disqualify_reason:  Optional[str] = None
    notify_shadow:      bool = False  # True si profil SHADOW doit être notifié


# ── FONCTIONS DE CALCUL ───────────────────────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance réelle entre deux points GPS (formule Haversine)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def score_skills(candidate: ProfileInput, company: ProfileInput) -> tuple[float, list[str]]:
    """
    Score compétences [0–100] via Jaccard pondéré par niveaux.
    
    Formule :
      jaccard = |intersection pondérée| / |union pondérée|
    
    Chaque compétence est pondérée par :
      - niveau (0.5 / 0.75 / 1.0)
      - bonus +15% si vérifiée en conditions réelles
    """
    if not candidate.skills or not company.skills:
        return 0.0, []

    c_map = {s.skill_id: s for s in candidate.skills}
    co_map = {s.skill_id: s for s in company.skills}

    # Skills communes
    common_ids = set(c_map.keys()) & set(co_map.keys())
    # Union totale
    all_ids = set(c_map.keys()) | set(co_map.keys())

    if not all_ids:
        return 0.0, []

    # Poids intersection : min des deux niveaux × bonus vérification
    intersection_w = sum(
        min(
            SKILL_LEVEL_WEIGHT[c_map[sid].level],
            SKILL_LEVEL_WEIGHT[co_map[sid].level],
        ) * (1 + SKILL_VERIFIED_BONUS if c_map[sid].verified else 1.0)
        for sid in common_ids
    )

    # Poids union : max des niveaux déclarés de chaque côté
    union_w = sum(
        max(
            SKILL_LEVEL_WEIGHT.get(c_map.get(sid, SkillEntry(sid)).level, 0.5),
            SKILL_LEVEL_WEIGHT.get(co_map.get(sid, SkillEntry(sid)).level, 0.5),
        )
        for sid in all_ids
    )

    jaccard = intersection_w / union_w if union_w > 0 else 0.0
    return round(jaccard * 100, 2), list(common_ids)


def score_culture(candidate: ProfileInput, company: ProfileInput) -> tuple[float, float]:
    """
    Score culture [0–100] via similarité cosinus entre vecteurs 6D.
    Retourne (score, similarity_raw [0–1]).
    """
    va = candidate.culture.as_list()
    vb = company.culture.as_list()

    dot = sum(a * b for a, b in zip(va, vb))
    mag_a = math.sqrt(sum(x ** 2 for x in va))
    mag_b = math.sqrt(sum(x ** 2 for x in vb))

    if mag_a == 0 or mag_b == 0:
        return 50.0, 0.5  # données manquantes → score neutre

    similarity = dot / (mag_a * mag_b)
    return round(similarity * 100, 2), round(similarity, 4)


def score_geo(candidate: ProfileInput, company: ProfileInput) -> tuple[float, float]:
    """
    Score géographique [0–100].
    distance_km calculée via Haversine.
    Score = max(0, 1 - distance / max_mobility) × 100
    Le rayon effectif est le max des deux mobilités déclarées.
    """
    dist = haversine_km(
        candidate.geo.lat, candidate.geo.lon,
        company.geo.lat, company.geo.lon,
    )
    max_mob = max(candidate.geo.mobility_km, company.geo.mobility_km)
    if max_mob == 0:
        return (100.0, 0.0) if dist < 1 else (0.0, dist)

    raw = max(0.0, 1.0 - (dist / max_mob))
    return round(raw * 100, 2), round(dist, 1)


def score_salary(candidate: ProfileInput, company: ProfileInput) -> tuple[float, bool]:
    """
    Score salaire [0–100] basé sur chevauchement des fourchettes ±10%.
    Si aucun chevauchement : retourne (0, False) → filtre disqualifiant.
    Si chevauchement parfait (plein recouvrement) : 100.
    """
    # Fourchettes avec tolérance
    c_min = candidate.salary.min_chf * (1 - SALARY_TOLERANCE)
    c_max = candidate.salary.max_chf * (1 + SALARY_TOLERANCE)
    co_min = company.salary.min_chf * (1 - SALARY_TOLERANCE)
    co_max = company.salary.max_chf * (1 + SALARY_TOLERANCE)

    # Chevauchement
    overlap_min = max(c_min, co_min)
    overlap_max = min(c_max, co_max)

    if overlap_max <= overlap_min:
        return 0.0, False  # incompatible

    overlap = overlap_max - overlap_min
    # Normaliser par la plus petite fourchette (représente l'alignement)
    smallest_range = min(c_max - c_min, co_max - co_min)
    if smallest_range == 0:
        return 100.0, True

    ratio = min(1.0, overlap / smallest_range)
    return round(ratio * 100, 2), True


def score_durability(
    candidate: ProfileInput,
    company: ProfileInput,
    skills_score: float,
    culture_score: float,
) -> float:
    """
    Score durabilité [0–100] — probabilité que le match tienne 18 mois.
    
    Facteurs :
    - Taux d'embauche historique de l'entreprise (signale sérieux)
    - Tension marché (pénurie = plus d'options = moins de stabilité)
    - Alignment skills × culture (mieux aligné = plus durable)
    """
    # Taux embauche entreprise (plus c'est élevé, plus l'entreprise est sérieuse)
    hire_factor = company.hire_rate_pct / 100.0

    # Tension marché : forte pénurie = candidat peut partir vite → moins durable
    tension_factor = 1.0 - (candidate.market_tension_pct / 200.0)  # pénalité max 50%

    # Qualité du match skills + culture (moyenne pondérée)
    match_quality = (skills_score * 0.6 + culture_score * 0.4) / 100.0

    raw = hire_factor * tension_factor * match_quality
    return round(min(100.0, raw * 100), 2)


def build_market_intel(tension_pct: float, sector_label: str, region: str) -> Optional[str]:
    """Génère le message d'intelligence marché contextuel."""
    if tension_pct >= 90:
        return f"Pénurie critique en {sector_label} sur {region}. Profil très recherché."
    elif tension_pct >= 75:
        return f"Forte tension en {sector_label} sur {region}. Marché favorable au candidat."
    elif tension_pct >= 50:
        return f"Marché actif en {sector_label}. Bonne adéquation offre/demande."
    return None


# ── MOTEUR PRINCIPAL ──────────────────────────────────────────────────────────

class MatchingEngine:
    """
    Moteur de matching UMBRA.
    
    Usage :
        engine = MatchingEngine()
        result = engine.compute(candidate_profile, company_profile)
        if not result.disqualified and result.total >= MIN_SCORE_THRESHOLD:
            # créer le match en base
    """

    def compute(self, a: ProfileInput, b: ProfileInput) -> MatchScore:
        """
        Calcule le score entre un candidat (a) et une entreprise (b).
        Toujours : a = CANDIDATE, b = COMPANY.
        """
        result = MatchScore(profile_a_id=a.profile_id, profile_b_id=b.profile_id)

        # ── FILTRES DISQUALIFIANTS ────────────────────────────────────────────

        # 1. Trust score trop bas
        if b.trust_score < 2.0:
            return self._disqualify(result, "trust_score_too_low")

        # 2. Protection employeur : IDE de l'entreprise bloqué par le candidat
        if b.company_ide and b.company_ide in a.employer_block_ids:
            return self._disqualify(result, "employer_blocked")

        # 3. Secteur incompatible
        if a.sector_id != b.sector_id:
            return self._disqualify(result, "sector_mismatch")

        # 4. Salary incompatible (filtre dur avant calcul complet)
        salary_score, salary_ok = score_salary(a, b)
        if not salary_ok:
            return self._disqualify(result, "salary_incompatible")

        # 5. Distance trop grande
        geo_score, dist_km = score_geo(a, b)
        if dist_km > max(a.geo.mobility_km, b.geo.mobility_km):
            return self._disqualify(result, "distance_exceeded")

        # ── CALCUL DES SOUS-SCORES ────────────────────────────────────────────

        sk_score, matched_ids = score_skills(a, b)
        cu_score, cu_sim      = score_culture(a, b)
        du_score              = score_durability(a, b, sk_score, cu_score)

        # ── SCORE COMPOSITE ───────────────────────────────────────────────────

        total = (
            sk_score * WEIGHT_SKILLS +
            cu_score * WEIGHT_CULTURE +
            geo_score * WEIGHT_GEO +
            salary_score * WEIGHT_SALARY +
            du_score * WEIGHT_DURABILITY
        )
        total = round(min(100.0, max(0.0, total)), 2)

        # ── INTELLIGENCE MARCHÉ ───────────────────────────────────────────────

        market_intel = build_market_intel(
            a.market_tension_pct, a.sector_id, a.geo.region_label if hasattr(a.geo, "region_label") else ""
        )

        # ── RÉSULTAT ──────────────────────────────────────────────────────────

        result.total             = total
        result.skills            = sk_score
        result.culture           = cu_score
        result.geo               = geo_score
        result.salary            = salary_score
        result.durability        = du_score
        result.distance_km       = dist_km
        result.salary_compatible = salary_ok
        result.matched_skill_ids = matched_ids
        result.culture_similarity = cu_sim
        result.market_intel      = market_intel
        result.market_tension_pct = a.market_tension_pct

        # Doit-on notifier un profil en mode SHADOW ?
        if a.is_shadow and total >= SHADOW_NOTIFY_THRESHOLD:
            result.notify_shadow = True

        logger.debug(
            "match computed",
            extra={
                "a": a.profile_id, "b": b.profile_id,
                "total": total, "skills": sk_score,
                "culture": cu_score, "geo": geo_score,
                "salary": salary_score, "dist_km": dist_km,
            }
        )
        return result

    def batch_compute(
        self,
        candidate: ProfileInput,
        companies: list[ProfileInput],
    ) -> list[MatchScore]:
        """
        Calcule les scores pour un candidat contre N entreprises.
        Retourne uniquement les matchs valides, triés par score décroissant.
        """
        results = []
        for company in companies:
            r = self.compute(candidate, company)
            if not r.disqualified and r.total >= MIN_SCORE_THRESHOLD:
                results.append(r)
        results.sort(key=lambda x: x.total, reverse=True)
        return results

    @staticmethod
    def _disqualify(result: MatchScore, reason: str) -> MatchScore:
        result.disqualified = True
        result.disqualify_reason = reason
        logger.debug("match disqualified: %s (%s vs %s)", reason, result.profile_a_id, result.profile_b_id)
        return result


# ── INSTANCE SINGLETON ────────────────────────────────────────────────────────

engine = MatchingEngine()


# ── UTILITAIRES API ───────────────────────────────────────────────────────────

def _merge_block_list(account) -> list[str]:
    """
    Construit la liste effective des IDE bloqués pour un candidat :
    la block-list explicite + l'employeur ACTUEL déclaré.

    Garantie anti-désanonymisation : même si le candidat oublie d'ajouter son patron
    à sa liste, son employeur actuel est exclu d'office de tous ses matchs. Un employeur
    ne peut donc PAS publier un faux poste pour identifier ses propres salariés en veille.
    """
    blocked = list(account.employer_block_list or [])
    current = getattr(account, "current_employer_ide", None)
    if current and current not in blocked:
        blocked.append(current)
    return blocked


def profile_to_input(profile, account, trust_score_obj, market_tension: float = 50.0) -> ProfileInput:
    """
    Convertit un AnonymousProfile SQLAlchemy en ProfileInput pour le moteur.
    À appeler dans les services API.
    """
    return ProfileInput(
        profile_id=profile.id,
        profile_type=profile.profile_type.value,
        sector_id=profile.sector_id or "",
        skills=[
            SkillEntry(
                skill_id=ps.skill_id,
                level=ps.level or 2,
                verified=ps.verified or False,
            )
            for ps in (profile.profile_skills or [])
        ],
        culture=CultureVector(
            autonomie=profile.culture_profile.dim_autonomie if profile.culture_profile else 0.5,
            structure=profile.culture_profile.dim_structure if profile.culture_profile else 0.5,
            collaboration=profile.culture_profile.dim_collaboration if profile.culture_profile else 0.5,
            remote=profile.culture_profile.dim_remote if profile.culture_profile else 0.5,
            croissance=profile.culture_profile.dim_croissance if profile.culture_profile else 0.5,
            stabilite=profile.culture_profile.dim_stabilite if profile.culture_profile else 0.5,
        ),
        geo=GeoPoint(
            lat=profile.geo_lat or 47.3769,   # défaut : Berne
            lon=profile.geo_lon or 8.5417,
            mobility_km=profile.mobility_km or 50,
        ),
        salary=SalaryRange(
            min_chf=profile.salary_min or 60000,
            max_chf=profile.salary_max or 120000,
            currency=profile.salary_currency or "CHF",
        ),
        notice_days=profile.notice_days or 0,
        trust_score=trust_score_obj.score if trust_score_obj else 3.0,
        trust_grade=trust_score_obj.grade.value if trust_score_obj else "standard",
        employer_block_ids=_merge_block_list(account),
        company_ide=account.ide_number,
        is_shadow=(profile.mode.value == "shadow"),
        hire_rate_pct=trust_score_obj.hire_rate_pct if trust_score_obj else 50.0,
        market_tension_pct=market_tension,
    )
