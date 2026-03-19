import { useState, useEffect, useRef, useCallback } from "react";

/* ═══════════════════════════════════════════════════════════════════════
   UMBRA — VERSION DÉFINITIVE
   Fusion complète v1 + v2
   
   Écrans :
   0. Landing          — réseau animé + tous les game changers
   1. Onboarding       — mode veille/actif + protection employeur
   2. Culture Quiz     — 5 questions → empreinte radar
   3. Profile          — secteur / compétences / géo / salaire / préavis
   4. Dashboard        — liste matchs avec score, trust, intel, salary
   5. Match Detail     — radar, entretien inversé, passeport, protocole
   6. Reveal           — animation cinématique mutuelle
   7. Trust Passport   — score détaillé + mécaniques anti-curieux
   8. Market Intel     — salaires, pénuries, prédictions IA
   9. Off-boarding     — départ géré = prochaine entrée
   ═══════════════════════════════════════════════════════════════════════ */

// ── PALETTE ──────────────────────────────────────────────────────────────────
const C = {
  void:    "#05080e",
  deep:    "#090d18",
  surface: "#0f1520",
  card:    "#121a28",
  lift:    "#172030",
  edge:    "#1c2a3e",
  rim:     "#243548",
  copper:  "#d97b3a",
  copperL: "#e8944f",
  copperD: "#9a5520",
  copperXL:"#f0aa70",
  copperG: "rgba(217,123,58,0.10)",
  copperB: "rgba(217,123,58,0.05)",
  ice:     "#edeae4",
  snow:    "#f8f5f0",
  mist:    "#7a8da8",
  fog:     "#4d5e75",
  dim:     "#2e3d52",
  ghost:   "#1a2436",
  green:   "#2dd4aa",
  greenD:  "#1a9978",
  red:     "#e05555",
  teal:    "#38bdf8",
  tealD:   "#0e8fc0",
  signal:  "#9b87f0",
  gold:    "#f0c060",
};

// ── STYLES ───────────────────────────────────────────────────────────────────
const STYLE = `
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500;1,600&family=JetBrains+Mono:wght@300;400;500&family=Outfit:wght@200;300;400;500;600&display=swap');

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html{scroll-behavior:smooth;}
body{background:${C.void};color:${C.ice};font-family:'Outfit',sans-serif;font-weight:300;overflow-x:hidden;}
::selection{background:${C.copperG};color:${C.copper};}
::-webkit-scrollbar{width:3px;}
::-webkit-scrollbar-track{background:${C.deep};}
::-webkit-scrollbar-thumb{background:${C.edge};}

/* TYPOGRAPHY */
.pf  {font-family:'Playfair Display',serif;}
.pfi {font-family:'Playfair Display',serif;font-style:italic;}
.jb  {font-family:'JetBrains Mono',monospace;}
.out {font-family:'Outfit',sans-serif;}

/* ANIMATIONS */
@keyframes fu      {from{opacity:0;transform:translateY(28px)}to{opacity:1;transform:none}}
@keyframes fi      {from{opacity:0}to{opacity:1}}
@keyframes pulse   {0%,100%{opacity:1}50%{opacity:.25}}
@keyframes breathe {0%,100%{transform:scale(1);opacity:.5}50%{transform:scale(1.08);opacity:1}}
@keyframes scan    {0%{top:-100%}100%{top:200%}}
@keyframes spin    {to{transform:rotate(360deg)}}
@keyframes shimmer {0%{transform:translateX(-100%)}100%{transform:translateX(400%)}}
@keyframes pgrow   {from{stroke-dashoffset:var(--c)}to{stroke-dashoffset:var(--o)}}
@keyframes particle{0%{opacity:0;transform:scale(0) translate(0,0)}50%{opacity:1;transform:scale(1) translate(0,0)}100%{opacity:0;transform:scale(0) translate(var(--tx),var(--ty))}}
@keyframes reveal  {from{opacity:0;transform:scale(.85)}to{opacity:1;transform:scale(1)}}
@keyframes copGlow {0%,100%{box-shadow:0 0 0 0 rgba(217,123,58,0)}50%{box-shadow:0 0 60px 8px rgba(217,123,58,.18)}}
@keyframes slideR  {from{transform:translateX(-20px);opacity:0}to{transform:none;opacity:1}}
@keyframes halo    {0%,100%{opacity:.15;transform:scale(1)}50%{opacity:.35;transform:scale(1.15)}}
@keyframes blink   {0%,100%{opacity:1}49%{opacity:1}50%{opacity:0}99%{opacity:0}}

.fu  {animation:fu .65s ease both;}
.fu1 {animation:fu .65s .08s ease both;}
.fu2 {animation:fu .65s .16s ease both;}
.fu3 {animation:fu .65s .24s ease both;}
.fu4 {animation:fu .65s .32s ease both;}
.fu5 {animation:fu .65s .40s ease both;}
.fu6 {animation:fu .65s .48s ease both;}
.fu7 {animation:fu .65s .56s ease both;}

/* LAYOUT */
.wrap   {max-width:960px;margin:0 auto;padding:48px 24px;}
.wrap-w {max-width:1080px;margin:0 auto;padding:48px 24px;}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;}
@media(max-width:768px){.g2{grid-template-columns:1fr}.g3{grid-template-columns:1fr 1fr}.g4{grid-template-columns:1fr 1fr}}

/* COMPONENTS */
.pill{
  display:inline-flex;align-items:center;gap:6px;
  padding:5px 12px;font-family:'JetBrains Mono',monospace;
  font-size:10px;letter-spacing:.08em;border:1px solid;
}
.p-cop{border-color:rgba(217,123,58,.5);color:${C.copper};background:${C.copperG};}
.p-tl {border-color:rgba(56,189,248,.3);color:${C.teal};background:rgba(56,189,248,.06);}
.p-gr {border-color:rgba(45,212,170,.3);color:${C.green};background:rgba(45,212,170,.06);}
.p-gh {border-color:${C.edge};color:${C.mist};}
.p-sig{border-color:rgba(155,135,240,.4);color:${C.signal};background:rgba(155,135,240,.08);}
.p-gld{border-color:rgba(240,192,96,.4);color:${C.gold};background:rgba(240,192,96,.08);}
.p-red{border-color:rgba(224,85,85,.4);color:${C.red};background:rgba(224,85,85,.08);}

.btn{font-family:'Outfit',sans-serif;font-size:14px;font-weight:400;letter-spacing:.03em;padding:14px 36px;cursor:pointer;transition:all .25s;border:none;outline:none;}
.btn-p{background:${C.copper};color:${C.void};font-weight:500;}
.btn-p:hover{background:${C.copperL};transform:translateY(-2px);box-shadow:0 12px 40px rgba(217,123,58,.35);}
.btn-p:active{transform:none;}
.btn-o{background:transparent;color:${C.mist};border:1px solid ${C.edge};}
.btn-o:hover{border-color:${C.copper};color:${C.copper};}
.btn-sm{padding:9px 20px;font-size:13px;}
.btn-xs{padding:6px 14px;font-size:12px;}

.card{background:${C.card};border:1px solid ${C.edge};transition:all .3s;}
.card-h:hover{border-color:rgba(217,123,58,.4);box-shadow:0 8px 48px rgba(217,123,58,.08);}

.inp{width:100%;background:${C.ghost};border:1px solid ${C.edge};color:${C.ice};padding:13px 16px;font-family:'Outfit',sans-serif;font-size:14px;font-weight:300;outline:none;transition:border-color .2s;}
.inp:focus{border-color:${C.copper};}
.inp::placeholder{color:${C.dim};}

.lbl{display:block;font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.1em;color:${C.mist};text-transform:uppercase;margin-bottom:10px;}

.rng{-webkit-appearance:none;width:100%;height:1px;background:${C.edge};outline:none;}
.rng::-webkit-slider-thumb{-webkit-appearance:none;width:18px;height:18px;background:${C.copper};border-radius:50%;cursor:pointer;transition:transform .15s;}
.rng::-webkit-slider-thumb:hover{transform:scale(1.25);}

.tog{width:48px;height:26px;background:${C.edge};border-radius:13px;cursor:pointer;position:relative;transition:background .25s;border:none;flex-shrink:0;}
.tog::after{content:'';position:absolute;top:3px;left:3px;width:20px;height:20px;border-radius:50%;background:${C.mist};transition:all .25s;}
.tog.on{background:${C.copper};}
.tog.on::after{transform:translateX(22px);background:${C.void};}

.div{height:1px;background:${C.edge};}

/* NAV */
.nav{position:sticky;top:0;z-index:200;display:flex;align-items:center;justify-content:space-between;padding:0 48px;height:64px;background:rgba(5,8,14,.88);backdrop-filter:blur(28px);border-bottom:1px solid ${C.edge};}
.logo{font-family:'Playfair Display',serif;font-size:22px;font-weight:400;letter-spacing:.28em;color:${C.copper};text-transform:uppercase;cursor:pointer;display:flex;align-items:center;gap:8px;}
.logo-d{width:5px;height:5px;border-radius:50%;background:${C.copper};animation:pulse 2.5s infinite;}
.nav-t{display:flex;gap:2px;}
.nav-b{padding:8px 20px;font-size:13px;color:${C.mist};cursor:pointer;background:none;border:none;font-family:'Outfit',sans-serif;transition:color .2s;border-bottom:2px solid transparent;}
.nav-b:hover{color:${C.ice};}
.nav-b.on{color:${C.copper};border-bottom-color:${C.copper};}

/* NOISE + SCAN */
.noise{position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.022;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");}
.scan-w{position:fixed;inset:0;pointer-events:none;z-index:1;overflow:hidden;}
.scan{position:absolute;left:0;right:0;height:2px;background:linear-gradient(to bottom,transparent,rgba(217,123,58,.04),transparent);animation:scan 9s linear infinite;}

/* MATCH CARD */
.mc{position:relative;overflow:hidden;background:${C.card};border:1px solid ${C.edge};padding:24px;cursor:pointer;transition:all .35s;}
.mc::after{content:'';position:absolute;inset:0;background:linear-gradient(135deg,${C.copperG} 0%,transparent 55%);opacity:0;transition:opacity .35s;}
.mc:hover{border-color:rgba(217,123,58,.5);transform:translateX(5px);}
.mc:hover::after{opacity:1;}
.mc-bar{position:absolute;left:0;top:0;bottom:0;width:3px;background:linear-gradient(to bottom,${C.copper},${C.copperD});transform:scaleY(0);transform-origin:top;transition:transform .35s;}
.mc:hover .mc-bar{transform:scaleY(1);}
.mc-rank{position:absolute;top:0;right:0;padding:5px 14px;background:${C.copperG};border-left:1px solid rgba(217,123,58,.3);border-bottom:1px solid rgba(217,123,58,.3);font-family:'JetBrains Mono',monospace;font-size:9px;color:${C.copper};letter-spacing:.1em;}

/* PROGRESS / INTEL BAR */
.pb{height:5px;background:${C.ghost};border-radius:3px;overflow:hidden;position:relative;}
.pf{height:100%;border-radius:3px;position:relative;overflow:hidden;transition:width 1.2s cubic-bezier(.4,0,.2,1);}
.pf::after{content:'';position:absolute;top:0;bottom:0;left:0;width:35%;background:linear-gradient(90deg,transparent,rgba(255,255,255,.28),transparent);animation:shimmer 2.4s infinite;}

/* REVEAL */
.rev-ov{position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;background:${C.void};animation:fi .4s ease;}
.rev-c{text-align:center;position:relative;}
.rev-pts{position:absolute;inset:-120px;pointer-events:none;}
.rp{position:absolute;border-radius:50%;animation:particle 1.8s ease both;}

/* SECTOR CARD */
.sc{padding:18px 12px;text-align:center;cursor:pointer;transition:all .22s;background:${C.card};border:1px solid ${C.edge};}
.sc:hover{border-color:rgba(217,123,58,.35);background:${C.copperB};}
.sc.sel{border-color:${C.copper};background:${C.copperG};}

/* QUIZ CHOICE */
.qc{padding:14px 18px;border:1px solid ${C.edge};cursor:pointer;transition:all .18s;background:transparent;color:${C.ice};text-align:left;font-family:'Outfit',sans-serif;font-size:14px;font-weight:300;display:flex;align-items:center;gap:12px;width:100%;}
.qc:hover{border-color:rgba(217,123,58,.4);background:${C.copperB};}
.qc.sel{border-color:${C.copper};background:${C.copperG};color:${C.copper};}
.qc-dot{width:10px;height:10px;border-radius:50%;border:1px solid ${C.edge};flex-shrink:0;transition:all .18s;}
.qc.sel .qc-dot{background:${C.copper};border-color:${C.copper};}

/* PASSPORT */
.pass{border:1px solid rgba(217,123,58,.4);background:linear-gradient(135deg,${C.card},${C.surface});padding:32px;position:relative;overflow:hidden;}
.pass::before{content:'';position:absolute;inset:0;background:repeating-linear-gradient(45deg,transparent,transparent 8px,rgba(217,123,58,.018) 8px,rgba(217,123,58,.018) 9px);}
.pass-mrz{font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:.12em;color:${C.dim};margin-top:20px;border-top:1px solid ${C.edge};padding-top:12px;user-select:none;line-height:2;}

/* CHOICE CARD */
.cc{padding:24px;cursor:pointer;transition:all .25s;border:1px solid ${C.edge};background:${C.card};}
.cc:hover{border-color:rgba(217,123,58,.35);}
.cc.sel{border-color:${C.copper};background:${C.copperG};}

/* FOOTER */
.foot{border-top:1px solid ${C.edge};padding:32px 48px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px;}

/* TRUST STEP ROW */
.ts-row{display:flex;align-items:center;gap:14px;padding:14px 0;border-bottom:1px solid ${C.edge};}
.ts-row:last-child{border-bottom:none;}
.ts-icon{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;}

/* CREDIT BADGE */
.credit{padding:4px 10px;border:1px solid;border-radius:2px;font-family:'JetBrains Mono',monospace;font-size:11px;}
`;

