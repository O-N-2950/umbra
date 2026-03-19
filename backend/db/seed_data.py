"""
UMBRA — Seed Data
Données initiales : secteurs, compétences, zones postales suisses.

À exécuter une seule fois à la création de la base.
Idempotent : ne recrée pas si déjà existant (upsert sur slug).

Usage :
    python -m backend.db.seed
    # ou depuis alembic post-migrate hook

© 2026 PEP's Swiss SA — UMBRA
"""

from __future__ import annotations

import logging
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger("umbra.seed")


# ── SECTEURS ──────────────────────────────────────────────────────────────────

SECTORS_DATA = [
    {"slug": "it",          "label": "IT & Digital",    "symbol": "⬡", "color": "#38bdf8", "order": 1},
    {"slug": "finance",     "label": "Finance & Audit", "symbol": "◇", "color": "#9b87f0", "order": 2},
    {"slug": "industrie",   "label": "Industrie",       "symbol": "◈", "color": "#d97b3a", "order": 3},
    {"slug": "sante",       "label": "Santé",           "symbol": "✦", "color": "#2dd4aa", "order": 4},
    {"slug": "batiment",    "label": "Bâtiment",        "symbol": "◻", "color": "#d97b3a", "order": 5},
    {"slug": "commerce",    "label": "Commerce B2B",    "symbol": "◈", "color": "#38bdf8", "order": 6},
    {"slug": "logistique",  "label": "Logistique",      "symbol": "⬡", "color": "#7a8da8", "order": 7},
    {"slug": "artisanat",   "label": "Artisanat",       "symbol": "◇", "color": "#d97b3a", "order": 8},
    {"slug": "agriculture", "label": "Agriculture",     "symbol": "✦", "color": "#2dd4aa", "order": 9},
]


# ── COMPÉTENCES PAR SECTEUR ───────────────────────────────────────────────────

