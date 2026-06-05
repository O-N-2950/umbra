# UMBRA — Déploiement sur Jelastic Cloud Infomaniak

> Hébergement 100% suisse · Données en Suisse · Auto-scaling · CHF

---

## 🚀 Option A — Import JPS (1 clic, recommandé)

Le fichier `manifest.jps` permet de déployer UMBRA **en un clic** depuis le dashboard Jelastic.

### Étapes

1. **Se connecter** au dashboard Jelastic Infomaniak
   - URL : `https://app.infomaniak.com` → Mes produits → Jelastic Cloud
   
2. **Importer le manifest**
   - Clic sur **Marketplace** en haut à droite
   - Onglet **Import** → **JPS URL**
   - Coller : `https://raw.githubusercontent.com/O-N-2950/umbra/master/manifest.jps`
   - Clic **Import** → **Install**

3. **Remplir les paramètres**
   | Paramètre | Valeur |
   |---|---|
   | Nom de l'environnement | `umbra-prod` |
   | Clé Gemini | Depuis [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
   | Clé Resend | Depuis [resend.com/api-keys](https://resend.com/api-keys) |
   | URL de l'app | `https://umbra-prod.jcloud.ik-server.com` |

4. **Clic Install** → attendre ~3 minutes ☕

---

## 🔧 Option B — Déploiement manuel via SSH

Si tu préfères contrôler chaque étape :

```bash
# 1. Obtenir l'accès SSH (dashboard Jelastic → Settings → SSH Keys)
ssh -p 3022 user@XXXX.jcloud.ik-server.com

# 2. Cloner le repo
git clone https://github.com/O-N-2950/umbra.git /app/umbra

# 3. Installer les dépendances
cd /app/umbra/backend
pip install -r requirements.txt

# 4. Configurer les variables (créer /app/.env ou injecter via dashboard)
export DATABASE_URL="postgresql://..."
export JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export ENCRYPTION_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export GEMINI_API_KEY="AIzaSy..."
export RESEND_API_KEY="re_..."

# 5. Migrations DB
cd /app/umbra/backend && alembic upgrade head

# 6. Démarrer
uvicorn umbra_main:app --host 0.0.0.0 --port 8000 --workers 2
```

---

## 🔄 CI/CD automatique (GitHub Actions)

Le fichier `.github/workflows/deploy-jelastic.yml` déploie automatiquement sur Jelastic à chaque push sur `master`.

### Secrets GitHub à configurer
> Settings → Secrets and variables → Actions → New repository secret

| Secret | Description | Où le trouver |
|---|---|---|
| `JELASTIC_SSH_KEY` | Clé privée SSH | Générer : `ssh-keygen -t ed25519` |
| `JELASTIC_SSH_HOST` | Host SSH Jelastic | Dashboard → Settings → SSH Gateway |
| `JELASTIC_SSH_USER` | User SSH | Dashboard → Settings → SSH Gateway |
| `JELASTIC_NODE_ID` | ID du nœud container | Dashboard → Environment → Node ID |

### Variables GitHub (publiques)
| Variable | Valeur |
|---|---|
| `JELASTIC_APP_URL` | `https://umbra-prod.jcloud.ik-server.com` |

---

## 🌐 Configuration domaine personnalisé (umbra.ch)

1. **Dans Jelastic** : Environment → Routing → Add Custom Domain → `umbra.ch`
2. **Dans Infomaniak DNS** :
   ```
   umbra.ch    CNAME    umbra-prod.jcloud.ik-server.com.
   www.umbra.ch CNAME   umbra-prod.jcloud.ik-server.com.
   ```
3. **SSL** : Environment → Add-ons → Let's Encrypt → Install

---

## 📊 Variables d'environnement requises

| Variable | Obligatoire | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | Injectée auto par Jelastic depuis la node PostgreSQL |
| `JWT_SECRET` | ✅ | Généré auto par le manifest JPS |
| `ENCRYPTION_KEY` | ✅ | Généré auto par le manifest JPS |
| `GEMINI_API_KEY` | ✅ | Google AI Studio |
| `RESEND_API_KEY` | ✅ | Emails transactionnels |
| `STRIPE_SECRET_KEY` | ⚡ | Paiements Stripe |
| `SENTRY_DSN` | ⚡ | Error tracking |
| `POSTHOG_API_KEY` | ⚡ | Product analytics (EU) |
| `GA4_MEASUREMENT_ID` | ⚡ | Google Analytics 4 |
| `FLAG_FACTURATION` | 🔜 | `true` après 10 embauches |

---

## ✅ Checklist post-déploiement

```bash
# Vérification depuis votre machine
BASE=https://umbra-prod.jcloud.ik-server.com

curl "$BASE/ping"                        # {"ok":true}
curl "$BASE/health"                      # {"status":"healthy","score":"100%"}
curl "$BASE/api/umbra/cv-pricing"        # {"model":"free_launch",...}
curl "$BASE/api/v1/analytics/events"     # {"events":[...],"posthog_active":true}
curl "$BASE/app"                          # Landing UMBRA complète (HTML 200)
```

---

## 💰 Coût estimé Jelastic Infomaniak

| Ressource | Config | Coût estimé |
|---|---|---|
| Container UMBRA API | 4 cloudlets fixes, max 16 | ~CHF 4–18/mois |
| PostgreSQL | 4 cloudlets fixes, max 8 | ~CHF 2–8/mois |
| IP publique | 1 IP dédiée | ~CHF 3/mois |
| **Total estimé** | | **~CHF 9–29/mois** |

*Paiement à l'usage réel. Bien moins cher que Railway Pro (~$20/service/mois).*

---

*© 2026 PEP's Swiss SA — UMBRA · Hébergement Jelastic Infomaniak (Suisse)*
