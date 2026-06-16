# UMBRA — TODO LIST

> État au 2026-06-16. Priorité décroissante. Voir CONTEXT.md (section de tête) pour le contexte complet.

---

## ✅ FAIT — Session 2026-06-16 (SMTP magic link + Merito + stabilisation prod)

- [x] **Register 500 → 201** : cause = uvicorn pré-fix resté collé au port 3000 (fix PgEnum sur disque mais pas chargé en mémoire). Pas un bug de code. Teardown PAR PORT + relance launcher. Candidat/entreprise/idempotence = 201, /health healthy.
- [x] **DATABASE_URL persisté** (avec mot de passe) dans `/.jelenv` — l'ancienne session ne l'avait corrigé qu'en mémoire (recassait à chaque restart).
- [x] **Magic link via SMTP Infomaniak** (`contact@merito.ch`) : `_send_magic_link` refait en SMTP-first → fallback Resend → log ; `_send_via_smtp` (smtplib 465 SSL / 587 STARTTLS) ; kill switch respecté ; branding `BRAND_NAME=Merito`. Commit `d9783f8`, poussé + déployé.
- [x] **Variables d'env prod** : SMTP_*, EMAIL_ENABLED=true, APP_URL, BRAND_NAME=Merito, ENV=production.
- [x] **DNS merito.ch publié** (NS ns11/ns12.infomaniak.ch, MX mta-gw.infomaniak.ch) → **envoi SMTP réel OK de bout en bout** (magic link fonctionnel).
- [x] **Rebrand UMBRA → Merito** (umbra.ch pris → merito.ch). Slogan retenu : « Les compétences avant l'identité. »
- [x] **Nettoyage** : parasite uvicorn :8000 tué ; 4 comptes de test purgés (prod = 0 compte résiduel).

## ✅ FAIT (sessions précédentes)

- [x] **LOT 1 — Fondations** : bug `metadata`→`meta` (migrations rejouables base vierge)
- [x] **LOT 1** : 18 routes `Depends(lambda:None)` → auth réelle (`get_current_account`/`get_db`)
- [x] **LOT 2 — Divorce MATCHO** : sel crypto `umbra-salt-2026-pep-swiss`
- [x] **LOT 2** : loggers/domaines/emails `umbra.*` ; token GitHub purgé deploy.sh/deploy.py
- [x] **LOT 2** : CONTEXT.md corrigé (repo umbra, stack Jelastic + PostgreSQL/PostGIS)
- [x] **LOT 3 — Anonymat** : PII Shield renforcé (ville/rue/NPA suisse + injection FR+EN, zéro fuite)
- [x] **LOT 3** : prompt CV délimité `<profil_candidat_non_fiable>` + validation sortie LLM
- [x] **LOT 3** : révélation mutuelle atomique (`with_for_update`)
- [x] **LOT 3** : blocage faux-poste auto (`current_employer_ide` + migration 0003)
- [x] **FIX PROD** : `PgEnum` values_callable (register 500 PostgreSQL)
- [x] **INFRA** : UMBRA déployé et LIVE sur Jelastic Infomaniak Genève (routing port 3000 résolu)
- [x] **INFRA** : base PostgreSQL prod créée, 19 tables, migrations appliquées
- [x] **CI** : nettoyage workflows (1 seul canonique `jelastic-deploy.yml`)

---

## 🔴 P0 — PROCHAINE SESSION

- [x] ~~Vérifier register prod~~ → **FAIT**, 201 confirmé (candidat/entreprise/idempotence), /health healthy.
- [ ] **Robustesse launcher** : `server.js` doit tuer tout squatteur du port 3000 avant de spawn (`fuser -k 3000/tcp`) pour éviter la boucle « Address already in use ». Persistance reboot fragile : systemd `nodejs.service` cassé (package.json ROOT = démo whiteboard, pas de script `start`) → le launcher tourne en **manuel détaché**. **NE PAS** faire `restartnodebyid` (casse l'app) ; relancer via `setsid node server.js`. À durcir (pm2 + `pm2 save`, ou vrai script start).
- [ ] **LOT 4 (business)** ci-dessous = priorité n°1.

## 🟠 P1 — BUSINESS (ce qui encaisse l'argent) — LOT 4

- [ ] `compute_listing_price(salaire_brut_mensuel) -> CHF` SERVEUR dans `api/umbra_credits.py`
      (barème 6.5% → 11%, jamais côté client)
- [ ] Stripe Checkout branché sur ce montant calculé serveur + webhooks signés
- [ ] Preuve d'embauche pour remboursement 50% si embauche < 30j (via double confirmation →
      `TrustEventType.HIRE_CONFIRMED`)
- [ ] Garde-fous pricing : succès-only pour bas salaires ; 1 annonce = 1 poste = 1 IDE

## 🟡 P2 — VIRAL (effet wahoo) — LOT 5

- [ ] CV analyzer "Combien vaut mon profil sur le marché suisse ?" → résultat partageable anonymisé
- [ ] Chaque analyse CV → proposition "rester en veille passive" (transforme en profil)
- [ ] Indice de marché caché publié (PR récurrente : `market_snapshots` + PostGIS agrégé)
- [ ] Passeport de confiance portable/exportable (PDF signé + URL `umbra.ch/verify/{hash}`)
- [ ] Glassdoor inversé comportemental (métriques employeur factuelles via trust_events)

## 🟢 P3 — CONSOLIDATION & SOUVERAINETÉ

- [ ] Front unique Next.js depuis `umbra-v3-pricing.jsx` branché sur FastAPI réel
- [ ] Supprimer `client/src` (tRPC mort) ; migrer cv-analyser + smart-onboarding
- [ ] CORS : aligner `ALLOWED_ORIGINS` sur **merito.ch** (+ jcloud) ; quand un A/CNAME merito.ch → Jelastic existera, basculer `APP_URL` sur https://merito.ch
- [ ] Chiffrement PII au repos AES-256-GCM (pattern Tournepage, classes A/B/C/D)
- [ ] Stockage CV souverain S3 Infomaniak (`s3.pub1.infomaniak.cloud`, runbook Tournepage)
- [ ] Immuabilité trust_events (permissions DB ou chaînage par hash) + `recompute_from_history()`
- [ ] Index PostGIS `ST_DWithin` pour pré-filtre géo avant scoring (perf 10k×1k profils)

## 🔵 P4 — INTÉGRATIONS

- [ ] **HUNTEED** : connecteur UMBRA↔Hunteed (importer missions anonymisées + pousser candidats).
      Besoin : doc API Hunteed OU credentials Olivier.
- [ ] MATCHO (session séparée) : retirer code UMBRA résiduel de matcho/backend/static/index.html

## ⚠️ ACTION OLIVIER (hors code)

- [ ] **Déliverabilité merito.ch** : ajouter SPF (`v=spf1 include:spf.infomaniak.ch ~all`), DKIM et DMARC dans la zone DNS Infomaniak. L'envoi MARCHE déjà ; c'est du durcissement anti-spam pour que les magic links n'atterrissent pas en indésirables.
- [ ] **(Optionnel) Site sur merito.ch** : ajouter un A/CNAME merito.ch → environnement Jelastic si le site doit vivre sur merito.ch (aujourd'hui seul le mail est configuré, pas de A). Me prévenir pour aligner `APP_URL` + CORS.
- [ ] **Révoquer** l'ancien token GitHub exposé `<ancien token GitHub exposé — commençant par ghp_BkM4, présent dans 2 vieux commits>`
      (Settings → Developer settings → Personal access tokens)
