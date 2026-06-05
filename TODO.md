# UMBRA — TODO
> Mise à jour : 05/06/2026 — Session 8 (Audit Premium+++ + Sprint 1 Fixes)

## 🏆 VISION : Application de référence recrutement anonyme suisse

---

## ✅ FAIT

### Infrastructure
- [x] Backend FastAPI déployé sur Railway (`matcho-production.up.railway.app`)
- [x] Health check `/ping` ultra-rapide (Railway ne surchage plus Gemini)
- [x] JWT_SECRET + ENCRYPTION_KEY générées et injectées
- [x] Sentry + PostHog + GA4 — code prêt, variables Railway en attente
- [x] Branche main synchronisée sur master

### Produit
- [x] `/api/umbra/cv-analyze` — 100% opérationnel (Gemini Flash, ~15s, gratuit)
- [x] `/api/umbra/cv-pricing` — modèle free_launch
- [x] 8 events PostHog définis (candidat + employeur)
- [x] Route analytics proxy `/api/v1/analytics/track`

### Sprint 1 (aujourd'hui — Audit Premium+++)
- [x] **Audit complet** livré (UMBRA_AUDIT.md)
- [x] **Magic tokens DB** — plus de perte au redémarrage Railway
- [x] **Rate limiting** — middleware anti-brute force sur /auth
- [x] **Security headers** — X-Frame-Options, HSTS, CSP
- [x] **Depends(lambda: None)** → get_current_account réel dans trust.py
- [x] **UI React complète déployée** — umbra-v3-pricing.jsx → `/app`
- [x] **Migration Alembic** — gestion propre de l'état existant

---

## 🔴 P0 — Cette semaine

- [ ] **Remplir variables** : SENTRY_DSN + POSTHOG_API_KEY + GA4_MEASUREMENT_ID
- [ ] Tester `/app` → vérifier les 10 écrans React UMBRA
- [ ] Vérifier auth flow end-to-end (register → magic link → login)
- [ ] Confirmer toutes les tables créées en DB

## 🟠 P1 — Semaine prochaine

- [ ] **Email HTML templates** magic link (branded UMBRA noir/cuivre)
- [ ] **Webhook Stripe** complet (activé après 10 embauches)
- [ ] **Market intel data** — seed salaires suisses réels (Confédération OFS)
- [ ] **Quiz culturel** — brancher sur vrai backend
- [ ] **Dashboard recruteur** — historique analyses CV, shortlist

## 🟡 P2 — Mois 1

- [ ] Rate limiting Redis (remplace in-memory)
- [ ] i18n FR/DE (Switzerland = bilingue minimum)
- [ ] Zefix IDE vérification dans le flow entreprise
- [ ] Export PDF résultat analyse CV
- [ ] Notifications email nouveaux matchs
- [ ] SEO landing page (meta, og, schema.org)

## 🔵 P3 — Mois 2-3

- [ ] Mobile PWA / React Native
- [ ] API partenaires (Jobup.ch, Indeed.ch)
- [ ] Admin dashboard (métriques plateforme)
- [ ] LPD/RGPD — export données, droit à l'oubli
- [ ] WebSocket real-time (match notifications)
- [ ] FLAG_FACTURATION activer après 10 embauches documentées

---

## 📊 Scoring actuel

| Dimension | Score |
|---|---|
| Architecture | ⭐⭐⭐⭐⭐ 95% |
| Backend Python | ⭐⭐⭐ 70% |
| Frontend déployé | ⭐⭐⭐⭐ 75% |
| Fiabilité production | ⭐⭐⭐ 65% |
| Expérience utilisateur | ⭐⭐⭐ 60% |
| Analytics/Observabilité | ⭐⭐ 35% |
| **Global** | **⭐⭐⭐ 66%** |

---

## 🌐 URLs Production

| | URL |
|---|---|
| Landing | `https://matcho-production.up.railway.app` |
| App UMBRA complète | `https://matcho-production.up.railway.app/app` |
| CV Analyzer | `POST /api/umbra/cv-analyze` |
| Analytics | `GET /api/v1/analytics/events` |
| Health | `GET /health` |
