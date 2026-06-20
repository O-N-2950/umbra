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
