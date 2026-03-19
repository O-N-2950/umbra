# UMBRA — TODO List

> Dernière mise à jour : 2026-02-27 — Session 2 complète

---

## ✅ FAIT

- [x] Concept et vision produit complets (10 game changers)
- [x] Prototype React complet `umbra-final.jsx` — 9 écrans fonctionnels
- [x] Design system UMBRA (palette, typo, composants, animations)
- [x] Canvas réseau animé, Quiz culturel 5Q, Radar 6D, Révélation cinématique
- [x] `backend/db/umbra_models.py` — 17 tables PostgreSQL
- [x] `backend/services/matching_engine.py` — Algorithme multicritères (5 dimensions pondérées)
- [x] `backend/services/trust_service.py` — Event-sourcing + anti-espionnage automatique
- [x] `backend/db/seed_data.py` — 9 secteurs + ~100 compétences + zones postales CH
- [x] `backend/api/umbra_auth.py` — Magic link + JWT (access + refresh)
- [x] `backend/api/umbra_profiles.py` — CRUD profil + quiz culturel + compétences
- [x] `backend/api/umbra_matches.py` — Matching + signaux + entretien inversé
- [x] `backend/api/umbra_trust.py` — Passeport + crédits + webhooks Stripe
- [x] `backend/umbra_main.py` — FastAPI app avec tous les routers
- [x] `backend/services/geo_service.py` — 50+ zones postales CH + Haversine + jitter anonymisation
- [x] `backend/db/session.py` — Pool connexions PostgreSQL (QueuePool)
- [x] `backend/migrations/versions/0001_umbra_init.py` — Migration Alembic complète
- [x] `backend/requirements.txt` — Stripe, JWT, Resend, Gemini, PostGIS optionnel
- [x] CONTEXT.md + TODO.md GitHub à jour

---

## 🔴 PRIORITÉ 1 — Wiring & Tests (prochaine session)

### Wiring FastAPI (dépendances injectées)
- [ ] Connecter `get_db` + `get_current_account` dans tous les routers (remplacer `lambda: None`)
- [ ] Créer `backend/api/umbra_credits.py` — router crédits séparé (importé par main)
- [ ] Tester le flow complet : register → verify → profile → quiz → match → signal → reveal

### Tests unitaires
- [ ] `test_matching_engine.py` — cas nominaux + disqualifications + shadow threshold
- [ ] `test_trust_service.py` — event-sourcing + anti-espionnage + suspension auto
- [ ] `test_auth.py` — magic token flow + JWT + expiration
- [ ] `test_geo_service.py` — résolution codes postaux + distances + jitter anonymisation
- [ ] `test_culture_quiz.py` — vecteurs 6D + labels calculés

### Railway déploiement
- [ ] Variables d'environnement Railway : DATABASE_URL, JWT_SECRET, STRIPE_*, RESEND_API_KEY, GEMINI_API_KEY, APP_URL, ENV
- [ ] Dockerfile — adapter pour UMBRA (copier pattern NEO)
- [ ] Health check Railway — `/health` comme probe
- [ ] Alembic — tester migration sur DB Railway fraîche

---

## 🟠 PRIORITÉ 2 — Frontend Next.js (semaine 2)

- [ ] Next.js setup — app router, layout, migration depuis prototype JSX
- [ ] Auth pages — /register, /login, /auth/verify?token=xxx
- [ ] Onboarding wizard — Mode → Culture Quiz → Profile → Skills
- [ ] Dashboard candidat — Matchs, profil, empreinte, passeport
- [ ] Dashboard entreprise — Matchs, crédits, passeport
- [ ] Match detail — Radar, entretien inversé, signal, révélation
- [ ] Canal post-révélation — messagerie sécurisée
- [ ] PWA — Service worker, push notifications

---

## 🟡 PRIORITÉ 3 — Intelligence & Crons (semaine 3)

- [ ] Cron matching — recalcul quotidien (APScheduler)
- [ ] Cron anti-espionnage — `check_and_run_suspensions()` toutes les heures
- [ ] Cron off-boarding — réactivation auto profils à reactivation_date
- [ ] Pipeline marché — agrégation anonymisée → market_snapshots
- [ ] Gemini predictions — SalaryBenchmark.ai_prediction_18m_pct
- [ ] Rapport mensuel — email insights marché (Resend + Jinja2)

---

## 🟢 PRIORITÉ 4 — Sécurité & Scale

- [ ] Rate limiting — slowapi sur auth, matching
- [ ] Redis — migrer magic_store dict → Redis (multi-instance)
- [ ] AES-256 — chiffrement identity_encrypted dans accounts
- [ ] RGPD / LPD — droit effacement, export données
- [ ] PostGIS — activer sur Railway + décommenter geoalchemy2

---

## 📐 Architecture (état session 2)

```
backend/
├── umbra_main.py            ✅ FastAPI UMBRA
├── api/
│   ├── umbra_auth.py        ✅ Magic link + JWT
│   ├── umbra_profiles.py    ✅ Profils + quiz + skills
│   ├── umbra_matches.py     ✅ Matching + signaux + Q&A
│   └── umbra_trust.py       ✅ Passeport + crédits + Stripe
├── db/
│   ├── umbra_models.py      ✅ 17 tables
│   ├── session.py           ✅ Pool PostgreSQL
│   └── seed_data.py         ✅ Seed complet
├── services/
│   ├── matching_engine.py   ✅ Algorithme 5 dimensions
│   ├── trust_service.py     ✅ Event-sourcing trust
│   └── geo_service.py       ✅ Géo + zones CH
└── migrations/
    └── 0001_umbra_init.py   ✅ Migration complète
```
