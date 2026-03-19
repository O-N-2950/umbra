import { useState, useEffect, useRef } from "react";

/* ═══════════════════════════════════════════════════════════════
   UMBRA — Analyseur de CVs (Interface Recruteur)
   Design : noir profond + cuivré
   Fonctionnalité : saisie poste + CV → rapport IA structuré
   ═══════════════════════════════════════════════════════════════ */

const C = {
  void:     "#05080e",
  deep:     "#090d18",
  surface:  "#0f1520",
  card:     "#121a28",
  lift:     "#172030",
  edge:     "#1c2a3e",
  rim:      "#243548",
  copper:   "#d97b3a",
  copperL:  "#e8944f",
  copperD:  "#9a5520",
  copperXL: "#f0aa70",
  copperG:  "rgba(217,123,58,0.10)",
  copperB:  "rgba(217,123,58,0.05)",
  ice:      "#edeae4",
  snow:     "#f8f5f0",
  mist:     "#7a8da8",
  fog:      "#4d5e75",
  dim:      "#2e3d52",
  green:    "#2dd4aa",
  greenD:   "#1a9978",
  greenG:   "rgba(45,212,170,0.12)",
  red:      "#e05555",
  redG:     "rgba(224,85,85,0.10)",
  gold:     "#f0c060",
  goldG:    "rgba(240,192,96,0.12)",
  teal:     "#38bdf8",
};

const STYLE = `
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400;1,600&family=JetBrains+Mono:wght@300;400;500&family=Outfit:wght@200;300;400;500;600&display=swap');

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html,body{height:100%;background:${C.void};color:${C.ice};font-family:'Outfit',sans-serif;font-weight:300;}
::selection{background:${C.copperG};color:${C.copper};}
::-webkit-scrollbar{width:3px;}
::-webkit-scrollbar-track{background:${C.deep};}
::-webkit-scrollbar-thumb{background:${C.edge};}
::-webkit-scrollbar-thumb:hover{background:${C.copper};}

.pf{font-family:'Playfair Display',serif;}
.pfi{font-family:'Playfair Display',serif;font-style:italic;}
.jb{font-family:'JetBrains Mono',monospace;}

@keyframes fu{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:none}}
@keyframes fi{from{opacity:0}to{opacity:1}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes pulse-ring{0%{transform:scale(1);opacity:1}100%{transform:scale(1.6);opacity:0}}
@keyframes scan-line{0%{top:-10%}100%{top:110%}}
@keyframes bar-fill{from{width:0}to{width:var(--w)}}
@keyframes count-up{from{opacity:0;transform:scale(0.5)}to{opacity:1;transform:scale(1)}}

.appear{animation:fu .5s ease both;}
.appear-1{animation:fu .5s .1s ease both;}
.appear-2{animation:fu .5s .2s ease both;}
.appear-3{animation:fu .5s .3s ease both;}
.appear-4{animation:fu .5s .4s ease both;}
.appear-5{animation:fu .5s .5s ease both;}
.appear-6{animation:fu .5s .6s ease both;}
.appear-7{animation:fu .5s .7s ease both;}
.appear-8{animation:fu .5s .8s ease both;}

input,textarea,select{background:transparent;border:none;outline:none;color:${C.ice};font-family:'Outfit',sans-serif;font-weight:300;}
input::placeholder,textarea::placeholder{color:${C.fog};}
textarea{resize:none;}
button{cursor:pointer;font-family:'Outfit',sans-serif;}
`;

