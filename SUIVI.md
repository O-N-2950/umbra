# UMBRA — Journal de Suivi (SUIVI.md)

> Journal chronologique des sessions, décisions et pièges rencontrés.
> Le plus récent en haut. Pour l'état actuel complet : voir la section de tête de CONTEXT.md.

═══════════════════════════════════════════════════════════════════════
## Session 2026-06-16 (soir) — MAGIC LINK SMTP + REBRAND MERITO + STABILISATION
═══════════════════════════════════════════════════════════════════════

### Objectif
Brancher le magic link sur le SMTP Infomaniak (contact@merito.ch), choisir un slogan pour
le nouveau domaine merito.ch, confirmer register=201 en prod.

### Réalisé
- **Register 500 → 201** : cause = uvicorn pré-fix collé au port 3000 (fix PgEnum sur disque
  mais pas chargé). Pas un bug de code. Teardown PAR PORT + relance launcher.
- **DATABASE_URL persisté** (avec mot de passe) dans /.jelenv — la session précédente l'avait
  corrigé en mémoire seulement → recassait à chaque restart.
- **Magic link SMTP** : refonte `_send_magic_link` (SMTP-first → Resend → log) + `_send_via_smtp`
  (smtplib 465 SSL / 587 STARTTLS), branding `BRAND_NAME=Merito`. Commit d9783f8, poussé + déployé.
- **Variables prod** : SMTP_*, EMAIL_ENABLED=true, APP_URL, BRAND_NAME=Merito, ENV=production.
- **DNS merito.ch publié** pendant la session (NS ns11/ns12.infomaniak.ch, MX mta-gw.infomaniak.ch)
  → **envoi SMTP réel confirmé** (« OK SMTP_SSL 465 → contact@merito.ch »). Magic link de bout en bout.
- **Slogan retenu** : « Les compétences avant l'identité. » (mécanisme d'anonymat, colle au nom Merito,
  = engagement nLPD). Secondaire : « Le recrutement sans préjugés. »
- **Nettoyage** : parasite uvicorn :8000 tué ; 4 comptes de test purgés (prod = 0 compte).

### 🔑 PIÈGES RÉSOLUS / APPRIS
9. **`AddContainerEnvVars` n'écrase PAS une clé existante** (upsert sur clés nouvelles seulement).
   Modifier une variable existante (ex. DATABASE_URL) → éditer /.jelenv directement.
10. **`RestartNodeById` casse l'app** : systemd `nodejs.service` → `npm start`, mais package.json
    de ROOT = démo whiteboard (pas de script start) → "Failed to start". Le launcher tourne en
    MANUEL détaché. NE PAS faire restartnodebyid ; relancer via `setsid node server.js`
    (un shell jexec hérite déjà des vars Jelastic à jour).
11. **Workers uvicorn orphelins** : `pkill -f uvicorn` les rate (cmdline = multiprocessing.spawn).
    Toujours tuer PAR PORT : `fuser -k -9 3000/tcp` (+ 8000).
12. **SMTP bloqué depuis la sandbox Claude** (egress filtre les ports mail) → tester depuis le node.
13. **DNS domaine fraîchement acheté** : merito.ch était au registre .ch sans zone publiée
    → SMTP « Sender address rejected: Domain not found ». Résolu une fois la zone publiée.

### Décisions
- **Rebrand vers Merito** (umbra.ch pris). Domaine merito.ch ; identité d'envoi contact@merito.ch.
- Magic link = SMTP Infomaniak prioritaire, Resend gardé en fallback.

