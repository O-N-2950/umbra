# UMBRA — TODO LIST

> État au 2026-06-25. Priorité décroissante. Voir CONTEXT.md (section de tête) pour le contexte complet.

---

## 🟢 SESSION 2026-06-22 — MIGRATION SOUVERAINE CH (Railway US → Infomaniak Jelastic Suisse)

### ✅ FAIT
- [x] **Migration souveraine nLPD** : backend Merito redéployé sur **Infomaniak Jelastic (Suisse)**. Image Docker `python:3.12-slim-bookworm` (⚠️ trixie refusé) → GHCR → pull Jelastic. App **LIVE** sur `merito-prod.jcloud-ver-jpc.ik-server.com`, /health `database:ok`.
- [x] **Données migrées + intégrité vérifiée par checksum md5** (Railway → CH) : accounts/magic_tokens/trust_scores/credit_balances = 11 lignes, MATCH des 2 côtés. UUID (pas de séquence à resync).
- [x] **Backup automatique souverain** : script Python pur (pg_dump → gzip → AES-256 → Swiss Backup S3 via SigV4 maison), **cron quotidien 03:00**, **restauration testée** (19 tables OK). mcli abandonné (binaire instable).
- [x] **Audit complet des flux** : DB (CH) ✓, e-mail SMTP Infomaniak (CH, login testé) ✓, Zefix/UID (CH) ✓, CV jamais stocké en brut ✓, PII Shield actif avant LLM ✓, PostHog/Stripe inactifs ✓. Seul flux hors-CH = analyse CV → Gemini (US), anonymisée.

### ✅ FAIT (suite — sessions 2026-06-24/25)
- [x] **Vague 1 best practices NEO complète** :
  - `scripts/check_claims.py` + `legal/claims.md` — garde-fou claims publics (pattern boom-contact). Home actuelle : 0 claim bloquant ; « 100% suisse » auto-interdit tant que `MERITO_SOVEREIGN_AI` ≠ true.
  - `.github/workflows/build-guard.yml` (pattern winwin-v2) — syntaxe + claims + boot réel de l'app (uvicorn + /ping + /health/deep) sur Postgres CI. **Vert dès le 1er run.**
  - `backend/api/health_deep.py` (pattern soluris) — GET /health/deep : database (19 tables), migrations (0003_current), smtp (mail.infomaniak.com:465), ai_llm, disk. Déployé Jelastic CH, **healthy 273 ms**.
  - `scripts/readiness_gate.py` (pattern soluris) — gate GO/NO-GO (claims+ping+health+deep+home+openapi). **🟢 GO 6/6 sur l'instance CH.**
- [x] **Module QR-facture suisse** `backend/services/qr_invoice.py` : QR-IBAN CH26 3080… (référence QRR → rapprochement auto, synergie MATCHO), sans TVA (pas de CA), adresse RC Courgenay. Facture démo CHF 290 livrée + scannable. Non branché à une route (zéro impact prod) ; branchement ≈ 30 min quand facturation activée.
- [x] Redeploy Jelastic image :latest vérifié (≈100 s d'indispo URL de test uniquement ; merito.ch public intouché — Railway n'auto-déploie pas, ancien code stable).

### 🔲 RESTE (à faire par Claude)
- [ ] **Bascule DNS merito.ch → Jelastic CH** (re-sync finale des données + fenêtre maintenance courte + SSL Let's Encrypt). Dernière étape technique avant prod publique souveraine.
- [ ] **Restaurer le claim « Hébergé en Suisse »** sur la home une fois basculé.
- [ ] Nettoyer le compte de test résiduel (`accounts`=12 → 11, FK à gérer) — réglé à la re-sync finale.
- [ ] Rétention auto backups >30j ; self-host Google Fonts ; confirmer persistance cron au reboot node.

### ⚠️ ACTION OLIVIER (reporté — « on le fera plus tard »)
- [ ] **Activer l'IA souveraine Infomaniak** (AI Services) dans le Manager + créer une **clé API** → Claude branche l'analyse CV **Gemini US → Llama 3.3 70B CH** (API compatible OpenAI, bascule en minutes). Rend le claim « 100 % Suisse » entièrement vrai. Comparatif validé : coût négligeable (~5 CHF/mois pour 1000 CV), perf équivalente, souveraineté totale. **PII Shield couvre l'intérim.**

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
- [x] **Robustesse launcher (en grande partie FAIT)** : `server.js` réécrit en superviseur robuste (libère le port via `fuser -k` AVANT spawn → fin des workers orphelins ; spawn en groupe de process + arrêt propre SIGTERM/SIGINT ; backoff plafonné). `package.json` a désormais un vrai script `start` (`node server.js`) → le boot systemd (`npm start`) ne devrait plus échouer. `DATABASE_URL` corrigé dans le **stored config** Jelastic (remove+add) → survit aux restarts. Fichiers versionnés dans `deploy/jelastic-ROOT/`. **Vérifié** : `npm start` relance prod saine (health ok, register 201).
- [ ] **RESTE à vérifier (quand l'API Jelastic sera stable)** : un vrai `restartnodebyid`/reboot pour confirmer le auto-recovery systemd→npm start→launcher de bout en bout. Non testé en live aujourd'hui (API exec Jelastic instable → trop risqué sans voie de récup fiable).
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

## Issu de la session landing premium (2026-06-16 suite 2)
- [ ] **Réparer le SPA React `umbra-app.html` (/app)** : bug « exports is not defined » (CommonJS dans un `<script type="text/babel">`) → bloque au splash. C'est le vrai produit (flux onStart candidat/entreprise) à restaurer.
- [ ] **Fiabiliser le boot** : `nodejs.service` systemd échoue → app lancée en manuel (setsid). Survie reboot non garantie. Piste : faire fonctionner `npm start` via le run-command Jelastic, ou superviser via pm2 + persistance.
- [x] **DATABASE_URL durable** : launcher lit `/home/jelastic/.merito_db_url` (persistant, hors repo) → survit à la régénération de /.jelenv. ✅
- [x] **Landing premium Merito sur `/`** : rebrand + inscription fonctionnelle. ✅

## 2026-06-20 — refonte Aurore + déploiement
- [x] Refonte home en thème Aurore (fond clair) + déploiement merito.ch (Railway, commit 765883e, deploy bf0f693f SUCCESS, vérifié 200 + visuel)
- [~] (relecture FR home faite 2026-06-20) Analyseur CV public : remplacer l'appel direct `api.anthropic.com` par un endpoint backend proxy (sinon analyseur KO en prod)
- [ ] Débrancher Jelastic (ancienne prod pm2) après validation durable de Railway
- [ ] (optionnel) Redirect www→apex · GitHub auto-deploy (OAuth Railway) · corriger « Groupe NEO » → « Groupe NEUKOMM » dans docs

- [x] Relecture FR complete de la home (anglicismes -> appariement/correspondance, ponctuation FR, espaces insecables, guillemets, virgule decimale) — deploiements 7f2e143, 6e999da, 5c588ba