// ── DATA ─────────────────────────────────────────────────────────────────────

const SECTORS = [
  {id:"it",          sym:"⬡", label:"IT & Digital",   col:C.teal  },
  {id:"industrie",   sym:"◈", label:"Industrie",       col:C.copper},
  {id:"finance",     sym:"◇", label:"Finance & Audit", col:C.signal},
  {id:"sante",       sym:"✦", label:"Santé",           col:C.green },
  {id:"batiment",    sym:"◻", label:"Bâtiment",        col:C.copper},
  {id:"commerce",    sym:"◈", label:"Commerce B2B",    col:C.teal  },
  {id:"logistique",  sym:"⬡", label:"Logistique",      col:C.mist  },
  {id:"artisanat",   sym:"◇", label:"Artisanat",       col:C.copper},
  {id:"agriculture", sym:"✦", label:"Agriculture",     col:C.green },
];

const SKILLS_MAP = {
  it:         ["React / Next.js","Node.js","Python","PostgreSQL","Docker / K8s","AWS / GCP","Machine Learning","Cybersécurité","Architecture microservices","React Native","DevOps CI/CD","TypeScript","Elasticsearch","GraphQL"],
  finance:    ["IFRS / Swiss GAAP","Comptabilité analytique","SAP FI/CO","Analyse financière","Audit interne","Risk Management","Fiscalité CH/FR","Bloomberg Terminal","Excel / Power BI","Consolidation","Contrôle de gestion","Trésorerie"],
  industrie:  ["CNC Fanuc","Fraisage 5 axes","Soudure TIG/MIG","Métrologie 3D","Lean / 5S","PLC Siemens","SolidWorks","AutoCAD","Contrôle qualité ISO","Heidenhain","Robotique KUKA","Injection plastique"],
  sante:      ["Soins infirmiers","Gériatrie","Urgences / SMUR","Bloc opératoire","Psychiatrie","Radiologie","Pharmacie clinique","Soins palliatifs","Pédiatrie","Oncologie","Anesthésie","Réanimation"],
  batiment:   ["Gestion de chantier","Béton armé","Coffreur-bancheur","Maçonnerie","Électricité NIBT","Plomberie / CVS","Isolation thermique","BIM / Revit","AutoCAD 2D/3D","Menuiserie chantier","Carrelage","Peinture"],
  commerce:   ["Vente B2B grands comptes","CRM Salesforce","Négociation","Key Account Management","E-commerce","Marketing digital","Trade marketing","Category management","Formation équipe vente"],
  logistique: ["WMS","Supply chain","Transport international","Douane / transit","CACES 1-5","Gestion entrepôt","ERP SAP MM","Planification stock","Last mile delivery"],
  artisanat:  ["Menuiserie","Ébénisterie","Peinture décoration","Carrelage","Couverture / zinguerie","Serrurerie","Climatisation / PAC","Plâtrerie","Vitrage"],
  agriculture:["Viticulture","Arboriculture","Maraîchage bio","Mécanique agricole","Certification BIO","Gestion irrigation","Certification GlobalG.A.P."],
};

const CULTURE_Q = [
  {
    q:"Comment préférez-vous avancer sur un projet ?",
    opts:[
      {l:"Autonomie totale — je m'organise seul·e",       v:"auto",    dim:"Autonomie"},
      {l:"Cadre clair, puis liberté d'exécution",         v:"semi",    dim:"Structure"},
      {l:"En équipe rapprochée, décisions collectives",   v:"team",    dim:"Collaboration"},
      {l:"Direction forte, j'exécute et je perfectionne", v:"exec",    dim:"Exécution"},
    ]
  },
  {
    q:"Quel environnement vous fait performer ?",
    opts:[
      {l:"Start-up — vitesse, chaos créatif, impact immédiat", v:"startup", dim:"Agilité"},
      {l:"PME — polyvalence, proximité, décisions rapides",    v:"pme",    dim:"Polyvalence"},
      {l:"Grand groupe — structure, ressources, international", v:"corp",   dim:"Structure"},
      {l:"Institution / public — stabilité, mission de service",v:"public", dim:"Stabilité"},
    ]
  },
  {
    q:"Face à l'erreur, votre réflexe est :",
    opts:[
      {l:"Analyser et documenter pour ne plus recommencer", v:"process", dim:"Rigueur"},
      {l:"Corriger vite et passer à autre chose",          v:"agile",  dim:"Agilité"},
      {l:"En discuter ouvertement en équipe",              v:"open",   dim:"Transparence"},
      {l:"L'assumer seul·e, sans en faire un drame",       v:"stoic",  dim:"Résilience"},
    ]
  },
  {
    q:"Votre relation au télétravail :",
    opts:[
      {l:"100% remote — je suis plus efficace",      v:"remote", dim:"Remote"},
      {l:"Hybride — le meilleur des deux mondes",    v:"hybrid", dim:"Hybride"},
      {l:"Présentiel — le bureau me structure",      v:"office", dim:"Présentiel"},
      {l:"Peu importe si la mission est bonne",      v:"flex",   dim:"Flexibilité"},
    ]
  },
  {
    q:"Ce qui vous retient durablement dans un poste :",
    opts:[
      {l:"La mission et l'impact réel",              v:"mission", dim:"Mission"},
      {l:"L'équipe et les relations humaines",       v:"people",  dim:"Humain"},
      {l:"La progression et les défis techniques",   v:"growth",  dim:"Croissance"},
      {l:"La rémunération et la stabilité",          v:"comp",    dim:"Sécurité"},
    ]
  },
];

const MATCHES = [
  {
    id:"M-7741", score:97, sector:"IT & Digital",   region:"Arc Jurassien", km:14,
    salMin:95, salMax:118, currency:"CHF", contract:"CDI", rate:"100%", notice:"Immédiat",
    trust:4.9, hireRate:94, hires:23, signalements:0, credits:18,
    skills:["React / Next.js","Node.js","PostgreSQL","Docker / K8s"],
    cultures:["Autonomie","Hybride","Mission & Impact","Start-up mindset"],
    certified:true, exclusive:true,
    intel:"Pénurie critique dans votre région. +340% de demandes en 6 mois.",
    intelColor:C.red,
    radarVals:[.93,.85,.80,.70,.88,.91],
    durability:94,
    recommendation:"Un pair travaillant dans le même secteur depuis +3 ans a validé ce profil (anonymement).",
    futureFit:"Profil aligné avec vos objectifs déclarés à 18 mois.",
  },
  {
    id:"M-6283", score:84, sector:"Finance & Audit", region:"Bâle",         km:47,
    salMin:82, salMax:97,  currency:"CHF", contract:"CDI", rate:"80%",  notice:"3 mois",
    trust:4.3, hireRate:78, hires:11, signalements:0, credits:9,
    skills:["IFRS / Swiss GAAP","SAP FI/CO","Analyse financière"],
    cultures:["Structure","Grand groupe","Progression"],
    certified:false, exclusive:false,
    intel:"Secteur finance bâlois : +12% salaires CPA depuis Q3.",
    intelColor:C.green,
    radarVals:[.60,.88,.55,.82,.72,.65],
    durability:79,
    recommendation:null,
    futureFit:null,
  },
  {
    id:"M-5019", score:76, sector:"Industrie",       region:"Bienne",       km:33,
    salMin:68, salMax:80,  currency:"CHF", contract:"CDI", rate:"100%", notice:"2 mois",
    trust:3.8, hireRate:62, hires:7,  signalements:1, credits:4,
    skills:["CNC Fanuc","Fraisage 5 axes","Contrôle qualité ISO"],
    cultures:["Polyvalence","PME","Stabilité"],
    certified:false, exclusive:false,
    intel:null, intelColor:C.mist,
    radarVals:[.75,.60,.90,.55,.68,.70],
    durability:65,
    recommendation:null,
    futureFit:null,
  },
];

// ── PURE COMPONENTS ───────────────────────────────────────────────────────────

function TrustBars({ score }) {
  return (
    <div style={{display:"flex",gap:3}}>
      {[1,2,3,4,5].map(i=>{
        const f = i<=score?1 : i-1<score ? score%1 : 0;
        return (
          <div key={i} style={{width:18,height:3,background:C.edge,position:"relative",overflow:"hidden"}}>
            {f>0 && <div style={{position:"absolute",inset:0,width:`${f*100}%`,background:C.copper}}/>}
          </div>
        );
      })}
    </div>
  );
}

function Arc({score,size=88,stroke=5}){
  const r=(size-stroke*2)/2, circ=2*Math.PI*r;
  const off=circ-(score/100)*circ;
  const col=score>=90?C.green:score>=75?C.copper:C.mist;
  return(
    <svg width={size} height={size} style={{flexShrink:0}}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={C.edge} strokeWidth={stroke}/>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={col} strokeWidth={stroke}
        strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={off}
        transform={`rotate(-90 ${size/2} ${size/2})`}
        style={{transition:"stroke-dashoffset 1.3s cubic-bezier(.4,0,.2,1)"}}/>
      <text x={size/2} y={size/2} textAnchor="middle" dominantBaseline="middle"
        fill={col} fontSize={size/5} fontFamily="Playfair Display" fontWeight="500">{score}</text>
      <text x={size/2} y={size/2+size/5.5+4} textAnchor="middle" dominantBaseline="middle"
        fill={C.fog} fontSize={7} fontFamily="JetBrains Mono">MATCH %</text>
    </svg>
  );
}

function Radar({vals,labels,size=200}){
  const cx=size/2,cy=size/2,r=size*.36,n=labels.length;
  const ang=(i)=>(i/n)*2*Math.PI-Math.PI/2;
  const pt=(v,i)=>[cx+r*v*Math.cos(ang(i)), cy+r*v*Math.sin(ang(i))];
  const poly=(pts)=>pts.map(([x,y])=>`${x},${y}`).join(" ");
  const grid=[.25,.5,.75,1];
  return(
    <svg width={size} height={size}>
      {grid.map(g=>(
        <polygon key={g} points={poly(labels.map((_,i)=>pt(g,i)))}
          fill="none" stroke={C.edge} strokeWidth={.6}/>
      ))}
      {labels.map((_,i)=>(
        <line key={i} x1={cx} y1={cy} x2={pt(1,i)[0]} y2={pt(1,i)[1]}
          stroke={C.edge} strokeWidth={.5}/>
      ))}
      <polygon points={poly(vals.map((v,i)=>pt(v,i)))}
        fill={C.copperG} stroke={C.copper} strokeWidth={1.5}/>
      {vals.map((v,i)=>(
        <circle key={i} cx={pt(v,i)[0]} cy={pt(v,i)[1]} r={3} fill={C.copper}/>
      ))}
      {labels.map((l,i)=>{
        const [lx,ly]=[cx+(r+22)*Math.cos(ang(i)), cy+(r+22)*Math.sin(ang(i))];
        return(
          <text key={i} x={lx} y={ly} textAnchor="middle" dominantBaseline="middle"
            fill={C.mist} fontSize={8} fontFamily="JetBrains Mono">{l}</text>
        );
      })}
    </svg>
  );
}

function IBar({label,val,color=C.copper,suffix="%",delay=0}){
  const [w,setW]=useState(0);
  useEffect(()=>{const t=setTimeout(()=>setW(val),300+delay);return()=>clearTimeout(t);},[val]);
  return(
    <div style={{marginBottom:14}}>
      <div style={{display:"flex",justifyContent:"space-between",marginBottom:7}}>
        <span style={{fontSize:13,color:C.mist}}>{label}</span>
        <span style={{fontFamily:"JetBrains Mono",fontSize:12,color}}>{val}{suffix}</span>
      </div>
      <div className="pb">
        <div className="pf" style={{width:`${w}%`,background:`linear-gradient(90deg,${C.copperD},${color})`}}/>
      </div>
    </div>
  );
}

// ── CANVAS PARTICLE NETWORK ────────────────────────────────────────────────────

function Network(){
  const ref=useRef();
  useEffect(()=>{
    const c=ref.current; if(!c)return;
    const ctx=c.getContext("2d");
    let W,H,nodes,raf;
    const init=()=>{
      W=c.width=c.offsetWidth; H=c.height=c.offsetHeight;
      nodes=Array.from({length:70},()=>({
        x:Math.random()*W, y:Math.random()*H,
        vx:(Math.random()-.5)*.28, vy:(Math.random()-.5)*.28,
        r:Math.random()*1.8+.4,
        type:Math.random()>.65?"co":"ca",
      }));
    };
    const draw=()=>{
      ctx.clearRect(0,0,W,H);
      nodes.forEach((a,i)=>{
        nodes.slice(i+1).forEach(b=>{
          if(a.type===b.type)return;
          const d=Math.hypot(a.x-b.x,a.y-b.y);
          if(d<130){
            ctx.strokeStyle=`rgba(217,123,58,${(1-d/130)*.22})`;
            ctx.lineWidth=.5;
            ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
          }
        });
      });
      nodes.forEach(n=>{
        const col=n.type==="co"?"217,123,58":"56,189,248";
        ctx.beginPath();ctx.arc(n.x,n.y,n.r,0,Math.PI*2);
        ctx.fillStyle=`rgba(${col},.65)`;ctx.fill();
        n.x+=n.vx;n.y+=n.vy;
        if(n.x<0||n.x>W)n.vx*=-1;
        if(n.y<0||n.y>H)n.vy*=-1;
      });
      raf=requestAnimationFrame(draw);
    };
    init(); draw();
    const ro=new ResizeObserver(init);
    ro.observe(c);
    return()=>{cancelAnimationFrame(raf);ro.disconnect();};
  },[]);
  return <canvas ref={ref} style={{position:"absolute",inset:0,width:"100%",height:"100%",opacity:.45}}/>;
}