### Prochaine session
LOT 4 (pricing serveur + Stripe + preuve d'embauche). Durcir launcher (anti-squat port + persistance).
Déliverabilité merito.ch : SPF/DKIM/DMARC (action Olivier).


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

═══════════════════════════════════════════════════════════════════════
## Session 2026-06-16 (suite) — DURCISSEMENT RUNTIME (robustesse)
═══════════════════════════════════════════════════════════════════════

### Réalisé (vérifié au curl : health healthy + register 201)
- **server.js → superviseur robuste** (`deploy/jelastic-ROOT/server.js`) :
  libère le port (`fuser -k -9 3000/tcp`) AVANT spawn → fin du « Address already in use »
  et des workers orphelins ; spawn uvicorn en groupe de process détaché ; arrêt propre
  SIGTERM/SIGINT (kill du groupe) ; relance avec backoff plafonné (reset si uptime > 60s).
- **package.json** : vrai script `start` (`node server.js`) → `npm start` (commande de boot
  systemd) fonctionne enfin (la démo whiteboard sans `start` était la cause du "Failed to start").
- **DATABASE_URL** corrigé dans le **stored config** Jelastic via **remove + add**
  (AddContainerEnvVars seul n'upsert pas) → survit désormais à un restart/regénération de /.jelenv.
- Fichiers ROOT versionnés dans le repo (`deploy/jelastic-ROOT/`) — avant ils n'existaient que sur le node.

### Non fait (volontairement, robustesse)
- Test de reboot plateforme complet (`restartnodebyid`) NON exécuté : l'API exec Jelastic
  était instable (timeouts) → pas de voie de récup fiable → reporté pour ne pas risquer prod.
  À faire quand l'API répond : déclencher le restart et confirmer auto-recovery.

### Piège appris (14)
- **`RemoveContainerEnvVars` + `AddContainerEnvVars`** = la bonne séquence pour MODIFIER une
  variable Jelastic existante (Add seul ignore les clés déjà présentes).

═══════════════════════════════════════════════════════════════════════
## Session 2026-06-16 (suite 2) — LANDING PREMIUM + INCIDENT P0 résolu
═══════════════════════════════════════════════════════════════════════

### Livré (vérifié en prod, rendu Playwright OK, 0 erreur JS)
- **Landing premium Merito LIVE sur `/`** (servie depuis `backend/static/index.html`) :
  rebrand complet UMBRA→Merito, hero « Les compétences, avant l'identité. »,
  formulaire d'inscription candidat/recruteur câblé sur /api/v1/auth/register (magic link),
  meta SEO, footer contact@merito.ch. Register 201 depuis le hero.
- `/` sert désormais la landing (avant : JSON). Info JSON déplacée sur **/api** (rebrandée Merito).
- `umbra-app.html` (SPA React) aussi rebrandé Merito.

### ⚠️ Bug pré-existant identifié (NON causé par le rebrand)
- Le SPA React `umbra-app.html` (servi sur **/app**) est **bloqué au splash** :
  erreur fatale **« exports is not defined »** (présente AUSSI dans le backup d'origine).
  → c'est pourquoi `/` sert `index.html` (qui rend correctement) et pas le SPA.
  TODO: débugger le script qui utilise exports/require (CommonJS) dans umbra-app.html.

### 🔴 Incident P0 (résolu) + apprentissages durables
- Cause : relance pour charger la route `/` → l'app ne rebinde pas + **canal exec Jelastic gelé**
  (même `echo` muet) + `restartnodebyid` échoue (nodejs.service systemd KO). Prod 502 plusieurs min.
- **Récupération : `restartcontainersbygroup` (nodeGroup=cp, result=0)** → réinitialise le conteneur
  ET débloque l'exec. (À retenir : c'est le levier quand l'exec est gelé et restartnodebyid échoue.)
- Au redémarrage conteneur, **DB cassée** : `/.jelenv` régénéré avec `DATABASE_URL` **SANS mot de passe**
  (Jelastic réinjecte une URL auto-générée qui écrase la nôtre, à CHAQUE restart).
  - `sed -i` sur `/.jelenv` impossible (permission sur `/`).
  - **FIX ROBUSTE** : le launcher `server.js` lit l'URL complète depuis un fichier persistant
    **`/home/jelastic/.merito_db_url`** (chmod 600, hors repo, jamais committé) et l'impose à uvicorn.
    → survit désormais à toute régénération de /.jelenv. DB ok + register 201 confirmés.

### Réserve honnête (robustesse restante)
- L'app tourne via relance manuelle `setsid node server.js`. La survie à un reboot complet n'est
  PAS garantie (nodejs.service systemd casse toujours). `restartcontainersbygroup` l'a remontée une fois,
  mais le chemin de boot propre reste à fiabiliser. NE PAS enchaîner de relances inutiles.

═══════════════════════════════════════════════════════════════════════
## Session 2026-06-16 (suite 3) — LANDING PREMIUM++ + fix flapping
═══════════════════════════════════════════════════════════════════════

### Livré (statique, déployé par git pull SANS restart → zéro risque API)
- **3 sections premium** ajoutées à `index.html` (servie sur `/`), rendu vérifié Playwright, 0 erreur JS :
  - « Comment ça marche » : parcours 4 étapes (profil anonyme → matching → entretien inversé → révélation mutuelle), pastilles numérotées reliées par une ligne copper.
  - Bandeau confiance : Hébergé en Suisse, Conforme nLPD, Anonymat par architecture, Prix à la valeur (motif grille à bord fin).
  - Footer premium multi-colonnes (Produit / Entreprise / Contact + PEP's Swiss SA + merito.ch).
- Principe appliqué : tout en statique → `git pull` = live immédiat, AUCUN restart du runtime.

### Piège appris (15) — FLAPPING par launchers multiples
- Après mes multiples relances pendant l'incident P0, **4 launchers `node server.js` + 2 masters uvicorn**
  tournaient en parallèle → bagarre sur le port 3000 → **502 intermittent (~17%)**.
- FIX : teardown total (`pkill -9 -f "node server.js"; pkill -9 -f "uvicorn umbra_main"; fuser -k -9 3000/tcp`)
  puis **UNE seule** relance `setsid node server.js`. Résultat : 12/12 pings à 200, 1 launcher, DB ok, register 201.
- RÈGLE : après une relance, toujours vérifier `pgrep -fc "node server.js"` == 1. Jamais empiler les relances.

═══════════════════════════════════════════════════════════════════════
## Session 2026-06-16 (suite 4) — FAQ + partage social + stabilité 1 worker
═══════════════════════════════════════════════════════════════════════

### Livré (statique, git pull sans restart)
- **Section FAQ** (5 objections clés, accordéon <details> natif sans JS) : employeur actuel,
  définition du mérite, prix, moment de la révélation, protection des données.
- **Partage social premium** : image OG 1200×630 on-brand (`/static/og.png`, servie en 200),
  meta og:/twitter:summary_large_image, favicon SVG inline, theme-color.
- **Nav** : lien « Comment ça marche ».

### Stabilité — passage à 1 worker uvicorn
- Le flapping 502 récurrent venait du mode **2 workers** : quand un worker devient instable,
  ~50-67% des requêtes tombent en 502 (le SLB round-robin sur le worker mort).
- FIX : relance avec **UVICORN_WORKERS=1** → 20/20 pings à 200, stable. Pour ce stade (trafic faible),
  1 worker = robustesse > débit. (Le launcher relance tout le process en cas de crash, pas de demi-panne.)
- Contexte : la plateforme Jelastic était elle-même perturbée (exec gelé, erreurs Hibernate côté API).

### ⚠️ Urgent (cause racine de tous les flappings)
- La supervision du process n'a PAS de source de vérité unique (relances manuelles vs boot conteneur).
  → **Fiabiliser le boot** (1 process supervisé proprement) est désormais la priorité n°1 de robustesse.
  Tant que ce n'est pas fait, chaque incident peut laisser des process orphelins qui flappent.

═══════════════════════════════════════════════════════════════════════
## Session 2026-06-16 (suite 5) — BOOT/SUPERVISION via pm2 (robustesse racine)
═══════════════════════════════════════════════════════════════════════

### Cause racine du boot cassé (identifiée)
- `nodejs.service` est `Type=forking` et lance le wrapper `/usr/local/sbin/nodejs start`.
- Défaut `PROCESS_MANAGER=npm` → `node server.js` en avant-plan → ne se daemonise pas →
  systemd croit à un échec ("Failed to start", result 4182). C'est pourquoi restartnodebyid échouait.
- Le wrapper supporte nativement pm2/forever/supervisor (lit `$PROCESS_MANAGER`).

### Mise en place (FAIT)
- **App lancée sous pm2** (`pm2 start server.js --name merito`, PM2_HOME=/home/jelastic/.pm2) →
  pm2 daemonise, survit à la fermeture de session exec (fini les orphelins du `setsid`), relance sur crash.
  Vérifié : `pm2 restart merito` → restarts=1, 1 seul uvicorn, app healthy. Stable 14/14.
- **`pm2 save`** → dump persistant (/home/jelastic/.pm2/dump.pm2).
- **`PROCESS_MANAGER=pm2` + `UVICORN_WORKERS=1`** posés dans le stored config (persistants /.jelenv) →
  au boot, le wrapper Jelastic fera lui-même `pm2 start server.js`.

### Limite connue (honnête)
- Je suis l'utilisateur `nodejs` (uid 700), PAS root → impossible d'installer `pm2 startup` (hook systemd).
- systemd `nodejs.service` reporte toujours "failed" (PID file Type=forking non écrit par pm2), MAIS
  le `pm2 start server.js` du wrapper devrait quand même monter l'app au boot.
- **Test reboot complet NON refait** (éviter une coupure délibérée avec clients actifs). Levier de
  récupération prouvé si besoin : `restartcontainersbygroup` (nodeGroup=cp).
- TODO (avec Olivier / accès root) : valider un reboot complet à une heure creuse, ou installer pm2 startup.

═══════════════════════════════════════════════════════════════════════
## Session 2026-06-20 — MIGRATION RAILWAY (production-grade, standard NEO)
═══════════════════════════════════════════════════════════════════════

### Décision (analyse best practices de TOUS les repos NEO)
Toutes les apps NEO tournent sur Railway (Docker/nixpacks, 1 process sur $PORT, healthcheck,
restart ON_FAILURE). Merito avait DÉJÀ Dockerfile+railway.json+entrypoint.sh conformes mais
tournait en env *nodejs* Jelastic avec launcher maison → cause racine de tous les incidents.
→ Déploiement de l'image Docker sur Railway (parallèle, zéro impact prod Jelastic).

### FAIT (Railway) — testé OK
- Projet Railway **merito** (id c0e816c1-69f3-4777-93aa-e8e3b4d4a114), services **merito-api** + **Postgres**.
- Token compte : /mnt/project/Token_railway_UMBRA (c'est un TOKEN COMPTE, pas projet → `RAILWAY_API_TOKEN`,
  PAS `RAILWAY_TOKEN`. CLI `railway` v5.19. whoami = NEO2950 / olivier.neukomm@bluewin.ch).
- Déploiement via `railway up` (build Docker). Migrations Alembic OK sur base fraîche. health=healthy (database ok).
- Vars d'env réutilisent les secrets PROD (JWT_SECRET + **ENCRYPTION_KEY identiques** = indispensable pour migration data).
- URL test : **https://merito-api-production.up.railway.app** — ping 200, register 201 en 0.2–0.9s, stable 10/10.
- FIX code : magic link envoyé en **BackgroundTask** (register/login ne bloquent plus sur SMTP ; avant = 40s !).
  Commit 52c1626 sur main.

### RESTE À FAIRE — bascule (touche clients actifs → coordonné avec Olivier)
1. **DNS merito.ch** (à poser chez Infomaniak — je n'ai pas l'accès DNS, seulement Jelastic) :
   - apex `@`  : CNAME → `m7r3m8kd.up.railway.app`  + TXT `_railway-verify` = `railway-verify=6eff2f63885d2bab9d43ef1841608f8c3a344ebe2f84a949eef8df442739faaa`
   - `www`     : CNAME → `avq93gwi.up.railway.app`   + TXT `_railway-verify.www` = `railway-verify=8455bfa22868cf6ea7f4e094b9190b988371034ac05c4ad08abd724dfc533e11`
2. **Migration data** : `pg_dump` Jelastic (10.101.5.59:5432, db umbra, webadmin) → restore Railway Postgres.
   Même ENCRYPTION_KEY déjà en place. À faire au moment du cutover (minimiser le gap).
3. Mettre `APP_URL`/`UMBRA_FRONTEND_URL` = https://merito.ch après vérif DNS.
4. Jelastk en filet quelques jours puis débranchement.

### Jelastic (prod actuelle) — toujours live sous pm2 le temps de la bascule
umbra-prod.jcloud-ver-jpc.ik-server.com — pm2 (name merito), PROCESS_MANAGER=pm2, 1 worker.

═══════════════════════════════════════════════════════════════════════
## Session 2026-06-20 (suite) — MIGRATION DATA Jelastic → Railway : FAITE & VÉRIFIÉE
═══════════════════════════════════════════════════════════════════════
- Méthode : depuis le node DB Jelastic 206539 (a pg_dump/psql 18.4 + egress vers Railway proxy
  kodama.proxy.rlwy.net:18494). Le SANDBOX ne peut PAS joindre ce proxy TCP (port non-HTTP bloqué)
  → toute opération DB Railway passe par le node Jelastic (scripts base64).
- Connexion source Jelastic : `-h 10.101.5.59 -U webadmin -d umbra` + PGPASSWORD depuis .pgpass
  (localhost/127.0.0.1 = ident auth qui ÉCHOUE ; il FAUT l'IP réseau 10.101.5.59).
- ⚠️ `pg_dump --clean --if-exists | psql` N'A PAS fonctionné (DROP non appliqués → restore vide).
  ✅ Méthode qui marche : `psql "$RAILWAY_URL" -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'`
  puis `pg_dump --no-owner --no-privileges -f dump.sql` puis `psql "$RAILWAY_URL" -f dump.sql`.
- Résultat vérifié : accounts=11, trust_scores=11, credit_balances=11, magic_tokens=11, alembic=0003.
  Mêmes 11 que la source. ENCRYPTION_KEY identique → données chiffrées compatibles.
- ⚠️⚠️ CONSTAT : les 11 comptes sont TOUS @example.com = comptes de TEST. AUCUN compte client réel
  dans la base prod Jelastic. À confirmer avec Olivier (pré-lancement ?).
- Railway URL publique DB : DATABASE_PUBLIC_URL (kodama.proxy.rlwy.net:18494) ; interne :
  postgres.railway.internal:5432. Service Postgres + service merito-api dans projet 'merito'.

### RESTE (cutover, nécessite Olivier)
1. DNS merito.ch chez Infomaniak (records déjà fournis — je n'ai pas l'accès DNS).
2. Au flip : re-sync final (re-DROP SCHEMA + re-dump, 30s) pour capter d'éventuels nouveaux comptes,
   puis APP_URL/UMBRA_FRONTEND_URL = https://merito.ch, puis vérif cert Railway.
3. Jelastic en filet quelques jours.

═══════════════════════════════════════════════════════════════════════
## Session 2026-06-20 (fin) — RAILWAY EN PRODUCTION, vérifié. Reste : DNS (Olivier).
═══════════════════════════════════════════════════════════════════════
- App LIVE & production-grade : https://merito-api-production.up.railway.app
  ping 200, health database:ok, landing premium, register 201 <1s. APP_URL pointe sur cette URL
  → magic links fonctionnels DÈS MAINTENANT sur l'URL railway.
- Data : re-sync final propre (DROP SCHEMA + redump + restore), errors=0, accounts=11 = mirror exact Jelastic.
- GitHub auto-deploy : serviceConnect = 403 (l'app GitHub Railway n'a pas accès au repo O-N-2950/umbra ;
  nécessite autorisation OAuth navigateur d'Olivier). En attendant, deploy via `railway up` depuis le repo local.
- DNS merito.ch : token Infomaniak (/mnt/project/Token_infomaniak) = 401 not_authorized sur TOUS les
  endpoints domain/DNS → PAS le scope DNS. Impossible de poser les records moi-même. NÉCESSITE Olivier
  (interface Infomaniak ou token avec scope DNS).
  Records à poser : @ CNAME m7r3m8kd.up.railway.app + TXT _railway-verify=6eff...faaa ;
  www CNAME avq93gwi.up.railway.app + TXT _railway-verify.www=8455...e11.
- CUTOVER (30s une fois DNS vérifié) : re-sync final + APP_URL=https://merito.ch + redeploy.
- CV analyzer : `analyze_cv` existe en service mais PAS monté en route HTTP dans umbra_main (pré-existant).