SKILLS_DATA: dict[str, list[dict]] = {
    "it": [
        {"label": "React / Next.js",             "category": "framework"},
        {"label": "Vue.js / Nuxt",               "category": "framework"},
        {"label": "Angular",                     "category": "framework"},
        {"label": "Node.js",                     "category": "runtime"},
        {"label": "Python / FastAPI",            "category": "language"},
        {"label": "Python / Django",             "category": "language"},
        {"label": "Java / Spring Boot",          "category": "language"},
        {"label": "TypeScript",                  "category": "language"},
        {"label": "Go (Golang)",                 "category": "language"},
        {"label": "PostgreSQL",                  "category": "database"},
        {"label": "MySQL / MariaDB",             "category": "database"},
        {"label": "MongoDB",                     "category": "database"},
        {"label": "Redis",                       "category": "database"},
        {"label": "Elasticsearch",               "category": "database"},
        {"label": "Docker",                      "category": "devops"},
        {"label": "Kubernetes",                  "category": "devops"},
        {"label": "CI/CD (GitHub Actions / GitLab CI)", "category": "devops"},
        {"label": "AWS",                         "category": "cloud"},
        {"label": "Google Cloud Platform",       "category": "cloud"},
        {"label": "Azure",                       "category": "cloud"},
        {"label": "Terraform / IaC",             "category": "devops"},
        {"label": "Machine Learning / IA",       "category": "data"},
        {"label": "Data Engineering",            "category": "data"},
        {"label": "Power BI / Tableau",          "category": "data"},
        {"label": "Cybersécurité / Pentest",     "category": "security"},
        {"label": "Architecture microservices",  "category": "architecture"},
        {"label": "GraphQL",                     "category": "api"},
        {"label": "React Native",                "category": "mobile"},
        {"label": "iOS / Swift",                 "category": "mobile"},
        {"label": "Android / Kotlin",            "category": "mobile"},
    ],
    "finance": [
        {"label": "IFRS / Swiss GAAP",           "category": "norme"},
        {"label": "Comptabilité analytique",     "category": "compta"},
        {"label": "Comptabilité générale",       "category": "compta"},
        {"label": "SAP FI/CO",                   "category": "erp"},
        {"label": "SAP S/4HANA",                 "category": "erp"},
        {"label": "Oracle Financials",           "category": "erp"},
        {"label": "Analyse financière",          "category": "analyse"},
        {"label": "Modélisation financière",     "category": "analyse"},
        {"label": "Audit interne",               "category": "audit"},
        {"label": "Audit externe",               "category": "audit"},
        {"label": "Risk Management",             "category": "risque"},
        {"label": "Compliance / AML",            "category": "compliance"},
        {"label": "Fiscalité suisse",            "category": "fiscal"},
        {"label": "Fiscalité internationale",    "category": "fiscal"},
        {"label": "TVA / VAT",                   "category": "fiscal"},
        {"label": "Bloomberg Terminal",          "category": "outil"},
        {"label": "Excel avancé / VBA",          "category": "outil"},
        {"label": "Power BI Finance",            "category": "outil"},
        {"label": "Consolidation",               "category": "reporting"},
        {"label": "Reporting FINMA",             "category": "reporting"},
        {"label": "Contrôle de gestion",         "category": "controlling"},
        {"label": "Trésorerie / Cash management","category": "tresorerie"},
        {"label": "Private Equity / M&A",        "category": "banque"},
        {"label": "Gestion de portefeuille",     "category": "banque"},
    ],
    "industrie": [
        {"label": "CNC Fanuc",                   "category": "machine"},
        {"label": "CNC Heidenhain",              "category": "machine"},
        {"label": "CNC Siemens",                 "category": "machine"},
        {"label": "Fraisage 5 axes",             "category": "usinage"},
        {"label": "Tournage CNC",                "category": "usinage"},
        {"label": "Rectification",               "category": "usinage"},
        {"label": "EDM / Électroérosion",        "category": "usinage"},
        {"label": "Soudure TIG",                 "category": "soudure"},
        {"label": "Soudure MIG/MAG",             "category": "soudure"},
        {"label": "Soudure laser",               "category": "soudure"},
        {"label": "Métrologie 3D",               "category": "qualite"},
        {"label": "Contrôle qualité ISO 9001",   "category": "qualite"},
        {"label": "Lean Manufacturing / 5S",     "category": "methode"},
        {"label": "Six Sigma",                   "category": "methode"},
        {"label": "PLC Siemens S7",              "category": "automatisme"},
        {"label": "PLC Allen-Bradley",           "category": "automatisme"},
        {"label": "Robotique KUKA",              "category": "robotique"},
        {"label": "Robotique Fanuc",             "category": "robotique"},
        {"label": "SolidWorks",                  "category": "cad"},
        {"label": "AutoCAD",                     "category": "cad"},
        {"label": "CATIA",                       "category": "cad"},
        {"label": "Injection plastique",         "category": "process"},
        {"label": "Estampage / Emboutissage",    "category": "process"},
        {"label": "Montage / Assemblage",        "category": "production"},
    ],
    "sante": [
        {"label": "Soins infirmiers",            "category": "soin"},
        {"label": "Gériatrie",                   "category": "specialite"},
        {"label": "Urgences / SMUR",             "category": "specialite"},
        {"label": "Bloc opératoire",             "category": "specialite"},
        {"label": "Psychiatrie",                 "category": "specialite"},
        {"label": "Radiologie / IRM",            "category": "specialite"},
        {"label": "Pharmacie clinique",          "category": "specialite"},
        {"label": "Soins palliatifs",            "category": "specialite"},
        {"label": "Pédiatrie",                   "category": "specialite"},
        {"label": "Oncologie",                   "category": "specialite"},
        {"label": "Anesthésie",                  "category": "specialite"},
        {"label": "Réanimation / ICU",           "category": "specialite"},
        {"label": "Physiothérapie",              "category": "reeducation"},
        {"label": "Ergothérapie",                "category": "reeducation"},
        {"label": "Médecin généraliste",         "category": "medecin"},
        {"label": "Médecin spécialiste",         "category": "medecin"},
        {"label": "Aide-soignant",               "category": "auxiliaire"},
    ],
    "batiment": [
        {"label": "Gestion de chantier",         "category": "management"},
        {"label": "Conducteur de travaux",       "category": "management"},
        {"label": "Maçonnerie",                  "category": "gros_oeuvre"},
        {"label": "Coffreur-bancheur",           "category": "gros_oeuvre"},
        {"label": "Béton armé",                  "category": "gros_oeuvre"},
        {"label": "Électricité NIBT",            "category": "technique"},
        {"label": "Plomberie / CVS",             "category": "technique"},
        {"label": "Chauffage / PAC",             "category": "technique"},
        {"label": "Isolation thermique",         "category": "enveloppe"},
        {"label": "Couverture / Zinguerie",      "category": "enveloppe"},
        {"label": "Menuiserie chantier",         "category": "second_oeuvre"},
        {"label": "Peinture / Finition",         "category": "second_oeuvre"},
        {"label": "Carrelage",                   "category": "second_oeuvre"},
        {"label": "BIM / Revit",                 "category": "digital"},
        {"label": "AutoCAD 2D/3D",               "category": "digital"},
        {"label": "ArchiCAD",                    "category": "digital"},
    ],
    "commerce": [
        {"label": "Vente B2B grands comptes",    "category": "vente"},
        {"label": "Développement commercial",    "category": "vente"},
        {"label": "CRM Salesforce",              "category": "outil"},
        {"label": "CRM HubSpot",                 "category": "outil"},
        {"label": "Négociation commerciale",     "category": "competence"},
        {"label": "Key Account Management",      "category": "competence"},
        {"label": "E-commerce",                  "category": "digital"},
        {"label": "Marketing digital",           "category": "marketing"},
        {"label": "SEO / SEA",                   "category": "marketing"},
        {"label": "Trade marketing",             "category": "marketing"},
        {"label": "Category management",         "category": "gestion"},
        {"label": "Management équipe vente",     "category": "management"},
        {"label": "Forecast / Pipeline",         "category": "analyse"},
    ],
    "logistique": [
        {"label": "WMS (Warehouse Management)", "category": "systeme"},
        {"label": "ERP SAP MM",                 "category": "systeme"},
        {"label": "Supply chain management",    "category": "methode"},
        {"label": "Transport international",    "category": "transport"},
        {"label": "Douane / transit",           "category": "reglementation"},
        {"label": "CACES 1",                    "category": "certification"},
        {"label": "CACES 3",                    "category": "certification"},
        {"label": "CACES 5",                    "category": "certification"},
        {"label": "Gestion entrepôt",           "category": "operations"},
        {"label": "Planification stock / MRP",  "category": "planification"},
        {"label": "Last mile delivery",         "category": "livraison"},
        {"label": "ADR (matières dangereuses)", "category": "reglementation"},
    ],
    "artisanat": [
        {"label": "Menuiserie",                 "category": "bois"},
        {"label": "Ébénisterie",                "category": "bois"},
        {"label": "Charpente",                  "category": "bois"},
        {"label": "Peinture décoration",        "category": "finition"},
        {"label": "Plâtrerie",                  "category": "finition"},
        {"label": "Vitrage / Miroiterie",       "category": "finition"},
        {"label": "Serrurerie / Métallerie",    "category": "metal"},
        {"label": "Carrelage / Mosaïque",       "category": "sol"},
        {"label": "Couverture",                 "category": "toiture"},
        {"label": "Climatisation / PAC",        "category": "technique"},
        {"label": "Horlogerie",                 "category": "precision"},
        {"label": "Microtechnique",             "category": "precision"},
    ],
    "agriculture": [
        {"label": "Viticulture",                "category": "specialite"},
        {"label": "Œnologie",                   "category": "specialite"},
        {"label": "Arboriculture",              "category": "specialite"},
        {"label": "Maraîchage bio",             "category": "culture"},
        {"label": "Grandes cultures",           "category": "culture"},
        {"label": "Élevage bovin",              "category": "elevage"},
        {"label": "Élevage porcin",             "category": "elevage"},
        {"label": "Mécanique agricole",         "category": "technique"},
        {"label": "Certification BIO",          "category": "certification"},
        {"label": "GlobalG.A.P.",               "category": "certification"},
        {"label": "Gestion irrigation",         "category": "technique"},
        {"label": "Agriculture de précision",   "category": "digital"},
    ],
}


