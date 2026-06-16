# UMBRA — TODO LIST

> État au 2026-06-16. Priorité décroissante. Voir CONTEXT.md (section de tête) pour le contexte complet.

---

## ✅ FAIT (cette session)

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

## 🔴 P0 — À VÉRIFIER IMMÉDIATEMENT (prochaine session)

- [ ] **Vérifier register en prod** après déploiement du fix PgEnum (commit 71250f1) :
      `curl -X POST https://umbra-prod.jcloud-ver-jpc.ik-server.com/api/v1/auth/register`
      → doit retourner 201 (et non 500). Si le node n'a pas le code à jour : re-cloner +
      restartservices (voir CONTEXT.md mécanisme déploiement).

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
- [ ] CORS : aligner `ALLOWED_ORIGINS` sur domaine réel (umbra.ch/jcloud)
- [ ] Chiffrement PII au repos AES-256-GCM (pattern Tournepage, classes A/B/C/D)
- [ ] Stockage CV souverain S3 Infomaniak (`s3.pub1.infomaniak.cloud`, runbook Tournepage)
- [ ] Immuabilité trust_events (permissions DB ou chaînage par hash) + `recompute_from_history()`
- [ ] Index PostGIS `ST_DWithin` pour pré-filtre géo avant scoring (perf 10k×1k profils)

## 🔵 P4 — INTÉGRATIONS

- [ ] **HUNTEED** : connecteur UMBRA↔Hunteed (importer missions anonymisées + pousser candidats).
      Besoin : doc API Hunteed OU credentials Olivier.
- [ ] MATCHO (session séparée) : retirer code UMBRA résiduel de matcho/backend/static/index.html

## ⚠️ ACTION OLIVIER (hors code)

- [ ] **Révoquer** l'ancien token GitHub exposé `<ancien token GitHub exposé — commençant par ghp_BkM4, présent dans 2 vieux commits>`
      (Settings → Developer settings → Personal access tokens)
