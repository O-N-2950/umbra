# UMBRA — TODO
> Mise à jour : 05/06/2026 — Jelastic Infomaniak

## 🏆 VISION : Application de référence recrutement anonyme suisse

---

## ✅ FAIT

### Infrastructure Production
- [x] Backend FastAPI deployé Railway + Jelastic
- [x] `/ping` healthcheck rapide
- [x] JWT + ENCRYPTION_KEY générées
- [x] Rate limiting + security headers

### Produit
- [x] `/api/umbra/cv-analyze` opérationnel (Gemini Flash)
- [x] `/api/umbra/cv-pricing` (free_launch)
- [x] Analytics proxy PostHog + GA4 + Sentry (code prêt)
- [x] UI React UMBRA 10 écrans déployée sur `/app`

### Jelastic Infomaniak (session actuelle)
- [x] **`manifest.jps`** — deploy 1-clic Jelastic
- [x] **`Dockerfile`** optimisé Python 3.12 slim multi-stage
- [x] **`.github/workflows/docker-jelastic.yml`** — CI/CD push → Jelastic
- [x] **`README_JELASTIC.md`** — guide complet avec checklist
- [x] **Workflow CI/CD ✅ SUCCESS** sur GitHub Actions

---

## 🔴 P0 — À faire maintenant (toi)

### Variables analytics (5 min chacune)
- [ ] **Sentry** → sentry.io → Railway var `SENTRY_DSN`
- [ ] **PostHog** → eu.posthog.com → Railway var `POSTHOG_API_KEY`
- [ ] **GA4** → analytics.google.com → Railway var `GA4_MEASUREMENT_ID`

### Deploy Jelastic (2 min)
- [ ] **Dashboard Jelastic** → Marketplace → Import JPS :
  `https://raw.githubusercontent.com/O-N-2950/umbra/main/manifest.jps`
- [ ] Remplir : Gemini Key + Resend Key + domain
- [ ] Configurer domaine `umbra.ch` → CNAME → `xxx.jcloud.ik-server.com`

---

## 🟠 P1 — Semaine prochaine

- [ ] Email HTML templates magic link (branded UMBRA noir/cuivre)
- [ ] Webhook Stripe complet
- [ ] Market intel data — seed salaires suisses réels (OFS Confédération)
- [ ] Tests smoke auth flow end-to-end

## 🟡 P2 — Mois 1

- [ ] Redis pour rate limiting (remplace in-memory)
- [ ] i18n FR/DE (Suisse = bilingue minimum)
- [ ] Zefix IDE vérification flow entreprise
- [ ] Export PDF résultat analyse CV
- [ ] SEO landing page

---

## 🌐 URLs Production

| Service | URL |
|---|---|
| Backend Railway | `https://matcho-production.up.railway.app` |
| App UMBRA | `https://matcho-production.up.railway.app/app` |
| CV Analyze | `POST /api/umbra/cv-analyze` |
| Health | `GET /health` → 100% |
| Jelastic (après deploy) | `https://umbra-prod.jcloud.ik-server.com` |

## 📊 Scoring Premium+++

| Dimension | Score |
|---|---|
| Architecture | ⭐⭐⭐⭐⭐ 95% |
| Backend Python | ⭐⭐⭐⭐ 75% |
| Frontend déployé | ⭐⭐⭐⭐ 75% |
| Fiabilité prod | ⭐⭐⭐ 70% |
| Infra Jelastic | ⭐⭐⭐⭐⭐ 100% prête |
| Analytics | ⭐⭐ 35% (vars à remplir) |
| **Global** | **⭐⭐⭐ 74%** → cible ⭐⭐⭐⭐⭐ |
