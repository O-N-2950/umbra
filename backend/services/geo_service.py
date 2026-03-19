"""
UMBRA — Geo Service
Calcul de distances, validation zones postales suisses, anonymisation géographique.

Responsabilités :
  - Convertir un code postal → centroïde anonymisé (décalage 2-5km)
  - Calculer la distance réelle entre deux points (Haversine / PostGIS)
  - Valider qu'un code postal appartient à la zone UMBRA (CH + frontaliers)
  - Enrichir un profil avec sa région/canton

En prod : requêtes PostGIS via ST_Distance pour des distances exactes.
En dev  : Haversine pur Python (fallback).

© 2026 PEP's Swiss SA — UMBRA
"""

from __future__ import annotations

import math
import random
import logging
from typing import Optional

logger = logging.getLogger("umbra.geo")

# Décalage aléatoire appliqué au centroïde de zone postale
# Pour ne JAMAIS stocker la position exacte d'un profil
GEO_JITTER_KM  = 3.0    # rayon max du décalage
GEO_JITTER_DEG = GEO_JITTER_KM / 111.0  # 1° lat ≈ 111km


# ── HAVERSINE ─────────────────────────────────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance réelle entre deux coordonnées GPS (formule Haversine)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── ZONES POSTALES ────────────────────────────────────────────────────────────

