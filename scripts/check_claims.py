#!/usr/bin/env python3
"""
scripts/check_claims.py — Garde-fou des affirmations publiques de Merito (PEP's Swiss SA).

Inspiré de boom-contact/scripts/check-claims.ts, adapté au stack Python de Merito.

But : empêcher qu'une affirmation marketing dépasse la réalité technique vérifiée
(superlatif non prouvable, certification trompeuse, souveraineté absolue pas encore
vraie tant que l'analyse CV passe par un LLM hors-CH).

Exit 0  ⇔  aucun claim bloquant
Exit 1  ⇔  ≥1 claim bloquant  (à brancher en CI / pre-commit)

Voir legal/claims.md pour la liste des claims approuvés et leurs preuves.

Usage :
  python3 scripts/check_claims.py            # rapport lisible
  python3 scripts/check_claims.py --json     # sortie JSON (CI)
"""
from __future__ import annotations
import re
import sys
import os
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SURFACES = sorted((ROOT / "backend" / "static").glob("*.html"))

# Tant que l'analyse CV passe par un LLM hors-CH (Gemini US), les claims de
# souveraineté ABSOLUE sont interdits. Passer MERITO_SOVEREIGN_AI=true le jour
# où l'IA suisse (Infomaniak) est branchée.
SOVEREIGN_AI = os.getenv("MERITO_SOVEREIGN_AI", "false").lower() == "true"

# ── Claims TOUJOURS bloquants (non prouvables / trompeurs) ──
FORBIDDEN = [
    (re.compile(r"\ble meilleur\b", re.I), "superlatif non prouvable « le meilleur »"),
    (re.compile(r"\bn[\u00b0o]\s*1\b|\bnum[\u00e9e]ro\s+un\b", re.I), "claim « n\u00b01 » non prouvable"),
    (re.compile(r"\bleader\s+(mondial|suisse|du\s+march[\u00e9e]|europ[\u00e9e]en)\b", re.I), "leadership non prouvable"),
    (re.compile(r"\b100\s*%?\s*s[\u00e9e]curis", re.I), "« 100% s\u00e9curis\u00e9 » \u2014 s\u00e9curit\u00e9 absolue jamais vraie"),
    (re.compile(r"\binviolable\b|\bimpossible\s+(\u00e0|a)\s+pirater\b|\baucun\s+risque\b", re.I), "promesse de s\u00e9curit\u00e9 absolue"),
    (re.compile(r"\bcertifi[\u00e9e]e?\s+(?:par\b|ISO|eIDAS|SOC|RGPD|GDPR|FINMA|PCI|HDS|HIPAA|conforme|\d)", re.I), "certification r\u00e9glementaire \u2014 exige une preuve documentée"),
    (re.compile(r"garanti[e]?\s+(\u00e0\s+)?100\s*%|garantie?\s+absolue|garanti[e]?\s+sans\s+risque", re.I), "garantie absolue"),
]

# ── Claims de souveraineté ABSOLUE — bloquants tant que l'IA n'est pas suisse ──
SOVEREIGN_ABSOLUTE = [
    (re.compile(r"100\s*%?\s*suisse", re.I), "« 100% suisse »"),
    (re.compile(r"toutes?\s+(vos|les)\s+donn[\u00e9e]es.{0,40}(en|dans|restent?\s+en)\s+suisse", re.I), "« toutes les donn\u00e9es en Suisse »"),
    (re.compile(r"aucune\s+donn[\u00e9e]e\s+ne\s+(quitte|sort\s+de)\s+(la\s+)?suisse", re.I), "« aucune donn\u00e9e ne quitte la Suisse »"),
    (re.compile(r"100\s*%?\s*souverain", re.I), "« 100% souverain »"),
]

# ── Whitelist contextuelle : si un de ces motifs est sur la même ligne, le claim est approuvé ──
WHITELIST_CONTEXT = [
    re.compile(r"employeur\s+certifi", re.I),            # badge interne « Employeur Certifié »
    re.compile(r"badge\s+certifi", re.I),                # badge interne
    re.compile(r"certifi[\u00e9e]e?\s*[>\u2265]\s*\d", re.I),  # « certifié > 4/5 » (note interne)
    re.compile(r"garanti[e]?\s+par\s+l['\u2019 ]architecture", re.I),  # anonymat garanti par l'architecture (vrai)
    re.compile(r"le\s+meilleur\s+des\s+deux\s+mondes", re.I),  # expression idiomatique, pas un superlatif marketing
]


def is_whitelisted(line: str) -> bool:
    return any(w.search(line) for w in WHITELIST_CONTEXT)


def scan():
    findings = []
    rules = list(FORBIDDEN)
    if not SOVEREIGN_AI:
        rules += SOVEREIGN_ABSOLUTE
    for f in SURFACES:
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        for n, line in enumerate(lines, 1):
            if is_whitelisted(line):
                continue
            for rx, why in rules:
                m = rx.search(line)
                if m:
                    findings.append({
                        "file": str(f.relative_to(ROOT)),
                        "line": n,
                        "match": m.group(0),
                        "reason": why,
                        "excerpt": line.strip()[:120],
                    })
    return findings


def main():
    findings = scan()
    if "--json" in sys.argv:
        print(json.dumps({"blocking": len(findings), "findings": findings}, ensure_ascii=False, indent=2))
        sys.exit(1 if findings else 0)
    if not findings:
        print(f"\u2705 check-claims : 0 claim bloquant ({len(SURFACES)} surface(s) scann\u00e9e(s)).")
        state = "SUISSE (Infomaniak)" if SOVEREIGN_AI else "Gemini US \u2014 claims absolus de souverainet\u00e9 BLOQU\u00c9S"
        print(f"   Souverainet\u00e9 IA = {state}")
    else:
        print(f"\u274c check-claims : {len(findings)} claim(s) bloquant(s) :\n")
        for x in findings:
            print(f"  \u2022 {x['file']}:{x['line']}  [{x['match']}] \u2014 {x['reason']}")
            print(f"      \u00ab {x['excerpt']} \u00bb")
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
