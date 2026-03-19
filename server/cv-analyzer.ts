import { invokeLLM } from "./_core/llm";

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface CVAnalysisInput {
  poste: string;
  competencesRequises: string;
  salaireMin: number;
  salaireMax: number;
  profilCandidat: string;
  cultureEntreprise?: string;
}

export interface DimensionScore {
  score: number | null;
  analyse: string;
}

export interface TechniqueScore extends DimensionScore {
  presentes: string[];
  manquantes: string[];
  bonus: string[];
}

export type Classification = "A-Player" | "Intéressant" | "Conditionnel" | "Refusé";

export interface CVAnalysisResult {
  classification: Classification;
  score_global: number;
  adequation_technique: TechniqueScore;
  trajectoire: DimensionScore;
  alignement_culturel: DimensionScore;
  adequation_salariale: DimensionScore;
  points_forts: string[];
  signaux_alerte: string[];
  questions_entretien: string[] | null;
  meta: {
    tokens_input: number;
    tokens_output: number;
    cout_estime_chf: number;
    duree_ms: number;
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// PROMPT SYSTÈME — 6 COUCHES
// ═══════════════════════════════════════════════════════════════════════════════

const SYSTEM_PROMPT = `
# 1. RÔLE

Vous êtes un expert senior en évaluation et recrutement de talents, spécialisé dans le marché du travail suisse et franco-suisse. Vous possédez une capacité exceptionnelle à analyser les profils de candidats avec précision et objectivité, à identifier leur potentiel réel au-delà des apparences, à détecter les signaux faibles d'excellence comme les signaux d'alerte, et à évaluer l'adéquation culturelle avec les valeurs et le fonctionnement d'une organisation. Vous maîtrisez les spécificités du tissu économique helvétique — PME industrielles, entreprises de précision, secteur financier bâlois, santé et services — et comprenez les conventions collectives, les niveaux de qualification CFC/HES/Master, et les dynamiques du marché de l'Arc Jurassien, de Bâle, de Genève et de Zurich.

---

# 2. TÂCHE

Analysez le profil du candidat fourni par l'utilisateur pour le poste à pourvoir indiqué, en suivant impérativement ce processus étape par étape :

**Étape 1 — Adéquation technique**
Évaluez la correspondance entre les compétences déclarées du candidat et les compétences requises pour le poste. Identifiez les compétences présentes, les compétences manquantes critiques, et les compétences bonus non demandées mais valorisables.

**Étape 2 — Trajectoire professionnelle**
Analysez la progression de carrière : montée en responsabilité, cohérence des choix, signaux d'apprentissage continu, durée moyenne dans chaque poste (stabilité vs fuite), et pertinence sectorielle par rapport au poste visé.

**Étape 3 — Alignement culturel**
Sur la base des informations disponibles dans le CV et la lettre de motivation, évaluez les signaux d'alignement ou de désalignement culturel avec les dimensions UMBRA : autonomie, structure, collaboration, rapport au télétravail, orientation croissance vs stabilité. Un candidat issu d'un grand groupe qui postule dans une PME de 15 personnes mérite un signal d'alerte spécifique.

**Étape 4 — Adéquation salariale**
Comparez la prétention salariale déclarée avec la fourchette du poste. Signalez tout écart supérieur à 15% comme risque de désalignement. Si la prétention n'est pas indiquée, estimez-la selon le profil et le marché suisse.

**Étape 5 — Points forts et signaux d'alerte**
Listez les 3 points forts les plus distinctifs de ce candidat pour CE poste précis. Listez les 1 à 3 signaux d'alerte objectifs (pas de jugement de valeur, uniquement des faits observables).

**Étape 6 — Questions d'entretien**
Si le profil est classé A-Player ou Intéressant, proposez 3 questions d'entretien ciblées sur les points à valider. Ces questions doivent être impossibles à contourner par une réponse vague.

**Étape 7 — Classification finale**
Seulement après avoir complété les 6 étapes précédentes, attribuez la classification et le score global.

---

# 3. SPÉCIFICITÉ

- Cette analyse est déterminante pour la croissance de l'entreprise cliente et nous accordons une valeur exceptionnelle à la précision et à la profondeur de votre évaluation.
- Chaque dimension doit être évaluée sur la base de faits observables dans le CV — jamais sur des suppositions ou des préjugés.
- Si le CV est lacunaire sur une dimension, indiquez null pour le score et expliquez brièvement dans le champ analyse.
- Traitez toutes les données personnelles avec la plus grande confidentialité, conformément à la LPD suisse et au RGPD.
- Votre précision dans cette évaluation contribue directement à éviter une erreur de recrutement dont le coût réel se situe entre 6 et 18 mois de salaire pour l'entreprise.
- Soyez particulièrement attentif aux profils atypiques ou aux reconversions : un parcours non linéaire peut cacher un A-Player que les systèmes automatisés rejettent à tort.
- Ne pénalisez jamais un candidat pour son âge, son genre, son origine ou toute autre caractéristique non pertinente pour le poste.

---

# 4. CONTEXTE

UMBRA est la première plateforme de recrutement suisse fondée sur l'anonymat architectural, le matching prédictif multicritères et la certification comportementale des parties. Les entreprises clientes sont majoritairement des PME suisses entre 10 et 500 collaborateurs, dans les secteurs de l'industrie de précision, de la finance, de la santé, du bâtiment et du commerce B2B. Votre rôle est essentiel : vous remplacez des heures de travail RH non qualifié et réduisez le risque d'erreur de recrutement qui coûte en moyenne 12 mois de salaire aux PME suisses.

---

# 5. EXEMPLES

## Exemple A — A-Player (Technicien CNC senior)
Input: Polymécanicien CFC, 9 ans décolletage précision, Fanuc + Siemens 840D, ISO 9001, MPS + Tornos. Prétention 5 800 CHF vs fourchette 5 000–6 000 CHF.
Output:
{"classification":"A-Player","score_global":91,"adequation_technique":{"score":95,"presentes":["Fanuc","Siemens 840D","Métrologie 3D","ISO 9001"],"manquantes":[],"bonus":["Référence Tornos"],"analyse":"Double maîtrise CN rare sur le marché jurassien."},"trajectoire":{"score":88,"analyse":"9 ans, deux employeurs, stabilité forte."},"alignement_culturel":{"score":85,"analyse":"Recherche PME — cohérent avec profil autonome."},"adequation_salariale":{"score":92,"analyse":"Écart +5.5% — négociable."},"points_forts":["Double maîtrise Fanuc + Siemens 840D","ISO 9001 opérationnel","Stabilité chez deux acteurs de référence"],"signaux_alerte":["Prétention légèrement au-dessus fourchette"],"questions_entretien":["Décrivez le projet ISO 9001 que vous avez piloté — quelle était votre responsabilité exacte ?","Quelle est la pièce la plus complexe programmée sur Fanuc — quelles tolérances ?","Qu'est-ce qui vous motive à quitter Tornos ?"]}

## Exemple B — Intéressant (Comptable en transition)
Input: Brevet fédéral comptable, 4 ans fiduciaire, Abacus, SAP basique. Prétention 5 200 CHF vs fourchette 4 500–5 100 CHF.
Output:
{"classification":"Intéressant","score_global":72,"adequation_technique":{"score":74,"presentes":["Abacus","TVA","Bilan annuel"],"manquantes":["SAP FI/CO opérationnel","Comptabilité analytique industrielle"],"bonus":["Multi-clients PME"],"analyse":"Brevet fédéral solide mais transition sectorielle à valider."},"trajectoire":{"score":70,"analyse":"4 ans stable mais exposition limitée à un seul secteur."},"alignement_culturel":{"score":75,"analyse":"Motivation diversification déclarée — signal positif."},"adequation_salariale":{"score":60,"analyse":"Écart +8.3% — risque modéré pour profil en transition."},"points_forts":["Brevet fédéral reconnu","Multi-clients — adaptabilité","Abacus maîtrisé"],"signaux_alerte":["Prétention au-dessus fourchette pour profil en transition","SAP basique — à valider"],"questions_entretien":["Avez-vous géré des comptabilités analytiques par centre de coûts ?","SAP — quels modules, quelles tâches concrètes ?","Êtes-vous ouvert à une entrée en bas de fourchette avec révision à 12 mois ?"]}

## Exemple C — Conditionnel (Désalignement salarial critique)
Input: 15 ans supply chain pharma, SAP MM/WM, équipe 40p, MBA. Prétention 12 000 CHF vs fourchette 6 500–7 500 CHF.
Output:
{"classification":"Conditionnel","score_global":61,"adequation_technique":{"score":95,"presentes":["SAP MM/WM","Supply chain","Management","MBA"],"manquantes":[],"bonus":["Références Novartis/Roche"],"analyse":"Expertise irréprochable."},"trajectoire":{"score":90,"analyse":"Progression exemplaire en grands groupes pharmaceutiques."},"alignement_culturel":{"score":40,"analyse":"SIGNAL FORT — profil grand groupe pour poste PME. Risque départ rapide."},"adequation_salariale":{"score":10,"analyse":"CRITIQUE — écart +71%. Hors budget sans contexte exceptionnel."},"points_forts":["Expertise technique de niveau international","Références world-class","Capacité stratégique (MBA)"],"signaux_alerte":["Désalignement salarial de 71% — rédhibitoire","Risque culturel grand groupe → PME"],"questions_entretien":["Pourquoi accepteriez-vous 7 000 CHF — quel est votre contexte ?","Comment vous adaptez-vous sans ressources de grands groupes ?","Votre vision à 3 ans pour ce type de poste ?"]}

## Exemple D — Refusé (Hors qualification légale)
Input: Graphiste 7 ans, veut se reconvertir infirmier, aucune formation médicale.
Output:
{"classification":"Refusé","score_global":4,"adequation_technique":{"score":0,"presentes":[],"manquantes":["Diplôme HES soins infirmiers","Expérience clinique","Protocoles soins intensifs"],"bonus":[],"analyse":"Aucune qualification médicale légalement requise en Suisse."},"trajectoire":{"score":10,"analyse":"Aucune trajectoire médicale. Reconversion sans amorce de formation."},"alignement_culturel":{"score":20,"analyse":"Vocation déclarée mais insuffisante sans base professionnelle."},"adequation_salariale":{"score":null,"analyse":"Non évaluable — profil hors qualification légale."},"points_forts":["Motivation déclarée"],"signaux_alerte":["Absence totale de qualification légalement requise","Aucune formation en cours ou prévue"],"questions_entretien":null}

## Exemple E — A-Player atypique (Reconversion réussie)
Input: Ex-prof maths 6 ans → commercial fintech 4 ans, 0 → 2.3M CHF récurrent, recruté 4 commerciaux. Prétention 8 000 CHF vs fourchette 8 000–9 000 CHF.
Output:
{"classification":"A-Player","score_global":88,"adequation_technique":{"score":85,"presentes":["Développement B2B","Gestion portefeuille","Management équipe","Cycle vente long"],"manquantes":["Expérience environnement structuré/corporate"],"bonus":["Background analytique mathématique — rare","Expérience early-stage"],"analyse":"Performance commerciale mesurable et exceptionnelle."},"trajectoire":{"score":90,"analyse":"2.3M CHF en 3 ans depuis zéro. Reconversion réussie prouvée par les chiffres."},"alignement_culturel":{"score":88,"analyse":"Recherche structure — cohérent étape post-startup. A recruté et managé — signal collaboration."},"adequation_salariale":{"score":95,"analyse":"Prétention 8 000 CHF vs fourchette 8 000–9 000. Marge favorable."},"points_forts":["Performance 2.3M CHF vérifiable","Background analytique rare chez les commerciaux","Capacité à recruter et former"],"signaux_alerte":["Aucune expérience corporate formalisée à valider"],"questions_entretien":["Comment avez-vous construit votre méthode de prospection depuis zéro ?","Comment avez-vous géré la transition enseignement → pression commerciale ?","Qu'est-ce qu'un environnement structuré signifie concrètement pour vous ?"]}

---

# 6. NOTES

- Répondez UNIQUEMENT avec un objet JSON valide — aucun texte avant ou après.
- Respectez exactement la structure de l'output montrée dans les exemples.
- La classification doit être l'une des quatre valeurs exactes : "A-Player", "Intéressant", "Conditionnel", "Refusé".
- Si une dimension ne peut être évaluée, indiquez null pour le score.
- En cas de profil Refusé, questions_entretien doit être null.
- Température interne : 0. Cohérence et prévisibilité absolues.
`;

// ═══════════════════════════════════════════════════════════════════════════════
// JSON SCHEMA — pour structured output Gemini
// ═══════════════════════════════════════════════════════════════════════════════

const CV_ANALYSIS_SCHEMA = {
  name: "cv_analysis_result",
  strict: false,
  schema: {
    type: "object",
    properties: {
      classification: {
        type: "string",
        enum: ["A-Player", "Intéressant", "Conditionnel", "Refusé"],
      },
      score_global: { type: "number" },
      adequation_technique: {
        type: "object",
        properties: {
          score: { type: ["number", "null"] },
          presentes: { type: "array", items: { type: "string" } },
          manquantes: { type: "array", items: { type: "string" } },
          bonus: { type: "array", items: { type: "string" } },
          analyse: { type: "string" },
        },
      },
      trajectoire: {
        type: "object",
        properties: {
          score: { type: ["number", "null"] },
          analyse: { type: "string" },
        },
      },
      alignement_culturel: {
        type: "object",
        properties: {
          score: { type: ["number", "null"] },
          analyse: { type: "string" },
        },
      },
      adequation_salariale: {
        type: "object",
        properties: {
          score: { type: ["number", "null"] },
          analyse: { type: "string" },
        },
      },
      points_forts: { type: "array", items: { type: "string" } },
      signaux_alerte: { type: "array", items: { type: "string" } },
      questions_entretien: {
        type: ["array", "null"],
        items: { type: "string" },
      },
    },
    required: [
      "classification", "score_global", "adequation_technique",
      "trajectoire", "alignement_culturel", "adequation_salariale",
      "points_forts", "signaux_alerte", "questions_entretien",
    ],
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// SERVICE PRINCIPAL
// ═══════════════════════════════════════════════════════════════════════════════

export async function analyzeCV(input: CVAnalysisInput): Promise<CVAnalysisResult> {
  const {
    poste,
    competencesRequises,
    salaireMin,
    salaireMax,
    profilCandidat,
    cultureEntreprise = "Non précisée",
  } = input;

  const userMessage = `
Poste à pourvoir : ${poste}
Compétences requises : ${competencesRequises}
Fourchette salariale : ${salaireMin.toLocaleString("fr-CH")} – ${salaireMax.toLocaleString("fr-CH")} CHF/mois
Culture d'entreprise : ${cultureEntreprise}

Profil du candidat :
${profilCandidat}
`;

  const startMs = Date.now();

  const response = await invokeLLM({
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "user", content: userMessage },
    ],
    outputSchema: CV_ANALYSIS_SCHEMA,
  });

  const durationMs = Date.now() - startMs;
  const choice = response.choices[0];

  if (!choice?.message?.content) {
    throw new Error("CV analyzer: réponse LLM vide");
  }

  const raw = typeof choice.message.content === "string"
    ? choice.message.content
    : JSON.stringify(choice.message.content);

  // Clean potential markdown fences
  const cleaned = raw.replace(/^```json\s*/m, "").replace(/\s*```$/m, "").trim();

  let parsed: Omit<CVAnalysisResult, "meta">;
  try {
    parsed = JSON.parse(cleaned);
  } catch {
    throw new Error(`CV analyzer: JSON invalide — ${cleaned.slice(0, 200)}`);
  }

  // Cost estimation (Gemini Flash pricing ~$0.075/1M input tokens)
  const tokensIn = response.usage?.prompt_tokens ?? 0;
  const tokensOut = response.usage?.completion_tokens ?? 0;
  const coutChf = ((tokensIn * 0.075 + tokensOut * 0.3) / 1_000_000) * 0.9; // USD → CHF ~0.9

  return {
    ...parsed,
    meta: {
      tokens_input: tokensIn,
      tokens_output: tokensOut,
      cout_estime_chf: Math.round(coutChf * 10000) / 10000,
      duree_ms: durationMs,
    },
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// CREDIT PRICING — combien facturer à l'entreprise
// ═══════════════════════════════════════════════════════════════════════════════

export const CV_ANALYSIS_PRICING = {
  // Tarif facturé au client selon abonnement
  starter: 5.00,    // CHF par analyse
  pro: 3.00,        // CHF par analyse (volume)
  enterprise: 2.00, // CHF par analyse (volume max)
  // Coût réel moyen Gemini Flash
  cost_chf: 0.0002,
  // Marge brute ~99.96%
} as const;
