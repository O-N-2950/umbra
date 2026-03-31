# UMBRA — Checklist Deploy

> À exécuter AVANT chaque commit vers `main`. Railway deploy automatiquement sur push.

## ✅ Avant chaque commit

### Code
- [ ] Aucune clé API en dur dans le code (grep `AIzaSy`, `sk_`, `re_`, `phc_`)
- [ ] Aucun `console.log` de données sensibles (email, token)
- [ ] `requirements.txt` à jour si nouvelles dépendances Python
- [ ] Variables d'environnement référencées via `os.getenv()`, jamais hardcodées

### Tests locaux
- [ ] `curl /ping` → HTTP 200
- [ ] `curl /health` → score ≥ 70%
- [ ] `curl /api/v1/analytics/events` → liste events PostHog
- [ ] Route impactée testée manuellement

---

## ✅ Après chaque commit (Railway auto-deploy)

### 1. Surveiller le build (~3 min)
```bash
# Via Railway API — vérifier que le deploy passe SUCCESS
railway logs --tail
```

### 2. Vérifier le status HTTP
```bash
curl https://matcho-production.up.railway.app/ping   # HTTP 200
curl https://matcho-production.up.railway.app/health  # score ≥ 70%
```

### 3. Vérifier analytics (si changements analytics)
```bash
curl https://matcho-production.up.railway.app/api/v1/analytics/events
# → posthog_active: true (si POSTHOG_API_KEY configuré)
# → sentry_active: true (si SENTRY_DSN configuré)
```

### 4. Si deploy FAILED
1. Railway Dashboard → Deployments → Build Logs
2. Chercher "Error" ou "ImportError"
3. Corriger + `git push` → nouveau deploy auto
4. NE PAS enchaîner plusieurs commits sans vérifier

---

## 📋 Variables Railway UMBRA requises

| Variable | Description | Obligatoire |
|---|---|---|
| `DATABASE_URL` | PostgreSQL Railway | ✅ |
| `JWT_SECRET` | Token auth (hex 32) | ✅ |
| `ENCRYPTION_KEY` | Chiffrement AES (hex 32) | ✅ |
| `GEMINI_API_KEY` | Google Gemini Flash | ✅ |
| `RESEND_API_KEY` | Emails transactionnels | ✅ |
| `STRIPE_SECRET_KEY` | Paiements | ✅ |
| `STRIPE_WEBHOOK_SECRET` | Webhooks Stripe | ✅ |
| `SENTRY_DSN` | Error tracking Sentry | ⚡ recommandé |
| `POSTHOG_API_KEY` | Product analytics PostHog | ⚡ recommandé |
| `POSTHOG_HOST` | EU: `https://eu.i.posthog.com` | ⚡ si EU |
| `GA4_MEASUREMENT_ID` | Google Analytics 4 | ⚡ recommandé |
| `SENTRY_DSN_FRONTEND` | Sentry browser SDK | ⚡ recommandé |
| `FLAG_FACTURATION` | Activer billing CV (après 10 embauches) | 🔜 |

---

## 🔐 Sécurité — JAMAIS dans le code

```bash
# Scanner avant commit
grep -r "AIzaSy\|sk_live\|re_\|phc_\|whsec_" backend/ client/ --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js"
# Résultat attendu: aucune ligne
```

---

## 🌑 URLs Production UMBRA

| Service | URL |
|---|---|
| Backend API | `https://matcho-production.up.railway.app` |
| Health | `https://matcho-production.up.railway.app/health` |
| CV Analyzer | `POST /api/v1/analytics/track` |
| Analytics | `GET /api/v1/analytics/events` |
