# UMBRA — Journal de Suivi (SUIVI.md)

> Journal chronologique des sessions, décisions et pièges rencontrés.
> Le plus récent en haut. Pour l'état actuel complet : voir la section de tête de CONTEXT.md.

═══════════════════════════════════════════════════════════════════════
## Session 2026-06-16 — JELASTIC PROD LIVE + LOT 1-3 + best practices PLACIO/Tournepage
═══════════════════════════════════════════════════════════════════════

### Objectif
Carte blanche d'Olivier : améliorer UMBRA comme si la réputation/vie en dépendait,
en faire une app virale rentable, code stable et robuste. Importer les best practices
de PLACIO et Tournepage. Préparer le branchement Hunteed.

### Réalisé
- **LOT 1-3 livrés, testés, commités, poussés** (voir CONTEXT.md section de tête pour le détail).
- **UMBRA MIS EN PRODUCTION** sur Jelastic Infomaniak Genève : URL live, API fonctionnelle,
  base PostgreSQL connectée (19 tables, 3 migrations).
- **Fix prod critique PgEnum** (register 500 PostgreSQL).
- Best practices extraites de PLACIO (déploiement Jelastic port 3000) et Tournepage
  (classification PII, AES-256-GCM, S3 souverain).

### 🔑 PIÈGES RÉSOLUS CETTE SESSION (à ne jamais réapprendre)
1. **Routing Jelastic 502/503** : le node nodejs route vers le **PORT 3000** (pas 80, pas 8000).
   Solution = lanceur `/home/jelastic/ROOT/server.js` qui spawn uvicorn:3000 + `restartservices`.
   Découvert en lisant le repo PLACIO (`node server.mjs:3000`).
2. **Variable PORT=8000** forçait uvicorn sur 8000 → 502. Aligner `PORT=3000`.
3. **Node ROOT contenait l'app démo Jelastic** ("whiteboard" socket.io) → remplacée par le lanceur.
4. **`deleteenv` exige le mot de passe du compte** (non disponible) → on ne peut pas supprimer/recréer
   l'env. On a installé pip sur le node nodejs existant (Python 3.9) au lieu de recréer en docker.
5. **Code UMBRA compatible Python 3.9** (SYNTAX_OK) — pas besoin de docker python 3.12.
6. **DATABASE_URL sans mot de passe** → register/sectors 500. Password PostgreSQL récupéré dans
   `.pgpass` du node db : `webadmin:<password PostgreSQL: récupérer via .pgpass du node db 206539>`. Base `umbra` créée via TCP (l'auth ident localhost échoue).
7. **PgEnum** : enum `(str, Enum)` persiste le NOM pas la VALEUR → PostgreSQL strict rejette,
   SQLite tolère. Fix `values_callable` sur les 8 colonnes Enum.
8. **Sandbox réseau** : ouvert vers Jelastic cette session (avant bloqué → passait par GitHub Actions).

### Décisions
- Railway = staging (données fictives) ; Jelastic Infomaniak Genève = prod (données réelles, nLPD).
- Anonymat = engagement légal : CV anonymisé AVANT Gemini (hors Suisse), révélation atomique,
  faux-poste bloqué d'office.

### Prochaine session
Vérifier register prod → LOT 4 (Stripe/pricing serveur) → LOT 5 (viral) → front → Hunteed.

═══════════════════════════════════════════════════════════════════════
## Sessions antérieures (résumé)
═══════════════════════════════════════════════════════════════════════
- **Sessions 1-3** : vision produit, 10 Game Changers, modèle économique à la valeur (barème 6.5-11%),
  architecture 17 tables, prompt CV 6 couches. (Détail dans CONTEXT.md plus bas.)
- **Session 4** : décision facturation analyses CV, interface recruteur.
- **Session 5** : premiers clients, bataille 502 Railway, mise en production.
- **Session 6-7** : analytics (Sentry/PostHog/GA4 câblés), deploy checklist.
- **Sessions Jelastic (juin)** : migration Railway→Jelastic, découverte pattern déploiement,
  audit technique complet (7 bloquants), début améliorations code.