// ─── MOCK ANALYSES ──────────────────────────────────────────────────────────
const MOCK_RESULTS = {
  aplayer: {
    classification: "A-Player",
    score_global: 91,
    adequation_technique: { score: 95, presentes: ["Fanuc", "Siemens 840D", "Métrologie Zeiss 3D", "ISO 9001"], manquantes: [], bonus: ["Expérience Tornos — référence sectorielle"] },
    trajectoire: { score: 88, analyse: "9 ans de progression cohérente dans le décolletage de précision. Durée moyenne 4.5 ans/poste — stabilité forte. Deux références majeures." },
    alignement_culturel: { score: 85, analyse: "Recherche explicite d'une PME à taille humaine — cohérent avec profil autonome. Signaux d'adaptabilité marqués." },
    adequation_salariale: { score: 92, analyse: "Prétention 5 800 CHF vs fourchette 5 500 CHF. Écart de 5.5% — négociable. Profil justifie le haut de fourchette." },
    points_forts: ["Double maîtrise Fanuc + Siemens 840D — rare sur le marché jurassien", "Expérience ISO 9001 opérationnelle — valeur immédiate", "Stabilité prouvée chez deux acteurs sectoriels de référence"],
    signaux_alerte: ["Prétention légèrement au-dessus de la fourchette — à négocier en entretien"],
    questions_entretien: ["Pouvez-vous décrire le projet ISO 9001 que vous avez piloté — quelle était votre responsabilité exacte ?", "Quelle est la pièce la plus complexe que vous avez programmée sur Fanuc — quelles tolérances teniez-vous ?", "Qu'est-ce qui vous motive à quitter Tornos après 3 ans ?"]
  },
  interessant: {
    classification: "Intéressant",
    score_global: 72,
    adequation_technique: { score: 74, presentes: ["Abacus", "Clôtures mensuelles", "TVA", "Brevet fédéral"], manquantes: ["SAP FI/CO niveau opérationnel", "Comptabilité analytique industrielle"], bonus: ["Connaissance multi-clients PME"] },
    trajectoire: { score: 70, analyse: "4 ans dans une seule structure — stabilité mais exposition limitée. Transition fiduciaire → industrie logique mais nécessite adaptation." },
    alignement_culturel: { score: 75, analyse: "Motivation de diversification déclarée — signal positif d'orientation croissance. Informations sur autonomie/remote absentes." },
    adequation_salariale: { score: 60, analyse: "Prétention 5 200 CHF vs fourchette 4 800 CHF. Écart de 8.3% — risque modéré. Profil junior en transition ne justifie pas le haut de fourchette." },
    points_forts: ["Brevet fédéral reconnu — formation solide", "Expérience multi-clients — capacité d'adaptation", "Abacus maîtrisé — standard PME suisse"],
    signaux_alerte: ["Prétention au-dessus de la fourchette pour un profil en transition", "SAP déclaré 'basique' — à valider précisément"],
    questions_entretien: ["Avez-vous déjà travaillé avec des comptabilités analytiques par centre de coûts ?", "Quelle est votre utilisation concrète de SAP — modules, tâches précises ?", "Êtes-vous ouvert à une entrée en bas de fourchette avec révision à 12 mois ?"]
  },
  conditionnel: {
    classification: "Conditionnel",
    score_global: 61,
    adequation_technique: { score: 95, presentes: ["SAP MM/WM", "Supply chain pharma", "Management équipe 40p", "MBA UNIL"], manquantes: [], bonus: ["Expérience Novartis/Roche — références world-class"] },
    trajectoire: { score: 90, analyse: "Trajectoire exemplaire dans les plus grandes entreprises du secteur. Progression claire vers la direction opérationnelle." },
    alignement_culturel: { score: 40, analyse: "⚠ SIGNAL FORT — profil grand groupe (50 000 m², 40 collaborateurs) pour un poste PME. Risque de sous-stimulation et départ rapide." },
    adequation_salariale: { score: 10, analyse: "DÉSALIGNEMENT CRITIQUE — prétention 12 000 CHF vs fourchette 7 000 CHF. Écart de 71%. Hors budget sans contexte exceptionnel." },
    points_forts: ["Expertise technique irréprochable", "Références sectorielles de très haut niveau", "MBA — vision stratégique et capacité de structuration"],
    signaux_alerte: ["Désalignement salarial de 71% — rédhibitoire sans contexte particulier", "Risque culturel grand groupe → structure PME non évalué"],
    questions_entretien: ["Pourquoi accepteriez-vous 7 000 CHF pour ce poste — quel est votre contexte actuel ?", "Comment vous adaptez-vous à des structures sans ressources de grands groupes ?", "Quelle est votre vision à 3 ans pour ce type de poste ?"]
  },
  refuse: {
    classification: "Refusé",
    score_global: 4,
    adequation_technique: { score: 0, presentes: [], manquantes: ["Diplôme HES soins infirmiers", "Expérience clinique", "Gestes d'urgence", "Protocoles soins intensifs"], bonus: [] },
    trajectoire: { score: 10, analyse: "Aucune trajectoire médicale. Reconversion souhaitée mais sans amorce de formation identifiée." },
    alignement_culturel: { score: 20, analyse: "Motivation de vocation déclarée — signal positif mais largement insuffisant sans base professionnelle." },
    adequation_salariale: { score: null, analyse: "Non évaluable — profil hors qualification légale requise en Suisse pour ce poste." },
    points_forts: ["Motivation déclarée et assumée"],
    signaux_alerte: ["Absence totale de qualification médicale légalement requise", "Aucune formation en cours ou prévue mentionnée"],
    questions_entretien: null
  }
};

