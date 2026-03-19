"""
UMBRA — API Profiles
CRUD du profil anonyme + quiz culturel + compétences.

Endpoints :
  POST /profiles/           → crée le profil anonyme (onboarding)
  GET  /profiles/me         → profil courant complet
  PUT  /profiles/me         → mise à jour profil
  POST /profiles/me/culture → soumet le quiz culturel
  GET  /profiles/me/skills  → liste compétences disponibles pour le secteur
  POST /profiles/me/skills  → met à jour les compétences sélectionnées
  PUT  /profiles/me/mode    → change mode (shadow/active) ou company_mode

© 2026 PEP's Swiss SA — UMBRA
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger("umbra.profiles")
router = APIRouter(prefix="/profiles", tags=["profiles"])


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

class ProfileCreate(BaseModel):
    sector_slug:   str
    postal_code:   str              # jamais stocké tel quel — converti en zone+centroïde
    mobility_km:   int = 50
    transport_mode: str = "car"    # car / public / bike / remote
    salary_min:    int
    salary_max:    int
    notice_days:   int = 0
    notice_label:  str = "Immédiat"
    contract_types: list[str] = ["cdi"]
    work_rate_min: int = 100
    work_rate_max: int = 100
    mode:          str = "shadow"
    company_mode:  str = "discreet"
    enable_recommendations: bool = True
    employer_block_postal: Optional[str] = None   # CP de l'employeur à bloquer


class ProfileUpdate(BaseModel):
    sector_slug:   Optional[str] = None
    postal_code:   Optional[str] = None
    mobility_km:   Optional[int] = None
    transport_mode: Optional[str] = None
    salary_min:    Optional[int] = None
    salary_max:    Optional[int] = None
    notice_days:   Optional[int] = None
    notice_label:  Optional[str] = None
    contract_types: Optional[list[str]] = None
    work_rate_min: Optional[int] = None
    work_rate_max: Optional[int] = None


class ModeUpdate(BaseModel):
    mode:         Optional[str] = None   # shadow / active
    company_mode: Optional[str] = None  # discreet / public


class CultureQuizSubmit(BaseModel):
    """
    5 réponses du quiz culturel.
    keys = index question (0-4), values = code réponse.
    """
    answers: dict[int, str]   # {0: "auto", 1: "startup", 2: "agile", 3: "hybrid", 4: "mission"}


class SkillsUpdate(BaseModel):
    skill_ids: list[str]   # IDs des compétences sélectionnées
    levels:    Optional[dict[str, int]] = None   # {skill_id: level (1/2/3)}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _postal_to_zone_and_geo(postal_code: str) -> tuple[str, str, Optional[float], Optional[float]]:
    """
    Convertit un code postal en zone (4 chiffres), label région,
    et coordonnées anonymisées (centroïde + décalage aléatoire).
    """
    from .db.seed_data import get_postal_centroid, SWISS_POSTAL_ZONES

    zone = postal_code[:4]
    # Trouver la région
    region_label = "Suisse"
    for z in SWISS_POSTAL_ZONES:
        if z["zone"] == zone or z["zone"].startswith(zone[:2]):
            region_label = z["region"]
            break

    geo = get_postal_centroid(zone)
    lat, lon = (geo[0], geo[1]) if geo else (47.3769, 8.5417)
    return zone, region_label, lat, lon


def _compute_culture_vector(answers: dict[int, str]) -> dict:
    """
    Convertit les 5 réponses en vecteur 6D normalisé [0-1].
    
    Mapping réponse → dimensions :
    Q0 (autonomie): auto→1.0, semi→0.65, team→0.35, exec→0.1
    Q1 (env):       startup→agilité+, corp→structure+
    Q2 (erreur):    process→structure+, open→collaboration+
    Q3 (remote):    remote→1.0, hybrid→0.6, office→0.1, flex→0.5
    Q4 (rétention): mission→mission+, growth→croissance+, comp→stabilite+
    """
    dims = {
        "autonomie":     0.5,
        "structure":     0.5,
        "collaboration": 0.5,
        "remote":        0.5,
        "croissance":    0.5,
        "stabilite":     0.5,
    }

    # Q0 — style d'autonomie
    q0 = answers.get(0, "semi")
    if q0 == "auto":
        dims["autonomie"] = 0.95; dims["structure"] = 0.2
    elif q0 == "semi":
        dims["autonomie"] = 0.7;  dims["structure"] = 0.5
    elif q0 == "team":
        dims["autonomie"] = 0.4;  dims["collaboration"] = 0.85
    elif q0 == "exec":
        dims["autonomie"] = 0.15; dims["structure"] = 0.9

    # Q1 — environnement
    q1 = answers.get(1, "pme")
    if q1 == "startup":
        dims["autonomie"]  = min(1.0, dims["autonomie"] + 0.1)
        dims["croissance"] = 0.85
        dims["stabilite"]  = 0.2
    elif q1 == "pme":
        dims["collaboration"] = min(1.0, dims["collaboration"] + 0.1)
    elif q1 == "corp":
        dims["structure"] = min(1.0, dims["structure"] + 0.2)
        dims["stabilite"] = min(1.0, dims["stabilite"] + 0.2)
    elif q1 == "public":
        dims["stabilite"] = 0.9
        dims["croissance"] = 0.3

    # Q2 — gestion erreur
    q2 = answers.get(2, "agile")
    if q2 == "process":
        dims["structure"] = min(1.0, dims["structure"] + 0.15)
    elif q2 == "agile":
        dims["croissance"] = min(1.0, dims["croissance"] + 0.1)
    elif q2 == "open":
        dims["collaboration"] = min(1.0, dims["collaboration"] + 0.15)
    elif q2 == "stoic":
        dims["autonomie"] = min(1.0, dims["autonomie"] + 0.1)

    # Q3 — remote
    q3 = answers.get(3, "hybrid")
    remote_map = {"remote": 0.95, "hybrid": 0.6, "office": 0.1, "flex": 0.5}
    dims["remote"] = remote_map.get(q3, 0.5)

    # Q4 — rétention
    q4 = answers.get(4, "growth")
    if q4 == "mission":
        dims["croissance"] = min(1.0, dims["croissance"] + 0.1)
        dims["stabilite"]  = min(1.0, dims["stabilite"] + 0.05)
    elif q4 == "people":
        dims["collaboration"] = min(1.0, dims["collaboration"] + 0.15)
    elif q4 == "growth":
        dims["croissance"] = min(1.0, dims["croissance"] + 0.2)
    elif q4 == "comp":
        dims["stabilite"] = 0.85

    # Normaliser [0, 1]
    for k in dims:
        dims[k] = round(max(0.0, min(1.0, dims[k])), 4)

    return dims


def _dims_to_labels(dims: dict) -> tuple[str, str, str]:
    """Génère les labels lisibles depuis le vecteur."""
    styles = []
    if dims["autonomie"] > 0.7:    styles.append("Autonome")
    if dims["collaboration"] > 0.7: styles.append("Collaboratif")
    if dims["structure"] > 0.7:    styles.append("Structuré")

    envs = []
    if dims["croissance"] > 0.7 and dims["stabilite"] < 0.4: envs.append("Start-up")
    elif dims["stabilite"] > 0.7: envs.append("Grand groupe / Public")
    else: envs.append("PME")

    motivations = []
    if dims["croissance"] > 0.7:    motivations.append("Croissance")
    if dims["remote"] > 0.7:        motivations.append("Remote")
    if dims["collaboration"] > 0.7: motivations.append("Humain")
    if dims["stabilite"] > 0.7:     motivations.append("Sécurité")

    return (
        " · ".join(styles) or "Équilibré",
        " · ".join(envs) or "Flexible",
        " · ".join(motivations) or "Mission",
    )


def _serialize_profile(profile, trust_score=None) -> dict:
    """Sérialise un AnonymousProfile pour l'API (sans données sensibles)."""
    out = {
        "id":           profile.id,
        "display_id":   profile.display_id,
        "profile_type": profile.profile_type.value,
        "mode":         profile.mode.value,
        "company_mode": profile.company_mode.value if profile.company_mode else None,
        "sector_id":    profile.sector_id,
        "region_label": profile.region_label,
        "mobility_km":  profile.mobility_km,
        "transport_mode": profile.transport_mode.value if profile.transport_mode else "car",
        "salary_min":   profile.salary_min,
        "salary_max":   profile.salary_max,
        "notice_days":  profile.notice_days,
        "notice_label": profile.notice_label,
        "contract_types": profile.contract_types,
        "work_rate_min": profile.work_rate_min,
        "work_rate_max": profile.work_rate_max,
        "is_visible":   profile.is_visible,
        "skills": [
            {
                "skill_id": ps.skill_id,
                "label":    ps.skill.label if ps.skill else None,
                "level":    ps.level,
                "verified": ps.verified,
            }
            for ps in (profile.profile_skills or [])
        ],
        "culture": None,
        "trust": None,
    }
    if profile.culture_profile:
        cp = profile.culture_profile
        out["culture"] = {
            "completed":      cp.completed,
            "dims": {
                "autonomie":     cp.dim_autonomie,
                "structure":     cp.dim_structure,
                "collaboration": cp.dim_collaboration,
                "remote":        cp.dim_remote,
                "croissance":    cp.dim_croissance,
                "stabilite":     cp.dim_stabilite,
            },
            "work_style":  cp.work_style,
            "environment": cp.environment,
            "motivation":  cp.motivation,
        }
    if trust_score:
        out["trust"] = {
            "score":         trust_score.score,
            "grade":         trust_score.grade.value,
            "hire_rate_pct": trust_score.hire_rate_pct,
            "hires":         trust_score.hires_confirmed,
        }
    return out


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
def create_profile(
    req: ProfileCreate,
    account=Depends(lambda: None),   # override: get_current_account
    db: Session = Depends(lambda: None),
):
    """
    Crée le profil anonyme lors de l'onboarding.
    Un seul profil par compte.
    """
    from .db.umbra_models import (
        AnonymousProfile, Sector, ProfileMode, CompanyMode, TransportMode, AccountType
    )
    from .api.umbra_auth import get_current_account, get_db

    # Vérifier profil existant
    existing = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Profil déjà existant. Utilisez PUT /profiles/me.")

    # Résoudre le secteur
    sector = db.query(Sector).filter(Sector.slug == req.sector_slug).first()
    if not sector:
        raise HTTPException(status_code=400, detail=f"Secteur inconnu : {req.sector_slug}")

    # Géo anonymisée
    zone, region, lat, lon = _postal_to_zone_and_geo(req.postal_code)

    profile = AnonymousProfile(
        account_id=account.id,
        profile_type=AccountType(account.account_type.value),
        mode=ProfileMode(req.mode),
        company_mode=CompanyMode(req.company_mode),
        sector_id=sector.id,
        postal_zone=zone,
        region_label=region,
        mobility_km=req.mobility_km,
        transport_mode=TransportMode(req.transport_mode),
        geo_lat=lat,
        geo_lon=lon,
        salary_min=req.salary_min,
        salary_max=req.salary_max,
        notice_days=req.notice_days,
        notice_label=req.notice_label,
        contract_types=req.contract_types,
        work_rate_min=req.work_rate_min,
        work_rate_max=req.work_rate_max,
        is_visible=(req.mode == "active"),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    logger.info("profile created: %s (%s)", profile.display_id, account.account_type.value)
    return {"profile_id": profile.id, "display_id": profile.display_id}


@router.get("/me")
def get_my_profile(
    account=Depends(lambda: None),
    db: Session = Depends(lambda: None),
):
    from .db.umbra_models import AnonymousProfile, TrustScore
    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).options(
        # eager load relations
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé. Complétez l'onboarding.")
    trust = db.query(TrustScore).filter(TrustScore.account_id == account.id).first()
    return _serialize_profile(profile, trust)


@router.put("/me")
def update_profile(
    req: ProfileUpdate,
    account=Depends(lambda: None),
    db: Session = Depends(lambda: None),
):
    from .db.umbra_models import AnonymousProfile, Sector, TransportMode

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé.")

    if req.sector_slug:
        sector = db.query(Sector).filter(Sector.slug == req.sector_slug).first()
        if sector:
            profile.sector_id = sector.id

    if req.postal_code:
        zone, region, lat, lon = _postal_to_zone_and_geo(req.postal_code)
        profile.postal_zone  = zone
        profile.region_label = region
        profile.geo_lat      = lat
        profile.geo_lon      = lon

    for field in ("mobility_km", "salary_min", "salary_max", "notice_days",
                  "notice_label", "contract_types", "work_rate_min", "work_rate_max"):
        val = getattr(req, field)
        if val is not None:
            setattr(profile, field, val)

    if req.transport_mode:
        profile.transport_mode = TransportMode(req.transport_mode)

    profile.updated_at = datetime.utcnow()
    db.commit()
    return {"updated": True}


@router.put("/me/mode")
def update_mode(
    req: ModeUpdate,
    account=Depends(lambda: None),
    db: Session = Depends(lambda: None),
):
    """Change le mode veille/actif ou discreet/public."""
    from .db.umbra_models import AnonymousProfile, ProfileMode, CompanyMode

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé.")

    if req.mode:
        profile.mode = ProfileMode(req.mode)
        profile.is_visible = (req.mode == "active")

    if req.company_mode:
        profile.company_mode = CompanyMode(req.company_mode)

    db.commit()
    logger.info("mode updated: %s → %s", profile.display_id, req.mode or req.company_mode)
    return {"updated": True, "is_visible": profile.is_visible}


@router.post("/me/culture")
def submit_culture_quiz(
    req: CultureQuizSubmit,
    account=Depends(lambda: None),
    db: Session = Depends(lambda: None),
):
    """
    Soumet les réponses du quiz culturel.
    Calcule le vecteur 6D et le persiste.
    Peut être re-soumis (mise à jour).
    """
    from .db.umbra_models import AnonymousProfile, CultureProfile

    if len(req.answers) < 5:
        raise HTTPException(status_code=400, detail="5 réponses requises (indices 0-4).")

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé.")

    dims = _compute_culture_vector(req.answers)
    style, env, motivation = _dims_to_labels(dims)

    cp = db.query(CultureProfile).filter(CultureProfile.profile_id == profile.id).first()
    if not cp:
        cp = CultureProfile(profile_id=profile.id)
        db.add(cp)

    cp.quiz_answers      = req.answers
    cp.dim_autonomie     = dims["autonomie"]
    cp.dim_structure     = dims["structure"]
    cp.dim_collaboration = dims["collaboration"]
    cp.dim_remote        = dims["remote"]
    cp.dim_croissance    = dims["croissance"]
    cp.dim_stabilite     = dims["stabilite"]
    cp.work_style        = style
    cp.environment       = env
    cp.motivation        = motivation
    cp.completed         = True
    cp.completed_at      = datetime.utcnow()

    db.commit()
    logger.info("culture quiz completed: %s", profile.display_id)
    return {
        "completed": True,
        "dims":      dims,
        "labels": {
            "work_style":  style,
            "environment": env,
            "motivation":  motivation,
        },
    }


@router.get("/me/skills/available")
def get_available_skills(
    account=Depends(lambda: None),
    db: Session = Depends(lambda: None),
):
    """Retourne les compétences disponibles pour le secteur du profil."""
    from .db.umbra_models import AnonymousProfile, Skill

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if not profile or not profile.sector_id:
        raise HTTPException(status_code=400, detail="Profil ou secteur non défini.")

    skills = db.query(Skill).filter(
        Skill.sector_id == profile.sector_id,
        Skill.is_active == True,
    ).order_by(Skill.category, Skill.label).all()

    # Grouper par catégorie
    by_cat: dict[str, list] = {}
    for sk in skills:
        cat = sk.category or "autre"
        by_cat.setdefault(cat, []).append({
            "id":    sk.id,
            "label": sk.label,
            "slug":  sk.slug,
        })

    return {"sector_id": profile.sector_id, "by_category": by_cat, "total": len(skills)}


@router.post("/me/skills")
def update_skills(
    req: SkillsUpdate,
    account=Depends(lambda: None),
    db: Session = Depends(lambda: None),
):
    """
    Met à jour les compétences sélectionnées.
    Remplace l'ensemble existant (non-destructif pour verified=True).
    """
    from .db.umbra_models import AnonymousProfile, ProfileSkill, Skill

    if len(req.skill_ids) < 2:
        raise HTTPException(status_code=400, detail="Minimum 2 compétences requises.")

    profile = db.query(AnonymousProfile).filter(
        AnonymousProfile.account_id == account.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé.")

    # Vérifier que toutes les skills existent
    valid_skills = db.query(Skill).filter(Skill.id.in_(req.skill_ids)).all()
    valid_ids = {s.id for s in valid_skills}
    invalid = set(req.skill_ids) - valid_ids
    if invalid:
        raise HTTPException(status_code=400, detail=f"Compétences inconnues : {invalid}")

    # Supprimer les skills désélectionnées (sauf celles vérifiées)
    existing = {ps.skill_id: ps for ps in profile.profile_skills}
    for skill_id, ps in list(existing.items()):
        if skill_id not in valid_ids and not ps.verified:
            db.delete(ps)

    # Ajouter / mettre à jour
    for skill_id in req.skill_ids:
        level = (req.levels or {}).get(skill_id, 2)
        if skill_id in existing:
            existing[skill_id].level = level
        else:
            ps = ProfileSkill(
                profile_id=profile.id,
                skill_id=skill_id,
                level=level,
            )
            db.add(ps)

    db.commit()
    logger.info("skills updated: %s (%d skills)", profile.display_id, len(req.skill_ids))
    return {"updated": True, "skill_count": len(req.skill_ids)}
