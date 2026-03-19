import { useState, useRef } from "react";
import { trpc } from "@/lib/trpc";
import { toast } from "sonner";
import { Link } from "wouter";
import {
  ArrowLeft, Sparkles, User, Briefcase, ChevronDown,
  CheckCircle2, AlertCircle, HelpCircle, RotateCcw,
  Download, ClipboardList,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import DashboardLayout from "@/components/DashboardLayout";

// ─── DEMO PROFILES ──────────────────────────────────────────────────────────

const DEMOS = [
  {
    label: "Technicien CNC senior",
    poste: "Technicien CNC / Programmeur Fanuc",
    competencesRequises: "Fanuc, métrologie 3D, décolletage précision, ISO 9001",
    salaireMin: 5000, salaireMax: 6000,
    cultureEntreprise: "PME industrielle, 25 collaborateurs, Arc Jurassien, autonomie valorisée",
    profilCandidat: `Polymécanicien CFC avec 9 ans d'expérience en décolletage de précision.

Expérience :
- MPS Micro Precision Systems, Bienne — Technicien CNC (6 ans)
  Programmation Fanuc 0i-MD, pièces <0.005mm, outillage céramique
- Tornos SA — Opérateur/Programmeur senior (3 ans)
  Décolletage automatique, Siemens 840D, ISO 9001

Compétences : Fanuc, Siemens 840D, métrologie Zeiss 3D, ISO 9001
Prétention : 5 800 CHF/mois`,
  },
  {
    label: "Comptable en transition",
    poste: "Comptable / Assistant financier",
    competencesRequises: "Abacus, clôtures mensuelles, TVA, bilan annuel",
    salaireMin: 4500, salaireMax: 5100,
    cultureEntreprise: "PME industrielle, Delémont, environnement structuré",
    profilCandidat: `Titulaire d'un brevet fédéral de comptable, 4 ans d'expérience fiduciaire.

Parcours :
- Fiduciaire Perrenoud & Associés, Porrentruy (4 ans)
  Gestion 35 clients PME, clôtures mensuelles, déclarations TVA

Logiciels : Abacus (maîtrisé), SAP (basique), Excel avancé
Prétention : 5 200 CHF/mois`,
  },
  {
    label: "Directeur supply chain surqualifié",
    poste: "Responsable logistique",
    competencesRequises: "SAP MM/WM, gestion entrepôt, supply chain, management",
    salaireMin: 6500, salaireMax: 7500,
    cultureEntreprise: "PME chimie, Bâle, 80 collaborateurs",
    profilCandidat: `15 ans supply chain pharma. Novartis (8 ans) + Roche (7 ans).
SAP MM/WM expert, entrepôts 50 000 m², équipe 40 personnes.
MBA UNIL. Prétention : 12 000 CHF/mois.`,
  },
];

// ─── CLASSIFICATION CONFIG ───────────────────────────────────────────────────

const CLASS_CONFIG: Record<string, { color: string; bg: string; icon: React.ReactNode }> = {
  "A-Player":    { color: "text-emerald-400", bg: "bg-emerald-400/10 border-emerald-400/30", icon: <CheckCircle2 className="w-4 h-4" /> },
  "Intéressant": { color: "text-amber-400",   bg: "bg-amber-400/10 border-amber-400/30",   icon: <HelpCircle className="w-4 h-4" /> },
  "Conditionnel":{ color: "text-sky-400",     bg: "bg-sky-400/10 border-sky-400/30",       icon: <AlertCircle className="w-4 h-4" /> },
  "Refusé":      { color: "text-red-400",     bg: "bg-red-400/10 border-red-400/30",       icon: <AlertCircle className="w-4 h-4" /> },
};

// ─── SUB COMPONENTS ──────────────────────────────────────────────────────────

function ScoreRing({ score, color }: { score: number | null; color: string }) {
  const r = 36;
  const circ = 2 * Math.PI * r;
  const fill = score != null ? (score / 100) * circ * 0.75 : 0;

  return (
    <div className="relative w-24 h-24 flex items-center justify-center">
      <svg width="96" height="96" viewBox="0 0 96 96" style={{ transform: "rotate(135deg)" }}>
        <circle cx="48" cy="48" r={r} fill="none" stroke="#1c2a3e" strokeWidth="6"
          strokeDasharray={`${circ * 0.75} ${circ * 0.25}`} strokeLinecap="round" />
        <circle cx="48" cy="48" r={r} fill="none" stroke="currentColor" strokeWidth="6"
          strokeDasharray={`${fill} ${circ - fill}`} strokeLinecap="round"
          className={`transition-all duration-1000 ${color}`}
          style={{ filter: "drop-shadow(0 0 6px currentColor)" }} />
      </svg>
      <div className="absolute text-center">
        <div className={`text-2xl font-mono font-medium ${color}`}>{score ?? "—"}</div>
        <div className="text-[10px] text-slate-500 tracking-wider">/100</div>
      </div>
    </div>
  );
}

function DimBar({ label, score, color }: { label: string; score: number | null; color: string }) {
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-400 uppercase tracking-wider">{label}</span>
        <span className={`font-mono ${color}`}>{score != null ? `${score}/100` : "N/A"}</span>
      </div>
      <div className="h-[3px] rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full transition-all duration-1000 ${color.replace("text-", "bg-")}`}
          style={{ width: `${score ?? 0}%` }}
        />
      </div>
    </div>
  );
}