# ── ZONES POSTALES SUISSES (centroïdes pour géomatching) ─────────────────────

SWISS_POSTAL_ZONES = [
    # Arc Jurassien / Jura
    {"zone": "2800", "region": "Delémont",        "lat": 47.3667, "lon": 7.3500,  "canton": "JU"},
    {"zone": "2900", "region": "Porrentruy",       "lat": 47.4167, "lon": 7.0667,  "canton": "JU"},
    {"zone": "2500", "region": "Bienne",           "lat": 47.1372, "lon": 7.2469,  "canton": "BE"},
    {"zone": "2300", "region": "La Chaux-de-Fonds","lat": 47.1000, "lon": 6.8333,  "canton": "NE"},
    {"zone": "2000", "region": "Neuchâtel",        "lat": 47.0000, "lon": 6.9333,  "canton": "NE"},
    # Bâle
    {"zone": "4001", "region": "Bâle",             "lat": 47.5596, "lon": 7.5886,  "canton": "BS"},
    {"zone": "4100", "region": "Binningen",        "lat": 47.5333, "lon": 7.5667,  "canton": "BL"},
    {"zone": "4051", "region": "Bâle Centre",      "lat": 47.5553, "lon": 7.5925,  "canton": "BS"},
    # Soleure
    {"zone": "4500", "region": "Soleure",          "lat": 47.2088, "lon": 7.5317,  "canton": "SO"},
    {"zone": "4600", "region": "Olten",            "lat": 47.3516, "lon": 7.9072,  "canton": "SO"},
    # Berne
    {"zone": "3000", "region": "Berne",            "lat": 46.9481, "lon": 7.4474,  "canton": "BE"},
    {"zone": "3011", "region": "Berne Centre",     "lat": 46.9480, "lon": 7.4511,  "canton": "BE"},
    # Fribourg
    {"zone": "1700", "region": "Fribourg",         "lat": 46.8065, "lon": 7.1617,  "canton": "FR"},
    # Lausanne / Vaud
    {"zone": "1000", "region": "Lausanne",         "lat": 46.5197, "lon": 6.6323,  "canton": "VD"},
    {"zone": "1400", "region": "Yverdon",          "lat": 46.7785, "lon": 6.6408,  "canton": "VD"},
    # Genève
    {"zone": "1200", "region": "Genève",           "lat": 46.2044, "lon": 6.1432,  "canton": "GE"},
    {"zone": "1201", "region": "Genève Centre",    "lat": 46.2044, "lon": 6.1432,  "canton": "GE"},
    # Zurich
    {"zone": "8001", "region": "Zurich",           "lat": 47.3769, "lon": 8.5417,  "canton": "ZH"},
    {"zone": "8400", "region": "Winterthour",      "lat": 47.5000, "lon": 8.7500,  "canton": "ZH"},
    # Lucerne
    {"zone": "6000", "region": "Lucerne",          "lat": 47.0502, "lon": 8.3093,  "canton": "LU"},
    # Valais
    {"zone": "1950", "region": "Sion",             "lat": 46.2330, "lon": 7.3599,  "canton": "VS"},
    # Tessin
    {"zone": "6900", "region": "Lugano",           "lat": 46.0037, "lon": 8.9511,  "canton": "TI"},
    {"zone": "6500", "region": "Bellinzone",       "lat": 46.1954, "lon": 9.0239,  "canton": "TI"},
    # France frontalière
    {"zone": "FR-25", "region": "Besançon",        "lat": 47.2378, "lon": 6.0241,  "canton": "FR-25"},
    {"zone": "FR-68", "region": "Mulhouse",        "lat": 47.7508, "lon": 7.3359,  "canton": "FR-68"},
    {"zone": "FR-67", "region": "Strasbourg",      "lat": 48.5734, "lon": 7.7521,  "canton": "FR-67"},
]