// ── REVEAL OVERLAY ────────────────────────────────────────────────────────────

function Reveal({onClose}){
  const [phase,setPhase]=useState(0);
  useEffect(()=>{
    const t=[
      setTimeout(()=>setPhase(1),600),
      setTimeout(()=>setPhase(2),1800),
      setTimeout(()=>setPhase(3),3000),
    ];
    return()=>t.forEach(clearTimeout);
  },[]);

  const parts=Array.from({length:40},(_,i)=>{
    const a=(i/40)*2*Math.PI;
    const d=70+Math.random()*100;
    return {
      tx:`${Math.cos(a)*d}px`, ty:`${Math.sin(a)*d}px`,
      size:2+Math.random()*4,
      delay:Math.random()*.6,
      col:i%3===0?C.copper:i%3===1?C.teal:C.copperL,
    };
  });

  return(
    <div className="rev-ov" onClick={phase===3?onClose:undefined}>
      <div className="rev-c">
        {/* Particles phase 1+ */}
        {phase>=1&&(
          <div className="rev-pts">
            {parts.map((p,i)=>(
              <div key={i} style={{
                position:"absolute",left:"50%",top:"50%",
                width:p.size,height:p.size,borderRadius:"50%",
                background:p.col,marginLeft:-p.size/2,marginTop:-p.size/2,
                animation:`particle 1.8s ${p.delay}s ease both`,
                "--tx":p.tx,"--ty":p.ty,
              }}/>
            ))}
          </div>
        )}

        {/* Phase 0 — spinner */}
        {phase===0&&(
          <div style={{animation:"fi .3s ease"}}>
            <svg width={100} height={100}>
              <circle cx={50} cy={50} r={42} fill="none" stroke={C.edge} strokeWidth={1.5}/>
              <circle cx={50} cy={50} r={42} fill="none" stroke={C.copper} strokeWidth={1.5}
                strokeDasharray="25 240" strokeLinecap="round">
                <animateTransform attributeName="transform" type="rotate" from="0 50 50" to="360 50 50" dur=".9s" repeatCount="indefinite"/>
              </circle>
            </svg>
            <div className="jb" style={{fontSize:10,color:C.mist,letterSpacing:".15em",marginTop:16}}>
              VÉRIFICATION MUTUELLE EN COURS
            </div>
          </div>
        )}

        {/* Phase 1 — accord */}
        {phase>=1&&phase<3&&(
          <div style={{animation:"reveal .5s ease"}}>
            <svg width={160} height={160}>
              <circle cx={80} cy={80} r={70} fill="none" stroke={C.copper} strokeWidth={.8}/>
              <circle cx={80} cy={80} r={55} fill="none" stroke={C.copper} strokeWidth={.4} opacity={.4}/>
              <circle cx={80} cy={80} r={35} fill="none" stroke={C.copper} strokeWidth={.2} opacity={.2}/>
              <text x={80} y={74} textAnchor="middle" fill={C.copper} fontSize={36} fontFamily="Playfair Display">✦</text>
              <text x={80} y={104} textAnchor="middle" fill={C.mist} fontSize={9} fontFamily="JetBrains Mono" letterSpacing="3">ACCORD MUTUEL</text>
            </svg>
          </div>
        )}

        {/* Phase 2 — identities */}
        {phase>=2&&(
          <div style={{marginTop:32,animation:"fu .6s ease"}}>
            <h2 className="pf" style={{fontSize:44,marginBottom:8,color:C.ice}}>Le voile se lève.</h2>
            <p style={{color:C.mist,fontSize:15,marginBottom:36}}>Les deux parties ont confirmé leur intérêt. Les identités se dévoilent.</p>
            <div className="g2" style={{gap:20,maxWidth:440,margin:"0 auto 32px"}}>
              {[
                {side:"Candidat",    name:"Jean-Marc R.",  role:"Développeur Full-Stack · 8 ans", icon:"👤"},
                {side:"Entreprise",  name:"TechCorp SA",   role:"Scale-up · Porrentruy",          icon:"🏢"},
              ].map((x,i)=>(
                <div key={i} className="card" style={{padding:20,textAlign:"center",borderColor:"rgba(217,123,58,.45)"}}>
                  <div style={{fontSize:32,marginBottom:8}}>{x.icon}</div>
                  <div className="jb" style={{fontSize:9,color:C.dim,marginBottom:4}}>{x.side}</div>
                  <div style={{fontWeight:500,fontSize:15,marginBottom:4}}>{x.name}</div>
                  <div style={{fontSize:12,color:C.mist,marginBottom:10}}>{x.role}</div>
                  <span className="pill p-gr" style={{fontSize:9}}>✓ RÉVÉLÉ</span>
                </div>
              ))}
            </div>
            <p className="jb" style={{fontSize:10,color:C.dim,letterSpacing:".08em"}}>
              Canal sécurisé activé · Cliquez pour accéder
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
// SCREENS
// ══════════════════════════════════════════════════════════════

function Landing({onStart}){
  return(
    <div style={{position:"relative",minHeight:"93vh",display:"flex",flexDirection:"column",justifyContent:"center",alignItems:"center",textAlign:"center",padding:"64px 24px",overflow:"hidden"}}>
      <Network/>
      <div style={{position:"relative",zIndex:2,maxWidth:760}}>

        {/* Overline */}
        <div className="fu" style={{marginBottom:28}}>
          <span className="pill p-cop">
            <span style={{width:6,height:6,borderRadius:"50%",background:C.copper,display:"inline-block",animation:"pulse 2s infinite"}}/>
            BÊTA PRIVÉE · SUISSE & FRONTALIERS · 2026
          </span>
        </div>

        {/* Hero */}
        <h1 className="fu1 pf" style={{fontSize:"clamp(50px,8vw,100px)",color:C.ice,marginBottom:4}}>
          Le talent se cache.
        </h1>
        <h2 className="fu1 pfi" style={{fontSize:"clamp(46px,7.5vw,94px)",color:C.copper,marginBottom:36}}>
          Nous le trouvons.
        </h2>

        <p className="fu2" style={{fontSize:17,color:C.mist,lineHeight:1.75,marginBottom:16}}>
          La première plateforme de recrutement où l'anonymat est architectural,
          le matching est prédictif, et la confiance est certifiée.
        </p>
        <p className="fu2 jb" style={{fontSize:11,color:C.dim,marginBottom:52,letterSpacing:".06em"}}>
          Pour les talents en poste. Pour les entreprises discrètes. Pour les deux.
        </p>

        {/* CTAs */}
        <div className="fu3" style={{display:"flex",gap:12,justifyContent:"center",flexWrap:"wrap",marginBottom:72}}>
          <button className="btn btn-p" onClick={()=>onStart("candidate")}>
            Je cherche discrètement →
          </button>
          <button className="btn btn-o" onClick={()=>onStart("company")}>
            Je recrute en confidentiel →
          </button>
        </div>

        {/* Stats */}
        <div className="fu4" style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:32,maxWidth:580,margin:"0 auto 64px"}}>
          {[
            {n:"97%",   l:"Score max\natteint"},
            {n:"72h",   l:"Contact\nmédian"},
            {n:"70%",   l:"Postes cachés\nrendus visibles"},
            {n:"0 CHF", l:"Pour les\ncandidats"},
          ].map((s,i)=>(
            <div key={i} style={{textAlign:"center"}}>
              <div className="pf" style={{fontSize:28,color:C.copper}}>{s.n}</div>
              <div className="jb" style={{fontSize:9,color:C.mist,whiteSpace:"pre-line",marginTop:6,letterSpacing:".05em"}}>{s.l}</div>
            </div>
          ))}
        </div>

        {/* 10 game changers strip */}
        <div className="fu5" style={{marginBottom:40}}>
          <div className="jb" style={{fontSize:10,color:C.fog,letterSpacing:".1em",marginBottom:16}}>10 GAME CHANGERS QUI CASSENT LE MARCHÉ</div>
          <div style={{display:"flex",flexWrap:"wrap",gap:8,justifyContent:"center"}}>
            {[
              "🌑 Marché caché rendu visible",
              "🔐 Anonymat par architecture",
              "🧠 Empreinte culturelle IA",
              "⭐ Passeport de confiance",
              "↩️ Entretien inversé",
              "📡 Intelligence de marché temps réel",
              "🤝 Révélation mutuelle cinématique",
              "🔮 Prédictions IA 18 mois",
              "🌑 Mode veille passive",
              "🚪 Off-boarding = prochaine entrée",
            ].map((f,i)=>(
              <span key={i} className="pill p-gh" style={{fontSize:10}}>{f}</span>
            ))}
          </div>
        </div>

        {/* Legend */}
        <div className="fu6" style={{display:"flex",gap:24,justifyContent:"center",alignItems:"center"}}>
          <div style={{display:"flex",gap:8,alignItems:"center"}}>
            <div style={{width:8,height:8,borderRadius:"50%",background:C.copper}}/>
            <span className="jb" style={{fontSize:10,color:C.mist}}>Entreprises</span>
          </div>
          <div style={{width:1,height:16,background:C.edge}}/>
          <div style={{display:"flex",gap:8,alignItems:"center"}}>
            <div style={{width:8,height:8,borderRadius:"50%",background:C.teal}}/>
            <span className="jb" style={{fontSize:10,color:C.mist}}>Candidats</span>
          </div>
          <div style={{width:1,height:16,background:C.edge}}/>
          <div style={{display:"flex",gap:8,alignItems:"center"}}>
            <div style={{width:40,height:1,background:`rgba(217,123,58,.4)`}}/>
            <span className="jb" style={{fontSize:10,color:C.mist}}>Connexion anonyme</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
function Onboarding({type,onNext}){
  const isC=type==="candidate";
  const [mode,setMode]=useState(isC?"shadow":"discreet");
  const [anon,setAnon]=useState(true);
  const [recom,setRecom]=useState(true);

  const cModes=[
    {id:"shadow",icon:"🌑",title:"Mode Veille",sub:"Invisible — mais disponible",
      desc:"Votre profil est masqué. L'algorithme tourne en arrière-plan 24/7. Si un match exceptionnel apparaît — score >85%, +20% de salaire, culture alignée — vous recevez une notification discrète. Zéro effort."},
    {id:"active",icon:"🌕",title:"Mode Actif",sub:"En recherche ouverte",
      desc:"Profil visible dans les résultats de matching. Vous participez activement. Idéal si vous êtes en recherche et pouvez y consacrer du temps."},
  ];
  const eModes=[
    {id:"discreet",icon:"🤫",title:"Confidentiel",sub:"Identité masquée",
      desc:"Votre entreprise reste anonyme jusqu'au dévoilement mutuel. Idéal pour remplacer un poste occupé, anticiper une réorganisation, ou tester le marché sans signal public."},
    {id:"public",icon:"🏢",title:"Transparent",sub:"Marque employeur visible",
      desc:"Votre identité est affichée dès le matching. Profitez du badge Employeur Certifié pour attirer les meilleurs talents passifs qui ne candidatent nulle part ailleurs."},
  ];

  return(
    <div className="wrap" style={{maxWidth:680}}>
      <div className="fu jb" style={{fontSize:10,color:C.dim,letterSpacing:".12em",marginBottom:8}}>ÉTAPE 01 · PRÉSENCE</div>
      <h2 className="fu1 pf" style={{fontSize:44,marginBottom:6}}>
        {isC?"Comment voulez-vous exister ?":"Comment voulez-vous chercher ?"}
      </h2>
      <p className="fu2" style={{color:C.mist,fontSize:15,marginBottom:36,lineHeight:1.65}}>
        {isC?"Votre niveau d'engagement sur le marché. Vous pouvez changer à tout moment.":"Définissez la visibilité de votre recrutement. Réversible à tout moment."}
      </p>

      <div className="fu2 g2" style={{marginBottom:24}}>
        {(isC?cModes:eModes).map(m=>(
          <div key={m.id} className={`cc ${mode===m.id?"sel":""}`} onClick={()=>setMode(m.id)}>
            <div style={{fontSize:30,marginBottom:12}}>{m.icon}</div>
            <div style={{fontWeight:500,fontSize:16,marginBottom:2,color:mode===m.id?C.copper:C.ice}}>{m.title}</div>
            <div className="jb" style={{fontSize:9,color:C.fog,marginBottom:12,letterSpacing:".05em"}}>{m.sub}</div>
            <div style={{fontSize:13,color:C.mist,lineHeight:1.65}}>{m.desc}</div>
          </div>
        ))}
      </div>

      {/* Protection toggles */}
      <div className="fu3 card" style={{padding:20,marginBottom:isC?16:24}}>
        {isC&&(
          <>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:anon?14:0}}>
              <div>
                <div style={{fontWeight:500,marginBottom:3}}>🔐 Protection employeur actuel</div>
                <div style={{fontSize:13,color:C.mist}}>Votre employeur ne peut jamais vous voir dans les résultats</div>
              </div>
              <button className={`tog ${anon?"on":""}`} onClick={()=>setAnon(!anon)}/>
            </div>
            {anon&&(
              <div className="jb" style={{fontSize:10,color:C.copper,letterSpacing:".06em"}}>
                🛡️ AUCUNE CORRÉLATION POSSIBLE AVEC VOTRE EMPLOYEUR ACTUEL
              </div>
            )}
          </>
        )}
      </div>

      {isC&&(
        <div className="fu3 card" style={{padding:20,marginBottom:24}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:recom?14:0}}>
            <div>
              <div style={{fontWeight:500,marginBottom:3}}>🤝 Recommandations anonymes</div>
              <div style={{fontSize:13,color:C.mist}}>
                Un collègue ou ex-collègue peut vous recommander anonymement à une entreprise.
                Sa recommandation booste votre score sans révéler son identité.
              </div>
            </div>
            <button className={`tog ${recom?"on":""}`} onClick={()=>setRecom(!recom)}/>
          </div>
          {recom&&(
            <div className="jb" style={{fontSize:10,color:C.green,letterSpacing:".06em"}}>
              ✓ RECOMMANDATIONS ACTIVES — RÉSEAU VALIDÉ SANS CONNEXIONS PUBLIQUES
            </div>
          )}
        </div>
      )}

      <button className="fu4 btn btn-p" style={{width:"100%"}} onClick={onNext}>Continuer →</button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
function CultureQuiz({onNext}){
  const [answers,setAnswers]=useState({});
  const [cur,setCur]=useState(0);
  const done=Object.keys(answers).length===CULTURE_Q.length;
  const progress=(Object.keys(answers).length/CULTURE_Q.length)*100;

  const pick=(v)=>{
    const next={...answers,[cur]:v};
    setAnswers(next);
    if(cur<CULTURE_Q.length-1) setTimeout(()=>setCur(c=>c+1),280);
  };

  const q=CULTURE_Q[cur];
  const dims=Object.values(answers).map((v,qi)=>{
    const qData=CULTURE_Q[qi];
    const opt=qData?.opts.find(o=>o.v===v);
    return opt?.dim;
  }).filter(Boolean);

  return(
    <div className="wrap" style={{maxWidth:660}}>
      <div className="fu jb" style={{fontSize:10,color:C.dim,letterSpacing:".12em",marginBottom:8}}>ÉTAPE 02 · EMPREINTE CULTURELLE</div>
      <h2 className="fu1 pf" style={{fontSize:42,marginBottom:6}}>5 questions. Un profil unique.</h2>
      <p className="fu2" style={{color:C.mist,fontSize:15,marginBottom:32,lineHeight:1.65}}>
        Votre empreinte culturelle est la dimension que LinkedIn et Indeed ignorent totalement.
        C'est ce qui différencie un bon match d'un match qui dure.
      </p>

      {/* Progress */}
      <div className="fu2" style={{marginBottom:28}}>
        <div style={{display:"flex",justifyContent:"space-between",marginBottom:8}}>
          <span className="jb" style={{fontSize:10,color:C.mist}}>Question {cur+1} / {CULTURE_Q.length}</span>
          <span className="jb" style={{fontSize:10,color:C.copper}}>{Math.round(progress)}% complété</span>
        </div>
        <div className="pb"><div className="pf" style={{width:`${progress}%`}}/></div>
      </div>

      {/* Step dots */}
      <div className="fu2" style={{display:"flex",gap:6,marginBottom:24}}>
        {CULTURE_Q.map((_,i)=>(
          <button key={i} onClick={()=>setCur(i)} style={{
            width:28,height:28,borderRadius:"50%",cursor:"pointer",
            border:`1px solid ${i===cur?C.copper:answers[i]?C.copperD:C.edge}`,
            background:i===cur?C.copper:answers[i]?C.copperG:"transparent",
            color:i===cur?C.void:answers[i]?C.copper:C.dim,
            fontSize:11,fontFamily:"JetBrains Mono",transition:"all .2s",
          }}>{i+1}</button>
        ))}
      </div>

      {/* Question */}
      <div className="fu3 card" style={{padding:28,marginBottom:16,borderColor:"rgba(217,123,58,.2)"}}>
        <div style={{fontSize:17,fontWeight:400,marginBottom:22,lineHeight:1.5}}>{q.q}</div>
        <div style={{display:"flex",flexDirection:"column",gap:10}}>
          {q.opts.map(opt=>(
            <button key={opt.v} className={`qc ${answers[cur]===opt.v?"sel":""}`} onClick={()=>pick(opt.v)}>
              <div className="qc-dot"/>
              {opt.l}
            </button>
          ))}
        </div>
      </div>

      {/* Dimensions so far */}
      {dims.length>0&&(
        <div className="fu" style={{display:"flex",gap:6,flexWrap:"wrap",marginBottom:16}}>
          {dims.map((d,i)=>(
            <span key={i} className="pill p-cop" style={{fontSize:10}}>✦ {d}</span>
          ))}
        </div>
      )}

      {done&&(
        <div className="fu">
          <div className="card" style={{padding:20,marginBottom:16,background:C.copperG,borderColor:"rgba(217,123,58,.4)"}}>
            <div style={{display:"flex",alignItems:"center",gap:12}}>
              <div style={{fontSize:28}}>✦</div>
              <div>
                <div style={{fontWeight:500,color:C.copper,marginBottom:2}}>Empreinte calculée</div>
                <div style={{fontSize:13,color:C.mist}}>
                  Votre profil culturel unique a été généré et sera croisé avec chaque entreprise pour prédire la durabilité de la relation de travail.
                </div>
              </div>
            </div>
          </div>
          <button className="btn btn-p" style={{width:"100%"}} onClick={onNext}>
            Configurer mes compétences →
          </button>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
function Profile({type,onNext}){
  const isC=type==="candidate";
  const [sector,setSector]=useState(null);
  const [skills,setSkills]=useState([]);
  const [radius,setRadius]=useState(50);
  const [notice,setNotice]=useState(null);
  const [transport,setTransport]=useState("voiture");
  const toggle=(s)=>setSkills(p=>p.includes(s)?p.filter(x=>x!==s):[...p,s]);
  const avail=sector?(SKILLS_MAP[sector]||[]):[];
  const ok=sector&&skills.length>=2&&notice;

  return(
    <div className="wrap" style={{maxWidth:760}}>
      <div className="fu jb" style={{fontSize:10,color:C.dim,letterSpacing:".12em",marginBottom:8}}>ÉTAPE 03 · COMPÉTENCES & MOBILITÉ</div>
      <h2 className="fu1 pf" style={{fontSize:42,marginBottom:32}}>
        {isC?"Cartographiez votre expertise.":"Décrivez le profil idéal."}
      </h2>

      {/* Sector */}
      <div className="fu2" style={{marginBottom:32}}>
        <span className="lbl">Secteur principal</span>
        <div className="g3">
          {SECTORS.map(s=>(
            <div key={s.id} className={`sc ${sector===s.id?"sel":""}`}
              onClick={()=>{setSector(s.id);setSkills([]);}}>
              <div style={{fontSize:22,marginBottom:6,color:sector===s.id?C.copper:s.col,fontFamily:"JetBrains Mono"}}>{s.sym}</div>
              <div style={{fontSize:12,color:sector===s.id?C.copper:C.mist}}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Skills */}
      {sector&&(
        <div className="fu" style={{marginBottom:32}}>
          <span className="lbl">Compétences — sélectionnez tout ce qui vous représente (min. 2)</span>
          <div style={{display:"flex",flexWrap:"wrap",gap:8}}>
            {avail.map(sk=>(
              <button key={sk} onClick={()=>toggle(sk)} style={{
                padding:"7px 14px",
                border:`1px solid ${skills.includes(sk)?C.copper:C.edge}`,
                background:skills.includes(sk)?C.copperG:"transparent",
                color:skills.includes(sk)?C.copper:C.mist,
                cursor:"pointer",fontSize:13,fontFamily:"Outfit",fontWeight:300,transition:"all .15s",
              }}>
                {skills.includes(sk)?"✓ ":""}{sk}
              </button>
            ))}
          </div>
          {skills.length>0&&(
            <div className="jb" style={{fontSize:10,color:C.copperD,marginTop:10}}>
              {skills.length} compétence{skills.length>1?"s":""} sélectionnée{skills.length>1?"s":""}
            </div>
          )}
        </div>
      )}

      {/* Location */}
      <div className="fu2 g2" style={{marginBottom:16}}>
        <div>
          <span className="lbl">Code postal (jamais affiché)</span>
          <input className="inp" placeholder="2900"/>
        </div>
        <div>
          <span className="lbl">Rayon de mobilité : <span style={{color:C.copper}}>{radius} km</span></span>
          <input type="range" className="rng" min={5} max={200} value={radius}
            onChange={e=>setRadius(+e.target.value)} style={{marginTop:16}}/>
          <div style={{display:"flex",justifyContent:"space-between",marginTop:4}}>
            <span className="jb" style={{fontSize:9,color:C.dim}}>5km</span>
            <span className="jb" style={{fontSize:9,color:C.dim}}>200km</span>
          </div>
        </div>
      </div>

      {/* Transport */}
      <div className="fu2" style={{marginBottom:24}}>
        <span className="lbl">Mode de transport principal</span>
        <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
          {["🚗 Voiture","🚆 Transports publics","🚲 Vélo","🏠 Remote uniquement"].map((t,i)=>{
            const v=["voiture","tp","velo","remote"][i];
            return(
              <button key={v} onClick={()=>setTransport(v)} style={{
                padding:"8px 16px",
                border:`1px solid ${transport===v?C.copper:C.edge}`,
                background:transport===v?C.copperG:"transparent",
                color:transport===v?C.copper:C.mist,
                cursor:"pointer",fontSize:13,fontFamily:"Outfit",fontWeight:300,transition:"all .15s",
              }}>{t}</button>
            );
          })}
        </div>
        <div style={{fontSize:12,color:C.fog,marginTop:8}}>
          Le mode de transport affine le rayon réel — 50km en voiture ≠ 50km en transports.
        </div>
      </div>

      {/* Salary */}
      <div className="fu3 g2" style={{marginBottom:12}}>
        <div>
          <span className="lbl">Salaire min. souhaité (CHF/an)</span>
          <input className="inp" placeholder="80'000"/>
        </div>
        <div>
          <span className="lbl">Salaire max. (CHF/an)</span>
          <input className="inp" placeholder="100'000"/>
        </div>
      </div>
      <div style={{fontSize:12,color:C.fog,marginBottom:24,padding:"10px 14px",background:C.ghost,borderLeft:`2px solid ${C.edge}`}}>
        💡 Ces fourchettes ne sont jamais affichées telles quelles. Le système compare la compatibilité avec une tolérance de ±10%. Ni vous, ni l'autre partie, ne voyez le chiffre exact de l'autre avant accord mutuel.
      </div>

      {/* Notice */}
      <div className="fu4" style={{marginBottom:40}}>
        <span className="lbl">{isC?"Délai de préavis contractuel":"Urgence du besoin"}</span>
        <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
          {["Immédiat","2 semaines","1 mois","2 mois","3 mois","> 3 mois"].map(n=>(
            <button key={n} onClick={()=>setNotice(n)} style={{
              padding:"9px 18px",
              border:`1px solid ${notice===n?C.copper:C.edge}`,
              background:notice===n?C.copperG:"transparent",
              color:notice===n?C.copper:C.mist,
              cursor:"pointer",fontSize:13,fontFamily:"Outfit",fontWeight:300,transition:"all .15s",
            }}>{n}</button>
          ))}
        </div>
        {notice&&(
          <div style={{fontSize:12,color:C.mist,marginTop:8}}>
            Ce délai est trackable — si vous ne le respectez pas, votre score baisse. C'est votre engagement envers le marché.
          </div>
        )}
      </div>

      <button className="fu5 btn btn-p" style={{width:"100%",opacity:ok?1:.4}}
        onClick={ok?onNext:undefined}>
        {ok?"Lancer le matching IA →":
          `Complétez le profil (${!sector?"secteur, ":""}${skills.length<2?"min 2 compétences, ":""}${!notice?"délai":""})`}
      </button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
function Dashboard({type,onView}){
  const isC=type==="candidate";
  return(
    <div className="wrap-w">
      {/* Header */}
      <div className="fu" style={{display:"flex",justifyContent:"space-between",alignItems:"flex-end",marginBottom:40,flexWrap:"wrap",gap:16}}>
        <div>
          <div className="jb" style={{fontSize:10,color:C.dim,letterSpacing:".12em",marginBottom:8}}>
            TABLEAU DE BORD · MATCHS ACTIFS
          </div>
          <h2 className="pf" style={{fontSize:42,marginBottom:6}}>3 correspondances.</h2>
          <p style={{color:C.mist,fontSize:14,lineHeight:1.5}}>
            Triées par score composite : compétences × empreinte culturelle × géographie × salary fit × durabilité prédite.
          </p>
        </div>
        <div style={{display:"flex",gap:24}}>
          {[
            {n:"3",    l:"Matchs actifs"},
            {n:"97%",  l:"Score max"},
            {n:"14km", l:"Plus proche"},
            {n:"18cr", l:"Crédits restants"},
          ].map((s,i)=>(
            <div key={i} style={{textAlign:"right"}}>
              <div className="pf" style={{fontSize:26,color:C.copper}}>{s.n}</div>
              <div className="jb" style={{fontSize:9,color:C.dim,letterSpacing:".05em"}}>{s.l}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Context banner */}
      <div className="fu1" style={{background:"rgba(56,189,248,.05)",border:`1px solid rgba(56,189,248,.15)`,padding:"14px 20px",marginBottom:24,display:"flex",alignItems:"center",gap:12}}>
        <span style={{fontSize:18}}>📡</span>
        <span style={{fontSize:13,color:C.mist,lineHeight:1.5}}>
          <span style={{color:C.teal,fontWeight:500}}>Intelligence marché :</span> Dans votre secteur (IT · Arc Jurassien), il y a actuellement 23 entreprises qui recrutent pour 6 candidats actifs. <span style={{color:C.ice}}>Vous êtes en position de force.</span>
        </span>
      </div>

      {/* Match cards */}
      <div style={{display:"flex",flexDirection:"column",gap:14}}>
        {MATCHES.map((m,i)=>(
          <div key={m.id} className={`mc fu`} style={{animationDelay:`${i*.1}s`}} onClick={()=>onView(m)}>
            <div className="mc-bar"/>
            <div className="mc-rank">#{i+1} · SCORE {m.score}%</div>

            <div style={{display:"flex",gap:20,alignItems:"flex-start",flexWrap:"wrap",paddingRight:90}}>
              <Arc score={m.score} size={90}/>
              <div style={{flex:1,minWidth:220}}>
                <div style={{display:"flex",gap:8,alignItems:"center",flexWrap:"wrap",marginBottom:8}}>
                  <span style={{fontSize:16,fontWeight:500}}>
                    {isC?m.sector:`Candidat · ${m.sector}`}
                  </span>
                  {m.certified&&<span className="pill p-gld" style={{fontSize:9}}>⭐ CERTIFIÉ · {m.hires} EMBAUCHES</span>}
                  {m.exclusive&&<span className="pill p-tl"  style={{fontSize:9}}>◈ EXCLUSIF UMBRA</span>}
                  {m.recommendation&&<span className="pill p-gr" style={{fontSize:9}}>🤝 RECOMMANDÉ</span>}
                </div>
                <div style={{fontSize:13,color:C.mist,marginBottom:10}}>
                  📍 {m.region} · {m.km} km &nbsp;·&nbsp; {m.contract} · {m.rate} &nbsp;·&nbsp; Dispo : {m.notice}
                </div>
                <div style={{display:"flex",flexWrap:"wrap",gap:6,marginBottom:10}}>
                  {m.skills.map(s=>(
                    <span key={s} className="pill p-gr" style={{fontSize:9}}>✓ {s}</span>
                  ))}
                </div>
                {m.intel&&(
                  <div style={{fontSize:12,color:m.intelColor,display:"flex",alignItems:"center",gap:6}}>
                    <span>📡</span>{m.intel}
                  </div>
                )}
              </div>

              <div style={{textAlign:"right",flexShrink:0}}>
                <div className="pf" style={{fontSize:21,color:C.copper,marginBottom:2}}>
                  {m.salMin}k–{m.salMax}k {m.currency}
                </div>
                <div style={{fontSize:11,color:C.mist,marginBottom:10}}>brut annuel · ±10%</div>
                <TrustBars score={m.trust}/>
                <div className="jb" style={{fontSize:9,color:C.dim,marginTop:4}}>
                  {m.trust}/5 · {m.hireRate}% aboutissent · {m.signalements} signalement{m.signalements!==1?"s":""}
                </div>
                <div style={{marginTop:8}}>
                  <span className="jb" style={{fontSize:9,color:C.copper}}>
                    Durabilité prédite : {m.durability}%
                  </span>
                </div>
              </div>
            </div>

            <div className="div" style={{margin:"16px 0"}}/>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <span className="jb" style={{fontSize:10,color:C.dim}}>
                🔐 {isC?"Identité entreprise masquée":"Identité candidat masquée"} · Protocole révélation mutuelle actif
              </span>
              <div style={{display:"flex",gap:8}}>
                <button className="btn btn-o btn-xs" onClick={e=>e.stopPropagation()}>Ignorer</button>
                <button className="btn btn-p btn-xs" onClick={e=>{e.stopPropagation();onView(m);}}>Ouvrir →</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
function MatchDetail({match,type,onBack,onReveal}){
  const isC=type==="candidate";
  const [interest,setInterest]=useState(false);
  const [q,setQ]=useState("");
  const [qs,setQs]=useState([]);
  const [reply,setReply]=useState(null);
  const radarLabels=["Autonomie","Structure","Culture","Rythme","Remote","Croissance"];

  const fakeReply="Excellente question. Nous privilégions une évolution vers des rôles de Tech Lead dans les 18 mois pour les profils juniors. Nos seniors peuvent viser Head of Engineering. Le parcours est documenté et révisé annuellement.";

  return(
    <div className="wrap" style={{maxWidth:800}}>
      <button className="btn btn-o btn-sm" onClick={onBack} style={{marginBottom:32}}>← Retour aux matchs</button>

      {/* Header */}
      <div className="fu" style={{display:"flex",justifyContent:"space-between",flexWrap:"wrap",gap:20,marginBottom:32}}>
        <div>
          <span className="pill p-cop" style={{marginBottom:16,display:"inline-flex"}}>
            RÉF {match.id} · {match.score}% COMPATIBILITÉ GLOBALE
          </span>
          <h2 className="pf" style={{fontSize:44,marginBottom:8}}>
            {isC?`Opportunité — ${match.sector}`:`Candidat — ${match.sector}`}
          </h2>
          <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
            {match.certified&&<span className="pill p-gld">⭐ EMPLOYEUR CERTIFIÉ · {match.hires} EMBAUCHES</span>}
            {match.exclusive&&<span className="pill p-tl">◈ EXCLUSIF UMBRA</span>}
            {match.recommendation&&<span className="pill p-gr">🤝 RECOMMANDÉ PAR UN PAIR</span>}
          </div>
        </div>
        <Arc score={match.score} size={100}/>
      </div>

      {/* Info grid */}
      <div className="fu1 g4" style={{marginBottom:24}}>
        {[
          {l:"Région",       v:match.region},
          {l:"Distance",     v:`${match.km} km`},
          {l:"Contrat",      v:`${match.contract} · ${match.rate}`},
          {l:"Disponible",   v:match.notice},
        ].map(item=>(
          <div key={item.l} className="card" style={{padding:"14px 16px"}}>
            <div className="lbl" style={{marginBottom:4}}>{item.l}</div>
            <div className="pf" style={{fontSize:18}}>{item.v}</div>
          </div>
        ))}
      </div>

      {/* Salary */}
      <div className="fu2 card" style={{padding:24,marginBottom:20,display:"flex",justifyContent:"space-between",alignItems:"center",flexWrap:"wrap",gap:16}}>
        <div>
          <div className="lbl" style={{marginBottom:6}}>Fourchette salariale · compatibilité confirmée</div>
          <div className="pf" style={{fontSize:36,color:C.copper}}>{match.salMin}k – {match.salMax}k CHF</div>
          <div style={{fontSize:12,color:C.mist,marginTop:4}}>brut annuel · ±10% de tolérance · {match.rate}</div>
        </div>
        <div style={{padding:"12px 20px",background:C.copperG,border:`1px solid rgba(217,123,58,.3)`}}>
          <div className="jb" style={{fontSize:10,color:C.copper,marginBottom:4}}>SALARY FIT</div>
          <div className="pf" style={{fontSize:28,color:C.copper}}>✓</div>
        </div>
      </div>

      {/* Skills */}
      <div className="fu2 card" style={{padding:24,marginBottom:20}}>
        <span className="lbl">Compétences matchées</span>
        <div style={{display:"flex",flexWrap:"wrap",gap:8,marginTop:8}}>
          {match.skills.map(s=><span key={s} className="pill p-gr">{s}</span>)}
        </div>
      </div>

      {/* Culture + Radar */}
      <div className="fu3 g2" style={{marginBottom:20}}>
        <div className="card" style={{padding:24}}>
          <span className="lbl">Empreinte culturelle · radar de compatibilité</span>
          <div style={{display:"flex",justifyContent:"center",padding:"8px 0"}}>
            <Radar vals={match.radarVals} labels={radarLabels} size={210}/>
          </div>
        </div>
        <div className="card" style={{padding:24}}>
          <span className="lbl">Valeurs communes détectées</span>
          <div style={{display:"flex",flexDirection:"column",gap:10,marginTop:8,marginBottom:16}}>
            {match.cultures.map(cu=>(
              <div key={cu} style={{display:"flex",alignItems:"center",gap:8}}>
                <div style={{width:6,height:6,borderRadius:"50%",background:C.copper,flexShrink:0}}/>
                <span style={{fontSize:14,color:C.mist}}>{cu}</span>
              </div>
            ))}
          </div>

          <div className="div" style={{marginBottom:16}}/>
          <span className="lbl" style={{marginBottom:8,display:"block"}}>Durabilité prédite du match</span>
          <div className="pf" style={{fontSize:36,color:C.copper,marginBottom:4}}>{match.durability}%</div>
          <div style={{fontSize:12,color:C.mist}}>
            Probabilité que ce poste soit encore occupé dans 18 mois, basée sur les données historiques de matchs similaires.
          </div>

          {match.futureFit&&(
            <>
              <div className="div" style={{margin:"16px 0"}}/>
              <span className="pill p-sig" style={{fontSize:9,marginBottom:8,display:"inline-flex"}}>🔮 PROJECTION 18 MOIS</span>
              <div style={{fontSize:12,color:C.mist,lineHeight:1.5,marginTop:8}}>{match.futureFit}</div>
            </>
          )}
        </div>
      </div>

      {/* Intel */}
      {match.intel&&(
        <div className="fu4" style={{background:"rgba(56,189,248,.04)",border:`1px solid rgba(56,189,248,.15)`,padding:20,marginBottom:20}}>
          <span className="pill p-tl" style={{marginBottom:10,display:"inline-flex"}}>📡 INTELLIGENCE MARCHÉ TEMPS RÉEL</span>
          <p style={{fontSize:14,color:C.mist,lineHeight:1.6,marginTop:8}}>{match.intel}</p>
        </div>
      )}

      {/* Recommendation */}
      {match.recommendation&&(
        <div className="fu4" style={{background:"rgba(45,212,170,.04)",border:`1px solid rgba(45,212,170,.2)`,padding:20,marginBottom:20}}>
          <span className="pill p-gr" style={{marginBottom:10,display:"inline-flex"}}>🤝 RECOMMANDATION ANONYME VALIDÉE</span>
          <p style={{fontSize:13,color:C.mist,lineHeight:1.6,marginTop:8}}>{match.recommendation}</p>
          <p style={{fontSize:11,color:C.dim,marginTop:6,fontFamily:"JetBrains Mono",letterSpacing:".05em"}}>
            L'identité du recommandant ne sera jamais révélée, sauf si cette personne décide elle-même de se dévoiler.
          </p>
        </div>
      )}

      {/* Trust Passport */}
      <div className="fu5 pass" style={{marginBottom:20}}>
        <div style={{position:"relative",zIndex:1}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",flexWrap:"wrap",gap:16}}>
            <div>
              <div className="jb" style={{fontSize:9,color:C.dim,letterSpacing:".15em",marginBottom:4}}>
                CONFÉDÉRATION SUISSE · UMBRA NETWORK
              </div>
              <div className="pf" style={{fontSize:28,color:C.copper,marginBottom:2}}>Passeport #{match.id}</div>
              <div className="jb" style={{fontSize:9,color:match.certified?C.gold:C.mist}}>
                {match.certified?"GRADE PLATINE — EMPLOYEUR CERTIFIÉ":"GRADE STANDARD"}
              </div>
            </div>
            <Arc score={Math.round(match.trust*20)} size={80} stroke={4}/>
          </div>
          <div className="div" style={{margin:"20px 0"}}/>
          <div className="g4">
            {[
              {l:"Trust Score",   v:`${match.trust}/5`},
              {l:"Taux embauche", v:`${match.hireRate}%`},
              {l:"Embauches",     v:match.hires},
              {l:"Signalements",  v:match.signalements},
            ].map(item=>(
              <div key={item.l}>
                <div className="jb" style={{fontSize:9,color:C.dim,marginBottom:4}}>{item.l}</div>
                <div className="pf" style={{fontSize:24,color:item.l==="Signalements"&&item.v>0?C.red:C.copper}}>{item.v}</div>
              </div>
            ))}
          </div>
          <div className="pass-mrz">
            P&lt;CHE UMBRA&lt;NETWORK&lt;&lt;{match.certified?"CERTIFIE&lt;PLATINE":"STANDARD&lt;&lt;&lt;&lt;&lt;"}&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;<br/>
            {match.id.replace("-","")}SCH900101{Math.floor(match.trust*10)}M2601010&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;{String(match.hireRate).padStart(2,"0")}
          </div>
        </div>
      </div>

      {/* Reverse interview */}
      {isC&&(
        <div className="fu6 card" style={{padding:24,marginBottom:20,borderColor:"rgba(217,123,58,.3)",background:C.copperG}}>
          <span className="lbl" style={{marginBottom:8,display:"block"}}>↩️ L'ENTRETIEN INVERSÉ — VOTRE DROIT</span>
          <p style={{fontSize:13,color:C.mist,marginBottom:16,lineHeight:1.65}}>
            Avant de vous révéler, interrogez cette entreprise en restant anonyme. Jusqu'à 3 questions.
            Ils répondent. Ensuite vous décidez. C'est vous qui choisissez, pas eux.
          </p>
          <div style={{display:"flex",gap:8,marginBottom:12}}>
            <input className="inp" placeholder="Ex: Quelles sont les perspectives d'évolution à 18 mois ?"
              value={q} onChange={e=>setQ(e.target.value)} style={{flex:1}}
              onKeyDown={e=>{if(e.key==="Enter"&&q.trim()&&qs.length<3){setQs([...qs,q]);setQ("");setTimeout(()=>setReply(fakeReply),800);}}}
            />
            <button className="btn btn-o btn-sm" onClick={()=>{
              if(q.trim()&&qs.length<3){setQs([...qs,q]);setQ("");setTimeout(()=>setReply(fakeReply),800);}
            }}>Envoyer</button>
          </div>
          {qs.map((qi,i)=>(
            <div key={i} style={{marginBottom:8}}>
              <div className="jb" style={{fontSize:10,color:C.fog,marginBottom:4}}>Q{i+1} (anonyme) :</div>
              <div style={{fontSize:13,color:C.ice,marginBottom:6,paddingLeft:12,borderLeft:`2px solid ${C.edge}`}}>{qi}</div>
              {reply&&i===qs.length-1&&(
                <div style={{fontSize:13,color:C.mist,paddingLeft:12,borderLeft:`2px solid ${C.copper}`,marginTop:8,animation:"slideR .4s ease",lineHeight:1.6}}>
                  <span className="jb" style={{fontSize:9,color:C.copper,display:"block",marginBottom:4}}>RÉPONSE DE L'ENTREPRISE :</span>
                  {reply}
                </div>
              )}
            </div>
          ))}
          <div className="jb" style={{fontSize:9,color:C.dim}}>{qs.length}/3 questions utilisées</div>
        </div>
      )}

      {/* Protocol */}
      <div className="fu7" style={{background:"rgba(45,212,170,.04)",border:`1px solid rgba(45,212,170,.18)`,padding:20,marginBottom:24}}>
        <div style={{fontWeight:500,marginBottom:8,color:C.green}}>🔐 Protocole de Révélation Mutuelle</div>
        <p style={{fontSize:13,color:C.mist,lineHeight:1.65}}>
          En confirmant votre intérêt, l'autre partie reçoit une notification anonyme.
          <strong style={{color:C.ice}}> Seulement si les deux confirment simultanément </strong>
          — et uniquement à ce moment — les identités se dévoilent dans un protocole chiffré et auditable.
          Personne ne peut voir l'identité de l'autre unilatéralement. Jamais.
        </p>
      </div>

      {/* CTA */}
      {!interest?(
        <div style={{display:"flex",gap:12}}>
          <button className="btn btn-o" style={{flex:1}} onClick={onBack}>Pas maintenant</button>
          <button className="btn btn-p" style={{flex:2,animation:"copGlow 3s infinite"}} onClick={()=>setInterest(true)}>
            ✦ Je suis intéressé·e — lancer le protocole
          </button>
        </div>
      ):(
        <div style={{textAlign:"center",padding:"48px 0"}}>
          <div style={{fontSize:52,marginBottom:16}}>⏳</div>
          <h3 className="pf" style={{fontSize:30,marginBottom:8}}>Signal envoyé.</h3>
          <p style={{color:C.mist,fontSize:14,marginBottom:28,lineHeight:1.65,maxWidth:440,margin:"0 auto 28px"}}>
            L'autre partie a été notifiée sans révélation d'identité.<br/>
            Dès qu'elle confirme à son tour, la révélation s'active.
          </p>
          <div className="card" style={{display:"inline-flex",gap:12,alignItems:"center",padding:"14px 24px",marginBottom:24}}>
            <div style={{width:10,height:10,borderRadius:"50%",background:C.copper,animation:"pulse 1.5s infinite"}}/>
            <span style={{fontSize:13,color:C.mist}}>En attente de confirmation · délai estimé 48h</span>
          </div>
          <br/>
          <button className="btn btn-p" onClick={onReveal}>⚡ Simuler la révélation mutuelle</button>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
function TrustScreen(){
  const [open,setOpen]=useState(false);
  useEffect(()=>{setTimeout(()=>setOpen(true),300);},[]);

  const steps=[
    {icon:"📤",label:"Contact initié",   val:12,col:C.copper,    pts:"+2 pts/contact"},
    {icon:"📞",label:"Entretien réalisé",val:11,col:C.copper,    pts:"+5 pts/entretien"},
    {icon:"📄",label:"Offre émise",      val:9, col:C.copperL,   pts:"+8 pts/offre"},
    {icon:"🤝",label:"Embauche confirmée",val:9,col:C.green,     pts:"+15 pts/embauche"},
  ];

  return(
    <div className="wrap" style={{maxWidth:860}}>
      <div className="fu jb" style={{fontSize:10,color:C.dim,letterSpacing:".12em",marginBottom:8}}>SYSTÈME DE CONFIANCE</div>
      <h2 className="fu1 pf" style={{fontSize:44,marginBottom:8}}>Le Passeport de Confiance.</h2>
      <p className="fu2" style={{color:C.mist,fontSize:15,marginBottom:48,lineHeight:1.65}}>
        L'anonymat sans responsabilité est une passoire. Le passeport est sa garantie.
        Chaque acteur est évalué sur ses actes, pas ses déclarations.
      </p>

      {/* Passport visual */}
      <div className="fu2 pass" style={{marginBottom:40}}>
        <div style={{position:"relative",zIndex:1}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",flexWrap:"wrap",gap:20}}>
            <div>
              <div className="jb" style={{fontSize:9,color:C.dim,letterSpacing:".15em",marginBottom:4}}>CONFÉDÉRATION SUISSE · UMBRA NETWORK · 2026</div>
              <div className="pf" style={{fontSize:36,color:C.copper,marginBottom:4}}>Passeport N° 7741</div>
              <span className="pill p-gld">⭐ GRADE PLATINE — EMPLOYEUR CERTIFIÉ</span>
            </div>
            <Arc score={89} size={100} stroke={5}/>
          </div>
          <div className="div" style={{margin:"24px 0"}}/>
          <div className="g4" style={{marginBottom:20}}>
            {[
              {l:"Contacts initiés",v:"12"},
              {l:"Embauches",v:"11"},
              {l:"Taux conversion",v:"92%"},
              {l:"Signalements",v:"0"},
            ].map(item=>(
              <div key={item.l}>
                <div className="jb" style={{fontSize:9,color:C.dim,marginBottom:4}}>{item.l}</div>
                <div className="pf" style={{fontSize:28,color:C.copper}}>{item.v}</div>
              </div>
            ))}
          </div>

          {/* Process funnel */}
          <div className="div" style={{marginBottom:20}}/>
          <span className="lbl" style={{marginBottom:16,display:"block"}}>Funnel de conversion · {steps[0].val} → {steps[3].val}</span>
          {steps.map((s,i)=>(
            <div key={i} className="ts-row">
              <div className="ts-icon" style={{background:`${s.col}18`,border:`1px solid ${s.col}40`}}>
                <span>{s.icon}</span>
              </div>
              <div style={{flex:1}}>
                <div style={{display:"flex",justifyContent:"space-between",marginBottom:6}}>
                  <span style={{fontSize:13}}>{s.label}</span>
                  <div style={{display:"flex",gap:8,alignItems:"center"}}>
                    <span className="jb" style={{fontSize:11,color:s.col}}>{s.val}/12</span>
                    <span className="pill p-cop" style={{fontSize:9}}>{s.pts}</span>
                  </div>
                </div>
                <div className="pb">
                  <div className="pf" style={{width:open?`${(s.val/12)*100}%`:0,background:`linear-gradient(90deg,${C.copperD},${s.col})`}}/>
                </div>
              </div>
            </div>
          ))}

          <div className="pass-mrz">
            P&lt;CHE UMBRA&lt;NETWORK&lt;&lt;EMPLOYEUR&lt;CERTIFIE&lt;PLATINE&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;<br/>
            7741000SCH9001010M2601010&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;92
          </div>
        </div>
      </div>

      {/* Mechanics */}
      <div className="fu3 g2" style={{marginBottom:40}}>
        {[
          {icon:"🚫",col:C.red,   title:"Accès restreint < 3/5",    body:"Plus d'initiation de contacts. Réception uniquement. Sous 2/5 : suspension et tous les profils vus deviennent définitivement inaccessibles."},
          {icon:"⭐",col:C.gold,  title:"Badge certifié > 4/5",     body:"Visible sur votre profil. Accès prioritaire aux talents en mode veille passive. Les meilleurs profils qui ne postulent nulle part ailleurs vous contactent."},
          {icon:"💳",col:C.copper,title:"Système de crédits contacts",body:"Chaque contact coûte des crédits. Un contact suivi d'une embauche les rembourse en partie. Un concurrent curieux vide son crédit en quelques semaines."},
          {icon:"🤝",col:C.green, title:"Double confirmation obligatoire",body:"Une embauche n'est validée QUE si les deux parties confirment indépendamment et sans communication préalable. Zéro manipulation possible."},
          {icon:"👁️",col:C.signal,title:"Anti-espionnage automatique",body:"10 contacts sans embauche → suspension + tous les profils vus sont définitivement masqués pour ce compte. Un concurrent espion est rapidement neutralisé."},
          {icon:"📊",col:C.teal,  title:"Taux d'embauche public",   body:"Votre taux d'embauche après contact est visible par tous les candidats. Votre réputation est votre actif le plus précieux sur UMBRA. Elle ne ment pas."},
          {icon:"⏱️",col:C.copper,title:"Chronomètre de décision",  body:"L'entreprise déclare son délai cible (ex: 3 semaines). Si elle dépasse sans motif, son score baisse. Le candidat est libéré de toute exclusivité implicite."},
          {icon:"🚪",col:C.green, title:"Off-boarding = entrée suivante",body:"Départ d'un employé ? Le système propose un off-boarding structuré. Les recommandations sont déposées. Son profil se réactive automatiquement à la date de fin."},
        ].map((item,i)=>(
          <div key={i} className="card card-h" style={{padding:20,borderLeft:`3px solid ${item.col}`}}>
            <div style={{fontSize:24,marginBottom:10}}>{item.icon}</div>
            <div style={{fontWeight:500,marginBottom:6,color:item.col}}>{item.title}</div>
            <div style={{fontSize:13,color:C.mist,lineHeight:1.55}}>{item.body}</div>
          </div>
        ))}
      </div>

      {/* Anti-concurrent callout */}
      <div className="fu4" style={{background:"rgba(217,123,58,.06)",border:`1px solid rgba(217,123,58,.25)`,padding:28}}>
        <div className="jb" style={{fontSize:10,color:C.copper,letterSpacing:".08em",marginBottom:12}}>
          ⚠️ PROTECTION ANTI-CONCURRENT — COMMENT ÇA FONCTIONNE
        </div>
        <p style={{fontSize:15,color:C.mist,lineHeight:1.75}}>
          Un concurrent peut créer un compte sur UMBRA pour espionner qui cherche un emploi dans son secteur.
          Il peut entrer — mais il <span style={{color:C.ice}}>ne peut pas y rester longtemps</span>.
          Sans embauches, son score chute progressivement. Ses crédits s'épuisent.
          Au bout de 10 contacts sans suite, son compte est <span style={{color:C.red}}>automatiquement suspendu</span>
          et l'ensemble des profils qu'il a consultés lui devient
          <span style={{color:C.ice}}> définitivement inaccessible</span>.
          Le coût de l'espionnage est trop élevé pour être rentable.
          C'est sa propre curiosité qui le détruit.
        </p>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
function IntelScreen(){
  const [shown,setShown]=useState(false);
  useEffect(()=>{setTimeout(()=>setShown(true),300);},[]);

  const salData=[
    {role:"Dev Full-Stack",     med:108,min:88, max:135,demand:94},
    {role:"DevOps / Cloud Eng.",med:118,min:92, max:148,demand:99},
    {role:"Data Scientist / ML",med:113,min:90, max:142,demand:91},
    {role:"Cybersécurité",      med:122,min:98, max:155,demand:96},
    {role:"Product Manager",    med:102,min:82, max:128,demand:78},
    {role:"UX/UI Designer",     med:88, min:70, max:112,demand:65},
    {role:"CTO / Head Eng.",    med:145,min:118,max:180,demand:87},
    {role:"QA / Test Engineer", med:82, min:65, max:104,demand:55},
  ];

  return(
    <div className="wrap" style={{maxWidth:900}}>
      <div className="fu jb" style={{fontSize:10,color:C.dim,letterSpacing:".12em",marginBottom:8}}>
        INTELLIGENCE DE MARCHÉ · FÉVRIER 2026 · ARC JURASSIEN & SUISSE
      </div>
      <h2 className="fu1 pf" style={{fontSize:44,marginBottom:8}}>Le marché. En temps réel.</h2>
      <p className="fu2" style={{color:C.mist,fontSize:15,marginBottom:48,lineHeight:1.65}}>
        Données agrégées et anonymisées de l'ensemble du réseau UMBRA.
        Actualisées toutes les 72h. Votre arme de négociation — ou d'anticipation.
      </p>

      {/* KPIs */}
      <div className="fu2 g4" style={{marginBottom:32}}>
        {[
          {n:"+4.8%",l:"Salaires IT\nArc Jurassien · 6 mois",     c:C.green},
          {n:"23",   l:"Entreprises tech\nrecrutent actuellement",  c:C.copper},
          {n:"8j",   l:"Délai médian\nde réponse entreprise",       c:C.teal},
          {n:"340%", l:"Pénurie DevOps\nvs il y a 6 mois",         c:C.red},
        ].map((s,i)=>(
          <div key={i} className="card" style={{padding:20,textAlign:"center"}}>
            <div className="pf" style={{fontSize:30,color:s.c,marginBottom:6}}>{s.n}</div>
            <div className="jb" style={{fontSize:9,color:C.mist,whiteSpace:"pre-line",letterSpacing:".04em"}}>{s.l}</div>
          </div>
        ))}
      </div>

      {/* Off-boarding insight */}
      <div className="fu2" style={{background:"rgba(45,212,170,.05)",border:`1px solid rgba(45,212,170,.2)`,padding:20,marginBottom:32}}>
        <div style={{display:"flex",gap:12,alignItems:"flex-start"}}>
          <span style={{fontSize:24}}>🚪</span>
          <div>
            <div style={{fontWeight:500,color:C.green,marginBottom:6}}>Le marché caché — rendu visible pour la première fois</div>
            <p style={{fontSize:13,color:C.mist,lineHeight:1.65}}>
              70% des postes ne sont jamais publiés. Ils se pourvoient par réseau.
              UMBRA le rend accessible à tous : une entreprise peut poser une intention future à 6 mois.
              Un candidat en poste peut signaler qu'il serait "ouvert à la bonne offre".
              L'algorithme les connecte maintenant, pour une transition douce.
              Ce mois : <span style={{color:C.ice}}>187 intentions futures actives</span> sur le réseau.
            </p>
          </div>
        </div>
      </div>

      {/* Salary bands */}
      <div className="fu3 card" style={{padding:28,marginBottom:28}}>
        <span className="lbl" style={{marginBottom:20,display:"block"}}>
          FOURCHETTES SALARIALES — IT · ARC JURASSIEN & BÂLE (CHF/AN BRUT)
        </span>
        {salData.map((row,i)=>(
          <div key={i} style={{marginBottom:22}}>
            <div style={{display:"flex",justifyContent:"space-between",marginBottom:6,flexWrap:"wrap",gap:6}}>
              <span style={{fontSize:14}}>{row.role}</span>
              <div style={{display:"flex",gap:10,alignItems:"center"}}>
                <span className="jb" style={{fontSize:11,color:C.copper}}>Médiane {row.med}k CHF</span>
                <span className="pill" style={{
                  fontSize:9,
                  borderColor:row.demand>90?"rgba(224,85,85,.4)":row.demand>75?"rgba(217,123,58,.4)":"rgba(45,212,170,.3)",
                  color:row.demand>90?C.red:row.demand>75?C.copper:C.green,
                  background:row.demand>90?"rgba(224,85,85,.08)":row.demand>75?C.copperG:"rgba(45,212,170,.06)",
                }}>
                  {row.demand>90?"🔥 PÉNURIE":row.demand>75?"⚡ TENSION":"✓ ÉQUILIBRÉ"} {row.demand}%
                </span>
              </div>
            </div>
            <div style={{position:"relative",height:8,background:C.ghost,borderRadius:4,overflow:"hidden"}}>
              {shown&&(
                <>
                  <div style={{
                    position:"absolute",
                    left:`${((row.min-60)/140)*100}%`,
                    width:`${((row.max-row.min)/140)*100}%`,
                    height:"100%",
                    background:`linear-gradient(90deg,rgba(217,123,58,.2),rgba(217,123,58,.1))`,
                    border:`1px solid rgba(217,123,58,.35)`,
                    transition:"all 1.2s ease",
                  }}/>
                  <div style={{
                    position:"absolute",
                    left:`${((row.med-60)/140)*100}%`,
                    width:2,height:"100%",
                    background:C.copper,
                    transition:"left 1.2s ease",
                  }}/>
                </>
              )}
            </div>
            <div style={{display:"flex",justifyContent:"space-between",marginTop:3}}>
              <span className="jb" style={{fontSize:9,color:C.dim}}>{row.min}k</span>
              <span className="jb" style={{fontSize:9,color:C.dim}}>{row.max}k</span>
            </div>
          </div>
        ))}
      </div>

      {/* Predictions */}
      <div className="fu4 card" style={{padding:28,marginBottom:28,background:"rgba(155,135,240,.05)",borderColor:"rgba(155,135,240,.2)"}}>
        <span className="pill p-sig" style={{marginBottom:20,display:"inline-flex"}}>🔮 PRÉDICTIONS IA · HORIZON 18 MOIS</span>
        <div className="g2">
          {[
            {role:"DevOps / Cloud Eng.", trend:"+28%", col:C.green,  reason:"Adoption cloud massive. 3× plus de postes que de candidats disponibles. Négociez."},
            {role:"Data Engineer / ML",  trend:"+21%", col:C.green,  reason:"L'IA générative crée une explosion des besoins en pipeline data et MLOps."},
            {role:"Cybersécurité",       trend:"+33%", col:C.red,    reason:"PÉNURIE CRITIQUE. Régulations NIS2. Les entreprises s'arrachent les profils."},
            {role:"Java Senior (legacy)",trend:"-12%", col:C.red,    reason:"Remplacement par stacks cloud-native. Les offres vont se raréfier."},
            {role:"Product Manager",     trend:"+14%", col:C.teal,   reason:"Complexité produit croissante dans tous secteurs. Profil en tension."},
            {role:"SEO / Growth",        trend:"-8%",  col:C.signal, reason:"IA générative réduit les besoins humains sur la production de contenu."},
          ].map((p,i)=>(
            <div key={i} style={{padding:16,background:C.ghost,border:`1px solid ${C.edge}`}}>
              <div style={{display:"flex",justifyContent:"space-between",marginBottom:6}}>
                <span style={{fontSize:14,fontWeight:500}}>{p.role}</span>
                <span className="jb" style={{fontSize:13,color:p.col,fontWeight:500}}>{p.trend}</span>
              </div>
              <div style={{fontSize:12,color:C.mist,lineHeight:1.5}}>{p.reason}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Off-boarding module teaser */}
      <div className="fu5 card card-h" style={{padding:28,background:"rgba(217,123,58,.05)",borderColor:"rgba(217,123,58,.2)"}}>
        <div style={{display:"flex",gap:16,alignItems:"flex-start",flexWrap:"wrap"}}>
          <div style={{fontSize:40}}>🚪</div>
          <div>
            <div style={{fontWeight:500,fontSize:16,marginBottom:6,color:C.copper}}>Off-boarding — La fonctionnalité que personne ne fait</div>
            <p style={{fontSize:13,color:C.mist,lineHeight:1.65,marginBottom:12}}>
              Quand un employé quitte votre entreprise — quelle qu'en soit la raison — UMBRA propose un processus de transition structuré.
              Délai de préavis géré dans la plateforme. Recommandations mutuelles déposées de façon anonyme.
              Profil du candidat réactivé automatiquement en mode veille à la date de fin de contrat.
            </p>
            <p style={{fontSize:13,color:C.mist,lineHeight:1.65}}>
              Résultat : l'employé qui part bien reste dans l'écosystème.
              L'entreprise qui gère bien ses départs <span style={{color:C.ice}}>attire de meilleurs profils</span> — parce que la réputation se voit dans le score.
              Chaque départ bien géré devient <span style={{color:C.copper}}>une future porte d'entrée</span>.
            </p>
            <div style={{marginTop:16,display:"flex",gap:8,flexWrap:"wrap"}}>
              <span className="pill p-cop">✓ Préavis trackable</span>
              <span className="pill p-gr">✓ Recommandations anonymes</span>
              <span className="pill p-tl">✓ Réactivation automatique</span>
              <span className="pill p-sig">✓ Score employeur préservé</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
// PRICING CALCULATOR — Écran 0 (avant onboarding)
// ══════════════════════════════════════════════════════════════

function PricingCalculator({type, onNext}){
  const isC = type==="candidate";
  const [salary, setSalary] = useState(isC ? 6500 : 8000);
  const [hovered, setHovered] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(()=>{ const t=setTimeout(()=>setReady(true),200); return()=>clearTimeout(t); },[]);

  // Barème progressif (% du salaire mensuel brut)
  function calcRate(sal){
    if(sal<=4500)  return 6.5;
    if(sal<=7000)  return 7.5;
    if(sal<=10000) return 8.5;
    if(sal<=15000) return 9.5;
    return 11.0;
  }
  function calcPrice(sal){ return Math.round(sal*(calcRate(sal)/100)); }

  const price   = calcPrice(salary);
  const rate    = calcRate(salary);
  const annuel  = salary*12;
  const roiX    = (annuel/price).toFixed(0);

  // Comparatifs
  const linkedin = 1188; // LinkedIn Recruiter Lite/an
  const chassMin = Math.round(annuel*0.18);
  const chassMax = Math.round(annuel*0.25);

  // Tranche active
  const TIERS = [
    {min:3000, max:4500,  rate:6.5,  label:"Entrée"},
    {min:4500, max:7000,  rate:7.5,  label:"Standard"},
    {min:7000, max:10000, rate:8.5,  label:"Senior"},
    {min:10000,max:15000, rate:9.5,  label:"Direction"},
    {min:15000,max:25000, rate:11.0, label:"C-Level"},
  ];
  const activeTier = TIERS.find(t=>salary>=t.min&&salary<t.max) || TIERS[TIERS.length-1];

  // Slider gradient fill
  const pct = ((salary-3000)/(25000-3000))*100;

  return(
    <div className="wrap" style={{maxWidth:720}}>

      {/* Header */}
      <div className="fu jb" style={{fontSize:10,color:C.dim,letterSpacing:".12em",marginBottom:8}}>
        {isC?"POSTULANT · TARIFICATION":"ENTREPRISE · TARIFICATION"}
      </div>
      <h2 className="fu1 pf" style={{fontSize:46,lineHeight:1.1,marginBottom:10}}>
        Votre investissement<br/>
        <span className="pfi" style={{color:C.copper}}>calculé à la valeur réelle.</span>
      </h2>
      <p className="fu2" style={{color:C.mist,fontSize:15,lineHeight:1.7,marginBottom:40,maxWidth:560}}>
        {isC
          ? "Chez UMBRA, le prix de votre annonce est proportionnel à votre prétention salariale — pas une formule d'abonnement. Vous payez selon ce que le marché vaut pour vous. Transparent. Équitable. Calculé maintenant."
          : "Le coût de votre annonce est indexé sur le salaire du poste à pourvoir — plus la valeur est haute, plus le tarif s'ajuste. Pas de crédits. Pas d'abonnement opaque. Une annonce, un prix, une logique."
        }
      </p>

      {/* CALCULATOR CARD */}
      <div className="fu2 card" style={{padding:40,marginBottom:16,border:`1px solid ${C.rim}`,position:"relative",overflow:"hidden"}}>

        {/* Ambient glow */}
        <div style={{position:"absolute",top:-80,right:-80,width:300,height:300,borderRadius:"50%",
          background:"radial-gradient(circle,rgba(217,123,58,.08) 0%,transparent 70%)",pointerEvents:"none"}}/>

        {/* Salary label */}
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline",marginBottom:6}}>
          <div className="jb" style={{fontSize:10,color:C.fog,letterSpacing:".1em"}}>
            {isC?"PRÉTENTION SALARIALE MENSUELLE (CHF)":"SALAIRE MENSUEL DU POSTE (CHF)"}
          </div>
          <div className="jb" style={{fontSize:10,color:C.copper,letterSpacing:".06em"}}>
            TRANCHE {activeTier.label.toUpperCase()} · {rate}%
          </div>
        </div>

        {/* Salary value display */}
        <div style={{display:"flex",alignItems:"baseline",gap:12,marginBottom:28}}>
          <div className="pf" style={{fontSize:56,fontWeight:500,color:C.ice,lineHeight:1,letterSpacing:"-.02em"}}>
            {salary.toLocaleString("fr-CH")}
          </div>
          <div className="jb" style={{fontSize:14,color:C.fog}}>CHF / mois</div>
          <div style={{marginLeft:"auto",textAlign:"right"}}>
            <div className="jb" style={{fontSize:10,color:C.fog,letterSpacing:".06em",marginBottom:2}}>= ANNUEL</div>
            <div className="jb" style={{fontSize:14,color:C.mist}}>{annuel.toLocaleString("fr-CH")} CHF</div>
          </div>
        </div>

        {/* Slider */}
        <div style={{position:"relative",marginBottom:32}}>
          <style>{`
            .umbra-slider{
              -webkit-appearance:none;appearance:none;
              width:100%;height:3px;outline:none;border:none;
              background:linear-gradient(90deg,${C.copper} ${pct}%,${C.edge} ${pct}%);
              cursor:pointer;
            }
            .umbra-slider::-webkit-slider-thumb{
              -webkit-appearance:none;appearance:none;
              width:22px;height:22px;border-radius:50%;
              background:${C.copper};cursor:pointer;
              box-shadow:0 0 0 4px rgba(217,123,58,.18),0 0 20px rgba(217,123,58,.3);
              transition:box-shadow .2s;
            }
            .umbra-slider::-webkit-slider-thumb:hover{
              box-shadow:0 0 0 6px rgba(217,123,58,.25),0 0 32px rgba(217,123,58,.4);
            }
            .umbra-slider::-moz-range-thumb{
              width:22px;height:22px;border-radius:50%;border:none;
              background:${C.copper};cursor:pointer;
            }
          `}</style>
          <input type="range" className="umbra-slider"
            min={3000} max={25000} step={100}
            value={salary}
            onChange={e=>setSalary(Number(e.target.value))}
          />
          {/* Tier markers */}
          <div style={{display:"flex",justifyContent:"space-between",marginTop:8}}>
            {[3000,4500,7000,10000,15000,25000].map(v=>{
              const p=((v-3000)/(25000-3000))*100;
              const active=salary>=v;
              return(
                <div key={v} style={{textAlign:"center",position:"relative"}}>
                  <div className="jb" style={{fontSize:8,color:active?C.copper:C.fog,letterSpacing:".04em"}}>
                    {v>=1000?`${v/1000}k`:"3k"}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* RESULT */}
        <div style={{
          background:C.ghost,border:`1px solid ${C.edge}`,
          padding:"28px 32px",
          display:"flex",alignItems:"center",gap:40,flexWrap:"wrap",
        }}>
          {/* Price */}
          <div style={{flex:"1 1 200px"}}>
            <div className="jb" style={{fontSize:9,color:C.fog,letterSpacing:".12em",marginBottom:8}}>
              PRIX DE VOTRE ANNONCE
            </div>
            <div style={{display:"flex",alignItems:"baseline",gap:10}}>
              <div className="pf" style={{fontSize:64,fontWeight:600,color:C.copper,lineHeight:1,
                textShadow:"0 0 40px rgba(217,123,58,.35)",transition:"all .2s"}}>
                {price.toLocaleString("fr-CH")}
              </div>
              <div className="jb" style={{fontSize:14,color:C.fog}}>CHF</div>
            </div>
            <div className="jb" style={{fontSize:10,color:C.fog,marginTop:6,letterSpacing:".05em"}}>
              VALABLE 90 JOURS · {rate}% DE {salary.toLocaleString("fr-CH")} CHF
            </div>
          </div>

          {/* Divider */}
          <div style={{width:1,height:80,background:C.edge,flexShrink:0}}/>

          {/* ROI */}
          <div style={{flex:"1 1 180px"}}>
            <div className="jb" style={{fontSize:9,color:C.fog,letterSpacing:".12em",marginBottom:12}}>
              RETOUR SUR INVESTISSEMENT
            </div>
            <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:6}}>
              <div className="pf" style={{fontSize:28,color:C.green}}>×{roiX}</div>
              <div style={{fontSize:12,color:C.mist,lineHeight:1.4}}>
                votre annonce représente<br/>
                <strong style={{color:C.ice}}>1/{roiX} de votre salaire annuel</strong>
              </div>
            </div>
            <span className="pill p-gr" style={{fontSize:9}}>✓ ROI IMMÉDIAT SI 1 MOIS GAGNÉ</span>
          </div>
        </div>

        {/* Validity details */}
        <div style={{display:"flex",gap:8,marginTop:12,flexWrap:"wrap"}}>
          <span className="pill p-cop">◉ 90 jours de visibilité</span>
          <span className="pill p-tl">↻ Prolongé si aucun match</span>
          <span className="pill p-gr">✓ Remboursé si annonce impossible</span>
        </div>
      </div>

      {/* COMPARATIF */}
      <div className="fu3 card" style={{padding:0,marginBottom:24,overflow:"hidden"}}>
        <div style={{
          padding:"14px 24px",
          borderBottom:`1px solid ${C.edge}`,
          display:"flex",alignItems:"center",gap:10
        }}>
          <div className="jb" style={{fontSize:9,color:C.fog,letterSpacing:".12em"}}>
            COMPARATIF — MÊME PROFIL À {salary.toLocaleString("fr-CH")} CHF/MOIS
          </div>
        </div>

        {[
          {
            name:"🌑 UMBRA",
            price:`${price.toLocaleString("fr-CH")} CHF`,
            note:"annonce 90 jours · anonymat complet",
            tag:"VOTRE CHOIX",
            tagCol:C.copper,
            isUmbra:true,
          },
          {
            name:"💼 Chasseur de tête",
            price:`${chassMin.toLocaleString("fr-CH")} – ${chassMax.toLocaleString("fr-CH")} CHF`,
            note:"18-25% du salaire annuel · facturé à l'embauche",
            tag:`×${Math.round(chassMin/price)}–${Math.round(chassMax/price)} PLUS CHER`,
            tagCol:C.red,
            isUmbra:false,
          },
          {
            name:"🔵 LinkedIn Recruiter",
            price:"1 188 CHF / an",
            note:"abonnement fixe · aucune garantie · identités publiques",
            tag:"IDENTITÉ EXPOSÉE",
            tagCol:C.mist,
            isUmbra:false,
          },
          {
            name:"📋 Indeed / JobUp",
            price:"Variable par clic",
            note:"coût au clic · profils non qualifiés · zéro matching culturel",
            tag:"0 MATCHING",
            tagCol:C.fog,
            isUmbra:false,
          },
        ].map((row,i)=>(
          <div key={i}
            onMouseEnter={()=>setHovered(i)}
            onMouseLeave={()=>setHovered(null)}
            style={{
              padding:"18px 24px",
              borderBottom:i<3?`1px solid ${C.edge}`:"none",
              display:"flex",alignItems:"center",gap:16,flexWrap:"wrap",
              background:row.isUmbra
                ? `rgba(217,123,58,.06)`
                : hovered===i?"rgba(255,255,255,.02)":"transparent",
              transition:"background .2s",
              borderLeft:row.isUmbra?`3px solid ${C.copper}`:"3px solid transparent",
            }}>
            <div style={{flex:"0 0 180px"}}>
              <div style={{fontWeight:row.isUmbra?500:400,fontSize:14,
                color:row.isUmbra?C.ice:C.mist,marginBottom:2}}>{row.name}</div>
              <div style={{fontSize:11,color:C.fog}}>{row.note}</div>
            </div>
            <div style={{flex:"1 1 140px"}}>
              <div className="jb" style={{
                fontSize:row.isUmbra?20:14,
                color:row.isUmbra?C.copper:C.fog,
                fontWeight:row.isUmbra?"500":"300",
              }}>{row.price}</div>
            </div>
            <div>
              <span className="pill" style={{
                borderColor:`${row.tagCol}50`,
                color:row.tagCol,
                background:`${row.tagCol}10`,
                fontSize:9,letterSpacing:".08em",
              }}>{row.tag}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Palier info */}
      <div className="fu4 card" style={{padding:20,marginBottom:28,background:C.ghost}}>
        <div className="jb" style={{fontSize:9,color:C.fog,letterSpacing:".12em",marginBottom:14}}>
          BARÈME COMPLET — ÉCHELLE PROGRESSIVE
        </div>
        <div style={{display:"flex",gap:4,flexWrap:"wrap"}}>
          {TIERS.map((t,i)=>{
            const active = salary>=t.min && salary<t.max || (i===TIERS.length-1&&salary>=t.min);
            return(
              <div key={i} style={{
                flex:"1 1 100px",padding:"10px 12px",
                background:active?C.copperG:"transparent",
                border:`1px solid ${active?C.copperD:C.edge}`,
                transition:"all .2s",
              }}>
                <div className="jb" style={{fontSize:8,color:active?C.copper:C.fog,marginBottom:4,letterSpacing:".05em"}}>
                  {t.label.toUpperCase()}
                </div>
                <div className="jb" style={{fontSize:10,color:active?C.copperL:C.mist}}>
                  {t.rate}%
                </div>
                <div style={{fontSize:10,color:C.fog,marginTop:2}}>
                  {t.min>=1000?`${t.min/1000}k`:t.min}–{t.max>=1000?`${t.max/1000}k`:t.max} CHF
                </div>
              </div>
            );
          })}
        </div>
        <div style={{marginTop:12,fontSize:12,color:C.fog,lineHeight:1.6}}>
          Le prix final est calculé au moment où vous validez votre profil.
          Si votre situation change, vous pouvez ajuster avant paiement.
        </div>
      </div>

      {/* CTA */}
      <div className="fu5" style={{display:"flex",flexDirection:"column",alignItems:"stretch",gap:12}}>
        <button className="btn btn-p" style={{fontSize:16,padding:"18px 40px",
          letterSpacing:".04em",fontWeight:500}}
          onClick={onNext}>
          Je comprends — commencer mon profil →
        </button>
        <div className="jb" style={{fontSize:10,color:C.dim,textAlign:"center",letterSpacing:".05em"}}>
          VOUS ENTREZ VOTRE SALAIRE EXACT LORS DU PROFIL · LE PRIX S'AJUSTE EN TEMPS RÉEL
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
// MAIN
// ══════════════════════════════════════════════════════════════

export default function UMBRA(){
  const [screen,setScreen]=useState("landing");
  const [type,setType]=useState(null);
  const [tab,setTab]=useState("matches");
  const [match,setMatch]=useState(null);
  const [reveal,setReveal]=useState(false);

  const go=(s)=>{setScreen(s);setMatch(null);};
  const start=(t)=>{setType(t);go("pricing");};
  const inApp=screen==="app";

  return(
    <>
      <style>{STYLE}</style>
      <div style={{minHeight:"100vh",background:C.void,position:"relative"}}>
        {/* Texture */}
        <div className="noise"/>
        <div className="scan-w"><div className="scan"/></div>

        {/* Ambient orbs */}
        <div style={{position:"fixed",inset:0,pointerEvents:"none",zIndex:0}}>
          <div style={{position:"absolute",top:-300,right:-200,width:900,height:900,borderRadius:"50%",background:"radial-gradient(circle,rgba(217,123,58,.055) 0%,transparent 60%)",filter:"blur(60px)"}}/>
          <div style={{position:"absolute",bottom:-200,left:-150,width:700,height:700,borderRadius:"50%",background:"radial-gradient(circle,rgba(56,189,248,.035) 0%,transparent 60%)",filter:"blur(60px)"}}/>
        </div>

        {/* Reveal overlay */}
        {reveal&&<Reveal onClose={()=>{setReveal(false);setMatch(null);setTab("matches");}}/>}

        {/* NAV */}
        <nav className="nav">
          <div className="logo" onClick={()=>go("landing")}>
            <div className="logo-d"/>
            UMBRA
          </div>

          {inApp&&(
            <div className="nav-t">
              {[
                {id:"matches",l:"Matchs"},
                {id:"trust",  l:"Confiance"},
                {id:"intel",  l:"Intelligence"},
              ].map(t=>(
                <button key={t.id} className={`nav-b ${tab===t.id?"on":""}`}
                  onClick={()=>{setTab(t.id);setMatch(null);}}>
                  {t.l}
                </button>
              ))}
            </div>
          )}

          <div style={{display:"flex",alignItems:"center",gap:10}}>
            {inApp?(
              <>
                <span className="pill p-gr">
                  <span style={{width:5,height:5,borderRadius:"50%",background:C.green,display:"inline-block",animation:"pulse 2s infinite"}}/>
                  EN LIGNE
                </span>
                <div style={{width:36,height:36,borderRadius:"50%",background:C.ghost,border:`1px solid ${C.edge}`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:16,cursor:"pointer"}}>
                  🎭
                </div>
              </>
            ):screen!=="landing"?(
              <button className="btn btn-o btn-xs" onClick={()=>go("landing")}>← Accueil</button>
            ):(
              <span className="pill p-gh" style={{fontSize:10}}>🔒 CHIFFRÉ E2E</span>
            )}
          </div>
        </nav>

        {/* CONTENT */}
        <div style={{position:"relative",zIndex:2}}>
          {screen==="landing"   &&<Landing onStart={start}/>}
          {screen==="pricing"   &&<PricingCalculator type={type} onNext={()=>go("onboarding")}/>}
          {screen==="onboarding"&&<Onboarding type={type} onNext={()=>go("quiz")}/>}
          {screen==="quiz"      &&<CultureQuiz onNext={()=>go("profile")}/>}
          {screen==="profile"   &&<Profile type={type} onNext={()=>{setScreen("app");setTab("matches");}}/>}

          {inApp&&!match&&tab==="matches"&&<Dashboard type={type} onView={m=>setMatch(m)}/>}
          {inApp&&match&&tab==="matches"&&(
            <MatchDetail match={match} type={type} onBack={()=>setMatch(null)} onReveal={()=>setReveal(true)}/>
          )}
          {inApp&&tab==="trust" &&<TrustScreen/>}
          {inApp&&tab==="intel" &&<IntelScreen/>}

          {/* FOOTER */}
          <footer className="foot">
            <div className="logo" style={{fontSize:16}}>
              <div className="logo-d"/>UMBRA
            </div>
            <div className="jb" style={{fontSize:10,color:C.dim,letterSpacing:".05em"}}>
              © 2026 · SUISSE · ANONYMAT PAR DESIGN · VOS DONNÉES NE NOUS APPARTIENNENT PAS
            </div>
            <div style={{display:"flex",gap:20}}>
              {["Confidentialité","CGU","Presse","API","Contact"].map(l=>(
                <span key={l} style={{fontSize:12,color:C.dim,cursor:"pointer",fontFamily:"Outfit"}}>{l}</span>
              ))}
            </div>
          </footer>
        </div>
      </div>
    </>
  );
}
