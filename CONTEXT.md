# UMBRA — Contexte Projet

> Fichier mis à jour à chaque session. Mémoire persistante entre les conversations.
> ⚠️ LIRE CETTE SECTION DE TÊTE EN PREMIER — c'est l'état réel le plus récent.
> L'historique des sessions 3 à 7 est conservé plus bas pour référence.

═══════════════════════════════════════════════════════════════════════
## 🟢 MAJ 2026-06-25 — VAGUE 1 BEST PRACTICES + QR-FACTURE (gate 🟢 GO)
═══════════════════════════════════════════════════════════════════════

**Qualité/ops installés (Vague 1 du catalogue NEO) — tout testé et déployé :**
- `scripts/check_claims.py` + `legal/claims.md` : garde-fou des claims publics. Bloque superlatifs/certifications/souveraineté absolue. `MERITO_SOVEREIGN_AI=true` (le jour de l'IA CH) débloquera « 100% suisse ».
- `.github/workflows/build-guard.yml` : syntaxe + claims + boot smoke réel (uvicorn+Postgres CI, /ping + /health/deep). Vert au 1er run (sha 4dd465d).
- `backend/api/health_deep.py` → GET /health/deep (racine, router défensif) : database/migrations/smtp/ai_llm/disk, chronométrés. En prod CH : healthy, 19 tables, rev 0003_current, SMTP OK, disk 94.9% libre.
- `scripts/readiness_gate.py <url>` : GO/NO-GO avant toute mise en prod (à utiliser AVANT et APRÈS la bascule DNS). Instance CH = 🟢 GO 6/6.
- `backend/services/qr_invoice.py` : QR-factures suisses (QR-IBAN `CH26 3080 8004 7066 1115 1` ≠ IBAN normal CH95 8080…, réf QRR 27 chiffres mod10r → rapprochement auto MATCHO). Sans TVA (pas de CA — décision Olivier). PEP's Swiss SA, Bellevue 7, 2950 Courgenay, UID CHE-476.484.632. Autonome, non routé (zéro impact).
- Redeploy Jelastic : `redeploycontainersbygroup` (cp, tag latest) — l'API timeout mais l'op continue (~100 s) ; merito.ch (Railway, ancien code) jamais impacté ; Railway n'auto-déploie PAS les push (404 sur /health/deep publique).
- **Rituel institué (mémoire Claude)** : lire CONTEXT.md+TODO.md en début de session ; les mettre à jour + push [skip ci] en fin de session.

═══════════════════════════════════════════════════════════════════════
## 🟢 MAJ 2026-06-22 — MIGRATION SOUVERAINE EN SUISSE (Railway US → Jelastic CH)
═══════════════════════════════════════════════════════════════════════

**État : Merito tourne EN SUISSE sur Infomaniak Jelastic (Docker). Données migrées + vérifiées. Backup opérationnel. Bascule DNS publique PAS encore faite.**

- **Migration souveraine nLPD** : backend redéployé sur Infomaniak Jelastic (Suisse). Image Docker `python:3.12-slim-bookworm` (⚠️ Debian 13/trixie REFUSÉ par Jelastic) → GHCR (`ghcr.io/o-n-2950/umbra:latest`) → pull Jelastic (user NEO2950 + PAT). App LIVE : `merito-prod.jcloud-ver-jpc.ik-server.com`, /health `database:ok`.
- **DB PostgreSQL 16** sur Jelastic (intIP 10.101.29.37, base `umbra`, user `webadmin`). **Migration Railway→CH vérifiée par checksum md5** (4 tables, 11 lignes, MATCH). UUID (pas de séquence à resync). 19 variables d'env sur node cp.
- **Backup souverain** : `/var/lib/pgsql/backup_merito.py` (Python pur) : pg_dump → gzip → AES-256 (`.backup_key` = ENCRYPTION_KEY) → **Swiss Backup S3** (`s3.swiss-backup04.infomaniak.com`, bucket `default`, préfixe `merito/`) via **SigV4 maison** (PAS mcli — instable). **Cron 03:00**, crond actif, **restauration testée OK** (19 tables). Secrets node DB : `.dbpw` (41o), `.backup_key` (65o), `.s3acc`, `.s3sec`.
- **Flux audités** : DB CH ✓ ; SMTP Infomaniak CH (`_send_via_smtp`, login testé) ✓ ; Zefix/UID admin.ch ✓ ; CV jamais stocké en brut (profil anonyme dissocié) ✓ ; **PII Shield** anonymise avant Gemini ✓ ; PostHog/Stripe INACTIFS ✓. Seul flux hors-CH = analyse CV → **Gemini US** (anonymisé). Mineurs : Google Fonts (IP), OpenIBAN.
- **Test fonctionnel CH** : register HTTP 201 (compte créé DB CH), magic link 200, SMTP login OK, /credits/pricing 200. ⚠️ `/sectors` vide (non seedé — Railway idem, pas une régression).
- **RESTE avant prod publique** : (1) **bascule DNS merito.ch → Jelastic CH** + re-sync finale + SSL ; (2) restaurer claim « Hébergé en Suisse » ; (3) **[ACTION OLIVIER, reportée]** activer IA Infomaniak + clé → brancher CV Gemini→Llama 3.3 70B (compatible OpenAI ; coût négligeable, perf équivalente ; PII Shield couvre l'intérim).
- **Accès Jelastic** : token `/mnt/project/token_full_access_JELASTIC_CLOUD_INFOMANIAK`, API `app.jpc.infomaniak.com/1.0/`, env `merito-prod`, node cp 207686 / DB 207685. ExecCmd node DB = user `postgres` mais **HOME=/root** (forcer HOME=/var/lib/pgsql). Shell = **dash**. Scripts via **base64**. pg_dump password via PGPASSWORD (jamais dans l'URL).

═══════════════════════════════════════════════════════════════════════
## 🟢 MAJ 2026-06-16 (soir) — MERITO + MAGIC LINK SMTP OPÉRATIONNEL
═══════════════════════════════════════════════════════════════════════

- **REBRAND : UMBRA → Merito.** Domaine public = **merito.ch** (umbra.ch était pris).
  Slogan retenu : **« Les compétences avant l'identité. »** Branding piloté par `BRAND_NAME=Merito`.
- **Register prod = 201** (le 500 venait d'un uvicorn pré-fix collé au port 3000, pas du code).
- **`DATABASE_URL` persisté avec mot de passe** dans `/.jelenv` (avant : corrigé en mémoire seulement).
- **Magic link branché sur SMTP Infomaniak** (`contact@merito.ch`) : SMTP-first → fallback Resend → log.
  Commit `d9783f8`. Variables prod : `SMTP_*`, `EMAIL_ENABLED=true`, `APP_URL`, `BRAND_NAME`, `ENV=production`.
- **DNS merito.ch publié** (NS ns11/ns12.infomaniak.ch, MX mta-gw.infomaniak.ch) → **envoi mail OK de bout en bout**.
  Reste (action Olivier) : SPF/DKIM/DMARC (anti-spam) ; A/CNAME merito.ch → Jelastic si le site doit vivre sur merito.ch.
- **Pièges clés** : `AddContainerEnvVars` n'upsert pas les clés existantes (éditer `/.jelenv`) ;
  ne PAS `restartnodebyid` (systemd cassé, launcher manuel) → relancer `setsid node server.js` ;
  tuer les uvicorn PAR PORT (`fuser -k 3000/tcp`), pas par `pkill -f uvicorn`.
- **Prochaine priorité : LOT 4** (pricing serveur + Stripe + preuve d'embauche).

═══════════════════════════════════════════════════════════════════════
## 🟢 ÉTAT ACTUEL — 2026-06-16 (Session Jelastic + LOT 1-3 + PROD LIVE)
═══════════════════════════════════════════════════════════════════════

### EN UNE PHRASE
UMBRA (plateforme de recrutement anonyme suisse, PEP's Swiss SA / Groupe NEO) est
**EN PRODUCTION sur Jelastic Infomaniak (Genève, Suisse)**, API 100% fonctionnelle,
base PostgreSQL connectée. Reste : LOT 4 (Stripe/pricing serveur), LOT 5 (viral),
front consolidé, et branchement Hunteed.

### ✅ URL PROD LIVE
- **https://umbra-prod.jcloud-ver-jpc.ik-server.com** (Jelastic Infomaniak, Genève 🇨🇭)
- `/ping` → 200 `{"ok":true}` | `/health` → 200 healthy (DB ok) | `/app` → 200 (landing)
- `/api/v1/sectors` → 200 | `/api/v1/matches/` → 401 (protégé) | register → 201

### 🏗 INFRA JELASTIC (production) — paramètres exacts
- Endpoint API Jelastic : `https://app.jpc.infomaniak.com/1.0/{path}` + `appid=cluster` + `session=<JELASTIC_TOKEN>`
- Env : `umbra-prod` | région `user2_region` (jcloud-ver-jpc) | status running | SSL actif
- Node CP (app) : **id 206538**, type `nodejs`, **Python 3.9.25** (pip installé via ensurepip)
- Node DB : **id 206539**, PostgreSQL 18.4, IP interne **10.101.5.59:5432**
  - DB `umbra` créée, user `webadmin`, **password `<password PostgreSQL: récupérer via .pgpass du node db 206539>`**
  - `DATABASE_URL=postgresql://webadmin:<password>@10.101.5.59:5432/umbra`
  - 19 tables, 3 migrations Alembic appliquées (0001, 0002, 0003)
- **MÉCANISME DE DÉPLOIEMENT (CLÉ — appris de PLACIO)** :
  - Le node nodejs Jelastic route le trafic public vers le **PORT 3000** (PAS 80, PAS 8000)
  - Au boot, le node lance `npm start` → `node /home/jelastic/ROOT/server.js`
  - `server.js` est un **lanceur** qui spawn `uvicorn umbra_main:app --port 3000`
  - Le code UMBRA vit dans `/home/jelastic/umbra/backend/` (cloné depuis GitHub main)
  - Après modif : `restartservices` (groupe cp) reconnecte le SLB au port 3000
  - ⚠️ La variable `PORT` doit valoir **3000** (sinon uvicorn écoute ailleurs → 502)
- Sandbox Claude : **réseau OUVERT vers Jelastic** cette session (avant il était bloqué).
  Si re-bloqué, passer par GitHub Actions (workflow `jelastic-deploy.yml`).

### 🔑 TOKENS ACTIFS (fichiers projet /mnt/project/)
- GitHub : `<voir fichier projet token_Github>` (fichier `token_Github`) — VALIDE, login O-N-2950
- Jelastic : `<voir fichier projet token_full_access_JELASTIC_CLOUD_INFOMANIAK>` (`token_full_access_JELASTIC_CLOUD_INFOMANIAK`) — VALIDE
- Infomaniak API : `<voir fichier projet Token_infomaniak>` (`Token_infomaniak`)
- Gemini : `<voir fichier projet Google_studio_GEMINI_key>` (`Google_studio_GEMINI_key`)
- Railway : `<voir fichier projet Token_railway_UMBRA>` (`Token_railway_UMBRA`) — Railway = STAGING uniquement
- S3 Infomaniak Swiss Backup (umbra-db) : endpoint `https://s3.swiss-backup04.infomaniak.com`,
  Access `<voir fichier projet infomaniak_Swiss_Backup_umbra-db>`, Secret `<voir fichier projet infomaniak_Swiss_Backup_umbra-db>`
- ⚠️ **ACTION OLIVIER EN ATTENTE** : révoquer l'ancien token GitHub exposé `<ancien token GitHub exposé — commençant par ghp_BkM4, présent dans 2 vieux commits>`
  (présent dans 2 commits de l'historique git public — révocation seule suffit à neutraliser)

### 📦 REPOS (strictement séparés — NE JAMAIS CONFONDRE)
- **`O-N-2950/umbra`** : PUBLIC, branche défaut `main`. C'EST LE REPO UMBRA.
- **`O-N-2950/matcho`** : PRIVÉ, branche `master`. App DISTINCTE (réconciliation bancaire fiduciaires).
- Autres repos NEO : PLACIO (privé, MAJUSCULES), tournepage, boom-contact, cctswiss, kido-pwa,
  kombo-api, neo-watcher, peps-swiss-site, pepssolutions-avatar-engine, claude-skills.

### ✅ LOTS LIVRÉS CETTE SESSION (commités + poussés + testés)
- **LOT 1 — Fondations** : bug `metadata`→`meta` (migrations OK base vierge) ; 18 routes
  `Depends(lambda:None)`→auth réelle. API passée de 50% HTTP 500 à 100% fonctionnelle.
- **LOT 2 — Divorce MATCHO** : sel crypto `umbra-salt-2026-pep-swiss` (était matcho-salt) ;
  loggers/domaines/emails `umbra.*` ; token GitHub purgé de deploy.sh/deploy.py ;
  CONTEXT.md corrigé (repo umbra, stack Jelastic+PostgreSQL/PostGIS).
- **LOT 3 — Anonymat architectural (engagement légal)** :
  - PII Shield (`backend/services/pii_shield.py`) renforcé : masque nom, email, tél CH, AVS,
    IBAN, date naissance, **ville/NPA suisse**, **rue+numéro**, LinkedIn, employeurs.
    Neutralise injections **FR + EN**. Testé : ZÉRO fuite sur CV piégé.
  - Prompt CV délimité `<profil_candidat_non_fiable>` + instruction sécurité (défense profondeur).
  - Branché dans `cv_analyzer_prompt.py` (anonymise AVANT envoi Gemini hors Suisse) + validation
    de sortie (bornes score 0-100, classification enum, métadonnées `_compliance`).
  - Révélation mutuelle ATOMIQUE : verrou `with_for_update` sur le match (`umbra_matches.py`).
  - Blocage faux-poste AUTO : champ `current_employer_ide` sur Account + `_merge_block_list()`
    injecte l'employeur actuel dans la block-list (migration 0003). L'employeur ne peut plus
    débusquer ses salariés en veille via un faux poste.
- **FIX PROD CRITIQUE** : `PgEnum` (values_callable) sur les 8 colonnes Enum. L'enum
  `AccountType(str,Enum)` persistait le NOM (CANDIDATE) au lieu de la VALEUR (candidate) →
  500 register sur PostgreSQL, invisible en SQLite. Best practice parité dev/prod (PLACIO/Tournepage).
- **CI nettoyée** : 1 seul workflow canonique `jelastic-deploy.yml` (3 obsolètes supprimés).

### 🟡 RESTE À FAIRE (priorité décroissante) — détail dans TODO.md
1. **Vérifier le register en prod** après le dernier déploiement du fix PgEnum (commit 71250f1).
2. **LOT 4 — Business/Stripe** : `compute_listing_price(salaire)` SERVEUR (barème 6.5-11%) +
   Stripe Checkout sur ce montant + webhooks + preuve d'embauche pour remboursement 50%/30j.
3. **LOT 5 — Viral** : CV analyzer "Combien vaut mon profil ?" partageable anonymisé ;
   indice de marché caché (PR) ; passeport de confiance portable/exportable.
4. **Front consolidé** : un seul Next.js depuis `umbra-v3-pricing.jsx` (le plus abouti),
   branché sur FastAPI réel. Supprimer `client/src` (tRPC mort). Migrer cv-analyser + smart-onboarding.
5. **CORS** : aligner `ALLOWED_ORIGINS` sur le domaine réel (umbra.ch ou jcloud) — actuellement
   umbra.work/jobs qui ne correspondent pas au déploiement.
6. **Chiffrement PII au repos** : importer le pattern Tournepage AES-256-GCM
   (`enc:iv:authTag:ciphertext`) pour chiffrer l'identité candidat stockée (classes A/B/C/D).
7. **Stockage CV souverain** : S3 Infomaniak (`s3.pub1.infomaniak.cloud`, forcePathStyle,
   region us-east-1) — runbook dans le repo Tournepage. Ne PAS confondre avec Swiss Backup.
8. **HUNTEED** : brancher UMBRA sur Hunteed (plateforme FR recrutement externalisé, présente
   CH+LU, offres anonymisées, succès 12% brut). Besoin : doc API Hunteed OU accès/credentials
   d'Olivier. Intégration cible : importer leurs missions dans le matching + pousser des candidats.
9. **MATCHO (session séparée)** : retirer le code UMBRA résiduel de matcho/backend/static/index.html.

### ⚠️ BEST PRACTICES IMPORTÉES DE PLACIO & TOURNEPAGE (à réutiliser)
- **PLACIO** : déploiement Jelastic = port 3000 + `/home/jelastic/ROOT/server.js` lanceur +
  `restartservices` ; déploiement par COPIE de fichier (FileService.Write bloqué → execcmdbyid) ;
  toujours récupérer le fichier LIVE avant de patcher (le prod peut avoir dérivé du repo).
- **TOURNEPAGE** : classification PII A(chiffré)/B(clair)/C(hashé)/D(jamais stocké) ;
  chiffrement AES-256-GCM `encryption.js` format `enc:iv:authTag:ciphertext` ;
  runbook S3 Infomaniak souverain ; runbooks migration PII détaillés.

### 🧭 RÈGLES PERMANENTES
- Séparation stricte MATCHO/UMBRA (repos + bases + secrets séparés).
- Jamais de clé API committée en clair.
- Tester réellement (TestClient fiable en sandbox) AVANT chaque commit.
- Après push → vérifier (run GitHub Actions OU ping prod). Ne jamais enchaîner sans vérifier.
- Données recrutement = ultra-sensibles (nLPD). Anonymat = engagement LÉGAL, pas marketing.
- Railway = staging (données fictives) ; Jelastic Infomaniak Genève = prod (données réelles).
- Travail par lots testés ; code stable et robuste exigé.

---

## Dernière mise à jour : 2026-02-27 — Session 3 : Modèle économique à la valeur réelle

---

## 🎯 Vision Produit

**UMBRA** est la première plateforme de recrutement où l'anonymat est architectural, le matching est prédictif, et la confiance est certifiée par le comportement réel — pas les déclarations.

> "Le talent se cache. Nous le trouvons."

> "Tous les concurrents font payer la visibilité. UMBRA fait payer la valeur."

- **Marché cible** : Suisse (Arc Jurassien, Bâle, Genève, Zurich) → Europe francophone
- **Entité** : PEP's Swiss SA (Groupe NEO)
- **Repo** : https://github.com/O-N-2950/umbra
- **Domaine** : à finaliser (umbra.work / umbra.jobs / umbra.ch)
- **Stack hosting** : Jelastic Infomaniak (Genève, Suisse) — prod ; Railway — staging

---

## 💡 Les 10 Game Changers

1. **Marché caché visible** — 70% des postes ne sont jamais publiés. Intentions futures croisées avec candidats en veille.
2. **Anonymat par architecture** — Protection employeur actuel. Révélation uniquement si les DEUX confirment.
3. **Empreinte Culturelle IA** — Quiz 5 questions → radar 6 dimensions. Matching: compétences × culture × géo × salary × durabilité.
4. **Passeport de Confiance** — Score basé comportement réel (event-sourcing). Auditable.
5. **Entretien Inversé** — Candidat interroge l'entreprise anonymement AVANT de se révéler.
6. **Intelligence Marché temps réel** — Salaires médians, pénuries, prédictions IA 18 mois.
7. **Révélation Mutuelle Cinématique** — Double confirmation → animation → identités dévoilées.
8. **Prédictions IA 18 mois** — Gemini Flash sur données réseau UMBRA.
9. **Mode Veille Passive** — 10 min d'inscription. Notification si match > seuil. Capture les talents qui ne cherchent pas.
10. **Off-boarding = Prochaine Entrée** — Départ structuré → recommandations → profil réactivé automatiquement.

---

## 💰 Modèle Économique — Tarification à la Valeur Réelle

### Principe fondamental

**Le prix de l'annonce est indexé sur le salaire déclaré — pas un abonnement fixe.**

Les deux parties paient : le postulant selon sa prétention salariale, l'entreprise selon le salaire du poste à pourvoir. Avant de remplir le moindre formulaire, un calculateur affiche le prix final. Transparent. Équitable. Jamais surprenant.

### Barème progressif (% du salaire mensuel brut)

| Tranche mensuelle | Taux  | Exemple           | Prix annonce |
|-------------------|-------|-------------------|-------------|
| 3 000 – 4 500 CHF | 6.5%  | Opérateur 4 000   | CHF 260     |
| 4 500 – 7 000 CHF | 7.5%  | Technicien 6 000  | CHF 450     |
| 7 000 – 10 000 CHF| 8.5%  | Ingénieur 8 000   | CHF 680     |
| 10 000 – 15 000 CHF| 9.5% | Directeur 12 000  | CHF 1 140   |
| 15 000 CHF +      | 11.0% | C-Level 18 000    | CHF 1 980   |

**Validité :** 90 jours. Prolongation gratuite si aucun match en 90 jours.

**Remboursement partiel** : si embauche confirmée dans les 30 premiers jours, remboursement de 50% du prix annonce (récompense la rapidité du réseau).

### Comparatif concurrentiel

| Solution              | Coût même profil 8k/mois | Anonymat | Matching culturel |
|-----------------------|--------------------------|----------|------------------|
| 🌑 UMBRA              | CHF 680                  | ✓ Total  | ✓ 6 dimensions   |
| Chasseur de tête      | CHF 17 000 – 24 000      | ✗        | ✗                |
| LinkedIn Recruiter    | CHF 1 188/an (fixe)      | ✗        | ✗                |
| Indeed / JobUp        | Variable/clic            | ✗        | ✗                |

UMBRA est **10 à 35× moins cher** que le recrutement traditionnel pour un résultat structurellement supérieur.

### Effet vertueux de la tarification à la valeur

- **Filtre naturel** : les profils opportunistes (qui s'inscrivent partout sans intention) n'entrent pas. Chaque profil a payé pour être là.
- **Qualité moyenne structurellement supérieure** aux plateformes gratuites.
- **Prix perceptible comme juste** : le candidat qui paie 450 CHF pour trouver un poste à 72k/an paie 0.6% de sa première année. Le ROI est visible avant même de remplir le formulaire.

### Calculateur de prix — Écran 0 (avant onboarding)

Interface interactive affichée AVANT tout formulaire :
- Slider salaire mensuel (3 000 – 25 000 CHF)
- Prix calculé en temps réel avec animation
- Tranche active mise en évidence
- Tableau comparatif intégré (chasseur de tête, LinkedIn, Indeed)
- ROI calculé (×N le salaire annuel / prix annonce)
- CTA "Je comprends — commencer mon profil →"

Fichier prototype : `umbra-v3-pricing.jsx`

---

## 🏗 Stack Technique

| Composant       | Technologie                                    |
|-----------------|------------------------------------------------|
| Frontend        | React / Next.js PWA (prototype: umbra-v3-pricing.jsx) |
| Backend         | FastAPI (Python) — Railway                     |
| Base de données | PostgreSQL + PostGIS (distances géo)           |
| ORM             | SQLAlchemy + Alembic (migrations)              |
| Matching        | Algorithme maison (matching_engine.py) + Gemini Flash |
| Auth            | JWT — profil anonyme dissocié du compte réel   |
| Paiement        | Stripe (annonces à la valeur + remboursements) |
| IA              | Google Gemini Flash (prédictions marché)       |
| Monitoring      | Pattern Groupe NEO (crash_monitor + health)    |
| Repo            | https://github.com/O-N-2950/umbra             |

---

## 📁 Fichiers produits

| Fichier                              | Description                                    |
|--------------------------------------|------------------------------------------------|
| `umbra-v3-pricing.jsx`              | Prototype React v3 — 10 écrans (pricing + 9)  |
| `backend/db/umbra_models.py`        | Schéma PostgreSQL complet (17 tables)          |
| `backend/services/matching_engine.py`| Algorithme matching multicritères             |
| `backend/services/trust_service.py` | Event-sourcing score de confiance              |
| `backend/services/geo_service.py`   | Zones postales CH + Haversine + anonymisation  |
| `backend/db/seed_data.py`           | 9 secteurs + ~100 compétences + zones postales |
| `backend/db/session.py`             | Pool connexions PostgreSQL                     |
| `backend/api/umbra_auth.py`         | Magic link + JWT                               |
| `backend/api/umbra_profiles.py`     | CRUD profils + quiz culturel + compétences     |
| `backend/api/umbra_matches.py`      | Matching + signaux + entretien inversé         |
| `backend/api/umbra_trust.py`        | Passeport + annonces Stripe + webhooks         |
| `backend/umbra_main.py`             | FastAPI app avec tous les routers              |
| `backend/migrations/0001_umbra_init.py` | Migration Alembic complète                |

---

## 🗄 Architecture Base de Données (17 tables)

```
accounts               → Identité réelle chiffrée AES-256
anonymous_profiles     → Profil visible matching (jamais lié publiquement au compte)
sectors / skills       → Référentiel secteurs (9) et compétences (~100)
profile_skills         → Compétences déclarées (niveau + vérification post-embauche)
culture_profiles       → Vecteur culturel 6D calculé depuis quiz
matches                → Correspondances calculées (score composite pondéré)
interest_signals       → Signaux d'intérêt (révélation si DOUBLE confirmation)
inverse_questions      → Entretien inversé (max 3 questions par match)
trust_events           → Event-sourcing score de confiance (immuable)
trust_scores           → Score dénormalisé pour performance
credit_balances        → Solde annonces (remplace système crédits)
credit_transactions    → Historique mouvements + Stripe payment intents
offboardings           → Départ structuré → réactivation auto profil
market_snapshots       → Données marché agrégées anonymisées (mensuel)
salary_benchmarks      → Benchmarks salariaux + prédictions IA Gemini
audit_logs             → Journal immuable toutes actions sensibles
```

---

## ⚙️ Algorithme de Matching

Score composite pondéré [0–100] :
```
score = (skills × 0.40) + (culture × 0.20) + (geo × 0.20) + (salary × 0.15) + (durabilité × 0.05)
```

---

## ⭐ Système de Confiance

| Grade      | Score | Accès                                         |
|------------|-------|-----------------------------------------------|
| PLATINUM   | > 4.5 | Accès talents passifs en mode SHADOW          |
| GOLD       | > 4.0 | Badge Certifié visible dans les matchs        |
| STANDARD   | > 3.0 | Accès normal                                  |
| RESTRICTED | > 2.0 | Réception uniquement                          |
| SUSPENDED  | ≤ 2.0 | Banni                                         |

Anti-espionnage : 10 contacts sans embauche consécutifs → suspension automatique.

---

## 🎨 Design System

| Token         | Valeur           |
|---------------|------------------|
| void          | #05080e          |
| copper        | #d97b3a          |
| ice           | #edeae4          |
| Display font  | Playfair Display |
| Mono font     | JetBrains Mono   |
| Body font     | Outfit           |

---

## 🔗 Synergies Groupe NEO

- **WIN WIN** : Entreprises UMBRA → prospects assurance RC pro / cyber / collective
- **PEP's** : PME réseau PEP's → onboarding prioritaire entreprises UMBRA
- **J'VAIS** : Candidats mobiles → recommandation UMBRA pour opportunités régionales
- **Soluris** : Questions droit du travail → redirection Soluris
- **MATCHO (bancaire)** : PME bien gérées → cibles recrutement UMBRA

---

## 🤖 Outils IA — Analyse de CVs (Session 3)

### Produit B2B autonome : Analyseur de CVs

Un deuxième produit à part entière intégré dans UMBRA. L'entreprise apporte ses propres CVs reçus (email, LinkedIn, courrier) — indépendamment du réseau UMBRA — et paie pour une analyse IA structurée.

**Modèle commercial :** 2–5 CHF par CV analysé. Marge quasi totale (Gemini Flash ~0.0002 CHF/analyse).

**Ce que le recruteur reçoit pour chaque CV :**
- Score global /100
- Classification : A-Player / Intéressant / Conditionnel / Refusé
- Détail par dimension : technique, culturel, salarial, trajectoire
- 3 questions suggérées pour entretien (si profil retenu)
- Signal de risque si identifié

### Architecture du Prompt Système (6 couches — cours Yass)

Structure validée scientifiquement :
1. **Rôle** (Role Prompting +10.3% précision)
2. **Tâche** + Chain of Thought (+90% sur tâches complexes) + variable CV
3. **Spécificité** + Emotion Prompt (+115% tâches complexes)
4. **Contexte** entreprise + importance tâche
5. **Exemples** Few-Shot (5 exemples input/output calibrés marché suisse)
6. **Notes** anti-Lost-in-the-Middle + format JSON + température 0

**Dimensions UMBRA ajoutées :** alignement culturel (quiz 6D), prétention salariale vs budget poste, mobilité géographique — critères absents des outils génériques.

**Fichier prompt :** `backend/services/cv_analyzer_prompt.py`

### Générateur de CV IA (Produit candidat)

Gemini Flash génère le CV depuis le profil UMBRA → template PDF aux couleurs UMBRA → logo + `umbra.work` discret en bas de page.

**Logique virale :** chaque CV envoyé à un recruteur externe porte UMBRA. Signal de qualité pour le recruteur (candidat sérieux, a payé pour chercher). Acquisition organique zéro coût.

**Limites :** 2 CVs offerts (mode veille), 5 inclus (mode actif), 9 CHF/unité ensuite.

**Fichier :** `backend/services/cv_generator.py`

---

## ✅ TODO LIST — État Session 3

### Complété
- [x] Modèle économique tarification à la valeur (% salaire mensuel)
- [x] PricingCalculator écran 0 dans prototype v3 (umbra-v3-pricing.jsx)
- [x] Prompt système analyseur CVs 6 couches (cv_analyzer_prompt.py)
- [x] CONTEXT.md mis à jour

### En cours / Prochain
- [ ] Interface recruteur dans prototype (écran "Analyser un CV")
- [ ] Endpoint FastAPI umbra_tools.py — brancher Gemini Flash + crédits
- [ ] Générateur de CVs candidat (Gemini Flash + PDF template UMBRA)

### Améliorations prompt cv_analyzer_prompt.py identifiées
- [ ] Passer de 5 à 10–32 exemples Few-Shot avec vrais cas validés terrain
- [ ] Injecter le vecteur culturel 6D UMBRA comme variable structurée quand le candidat vient du réseau (actuellement l'IA le déduit depuis le texte — moins précis)

### Générateur CV candidat (rappel)
- Logo + umbra.work discret en bas = publicité virale organique
- Signal de qualité pour recruteur externe (candidat a payé = sérieux)
- Limites : 2 CVs offerts (veille), 5 inclus (actif), 9 CHF/unité ensuite
- Stack : Gemini Flash (contenu) + PDF Python (template)

---

## 🚦 DÉCISIONS STRATÉGIQUES — Session 4

### Facturation analyses CV — Décision actée

**Phase lancement (maintenant) :** analyses CV gratuites pour tous les recruteurs connectés.
Coût réel Gemini Flash ~0.0002 CHF/analyse — risque financier nul.
Objectif : adoption sans friction, prouver la valeur avant de monétiser.
Code : FLAG_FACTURATION dans server/routers.ts

**⚠️ RAPPEL AUTOMATIQUE — À activer dès 10 embauches documentées :**
Passer à l'Option 2 — analyses bundlées dans l'annonce UMBRA :
- Toute annonce active (durée 90 jours) → analyses CV illimitées incluses
- Le coût (~0.0002 CHF) est absorbé dans la marge de l'annonce (680 CHF+)
- Pas de ligne de revenus séparée — c'est un argument différenciateur vs LinkedIn/Indeed
- Fichier à modifier : server/routers.ts → remplacer FLAG_FACTURATION par vérification annonce active

**Modèle écarté :** crédits prépayés (trop générique, ne correspond pas au positionnement UMBRA premium)

### Fichiers livrés — Session 4 (interface recruteur complète)
- [x] server/cv-analyzer.ts — service TypeScript, prompt 6 couches, invokeLLM
- [x] server/routers.ts — endpoints tRPC umbra.analyzeCV + umbra.cvPricing
- [x] client/src/pages/CVAnalyzer.tsx — page React, tRPC mutation, 4 onglets résultat
- [x] client/src/App.tsx — route /cv-analyzer ajoutée

### Prochaines étapes
- [ ] Ajouter lien "Analyser un CV" dans le Dashboard principal
- [ ] Tester le flow complet sur Railway (déploiement)
- [ ] Générateur de CVs candidat (Gemini Flash + PDF template UMBRA)
- [ ] Améliorer prompt : passer à 10-32 exemples Few-Shot avec vrais cas terrain
- [ ] Injecter vecteur culturel 6D quand candidat vient du réseau UMBRA

---

## 🚀 SESSION 5 — État complet au 06/03/2026

### ⚠️ OLIVIER A SES PREMIERS CLIENTS — PRIORITÉ ABSOLUE : SITE EN PRODUCTION

### 🔴 PROBLÈME EN COURS : 502 Railway
**Cause identifiée :** App crash avant d'écouter — logs Railway nécessaires
**Fichiers ajoutés pour résoudre :**
- `railway.toml` : healthcheck /health + restart ON_FAILURE x10
- `server/_core/index.ts` : endpoint GET /health ajouté
**Action requise :** Olivier doit copier les Build Logs + Deploy Logs Railway ici

### ✅ CE QUI EST LIVRÉ ET FONCTIONNEL (code)
- `server/cv-analyzer.ts` — prompt 6 couches, invokeLLM Gemini Flash
- `server/routers.ts` — tRPC umbra.analyzeCV + umbra.cvPricing
- `client/src/pages/CVAnalyzer.tsx` — interface recruteur complète
- `client/src/App.tsx` — route /cv-analyzer
- `client/src/pages/Dashboard.tsx` — carte Outils UMBRA + lien sidebar
- `client/src/hooks/usePersistentForm.ts` — hook localStorage réutilisable
- localStorage persistence sur CVAnalyzer, Survey, MatchNew

### 📋 TODO LIST COMPLÈTE PAR PRIORITÉ

#### P0 — BLOQUANT (site en production)
- [ ] Résoudre 502 Railway → logs nécessaires
- [ ] Vérifier variables ENV sur Railway (DATABASE_URL, BUILT_IN_FORGE_API_KEY, JWT_SECRET)
- [ ] Tester flow complet CVAnalyzer en production

#### P1 — CRITIQUE (clients actifs)
- [ ] Crash monitor inspiré WinWin V2 (heartbeat 5min, alerte email, /health)
- [ ] Error boundaries React sur toutes les pages
- [ ] Logging structuré côté serveur (chaque analyse CV loggée)
- [ ] Page d'erreur 500 propre (pas de crash visible)

#### P2 — IMPORTANT (expérience client)
- [ ] Améliorer prompt CV : passer 5→10-32 exemples Few-Shot avec vrais cas terrain
- [ ] Injecter vecteur 6D UMBRA quand candidat vient du réseau
- [ ] Historique analyses CV par recruteur (liste + recherche)
- [ ] Export rapport CV en PDF

#### P3 — ROADMAP
- [ ] Générateur de CVs candidat (Gemini Flash + PDF template UMBRA)
- [ ] Billing : activer FLAG_FACTURATION après 10 embauches documentées
- [ ] Quiz culturel 6D intégré au flow candidat complet
- [ ] Dashboard analytics recruteur (stats analyses, taux A-Player, etc.)

### 🔧 RÈGLES TECHNIQUES ABSOLUES
1. Toujours vérifier HTTP status après chaque commit Railway
2. Ne jamais enchaîner commits sans vérifier que le site tient
3. Utiliser Git Blobs API pour les gros fichiers (>100KB)
4. Toujours lire CONTEXT.md en début de session

### 💰 FACTURATION
- FLAG_FACTURATION dans server/routers.ts ~ligne 252
- Activer quand 10 embauches documentées
- Modèle : analyses bundlées dans annonce UMBRA (pas de crédits séparés)

### 📦 STACK TECHNIQUE
- Frontend : React + TypeScript + Tailwind + shadcn/ui + tRPC client
- Backend : Node.js + Express + tRPC + Drizzle ORM
- IA : Gemini Flash via invokeLLM (server/_core/llm.ts)
- DB : PostgreSQL + PostGIS (DATABASE_URL)
- Deploy : Jelastic Infomaniak (umbra-prod, Genève) — prod ; Railway — staging
- Repo : github.com/O-N-2950/umbra


---

## 🚀 SESSION 7 — Observabilité complète — 31/03/2026

### ✅ Accompli cette session
- `/api/umbra/cv-analyze` — 100% opérationnel (testé: Sophie Müller 86/100 A-Player ✅)
- Sentry backend Python — `monitoring/analytics.py` → `init_sentry()` au boot
- PostHog events server-side — proxy `/api/v1/analytics/track` (clé jamais exposée)
- GA4 + Sentry browser — injectés dans `static/index.html` via meta tags
- Hook TypeScript `useAnalytics()` + `client/src/lib/analytics.ts`
- 8 events UMBRA définis (`UmbraEvent.LANDING_VUE` → `ABONNEMENT_ACTIVE`)
- `DEPLOY_CHECKLIST.md` créée (scanner secrets + vérif post-deploy)
- Variables Railway injectées: `SENTRY_DSN`, `POSTHOG_API_KEY`, `GA4_MEASUREMENT_ID`, `POSTHOG_HOST` (EU)
- `APP_NAME` corrigé MATCHO→UMBRA sur Railway

### 📋 Variables à remplir (Sentry + PostHog + GA4)
1. **Sentry** → sentry.io → New Project → Python → copier DSN → Railway `SENTRY_DSN`
2. **PostHog** → eu.posthog.com → New Project → copier clé `phc_xxx` → Railway `POSTHOG_API_KEY`
3. **GA4** → analytics.google.com → Créer propriété → `G-XXXXXXXXXX` → Railway `GA4_MEASUREMENT_ID`
4. Idem `SENTRY_DSN_FRONTEND` pour le browser SDK

### 🔧 Architecture analytics UMBRA

```
Candidat/Employeur
      │
      ▼
React track() ──────────► POST /api/v1/analytics/track
                                    │
                      ┌─────────────┼─────────────┐
                      ▼             ▼              ▼
                  PostHog        Sentry         GA4
               (product)       (errors)      (traffic)
               eu.posthog.com  sentry.io    analytics.google
```

### 📊 Events PostHog actifs
| Event | Déclenché quand |
|---|---|
| `landing_vue` | Page UMBRA chargée |
| `inscription_démarrée` | Clic CTA inscription |
| `profil_candidat_créé` | Profil candidat sauvegardé |
| `offre_publiée` | Employeur publie une annonce |
| `matching_déclenché` | Algorithme matching lancé |
| `contact_initié` | Signal d'intérêt envoyé |
| `checkout_lancé` | Flow Stripe démarré |
| `abonnement_activé` | Paiement Stripe confirmé |

### 🔴 Reste à faire (P0)
- Remplir les 4 variables analytics sur Railway
- Vérifier `/api/v1/analytics/events` → `posthog_active: true`
- Tables DB manquantes (fiduciaries, clients...) → alembic stamp + migration

### 🟠 Reste à faire (P1)
- Déclencher `inscription_démarrée` dans la route `/api/v1/auth/register`
- Déclencher `checkout_lancé` dans `umbra_credits.py` route checkout
- Déclencher `abonnement_activé` dans le webhook Stripe
- Déclencher `matching_déclenché` dans `umbra_matches.py`

## 2026-06-20 — Refonte visuelle de la home (thème « Aurore ») + déploiement Railway
- Home **merito.ch** ré-habillée en thème CLAIR « Aurore » : halos pastel, cartes verre (glass), police Plus Jakarta Sans, accent violet #7C5CFC, dégradés. **Contenu et scripts inchangés** (inscription `/api/v1/auth/register`, analyseur CV, FAQ `<details>`, compteurs animés, canvas réseau).
- **Méthode** : calque CSS superposé injecté en fin de `<style>` + remap des variables (`--void/--ice/--copper`… → palette claire, mêmes noms = compat JS/inline) + halos via `body::before/::after` + recolor du canvas (copper→violet) en JS. Verrou `color-scheme: light only` (propriété CSS + meta) = anti dark-mode forcé du mobile.
- **Déploiement** : commit GitHub `765883e` → build Railway via `railway up` (service `merito-api` non connecté au repo → `up` obligatoire, l'auto-deploy GitHub ne se déclenche pas). Déploiement `bf0f693f` = SUCCESS. Vérifié : ping/home 200, health `database:ok` env=production, version Aurore servie (AURORE OVERLAY + Plus Jakarta), capture live OK.
- **Rollback** : ancien `index.html` = sha `3f7374964a103270476c67c09a1554e333ae0477` (PUT contents avec ce sha pour revenir en arrière).
- **Design** : 7 maquettes explorées (Humain / Éditorial / Minimal / Blueprint / Riso / Aurore / Index). Olivier a retenu **Aurore**.

### Points ouverts détectés cette session
- ⚠️ **Analyseur CV public** : le JS appelle `https://api.anthropic.com/v1/messages` directement depuis le navigateur, sans clé visible → l'appel échoue en prod hors proxy. À rebrancher sur un endpoint backend (un service `cv-analyze` existe côté serveur) si on veut l'analyseur public fonctionnel. (Pré-existant, non introduit par la refonte.)
- Débrancher l'ancienne prod **Jelastic** (filet pm2) une fois merito.ch / Railway validé dans la durée.