# Base de référence : centroïdes par zone (4 premiers chiffres du NPA)
# Source : Office fédéral de la topographie swisstopo (centroïdes approximatifs)
POSTAL_ZONES: dict[str, dict] = {
    # Jura
    "2800": {"region": "Delémont",          "canton": "JU", "lat": 47.3667, "lon": 7.3500},
    "2900": {"region": "Porrentruy",        "canton": "JU", "lat": 47.4167, "lon": 7.0667},
    "2350": {"region": "Saignelégier",      "canton": "JU", "lat": 47.2558, "lon": 7.0008},
    # Bienne / Seeland
    "2500": {"region": "Bienne",            "canton": "BE", "lat": 47.1372, "lon": 7.2469},
    "2503": {"region": "Bienne Est",        "canton": "BE", "lat": 47.1372, "lon": 7.2600},
    # Neuchâtel
    "2000": {"region": "Neuchâtel",         "canton": "NE", "lat": 47.0000, "lon": 6.9333},
    "2300": {"region": "La Chaux-de-Fonds", "canton": "NE", "lat": 47.1000, "lon": 6.8333},
    "2400": {"region": "Le Locle",          "canton": "NE", "lat": 47.0574, "lon": 6.7521},
    # Bâle-Ville
    "4001": {"region": "Bâle",              "canton": "BS", "lat": 47.5596, "lon": 7.5886},
    "4051": {"region": "Bâle Centre",       "canton": "BS", "lat": 47.5553, "lon": 7.5925},
    "4052": {"region": "Bâle Sud",          "canton": "BS", "lat": 47.5400, "lon": 7.5900},
    # Bâle-Campagne
    "4100": {"region": "Binningen",         "canton": "BL", "lat": 47.5333, "lon": 7.5667},
    "4102": {"region": "Binningen",         "canton": "BL", "lat": 47.5333, "lon": 7.5667},
    "4133": {"region": "Pratteln",          "canton": "BL", "lat": 47.5167, "lon": 7.6833},
    "4310": {"region": "Rheinfelden",       "canton": "AG", "lat": 47.5549, "lon": 7.7957},
    # Soleure
    "4500": {"region": "Soleure",           "canton": "SO", "lat": 47.2088, "lon": 7.5317},
    "4600": {"region": "Olten",             "canton": "SO", "lat": 47.3516, "lon": 7.9072},
    "4900": {"region": "Langenthal",        "canton": "BE", "lat": 47.2153, "lon": 7.7942},
    # Berne
    "3000": {"region": "Berne",             "canton": "BE", "lat": 46.9481, "lon": 7.4474},
    "3006": {"region": "Berne Est",         "canton": "BE", "lat": 46.9481, "lon": 7.4700},
    "3011": {"region": "Berne Centre",      "canton": "BE", "lat": 46.9480, "lon": 7.4511},
    "3600": {"region": "Thoune",            "canton": "BE", "lat": 46.7577, "lon": 7.6219},
    # Fribourg
    "1700": {"region": "Fribourg",          "canton": "FR", "lat": 46.8065, "lon": 7.1617},
    "1630": {"region": "Bulle",             "canton": "FR", "lat": 46.6166, "lon": 7.0574},
    # Vaud
    "1000": {"region": "Lausanne",          "canton": "VD", "lat": 46.5197, "lon": 6.6323},
    "1003": {"region": "Lausanne Centre",   "canton": "VD", "lat": 46.5197, "lon": 6.6350},
    "1200": {"region": "Genève",            "canton": "GE", "lat": 46.2044, "lon": 6.1432},
    "1400": {"region": "Yverdon",           "canton": "VD", "lat": 46.7785, "lon": 6.6408},
    "1800": {"region": "Vevey",             "canton": "VD", "lat": 46.4631, "lon": 6.8426},
    "1110": {"region": "Morges",            "canton": "VD", "lat": 46.5122, "lon": 6.4994},
    # Genève
    "1201": {"region": "Genève Centre",     "canton": "GE", "lat": 46.2044, "lon": 6.1432},
    "1227": {"region": "Carouge",           "canton": "GE", "lat": 46.1775, "lon": 6.1405},
    "1228": {"region": "Plan-les-Ouates",   "canton": "GE", "lat": 46.1631, "lon": 6.0822},
    # Zurich
    "8001": {"region": "Zurich",            "canton": "ZH", "lat": 47.3769, "lon": 8.5417},
    "8005": {"region": "Zurich Ouest",      "canton": "ZH", "lat": 47.3840, "lon": 8.5222},
    "8400": {"region": "Winterthour",       "canton": "ZH", "lat": 47.5000, "lon": 8.7500},
    "8600": {"region": "Dübendorf",         "canton": "ZH", "lat": 47.3952, "lon": 8.6209},
    # Argovie
    "5000": {"region": "Aarau",             "canton": "AG", "lat": 47.3924, "lon": 8.0436},
    "5400": {"region": "Baden",             "canton": "AG", "lat": 47.4742, "lon": 8.3074},
    # Lucerne
    "6000": {"region": "Lucerne",           "canton": "LU", "lat": 47.0502, "lon": 8.3093},
    "6003": {"region": "Lucerne Centre",    "canton": "LU", "lat": 47.0502, "lon": 8.3150},
    # Valais
    "1950": {"region": "Sion",              "canton": "VS", "lat": 46.2330, "lon": 7.3599},
    "3900": {"region": "Brigue",            "canton": "VS", "lat": 46.3143, "lon": 7.9882},
    # Tessin
    "6900": {"region": "Lugano",            "canton": "TI", "lat": 46.0037, "lon": 8.9511},
    "6500": {"region": "Bellinzone",        "canton": "TI", "lat": 46.1954, "lon": 9.0239},
    "6600": {"region": "Locarno",           "canton": "TI", "lat": 46.1686, "lon": 8.7971},
    # Graubünden
    "7000": {"region": "Coire",             "canton": "GR", "lat": 46.8508, "lon": 9.5329},
    # Thurgovie
    "8500": {"region": "Frauenfeld",        "canton": "TG", "lat": 47.5574, "lon": 8.8989},
    # Saint-Gall
    "9000": {"region": "Saint-Gall",        "canton": "SG", "lat": 47.4245, "lon": 9.3767},
    # France frontalière (codes départements)
    "FR25": {"region": "Besançon",          "canton": "FR-25", "lat": 47.2378, "lon": 6.0241},
    "FR68": {"region": "Mulhouse",          "canton": "FR-68", "lat": 47.7508, "lon": 7.3359},
    "FR67": {"region": "Strasbourg",        "canton": "FR-67", "lat": 48.5734, "lon": 7.7521},
    "FR74": {"region": "Annecy",            "canton": "FR-74", "lat": 45.8992, "lon": 6.1294},
    "FR01": {"region": "Oyonnax / Pays de Gex", "canton": "FR-01", "lat": 46.2561, "lon": 5.6554},
}


# ── FONCTIONS PRINCIPALES ─────────────────────────────────────────────────────