// ─── DEMO PROFILES ──────────────────────────────────────────────────────────
const DEMO_PROFILES = [
  {
    label: "Technicien CNC senior",
    poste: "Technicien CNC / Programmeur Fanuc",
    competences: "Fanuc, métrologie 3D, décolletage précision, qualité ISO 9001",
    salaire_min: "5000", salaire_max: "6000",
    culture: "PME industrielle, 25 collaborateurs, Arc Jurassien, autonomie valorisée",
    cv: `Polymécanicien CFC avec 9 ans d'expérience en décolletage de précision.

Expérience professionnelle :
- MPS Micro Precision Systems, Bienne — Technicien CNC (6 ans)
  Programmation Fanuc 0i-MD et 31i, pièces de précision <0.005mm, outillage céramique
- Tornos SA — Opérateur/Programmeur senior (3 ans)
  Décolletage automatique, Siemens 840D, participation mise en place ISO 9001

Compétences : Fanuc, Siemens 840D, métrologie Zeiss 3D, ISO 9001, lecture plans techniques

Prétention : 5 800 CHF/mois`,
    mock: "aplayer"
  },
  {
    label: "Comptable en transition",
    poste: "Comptable / Assistant financier",
    competences: "Abacus, clôtures mensuelles, TVA, bilan annuel",
    salaire_min: "4500", salaire_max: "5100",
    culture: "PME industrielle, Delémont, environnement structuré",
    cv: `Titulaire d'un brevet fédéral de comptable, 4 ans d'expérience fiduciaire.

Parcours :
- Fiduciaire Perrenoud & Associés, Porrentruy — Collaborateur comptable (4 ans)
  Gestion autonome de 35 clients PME, clôtures mensuelles, déclarations TVA, bilan annuel

Logiciels : Abacus (maîtrisé), SAP (basique), Excel avancé

Objectif : Intégrer une entreprise industrielle pour diversifier mon expérience et évoluer vers un rôle de responsable financier.

Prétention : 5 200 CHF/mois`,
    mock: "interessant"
  },
  {
    label: "Directeur supply chain surqualifié",
    poste: "Responsable logistique",
    competences: "SAP MM/WM, gestion entrepôt, planification supply chain, management équipe",
    salaire_min: "6500", salaire_max: "7500",
    culture: "PME chimie, Bâle, 80 collaborateurs",
    cv: `15 ans d'expérience en supply chain dans l'industrie pharmaceutique suisse.

Parcours :
- Novartis AG, Bâle — Head of Supply Chain Operations (8 ans)
  Management équipe 40 personnes, entrepôts 50 000 m², optimisation KPI -23% coûts
- Roche, Kaiseraugst — Supply Chain Manager (7 ans)
  SAP MM/WM expert, projets d'intégration internationale, certification APICS

Formation : MBA UNIL, Licence en gestion logistique HES-SO

Prétention : 12 000 CHF/mois`,
    mock: "conditionnel"
  }
];

// ─── UTILS ──────────────────────────────────────────────────────────────────
const classificationConfig = {
  "A-Player":    { color: C.green,  bg: C.greenG,  icon: "◆", label: "A-PLAYER" },
  "Intéressant": { color: C.gold,   bg: C.goldG,   icon: "◇", label: "INTÉRESSANT" },
  "Conditionnel":{ color: C.teal,   bg: "rgba(56,189,248,0.10)", icon: "◈", label: "CONDITIONNEL" },
  "Refusé":      { color: C.red,    bg: C.redG,    icon: "✕", label: "REFUSÉ" },
};

function ScoreArc({ score, size = 120, color }) {
  const r = 46;
  const cx = size / 2;
  const cy = size / 2;
  const circ = 2 * Math.PI * r;
  const dash = score != null ? (score / 100) * circ * 0.75 : 0;
  const gap = circ * 0.25;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: "rotate(135deg)" }}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={C.edge} strokeWidth="6"
        strokeDasharray={`${circ * 0.75} ${circ * 0.25}`}
        strokeLinecap="round"
      />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth="6"
        strokeDasharray={`${dash} ${circ - dash}`}
        strokeLinecap="round"
        style={{ transition: "stroke-dasharray 1s ease", filter: `drop-shadow(0 0 6px ${color})` }}
      />
    </svg>
  );
}

function BarScore({ label, score, color }) {
  const pct = score != null ? score : 0;
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: 11, letterSpacing: "0.08em" }}>
        <span style={{ color: C.mist, textTransform: "uppercase" }}>{label}</span>
        <span style={{ color, fontFamily: "'JetBrains Mono'", fontWeight: 500 }}>
          {score != null ? `${score}/100` : "N/A"}
        </span>
      </div>
      <div style={{ height: 3, background: C.edge, borderRadius: 2, overflow: "hidden" }}>
        <div style={{
          height: "100%", borderRadius: 2,
          width: `${pct}%`, background: color,
          transition: "width 1.2s cubic-bezier(.16,1,.3,1)",
          boxShadow: `0 0 8px ${color}60`,
        }} />
      </div>
    </div>
  );
}