function Chip({ text, type }: { text: string; type: "present" | "missing" | "bonus" }) {
  const styles = {
    present: "bg-emerald-400/10 border-emerald-400/30 text-emerald-400",
    missing:  "bg-red-400/10 border-red-400/30 text-red-400",
    bonus:    "bg-sky-400/10 border-sky-400/30 text-sky-400",
  };
  return (
    <span className={`inline-block border rounded px-2 py-0.5 text-xs mr-1.5 mb-1.5 ${styles[type]}`}>
      {text}
    </span>
  );
}

// ─── MAIN PAGE ───────────────────────────────────────────────────────────────

export default function CVAnalyzer() {
  const [form, setForm] = useState({
    poste: "", competencesRequises: "", salaireMin: "", salaireMax: "",
    cultureEntreprise: "", profilCandidat: "",
  });
  const [showDemo, setShowDemo] = useState(false);
  const [activeTab, setActiveTab] = useState<"technique" | "culture" | "synthese" | "entretien">("technique");
  const resultRef = useRef<HTMLDivElement>(null);

  const mutation = trpc.umbra.analyzeCV.useMutation({
    onSuccess: () => {
      toast.success("Analyse terminée");
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    },
    onError: (err) => {
      toast.error(`Erreur : ${err.message}`);
    },
  });

  const { data: result, isPending } = mutation;
  const cfg = result ? CLASS_CONFIG[result.classification] : null;

  function loadDemo(d: typeof DEMOS[0]) {
    setForm({
      poste: d.poste,
      competencesRequises: d.competencesRequises,
      salaireMin: String(d.salaireMin),
      salaireMax: String(d.salaireMax),
      cultureEntreprise: d.cultureEntreprise,
      profilCandidat: d.profilCandidat,
    });
    setShowDemo(false);
    mutation.reset();
  }

  function handleSubmit() {
    if (!form.poste.trim() || !form.profilCandidat.trim()) {
      toast.error("Le poste et le profil candidat sont requis.");
      return;
    }
    mutation.mutate({
      poste: form.poste,
      competencesRequises: form.competencesRequises,
      salaireMin: Number(form.salaireMin) || 0,
      salaireMax: Number(form.salaireMax) || 0,
      profilCandidat: form.profilCandidat,
      cultureEntreprise: form.cultureEntreprise || undefined,
    });
  }

  function handleReset() {
    setForm({ poste: "", competencesRequises: "", salaireMin: "", salaireMax: "", cultureEntreprise: "", profilCandidat: "" });
    mutation.reset();
  }

  const canSubmit = form.poste.trim() && form.profilCandidat.trim() && !isPending;

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto px-4 py-8">

        {/* Header */}
        <div className="mb-8">
          <Link href="/dashboard">
            <Button variant="ghost" size="sm" className="text-slate-400 hover:text-slate-200 mb-4 -ml-2">
              <ArrowLeft className="w-4 h-4 mr-1" /> Tableau de bord
            </Button>
          </Link>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-slate-100 flex items-center gap-2">
                <Sparkles className="w-6 h-6 text-amber-500" />
                Analyseur de profils
              </h1>
              <p className="text-slate-400 text-sm mt-1">
                Évaluation IA structurée — compétences, trajectoire, alignement culturel et salarial
              </p>
            </div>
            <div className="text-right text-xs text-slate-500">
              <div>Gemini Flash · Prompt 6 couches</div>
              <div className="text-emerald-500">~0.0002 CHF / analyse</div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6 items-start">

          {/* ── FORM ─────────────────────────────────────────────────── */}
          <div className="space-y-4">

            {/* Demo loader */}
            <div className="relative">
              <Button
                variant="outline" size="sm"
                className="border-amber-700/50 text-amber-500 hover:bg-amber-500/10"
                onClick={() => setShowDemo(d => !d)}
              >
                <ChevronDown className="w-3 h-3 mr-1.5" />
                Charger un profil de démonstration
              </Button>
              {showDemo && (
                <div className="absolute top-10 left-0 z-20 w-72 rounded-xl border border-slate-700 bg-slate-900 shadow-2xl overflow-hidden">
                  {DEMOS.map((d, i) => (
                    <button key={i} onClick={() => loadDemo(d)}
                      className="w-full text-left px-4 py-3 hover:bg-slate-800 border-b border-slate-800 last:border-b-0 transition-colors">
                      <div className="text-sm text-slate-200 font-medium">{d.label}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{d.poste}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Form card */}
            <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">

              {/* Poste */}
              <div className="px-5 py-4 border-b border-slate-800">
                <label className="text-[10px] text-amber-500 tracking-widest uppercase block mb-2 flex items-center gap-1.5">
                  <Briefcase className="w-3 h-3" /> Poste à pourvoir
                </label>
                <input
                  value={form.poste}
                  onChange={e => setForm(f => ({ ...f, poste: e.target.value }))}
                  placeholder="Ex: Technicien CNC / Programmeur Fanuc"
                  className="w-full bg-transparent text-slate-100 text-sm placeholder:text-slate-600 outline-none"
                />
              </div>

              {/* Compétences */}
              <div className="px-5 py-4 border-b border-slate-800">
                <label className="text-[10px] text-amber-500 tracking-widest uppercase block mb-2">
                  Compétences requises
                </label>
                <input
                  value={form.competencesRequises}
                  onChange={e => setForm(f => ({ ...f, competencesRequises: e.target.value }))}
                  placeholder="Ex: Fanuc, métrologie 3D, ISO 9001"
                  className="w-full bg-transparent text-slate-300 text-sm placeholder:text-slate-600 outline-none"
                />
              </div>

              {/* Salaire */}
              <div className="px-5 py-4 border-b border-slate-800 grid grid-cols-2 gap-4">
                <div>
                  <label className="text-[10px] text-amber-500 tracking-widest uppercase block mb-2">Salaire min (CHF)</label>
                  <input type="number" value={form.salaireMin}
                    onChange={e => setForm(f => ({ ...f, salaireMin: e.target.value }))}
                    placeholder="5 000"
                    className="w-full bg-transparent text-slate-300 text-sm placeholder:text-slate-600 outline-none" />
                </div>
                <div>
                  <label className="text-[10px] text-amber-500 tracking-widest uppercase block mb-2">Salaire max (CHF)</label>
                  <input type="number" value={form.salaireMax}
                    onChange={e => setForm(f => ({ ...f, salaireMax: e.target.value }))}
                    placeholder="6 500"
                    className="w-full bg-transparent text-slate-300 text-sm placeholder:text-slate-600 outline-none" />
                </div>
              </div>

              {/* Culture */}
              <div className="px-5 py-4 border-b border-slate-800">
                <label className="text-[10px] text-amber-500 tracking-widest uppercase block mb-2">
                  Culture d'entreprise <span className="text-slate-600 normal-case tracking-normal">(optionnel)</span>
                </label>
                <input
                  value={form.cultureEntreprise}
                  onChange={e => setForm(f => ({ ...f, cultureEntreprise: e.target.value }))}
                  placeholder="Ex: PME industrielle, 25 personnes, autonomie valorisée"
                  className="w-full bg-transparent text-slate-300 text-sm placeholder:text-slate-600 outline-none" />
              </div>

              {/* CV */}
              <div className="px-5 py-4">
                <label className="text-[10px] text-amber-500 tracking-widest uppercase block mb-2 flex items-center gap-1.5">
                  <User className="w-3 h-3" /> Profil candidat — CV + lettre
                </label>
                <textarea
                  value={form.profilCandidat}
                  onChange={e => setForm(f => ({ ...f, profilCandidat: e.target.value }))}
                  placeholder="Collez ici le CV, la lettre de motivation ou toute information sur le candidat..."
                  rows={10}
                  className="w-full bg-transparent text-slate-400 text-sm placeholder:text-slate-600 outline-none resize-none leading-relaxed"
                />
                {form.profilCandidat && (
                  <div className="text-right text-[10px] text-slate-600 mt-1 font-mono">
                    {form.profilCandidat.split(/\s+/).filter(Boolean).length} mots
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="px-5 pb-5 flex gap-3">
                <Button
                  onClick={handleSubmit}
                  disabled={!canSubmit}
                  className="flex-1 bg-amber-600 hover:bg-amber-500 text-slate-950 font-semibold disabled:opacity-40"
                >
                  {isPending ? (
                    <><span className="animate-spin mr-2">◆</span> Analyse en cours…</>
                  ) : (
                    <><Sparkles className="w-4 h-4 mr-2" /> Analyser le profil</>
                  )}
                </Button>
                {(result || form.profilCandidat) && (
                  <Button variant="outline" size="icon" onClick={handleReset} className="border-slate-700">
                    <RotateCcw className="w-4 h-4" />
                  </Button>
                )}
              </div>
            </div>

            {/* Info */}
            <p className="text-[11px] text-slate-600 px-1">
              Prompt système 6 couches · Gemini Flash · Température 0 · Conforme LPD / RGPD
            </p>
          </div>

          {/* ── RESULTS ──────────────────────────────────────────────── */}
          <div ref={resultRef}>

            {/* Idle state */}
            {!result && !isPending && (
              <div className="rounded-xl border border-slate-800 bg-slate-900 flex flex-col items-center justify-center py-20 text-center">
                <ClipboardList className="w-10 h-10 text-slate-700 mb-4" />
                <p className="text-slate-500 text-sm">En attente d'analyse</p>
                <p className="text-slate-600 text-xs mt-2 max-w-48 leading-relaxed">
                  Renseignez le poste et le profil candidat, puis lancez l'analyse.
                </p>
                <div className="mt-6 space-y-2 text-xs text-slate-600">
                  {["Score global /100", "Analyse 4 dimensions", "Signaux d'alerte", "Questions d'entretien"].map(l => (
                    <div key={l} className="flex items-center gap-2">
                      <span className="text-amber-700">◆</span> {l}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Loading state */}
            {isPending && (
              <div className="rounded-xl border border-amber-700/30 bg-slate-900 flex flex-col items-center justify-center py-16 text-center relative overflow-hidden">
                <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-amber-500/60 to-transparent animate-pulse" />
                <div className="w-16 h-16 rounded-full border-2 border-slate-800 border-t-amber-500 animate-spin mb-6" />
                <p className="text-slate-300 text-sm font-medium mb-6">Analyse en cours</p>
                <div className="space-y-3 text-left w-56">
                  {[
                    "Évaluation des compétences techniques",
                    "Analyse de la trajectoire",
                    "Détection des signaux culturels",
                    "Vérification de l'adéquation salariale",
                    "Génération du rapport structuré",
                  ].map((step, i) => (
                    <div key={i} className="flex items-center gap-2.5 text-xs text-slate-400">
                      <div className="w-4 h-4 rounded-full border border-amber-700/50 flex items-center justify-center flex-shrink-0">
                        <span className="text-amber-500 animate-pulse text-[8px]">◆</span>
                      </div>
                      {step}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Result */}
            {result && cfg && (
              <div className="space-y-4 animate-in fade-in duration-500">

                {/* Classification card */}
                <div className="rounded-xl border border-slate-700 bg-slate-900 p-5 flex items-center gap-6">
                  <ScoreRing score={result.score_global} color={cfg.color} />
                  <div className="flex-1">
                    <Badge className={`mb-3 border ${cfg.bg} ${cfg.color} flex items-center gap-1.5 w-fit`}>
                      {cfg.icon} {result.classification}
                    </Badge>
                    <div className="grid grid-cols-2 gap-x-6">
                      <DimBar label="Technique" score={result.adequation_technique.score} color={cfg.color} />
                      <DimBar label="Trajectoire" score={result.trajectoire.score} color={cfg.color} />
                      <DimBar label="Culturel" score={result.alignement_culturel.score} color={cfg.color} />
                      <DimBar label="Salarial" score={result.adequation_salariale.score} color={cfg.color} />
                    </div>
                  </div>
                </div>

                {/* Tabs */}
                <div className="rounded-lg border border-slate-800 bg-slate-900 p-1 flex gap-1">
                  {(["technique", "culture", "synthese", "entretien"] as const).map(tab => (
                    <button key={tab} onClick={() => setActiveTab(tab)}
                      className={`flex-1 py-2 rounded-md text-xs font-medium tracking-wide transition-colors ${
                        activeTab === tab
                          ? "bg-slate-800 text-slate-100"
                          : "text-slate-500 hover:text-slate-300"
                      }`}>
                      {tab === "technique" ? "Technique" :
                       tab === "culture" ? "Culture & Salaire" :
                       tab === "synthese" ? "Synthèse" : "Entretien"}
                    </button>
                  ))}
                </div>

                {/* Tab panels */}
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">

                  {activeTab === "technique" && (
                    <div>
                      <h3 className="text-slate-200 font-medium mb-4">Adéquation technique</h3>
                      {result.adequation_technique.presentes.length > 0 && (
                        <div className="mb-4">
                          <p className="text-[10px] text-emerald-500 uppercase tracking-widest mb-2">✓ Présentes</p>
                          <div>{result.adequation_technique.presentes.map(c => <Chip key={c} text={c} type="present" />)}</div>
                        </div>
                      )}
                      {result.adequation_technique.manquantes.length > 0 && (
                        <div className="mb-4">
                          <p className="text-[10px] text-red-500 uppercase tracking-widest mb-2">✕ Manquantes</p>
                          <div>{result.adequation_technique.manquantes.map(c => <Chip key={c} text={c} type="missing" />)}</div>
                        </div>
                      )}
                      {result.adequation_technique.bonus.length > 0 && (
                        <div className="mb-4">
                          <p className="text-[10px] text-sky-500 uppercase tracking-widest mb-2">+ Bonus</p>
                          <div>{result.adequation_technique.bonus.map(c => <Chip key={c} text={c} type="bonus" />)}</div>
                        </div>
                      )}
                      <div className="mt-4 pt-4 border-t border-slate-800">
                        <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-2">Trajectoire</p>
                        <p className="text-sm text-slate-400 leading-relaxed">{result.trajectoire.analyse}</p>
                      </div>
                    </div>
                  )}

                  {activeTab === "culture" && (
                    <div className="space-y-6">
                      <div>
                        <h3 className="text-slate-200 font-medium mb-3">Alignement culturel</h3>
                        <p className="text-sm text-slate-400 leading-relaxed">{result.alignement_culturel.analyse}</p>
                      </div>
                      <div className="pt-4 border-t border-slate-800">
                        <h3 className="text-slate-200 font-medium mb-3">Adéquation salariale</h3>
                        <p className="text-sm text-slate-400 leading-relaxed">{result.adequation_salariale.analyse}</p>
                      </div>
                    </div>
                  )}

                  {activeTab === "synthese" && (
                    <div className="space-y-4">
                      <div>
                        <p className="text-[10px] text-emerald-500 uppercase tracking-widest mb-3">Points forts</p>
                        {result.points_forts.map((p, i) => (
                          <div key={i} className="flex gap-3 mb-2.5 bg-emerald-400/5 border border-emerald-400/15 rounded-lg px-3 py-2.5">
                            <span className="text-emerald-500 flex-shrink-0 mt-0.5">◆</span>
                            <span className="text-sm text-slate-300">{p}</span>
                          </div>
                        ))}
                      </div>
                      <div className="pt-2">
                        <p className="text-[10px] text-red-500 uppercase tracking-widest mb-3">Signaux d'alerte</p>
                        {result.signaux_alerte.map((s, i) => (
                          <div key={i} className="flex gap-3 mb-2.5 bg-red-400/5 border border-red-400/15 rounded-lg px-3 py-2.5">
                            <span className="text-red-500 flex-shrink-0 mt-0.5">⚠</span>
                            <span className="text-sm text-slate-300">{s}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {activeTab === "entretien" && (
                    result.questions_entretien ? (
                      <div>
                        <h3 className="text-slate-200 font-medium mb-1">Questions d'entretien</h3>
                        <p className="text-xs text-slate-500 mb-4">Ciblées sur les points à valider. Conçues pour être impossibles à contourner.</p>
                        {result.questions_entretien.map((q, i) => (
                          <div key={i} className="flex gap-3 mb-3 bg-slate-800 rounded-lg px-4 py-3">
                            <span className="font-mono text-amber-500 text-xs font-medium flex-shrink-0 mt-0.5">Q{i + 1}</span>
                            <span className="text-sm text-slate-200 leading-relaxed">{q}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-10">
                        <AlertCircle className="w-8 h-8 text-slate-700 mx-auto mb-3" />
                        <p className="text-slate-500 text-sm">Pas de questions — profil <span className="text-red-400">Refusé</span>.</p>
                      </div>
                    )
                  )}
                </div>

                {/* Meta + actions */}
                <div className="flex items-center justify-between">
                  <div className="text-[10px] text-slate-600 font-mono">
                    {result.meta.tokens_input}t in · {result.meta.tokens_output}t out ·{" "}
                    {result.meta.cout_estime_chf.toFixed(4)} CHF · {result.meta.duree_ms}ms
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" className="border-amber-700/40 text-amber-600 hover:bg-amber-500/10 text-xs">
                      <Download className="w-3 h-3 mr-1.5" /> Exporter
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
