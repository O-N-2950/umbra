# Merito — Registre des affirmations publiques (claims)

> Source de vérité des affirmations marketing / légales de Merito (PEP's Swiss SA).
> Le script `scripts/check_claims.py` fait respecter ce registre automatiquement.
> **Toute nouvelle affirmation forte doit être ajoutée ici avec sa preuve AVANT publication.**

## ✅ Approuvés (vérifiés)

| Claim | Preuve technique | Vérifié le |
|---|---|---|
| Données hébergées en Suisse | PostgreSQL sur Infomaniak Jelastic (CH) + backup Swiss Backup (CH). Migration vérifiée par checksum md5. | 2026-06-22 |
| Anonyme / anonymat par l'architecture | Profil anonyme dissocié du compte (aucune FK directe profil→compte) ; CV jamais stocké en brut. | 2026-06-22 |
| CV jamais stocké | Aucune table CV/resume ; analyse à la volée, seul le profil anonymisé est conservé. | 2026-06-22 |
| Pensé pour la nLPD | PII Shield avant tout LLM ; SMTP Infomaniak (CH) ; registres admin.ch (Zefix/UID) ; PostHog & Stripe inactifs. | 2026-06-22 |
| Badge « Employeur Certifié » / « Certifié > 4/5 » | Label **interne** de la plateforme (basé sur les embauches/notes), **pas** une certification réglementaire externe. | 2026-06-22 |

## 🔶 Conditionnels

| Claim | Condition d'autorisation | État actuel |
|---|---|---|
| « 100 % suisse » · « toutes vos données en Suisse » · « aucune donnée ne quitte la Suisse » · « 100 % souverain » | Autorisé **uniquement** quand l'analyse CV est souveraine (IA Infomaniak). Activé par `MERITO_SOVEREIGN_AI=true`. | ⛔ **INTERDIT** — l'analyse CV passe encore par Gemini (US), même anonymisée par le PII Shield. |

## ⛔ Interdits (toujours)

- **Superlatifs non prouvables** : « le meilleur », « n°1 », « numéro un », « leader mondial/suisse ».
- **Sécurité absolue** : « 100 % sécurisé », « inviolable », « impossible à pirater », « aucun risque ».
- **Certifications réglementaires non détenues** : « certifié ISO 2700x », « certifié eIDAS », « certifié par [organisme] »…

## Faire respecter

```bash
python3 scripts/check_claims.py            # rapport lisible
python3 scripts/check_claims.py --json     # CI : exit 1 si claim bloquant
```

À brancher dans `.github/workflows/build-guard.yml` → bloque tout déploiement introduisant un claim non approuvé.