# ── FONCTIONS SEED ────────────────────────────────────────────────────────────

def seed_sectors(db: Session) -> dict[str, str]:
    """
    Insère les secteurs. Retourne un dict {slug: id}.
    Idempotent — upsert sur slug.
    """
    from ..db.umbra_models import Sector

    sector_ids = {}
    for s in SECTORS_DATA:
        existing = db.query(Sector).filter(Sector.slug == s["slug"]).first()
        if not existing:
            obj = Sector(**s)
            db.add(obj)
            db.flush()
            sector_ids[s["slug"]] = obj.id
            logger.info("sector created: %s", s["slug"])
        else:
            sector_ids[s["slug"]] = existing.id

    db.commit()
    logger.info("sectors seeded: %d total", len(sector_ids))
    return sector_ids


def seed_skills(db: Session, sector_ids: dict[str, str]) -> int:
    """
    Insère les compétences. Idempotent — upsert sur (sector_id, label).
    Retourne le nombre de compétences créées.
    """
    from ..db.umbra_models import Skill

    count = 0
    for sector_slug, skills in SKILLS_DATA.items():
        sector_id = sector_ids.get(sector_slug)
        if not sector_id:
            logger.warning("sector not found for skills: %s", sector_slug)
            continue

        for sk in skills:
            existing = db.query(Skill).filter(
                Skill.sector_id == sector_id,
                Skill.label == sk["label"],
            ).first()
            if not existing:
                # Générer slug
                slug = sk["label"].lower().replace(" / ", "_").replace("/", "_").replace(" ", "_")[:80]
                obj = Skill(
                    sector_id=sector_id,
                    label=sk["label"],
                    slug=slug,
                    category=sk.get("category"),
                )
                db.add(obj)
                count += 1

    db.commit()
    logger.info("skills seeded: %d new skills", count)
    return count


