# UMBRA 🇨🇭

**La première plateforme de recrutement suisse où l'anonymat est architectural.**

> "Le talent se cache. Nous le trouvons."

## Vision

- **Anonymat par architecture** — révélation uniquement si les DEUX parties confirment
- **Matching prédictif** — compétences × culture × géo × salary × durabilité
- **Confiance certifiée** — event-sourcing comportemental, auditable
- **Tarification à la valeur** — % du salaire mensuel, pas d'abonnement

## Stack

- **Backend** : FastAPI Python 3.12 — Railway
- **Base de données** : PostgreSQL + PostGIS
- **IA** : Google Gemini Flash
- **Auth** : Magic Link + JWT
- **Paiement** : Stripe

## Démarrage rapide

```bash
cp .env.example .env
# Remplir les variables
pip install -r backend/requirements.txt
cd backend && alembic upgrade head
uvicorn umbra_main:app --reload
```

## Docs

- `CONTEXT.md` — Vision, architecture, décisions
- `TODOLIST.md` — Priorités et état d'avancement
- `SUIVI.md` — Journal des sessions

---
© 2026 PEP's Swiss SA — Groupe NEO