// ─── MAIN COMPONENT ──────────────────────────────────────────────────────────
export default function UMBRACVAnalyser() {
  const [form, setForm] = useState({
    poste: "", competences: "", salaire_min: "", salaire_max: "", culture: "", cv: ""
  });
  const [result, setResult] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [activeTab, setActiveTab] = useState("technique");
  const [scanLine, setScanLine] = useState(false);
  const [creditsUsed, setCreditsUsed] = useState(0);
  const [showDemo, setShowDemo] = useState(false);
  const resultRef = useRef(null);

  function loadDemo(demo) {
    setForm({
      poste: demo.poste, competences: demo.competences,
      salaire_min: demo.salaire_min, salaire_max: demo.salaire_max,
      culture: demo.culture, cv: demo.cv
    });
    setResult(null);
    setShowDemo(false);
  }

  function handleChange(k, v) {
    setForm(f => ({ ...f, [k]: v }));
  }

  async function handleAnalyze() {
    if (!form.poste || !form.cv) return;
    setAnalyzing(true);
    setScanLine(true);
    setResult(null);
    setActiveTab("technique");

    // Simulate API call — pick mock based on a keyword
    await new Promise(r => setTimeout(r, 3200));

    const cv = form.cv.toLowerCase();
    let mockKey = "interessant";
    if (cv.includes("fanuc") || cv.includes("cnc") || cv.includes("a-player")) mockKey = "aplayer";
    else if (cv.includes("novartis") || cv.includes("roche") || cv.includes("12 000")) mockKey = "conditionnel";
    else if (cv.includes("graphiste") || cv.includes("infirmier") || cv.includes("reconverti") && !cv.includes("ans")) mockKey = "refuse";

    setResult(MOCK_RESULTS[mockKey]);
    setCreditsUsed(c => c + 1);
    setAnalyzing(false);
    setScanLine(false);

    setTimeout(() => {
      resultRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  }

  function handleReset() {
    setForm({ poste: "", competences: "", salaire_min: "", salaire_max: "", culture: "", cv: "" });
    setResult(null);
  }

  const cfg = result ? classificationConfig[result.classification] : null;
  const canAnalyze = form.poste.trim() && form.cv.trim();

  return (
    <div style={{ minHeight: "100vh", background: C.void, fontFamily: "'Outfit', sans-serif" }}>
      <style>{STYLE}</style>

      {/* ── HEADER ──────────────────────────────────────────────────────── */}
      <header style={{
        position: "sticky", top: 0, zIndex: 50,
        background: `${C.deep}e8`, backdropFilter: "blur(20px)",
        borderBottom: `1px solid ${C.edge}`,
        padding: "0 32px", height: 64,
        display: "flex", alignItems: "center", justifyContent: "space-between"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <svg width="28" height="28" viewBox="0 0 28 28">
            <polygon points="14,2 26,8 26,20 14,26 2,20 2,8"
              fill="none" stroke={C.copper} strokeWidth="1.5" />
            <polygon points="14,7 21,10.5 21,17.5 14,21 7,17.5 7,10.5"
              fill={`${C.copper}20`} stroke={C.copperL} strokeWidth="1" />
            <circle cx="14" cy="14" r="2.5" fill={C.copper} />
          </svg>
          <span className="pf" style={{ fontSize: 20, fontWeight: 600, color: C.snow, letterSpacing: "0.02em" }}>
            UMBRA
          </span>
          <span style={{
            fontSize: 10, color: C.copper, letterSpacing: "0.15em",
            textTransform: "uppercase", marginLeft: 4, fontWeight: 400,
            borderLeft: `1px solid ${C.edge}`, paddingLeft: 12
          }}>
            Analyseur de Profils
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          {creditsUsed > 0 && (
            <div className="jb" style={{ fontSize: 11, color: C.mist }}>
              <span style={{ color: C.copper }}>{creditsUsed}</span> analyse{creditsUsed > 1 ? "s" : ""} effectuée{creditsUsed > 1 ? "s" : ""}
            </div>
          )}
          <div style={{
            fontSize: 11, color: C.mist, display: "flex", alignItems: "center", gap: 6
          }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: C.green, boxShadow: `0 0 6px ${C.green}` }} />
            Gemini Flash · 0.0002 CHF/analyse
          </div>
        </div>
      </header>

      {/* ── MAIN ────────────────────────────────────────────────────────── */}
      <main style={{ maxWidth: 1280, margin: "0 auto", padding: "48px 32px" }}>

        {/* Title */}
        <div className="appear" style={{ textAlign: "center", marginBottom: 56 }}>
          <div className="pfi" style={{ fontSize: 42, fontWeight: 600, color: C.snow, lineHeight: 1.2 }}>
            Analyse de profil candidat
          </div>
          <p style={{ marginTop: 12, color: C.mist, fontSize: 15, fontWeight: 300, maxWidth: 480, margin: "12px auto 0" }}>
            Obtenez une évaluation structurée en quelques secondes — compétences, trajectoire, alignement culturel et salarial.
          </p>
        </div>

        {/* Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, alignItems: "start" }}>

          {/* ── LEFT PANEL — FORM ──────────────────────────────────────── */}
          <div className="appear-1">

            {/* Demo selector */}
            <div style={{ marginBottom: 20, position: "relative" }}>
              <button
                onClick={() => setShowDemo(d => !d)}
                style={{
                  background: C.copperB, border: `1px solid ${C.copperD}`,
                  borderRadius: 8, padding: "8px 16px",
                  color: C.copper, fontSize: 12, letterSpacing: "0.08em",
                  textTransform: "uppercase", fontWeight: 500,
                  display: "flex", alignItems: "center", gap: 8, transition: "all .2s"
                }}
              >
                <span>▾</span> Charger un profil de démonstration
              </button>

              {showDemo && (
                <div style={{
                  position: "absolute", top: 40, left: 0, zIndex: 20,
                  background: C.card, border: `1px solid ${C.edge}`,
                  borderRadius: 10, overflow: "hidden", minWidth: 300,
                  boxShadow: `0 20px 60px ${C.void}`
                }}>
                  {DEMO_PROFILES.map((d, i) => (
                    <button key={i} onClick={() => loadDemo(d)} style={{
                      display: "block", width: "100%", textAlign: "left",
                      padding: "14px 18px", background: "transparent",
                      border: "none", borderBottom: i < DEMO_PROFILES.length - 1 ? `1px solid ${C.edge}` : "none",
                      color: C.ice, fontSize: 13, cursor: "pointer",
                      transition: "background .15s",
                    }}
                      onMouseEnter={e => e.target.style.background = C.lift}
                      onMouseLeave={e => e.target.style.background = "transparent"}
                    >
                      <div style={{ fontWeight: 500 }}>{d.label}</div>
                      <div style={{ color: C.fog, fontSize: 11, marginTop: 2 }}>{d.poste}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Form card */}
            <div style={{
              background: C.card, border: `1px solid ${C.edge}`,
              borderRadius: 14, overflow: "hidden"
            }}>
              {/* Poste */}
              <div style={{ padding: "20px 24px", borderBottom: `1px solid ${C.edge}` }}>
                <label style={{ fontSize: 10, color: C.copper, letterSpacing: "0.12em", textTransform: "uppercase", display: "block", marginBottom: 8 }}>
                  Poste à pourvoir
                </label>
                <input
                  value={form.poste}
                  onChange={e => handleChange("poste", e.target.value)}
                  placeholder="Ex: Technicien CNC / Programmeur Fanuc"
                  style={{ width: "100%", fontSize: 15, color: C.snow, fontWeight: 400 }}
                />
              </div>

              {/* Compétences */}
              <div style={{ padding: "20px 24px", borderBottom: `1px solid ${C.edge}` }}>
                <label style={{ fontSize: 10, color: C.copper, letterSpacing: "0.12em", textTransform: "uppercase", display: "block", marginBottom: 8 }}>
                  Compétences requises
                </label>
                <input
                  value={form.competences}
                  onChange={e => handleChange("competences", e.target.value)}
                  placeholder="Ex: Fanuc, métrologie 3D, ISO 9001"
                  style={{ width: "100%", fontSize: 14, color: C.ice }}
                />
              </div>

              {/* Salaire */}
              <div style={{ padding: "20px 24px", borderBottom: `1px solid ${C.edge}`, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <div>
                  <label style={{ fontSize: 10, color: C.copper, letterSpacing: "0.12em", textTransform: "uppercase", display: "block", marginBottom: 8 }}>
                    Salaire min (CHF/mois)
                  </label>
                  <input
                    value={form.salaire_min}
                    onChange={e => handleChange("salaire_min", e.target.value)}
                    placeholder="5 000"
                    type="number"
                    style={{ width: "100%", fontSize: 14, color: C.ice }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: C.copper, letterSpacing: "0.12em", textTransform: "uppercase", display: "block", marginBottom: 8 }}>
                    Salaire max (CHF/mois)
                  </label>
                  <input
                    value={form.salaire_max}
                    onChange={e => handleChange("salaire_max", e.target.value)}
                    placeholder="6 500"
                    type="number"
                    style={{ width: "100%", fontSize: 14, color: C.ice }}
                  />
                </div>
              </div>

              {/* Culture */}
              <div style={{ padding: "20px 24px", borderBottom: `1px solid ${C.edge}` }}>
                <label style={{ fontSize: 10, color: C.copper, letterSpacing: "0.12em", textTransform: "uppercase", display: "block", marginBottom: 8 }}>
                  Culture d'entreprise <span style={{ color: C.fog, textTransform: "none", letterSpacing: 0 }}>(optionnel)</span>
                </label>
                <input
                  value={form.culture}
                  onChange={e => handleChange("culture", e.target.value)}
                  placeholder="Ex: PME industrielle, 25 personnes, autonomie valorisée"
                  style={{ width: "100%", fontSize: 14, color: C.ice }}
                />
              </div>

              {/* CV */}
              <div style={{ padding: "20px 24px" }}>
                <label style={{ fontSize: 10, color: C.copper, letterSpacing: "0.12em", textTransform: "uppercase", display: "block", marginBottom: 8 }}>
                  Profil candidat — CV + lettre de motivation
                </label>
                <textarea
                  value={form.cv}
                  onChange={e => handleChange("cv", e.target.value)}
                  placeholder="Collez ici le CV, la lettre de motivation ou toute information sur le candidat..."
                  rows={12}
                  style={{ width: "100%", fontSize: 13, color: C.ice, lineHeight: 1.7, color: C.mist }}
                />
                {form.cv && (
                  <div className="jb" style={{ marginTop: 8, fontSize: 10, color: C.fog, textAlign: "right" }}>
                    {form.cv.split(/\s+/).length} mots · ~{(form.cv.length * 0.0000001 * 1.3 * 100).toFixed(4)} CHF
                  </div>
                )}
              </div>

              {/* CTA */}
              <div style={{ padding: "0 24px 24px", display: "flex", gap: 12 }}>
                <button
                  onClick={handleAnalyze}
                  disabled={!canAnalyze || analyzing}
                  style={{
                    flex: 1, padding: "14px 0",
                    background: canAnalyze && !analyzing
                      ? `linear-gradient(135deg, ${C.copper}, ${C.copperL})`
                      : C.edge,
                    border: "none", borderRadius: 10,
                    color: canAnalyze && !analyzing ? C.void : C.fog,
                    fontSize: 13, fontWeight: 600, letterSpacing: "0.08em",
                    textTransform: "uppercase", transition: "all .3s",
                    display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                    boxShadow: canAnalyze && !analyzing ? `0 8px 24px ${C.copperD}60` : "none",
                  }}
                >
                  {analyzing ? (
                    <>
                      <div style={{
                        width: 14, height: 14, border: `2px solid ${C.fog}`,
                        borderTopColor: C.copper, borderRadius: "50%",
                        animation: "spin 0.8s linear infinite"
                      }} />
                      Analyse en cours...
                    </>
                  ) : (
                    <>◆ Analyser le profil</>
                  )}
                </button>
                {(result || form.cv) && (
                  <button onClick={handleReset} style={{
                    padding: "14px 18px", background: "transparent",
                    border: `1px solid ${C.edge}`, borderRadius: 10,
                    color: C.fog, fontSize: 13, transition: "all .2s"
                  }}
                    onMouseEnter={e => { e.target.style.borderColor = C.rim; e.target.style.color = C.mist; }}
                    onMouseLeave={e => { e.target.style.borderColor = C.edge; e.target.style.color = C.fog; }}
                  >
                    ↺
                  </button>
                )}
              </div>
            </div>

            {/* Info */}
            <div style={{ marginTop: 16, padding: "12px 16px", background: C.copperB, borderRadius: 8, border: `1px solid ${C.copperD}30`, fontSize: 12, color: C.fog, lineHeight: 1.6 }}>
              Prompt système 6 couches · Gemini Flash · Température 0 · Conforme LPD/RGPD
            </div>
          </div>

          {/* ── RIGHT PANEL — RESULTS ─────────────────────────────────── */}
          <div ref={resultRef}>
            {!result && !analyzing && (
              <div style={{
                background: C.card, border: `1px solid ${C.edge}`,
                borderRadius: 14, padding: 48, textAlign: "center", minHeight: 400,
                display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
              }}>
                <div style={{ fontSize: 48, marginBottom: 20, opacity: 0.3 }}>◆</div>
                <div className="pfi" style={{ fontSize: 22, color: C.fog }}>
                  En attente d'analyse
                </div>
                <p style={{ color: C.dim, fontSize: 13, marginTop: 10, lineHeight: 1.6, maxWidth: 280 }}>
                  Renseignez le poste et collez le profil candidat pour obtenir une évaluation structurée.
                </p>
                <div style={{ marginTop: 32, display: "flex", flexDirection: "column", gap: 10 }}>
                  {["◆ Score global sur 100", "◇ Analyse technique & culturelle", "◈ Signaux d'alerte", "→ Questions d'entretien suggérées"].map((item, i) => (
                    <div key={i} style={{ fontSize: 12, color: C.fog, display: "flex", alignItems: "center", gap: 8 }}>
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {analyzing && (
              <div style={{
                background: C.card, border: `1px solid ${C.copperD}60`,
                borderRadius: 14, padding: 48, textAlign: "center", minHeight: 400,
                display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                position: "relative", overflow: "hidden",
              }}>
                {/* Scan line */}
                <div style={{
                  position: "absolute", left: 0, right: 0, height: 2,
                  background: `linear-gradient(90deg, transparent, ${C.copper}, transparent)`,
                  animation: "scan-line 1.5s linear infinite", top: 0,
                }} />

                <div style={{ position: "relative", marginBottom: 28 }}>
                  <div style={{ width: 80, height: 80 }}>
                    <svg width="80" height="80" viewBox="0 0 80 80">
                      <polygon points="40,4 76,22 76,58 40,76 4,58 4,22"
                        fill="none" stroke={C.copperD} strokeWidth="1.5" />
                      <polygon points="40,4 76,22 76,58 40,76 4,58 4,22"
                        fill="none" stroke={C.copper} strokeWidth="1.5"
                        strokeDasharray="200"
                        style={{ animation: "spin 3s linear infinite", transformOrigin: "40px 40px" }} />
                    </svg>
                  </div>
                </div>

                <div className="pfi" style={{ fontSize: 20, color: C.ice, marginBottom: 8 }}>
                  Analyse en cours
                </div>

                {[
                  { label: "Évaluation des compétences techniques", delay: 0 },
                  { label: "Analyse de la trajectoire professionnelle", delay: 600 },
                  { label: "Détection des signaux culturels", delay: 1200 },
                  { label: "Vérification de l'adéquation salariale", delay: 1800 },
                  { label: "Génération du rapport structuré", delay: 2400 },
                ].map((step, i) => (
                  <AnalyzingStep key={i} label={step.label} delay={step.delay} />
                ))}
              </div>
            )}

            {result && (
              <div style={{ animation: "fi .6s ease" }}>

                {/* Classification header */}
                <div className="appear" style={{
                  background: C.card, border: `1px solid ${cfg.color}40`,
                  borderRadius: 14, padding: 28, marginBottom: 16,
                  display: "flex", alignItems: "center", gap: 24,
                  boxShadow: `0 0 40px ${cfg.color}10`,
                }}>
                  {/* Arc score */}
                  <div style={{ position: "relative", flexShrink: 0 }}>
                    <ScoreArc score={result.score_global} size={110} color={cfg.color} />
                    <div style={{
                      position: "absolute", top: "50%", left: "50%",
                      transform: "translate(-50%, -50%)",
                      textAlign: "center", marginTop: -4,
                    }}>
                      <div className="jb" style={{ fontSize: 26, fontWeight: 500, color: cfg.color, lineHeight: 1 }}>
                        {result.score_global}
                      </div>
                      <div style={{ fontSize: 9, color: C.fog, letterSpacing: "0.1em", textTransform: "uppercase", marginTop: 2 }}>
                        /100
                      </div>
                    </div>
                  </div>

                  <div style={{ flex: 1 }}>
                    <div style={{
                      display: "inline-flex", alignItems: "center", gap: 8,
                      background: cfg.bg, border: `1px solid ${cfg.color}40`,
                      borderRadius: 6, padding: "5px 12px", marginBottom: 12,
                    }}>
                      <span style={{ color: cfg.color, fontSize: 14 }}>{cfg.icon}</span>
                      <span className="jb" style={{ fontSize: 11, color: cfg.color, letterSpacing: "0.12em", fontWeight: 500 }}>
                        {cfg.label}
                      </span>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                      {[
                        ["Technique", result.adequation_technique.score],
                        ["Trajectoire", result.trajectoire.score],
                        ["Culturel", result.alignement_culturel.score],
                        ["Salarial", result.adequation_salariale.score],
                      ].map(([label, score]) => (
                        <BarScore key={label} label={label} score={score} color={cfg.color} />
                      ))}
                    </div>
                  </div>
                </div>

                {/* Tabs */}
                <div className="appear-1" style={{
                  display: "flex", gap: 2, background: C.card,
                  border: `1px solid ${C.edge}`, borderRadius: 10,
                  padding: 4, marginBottom: 16,
                }}>
                  {[
                    { key: "technique", label: "Technique" },
                    { key: "culture", label: "Culture & Salaire" },
                    { key: "synthese", label: "Synthèse" },
                    { key: "questions", label: "Entretien" },
                  ].map(tab => (
                    <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
                      flex: 1, padding: "8px 0", borderRadius: 7,
                      background: activeTab === tab.key ? C.lift : "transparent",
                      border: activeTab === tab.key ? `1px solid ${C.edge}` : "1px solid transparent",
                      color: activeTab === tab.key ? C.ice : C.fog,
                      fontSize: 12, fontWeight: 500, letterSpacing: "0.04em",
                      transition: "all .2s",
                    }}>
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Tab content */}
                <div className="appear-2" style={{
                  background: C.card, border: `1px solid ${C.edge}`,
                  borderRadius: 14, overflow: "hidden"
                }}>

                  {activeTab === "technique" && (
                    <div style={{ padding: 24 }}>
                      <div className="pfi" style={{ fontSize: 18, color: C.snow, marginBottom: 20 }}>
                        Adéquation technique
                      </div>

                      {result.adequation_technique.presentes.length > 0 && (
                        <div style={{ marginBottom: 20 }}>
                          <div style={{ fontSize: 10, color: C.green, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10 }}>
                            ✓ Compétences présentes
                          </div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                            {result.adequation_technique.presentes.map(c => (
                              <span key={c} style={{
                                background: C.greenG, border: `1px solid ${C.green}40`,
                                borderRadius: 4, padding: "4px 10px",
                                fontSize: 12, color: C.green, fontWeight: 400
                              }}>{c}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      {result.adequation_technique.manquantes.length > 0 && (
                        <div style={{ marginBottom: 20 }}>
                          <div style={{ fontSize: 10, color: C.red, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10 }}>
                            ✕ Compétences manquantes
                          </div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                            {result.adequation_technique.manquantes.map(c => (
                              <span key={c} style={{
                                background: C.redG, border: `1px solid ${C.red}40`,
                                borderRadius: 4, padding: "4px 10px",
                                fontSize: 12, color: C.red
                              }}>{c}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      {result.adequation_technique.bonus.length > 0 && (
                        <div style={{ marginBottom: 20 }}>
                          <div style={{ fontSize: 10, color: C.teal, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10 }}>
                            + Compétences bonus
                          </div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                            {result.adequation_technique.bonus.map(c => (
                              <span key={c} style={{
                                background: "rgba(56,189,248,0.10)", border: `1px solid ${C.teal}40`,
                                borderRadius: 4, padding: "4px 10px",
                                fontSize: 12, color: C.teal
                              }}>{c}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      <div style={{ borderTop: `1px solid ${C.edge}`, paddingTop: 20, marginTop: 4 }}>
                        <div style={{ fontSize: 10, color: C.mist, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10 }}>
                          Trajectoire professionnelle
                        </div>
                        <p style={{ fontSize: 13, color: C.mist, lineHeight: 1.7 }}>
                          {result.trajectoire.analyse}
                        </p>
                      </div>
                    </div>
                  )}

                  {activeTab === "culture" && (
                    <div style={{ padding: 24 }}>
                      <div style={{ marginBottom: 24 }}>
                        <div className="pfi" style={{ fontSize: 18, color: C.snow, marginBottom: 12 }}>
                          Alignement culturel
                        </div>
                        <p style={{ fontSize: 13, color: C.mist, lineHeight: 1.7 }}>
                          {result.alignement_culturel.analyse}
                        </p>
                      </div>

                      <div style={{ borderTop: `1px solid ${C.edge}`, paddingTop: 20 }}>
                        <div className="pfi" style={{ fontSize: 18, color: C.snow, marginBottom: 12 }}>
                          Adéquation salariale
                        </div>
                        <p style={{ fontSize: 13, color: C.mist, lineHeight: 1.7 }}>
                          {result.adequation_salariale.analyse}
                        </p>
                      </div>
                    </div>
                  )}

                  {activeTab === "synthese" && (
                    <div style={{ padding: 24 }}>
                      <div style={{ marginBottom: 24 }}>
                        <div style={{ fontSize: 10, color: C.green, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 14 }}>
                          Points forts distinctifs
                        </div>
                        {result.points_forts.map((p, i) => (
                          <div key={i} style={{
                            display: "flex", gap: 12, marginBottom: 12,
                            padding: "12px 16px", background: C.greenG,
                            border: `1px solid ${C.green}20`, borderRadius: 8
                          }}>
                            <span style={{ color: C.green, flexShrink: 0, marginTop: 1 }}>◆</span>
                            <span style={{ fontSize: 13, color: C.ice, lineHeight: 1.5 }}>{p}</span>
                          </div>
                        ))}
                      </div>

                      <div>
                        <div style={{ fontSize: 10, color: C.red, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 14 }}>
                          Signaux d'alerte
                        </div>
                        {result.signaux_alerte.map((s, i) => (
                          <div key={i} style={{
                            display: "flex", gap: 12, marginBottom: 12,
                            padding: "12px 16px", background: C.redG,
                            border: `1px solid ${C.red}20`, borderRadius: 8
                          }}>
                            <span style={{ color: C.red, flexShrink: 0, marginTop: 1 }}>⚠</span>
                            <span style={{ fontSize: 13, color: C.ice, lineHeight: 1.5 }}>{s}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {activeTab === "questions" && (
                    <div style={{ padding: 24 }}>
                      {result.questions_entretien ? (
                        <>
                          <div className="pfi" style={{ fontSize: 18, color: C.snow, marginBottom: 6 }}>
                            Questions d'entretien suggérées
                          </div>
                          <p style={{ fontSize: 12, color: C.fog, marginBottom: 24, lineHeight: 1.5 }}>
                            Ciblées sur les points à valider identifiés pendant l'analyse. Conçues pour être impossibles à contourner par une réponse vague.
                          </p>
                          {result.questions_entretien.map((q, i) => (
                            <div key={i} style={{
                              display: "flex", gap: 16, marginBottom: 16,
                              padding: "16px 20px", background: C.lift,
                              border: `1px solid ${C.edge}`, borderRadius: 10
                            }}>
                              <span className="jb" style={{
                                color: C.copper, fontSize: 11, fontWeight: 500,
                                flexShrink: 0, marginTop: 2, letterSpacing: "0.05em"
                              }}>Q{i + 1}</span>
                              <span style={{ fontSize: 14, color: C.ice, lineHeight: 1.6 }}>{q}</span>
                            </div>
                          ))}
                        </>
                      ) : (
                        <div style={{ textAlign: "center", padding: "32px 0" }}>
                          <div style={{ fontSize: 32, marginBottom: 12, opacity: 0.4 }}>✕</div>
                          <div style={{ color: C.fog, fontSize: 14 }}>
                            Aucune question d'entretien — profil classé <span style={{ color: C.red }}>Refusé</span>.
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Footer actions */}
                <div className="appear-3" style={{ marginTop: 16, display: "flex", gap: 12 }}>
                  <button style={{
                    flex: 1, padding: "12px 0",
                    background: C.copperB, border: `1px solid ${C.copperD}`,
                    borderRadius: 8, color: C.copper, fontSize: 12,
                    fontWeight: 500, letterSpacing: "0.08em", textTransform: "uppercase",
                  }}>
                    ↓ Exporter le rapport
                  </button>
                  <button style={{
                    flex: 1, padding: "12px 0",
                    background: "transparent", border: `1px solid ${C.edge}`,
                    borderRadius: 8, color: C.mist, fontSize: 12,
                    fontWeight: 500, letterSpacing: "0.08em", textTransform: "uppercase",
                  }}>
                    + Ajouter à un dossier
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function AnalyzingStep({ label, delay }) {
  const [visible, setVisible] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    const t1 = setTimeout(() => setVisible(true), delay);
    const t2 = setTimeout(() => setDone(true), delay + 400);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [delay]);

  if (!visible) return null;

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 10, marginTop: 10,
      animation: "fu .3s ease",
    }}>
      <div style={{
        width: 16, height: 16, borderRadius: "50%",
        background: done ? C.green : "transparent",
        border: `1.5px solid ${done ? C.green : C.copper}`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 9, color: C.green, flexShrink: 0,
        transition: "all .3s", boxShadow: done ? `0 0 8px ${C.green}60` : "none",
      }}>
        {done ? "✓" : ""}
      </div>
      <span style={{ fontSize: 12, color: done ? C.mist : C.ice, transition: "color .3s" }}>
        {label}
      </span>
    </div>
  );
}