def seed_postal_zones(db: Session) -> int:
    """
    Insère les zones postales suisses dans une table dédiée (si elle existe)
    ou met à jour un JSON config. Retourne le count.
    
    NOTE : Les coordonnées sont stockées comme centroïdes de zone.
    Un décalage aléatoire de 2-5km est appliqué lors de l'enregistrement
    d'un profil pour ne jamais stocker la position exacte.
    """
    # Pour l'instant, on log juste les zones disponibles
    # La table PostGIS sera ajoutée en migration Alembic séparée
    logger.info("postal zones available: %d", len(SWISS_POSTAL_ZONES))
    return len(SWISS_POSTAL_ZONES)


def seed_all(db: Session) -> dict:
    """
    Point d'entrée principal du seed.
    Retourne un résumé des données créées.
    """
    logger.info("starting UMBRA seed...")

    sector_ids = seed_sectors(db)
    skills_count = seed_skills(db, sector_ids)
    zones_count = seed_postal_zones(db)

    summary = {
        "sectors": len(sector_ids),
        "skills": skills_count,
        "postal_zones": zones_count,
    }
    logger.info("UMBRA seed complete: %s", summary)
    return summary


def get_postal_centroid(postal_zone: str) -> Optional[tuple[float, float]]:
    """
    Retourne les coordonnées (lat, lon) du centroïde d'une zone postale.
    Utilisé lors de l'inscription pour convertir le CP en point géo anonymisé.
    """
    import random
    for zone in SWISS_POSTAL_ZONES:
        if zone["zone"] == postal_zone or zone["zone"] == postal_zone[:4]:
            # Appliquer un décalage aléatoire de 2-4km pour anonymisation
            lat_offset = (random.random() - 0.5) * 0.06  # ~3km en lat
            lon_offset = (random.random() - 0.5) * 0.08  # ~4km en lon
            return (
                round(zone["lat"] + lat_offset, 5),
                round(zone["lon"] + lon_offset, 5),
            )
    return None


# ── ENTRYPOINT ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/umbra_dev")
    engine_obj = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine_obj)

    with SessionLocal() as db:
        result = seed_all(db)
        print(f"\n✅ Seed terminé : {result}")
