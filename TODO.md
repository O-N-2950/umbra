# UMBRA — TODO
> Mise à jour : 31/03/2026 — Session 7 (Analytics)

## ✅ FAIT

- [x] `/api/umbra/cv-analyze` — 100% opérationnel en production
- [x] `/api/umbra/cv-pricing` — modèle free_launch
- [x] `/api/umbra/cv-debug` — debug Gemini raw
- [x] Sentry backend Python — `monitoring/analytics.py`
- [x] PostHog proxy server-side — `/api/v1/analytics/track`
- [x] GA4 + Sentry browser injectés dans landing page
- [x] Hook TypeScript `useAnalytics()` — `client/src/lib/analytics.ts`
- [x] 8 events UMBRA définis (candidat + employeur)
- [x] `DEPLOY_CHECKLIST.md` créée avec checklist sécurité
- [x] Variables Railway: SENTRY_DSN, POSTHOG_API_KEY, GA4_MEASUREMENT_ID
- [x] main → master synchro (deploy Railway sur bonne branche)
- [x] /ping healthcheck rapide (Railway ne surchage plus Gemini)
- [x] JWT_SECRET + ENCRYPTION_KEY injectées Railway

## 🔴 P0 — À faire maintenant

- [ ] **Remplir sur Railway**: SENTRY_DSN, POSTHOG_API_KEY, GA4_MEASUREMENT_ID
- [ ] Vérifier `/api/v1/analytics/events` → `posthog_active: true`
- [ ] Tables DB manquantes: alembic stamp head + migration (fiduciaries, clients...)
- [ ] `matcho-production.up.railway.app` — 502 résiduel → vérifier routage Railway

## 🟠 P1 — Cette semaine

- [ ] Déclencher events PostHog dans les routes auth/stripe/matching
- [ ] Dashboard recruteur (interface historique analyses CV)
- [ ] Export PDF résultat analyse CV
- [ ] Améliorer prompt CV: 5→15 exemples few-shot terrain suisse
- [ ] Injecter vecteur culturel 6D si candidat vient du réseau UMBRA

## 🟡 P2 — Roadmap

- [ ] Activer FLAG_FACTURATION après 10 embauches documentées
- [ ] Quiz culturel 6D intégré au flow candidat
- [ ] Générateur CV IA (Gemini Flash + PDF template)
- [ ] Stripe billing actif (annonces à la valeur)

## 📋 URLs Production

| | URL |
|---|---|
| Backend actif | `https://matcho-api-production.up.railway.app` |
| CV Analyze | `POST /api/umbra/cv-analyze` |
| Analytics | `GET /api/v1/analytics/events` |
| Health | `GET /health` → 100% |