def resolve_postal_code(postal_code: str) -> Optional[dict]:
    """
    Résout un code postal en zone, région, canton et centroïde anonymisé.
    Retourne None si code inconnu.
    
    L'anonymisation applique un décalage aléatoire au centroïde pour
    ne JAMAIS stocker la position exacte du profil.
    """
    # Nettoyage
    code = postal_code.strip().upper().replace(" ", "").replace("-", "")

    # Tentative exacte (4 chiffres)
    zone = code[:4]
    data = POSTAL_ZONES.get(zone)

    # Fallback : chercher par préfixe 3 chiffres
    if not data:
        zone3 = code[:3]
        for key, val in POSTAL_ZONES.items():
            if key.startswith(zone3):
                data = val
                zone = key
                break

    if not data:
        logger.warning("postal code not found: %s", postal_code)
        return None

    # Décalage aléatoire pour anonymisation
    angle  = random.uniform(0, 2 * math.pi)
    dist   = random.uniform(1.0, GEO_JITTER_KM)
    d_lat  = (dist / 111.0) * math.cos(angle)
    d_lon  = (dist / (111.0 * math.cos(math.radians(data["lat"])))) * math.sin(angle)

    return {
        "zone":     zone,
        "region":   data["region"],
        "canton":   data["canton"],
        "lat":      round(data["lat"] + d_lat, 5),
        "lon":      round(data["lon"] + d_lon, 5),
        "centroid_lat": data["lat"],
        "centroid_lon": data["lon"],
    }


def distance_between_profiles(
    lat_a: float, lon_a: float,
    lat_b: float, lon_b: float,
) -> float:
    """Distance réelle entre deux profils en km (Haversine)."""
    return round(haversine_km(lat_a, lon_a, lat_b, lon_b), 1)


def is_in_range(
    lat_a: float, lon_a: float, mobility_a: int,
    lat_b: float, lon_b: float, mobility_b: int,
) -> tuple[bool, float]:
    """
    Vérifie si deux profils sont à portée l'un de l'autre.
    Retourne (dans_rayon, distance_km).
    Le rayon effectif est le max des deux mobilités déclarées.
    """
    dist = distance_between_profiles(lat_a, lon_a, lat_b, lon_b)
    max_mob = max(mobility_a, mobility_b)
    return dist <= max_mob, dist


def geo_score(distance_km: float, max_mobility_km: int) -> float:
    """
    Score géographique [0.0–1.0].
    0km = 1.0, distance = max_mobility = 0.0, au-delà = 0.0
    """
    if max_mobility_km <= 0:
        return 1.0 if distance_km < 1 else 0.0
    return round(max(0.0, 1.0 - (distance_km / max_mobility_km)), 4)


def get_regions_near(
    lat: float, lon: float, radius_km: float, limit: int = 10
) -> list[dict]:
    """
    Retourne les zones postales dans un rayon donné.
    Utile pour suggérer des zones de recherche étendues.
    """
    results = []
    for zone, data in POSTAL_ZONES.items():
        dist = haversine_km(lat, lon, data["lat"], data["lon"])
        if dist <= radius_km:
            results.append({
                "zone":     zone,
                "region":   data["region"],
                "canton":   data["canton"],
                "dist_km":  round(dist, 1),
            })
    results.sort(key=lambda x: x["dist_km"])
    return results[:limit]


def format_distance_label(km: float) -> str:
    """Formate la distance pour affichage UI."""
    if km < 1:
        return "< 1 km"
    if km < 10:
        return f"{km:.1f} km"
    return f"{round(km)} km"


def validate_swiss_postal_code(postal_code: str) -> bool:
    """Vérifie qu'un code postal est dans la zone UMBRA (Suisse + frontaliers)."""
    return resolve_postal_code(postal_code) is not None


# ── POSTGIS (optionnel — actif si geoalchemy2 installé) ──────────────────────

try:
    from sqlalchemy.orm import Session
    from sqlalchemy import text as sql_text

    def postgis_distance_km(db: Session, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Distance via PostGIS ST_Distance (plus précis que Haversine).
        Utilisé si PostGIS est disponible.
        """
        result = db.execute(sql_text(
            "SELECT ST_Distance("
            "ST_SetSRID(ST_MakePoint(:lon1, :lat1), 4326)::geography,"
            "ST_SetSRID(ST_MakePoint(:lon2, :lat2), 4326)::geography"
            ") / 1000.0 AS dist_km"
        ), {"lat1": lat1, "lon1": lon1, "lat2": lat2, "lon2": lon2})
        row = result.fetchone()
        return round(row.dist_km, 1) if row else haversine_km(lat1, lon1, lat2, lon2)

    HAS_POSTGIS = True
    logger.info("PostGIS disponible — distances exactes activées")

except ImportError:
    HAS_POSTGIS = False
    logger.info("PostGIS non disponible — fallback Haversine")
