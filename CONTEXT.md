# UMBRA — Contexte Projet

> Fichier mis à jour automatiquement à chaque session. Sert de mémoire persistante entre les conversations.

## Dernière mise à jour : 2026-02-27 — Session 3 : Modèle économique à la valeur réelle

---

## 🎯 Vision Produit

**UMBRA** est la première plateforme de recrutement où l'anonymat est architectural, le matching est prédictif, et la confiance est certifiée par le comportement réel — pas les déclarations.

> "Le talent se cache. Nous le trouvons."

> "Tous les concurrents font payer la visibilité. UMBRA fait payer la valeur."

- **Marché cible** : Suisse (Arc Jurassien, Bâle, Genève, Zurich) → Europe francophone
- **Entité** : PEP's Swiss SA (Groupe NEO)
- **Repo** : https://github.com/O-N-2950/matcho
- **Domaine** : à finaliser (umbra.work / umbra.jobs / umbra.ch)
- **Stack hosting** : Railway + PostgreSQL

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
| Repo            | https://github.com/O-N-2950/matcho             |

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
- DB : MySQL (DATABASE_URL)
- Deploy : Railway (matcho-production.up.railway.app)
- Repo : github.com/O-N-2950/matcho
