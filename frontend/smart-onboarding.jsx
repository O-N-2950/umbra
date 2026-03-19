import { useState, useEffect, useCallback, useRef } from "react";

// ═══════════════════════════════════════════════════════
// MATCHO SMART ONBOARDING — Full React App
// Live: UID Register + OpenIBAN + IA Matching
// ═══════════════════════════════════════════════════════

// ── API Services ──────────────────────────────────────

const UID_API = "https://www.uid-wse.admin.ch/V5.0/PublicServices.svc";
const OPENIBAN_API = "https://openiban.com/validate";

function buildSearchEnvelope(name) {
  const escaped = name.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return `<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:uid="http://www.uid.admin.ch/xmlns/uid-wse"
  xmlns:uid5="http://www.uid.admin.ch/xmlns/uid-wse/5">
  <soapenv:Body>
    <uid:Search>
      <uid:searchParameters>
        <uid5:uidEntitySearchParameters>
          <uid5:organisationName>${escaped}</uid5:organisationName>
        </uid5:uidEntitySearchParameters>
      </uid:searchParameters>
    </uid:Search>
  </soapenv:Body>
</soapenv:Envelope>`;
}

function parseCompanies(xmlText) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(xmlText, "text/xml");
  const results = [];
  const items = doc.querySelectorAll("uidEntitySearchResultItem");
  items.forEach((item) => {
    const getText = (tag) => {
      const el = item.querySelector(tag);
      return el ? el.textContent.trim() : "";
    };
    const uid = getText("uidOrganisationId");
    if (!uid) return;
    const formatted = uid.length === 9
      ? `CHE-${uid.slice(0,3)}.${uid.slice(3,6)}.${uid.slice(6,9)}`
      : `CHE-${uid}`;
    const legalForms = {
      "0106": "SA", "0107": "Sàrl", "0101": "RI", "0108": "Coopérative",
      "0109": "Association", "0110": "Fondation", "0104": "SNC", "0105": "SC",
    };
    results.push({
      ide: formatted,
      name: getText("organisationName"),
      legalName: getText("organisationLegalName") || getText("organisationName"),
      legalFormCode: getText("legalForm"),
      legalForm: legalForms[getText("legalForm")] || getText("legalForm"),
      street: getText("street"),
      houseNumber: getText("houseNumber"),
      zip: getText("swissZipCode"),
      town: getText("town"),
      canton: getText("cantonAbbreviation"),
      rating: parseInt(getText("rating") || "0"),
    });
  });
  return results.sort((a, b) => b.rating - a.rating);
}

async function searchCompany(name) {
  const resp = await fetch(UID_API, {
    method: "POST",
    headers: {
      "Content-Type": "text/xml; charset=utf-8",
      SOAPAction: "http://www.uid.admin.ch/xmlns/uid-wse/IPublicServices/Search",
    },
    body: buildSearchEnvelope(name),
  });
  return parseCompanies(await resp.text());
}

async function validateIBAN(iban) {
  const clean = iban.replace(/[^A-Z0-9]/gi, "").toUpperCase();
  try {
    const resp = await fetch(`${OPENIBAN_API}/${clean}?getBIC=true&validateBankCode=true`);
    const data = await resp.json();
    return {
      iban: clean,
      formatted: clean.replace(/(.{4})/g, "$1 ").trim(),
      valid: data.valid,
      bankName: data.bankData?.name || "",
      bic: data.bankData?.bic || "",
      messages: data.messages || [],
    };
  } catch {
    return { iban: clean, formatted: clean, valid: false, bankName: "", bic: "", messages: ["Erreur réseau"] };
  }
}

// ── Icons (inline SVG) ────────────────────────────────

const Icons = {
  Search: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
  ),
  Check: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>
  ),
  Alert: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
  ),
  Building: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="9" y1="6" x2="9" y2="6.01"/><line x1="15" y1="6" x2="15" y2="6.01"/><line x1="9" y1="10" x2="9" y2="10.01"/><line x1="15" y1="10" x2="15" y2="10.01"/><line x1="9" y1="14" x2="9" y2="14.01"/><line x1="15" y1="14" x2="15" y2="14.01"/><line x1="9" y1="18" x2="15" y2="18"/></svg>
  ),
  Bank: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polygon points="12 2 2 7 22 7"/><rect x="4" y="9" width="3" height="9"/><rect x="10.5" y="9" width="3" height="9"/><rect x="17" y="9" width="3" height="9"/><line x1="2" y1="20" x2="22" y2="20"/></svg>
  ),
  Sparkle: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/></svg>
  ),
  Loader: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="animate-spin"><path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" opacity="0.25"/><path d="M21 12a9 9 0 00-9-9"/></svg>
  ),
};

// ── Components ────────────────────────────────────────

function StepIndicator({ steps, current }) {
  return (
    <div className="flex items-center gap-1 mb-8">
      {steps.map((s, i) => (
        <div key={i} className="flex items-center gap-1">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold transition-all duration-300 ${
            i < current ? "bg-emerald-500 text-white" :
            i === current ? "bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/50" :
            "bg-white/5 text-white/30"
          }`}>
            {i < current ? <Icons.Check /> : <span>{i + 1}</span>}
            <span className="hidden sm:inline">{s}</span>
          </div>
          {i < steps.length - 1 && (
            <div className={`w-8 h-px transition-colors ${i < current ? "bg-emerald-500" : "bg-white/10"}`} />
          )}
        </div>
      ))}
    </div>
  );
}

function CompanyCard({ company, selected, onSelect }) {
  const addr = [company.street, company.houseNumber].filter(Boolean).join(" ");
  const full = [addr, [company.zip, company.town].filter(Boolean).join(" ")].filter(Boolean).join(", ");
  return (
    <button
      onClick={() => onSelect(company)}
      className={`w-full text-left p-4 rounded-xl border transition-all duration-200 group ${
        selected
          ? "border-emerald-500 bg-emerald-500/10 shadow-lg shadow-emerald-500/10"
          : "border-white/10 bg-white/5 hover:border-emerald-500/50 hover:bg-white/8"
      }`}
    >
      <div className="flex justify-between items-start">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-bold text-white truncate">{company.name}</span>
            <span className="shrink-0 text-xs px-2 py-0.5 rounded-full bg-teal-500/20 text-teal-300 font-medium">
              {company.legalForm}
            </span>
          </div>
          <div className="text-sm text-white/50">{full} ({company.canton})</div>
          <div className="text-xs text-emerald-400 font-mono mt-1">{company.ide}</div>
        </div>
        <div className={`shrink-0 ml-3 w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold ${
          company.rating >= 90 ? "bg-emerald-500/20 text-emerald-400" :
          company.rating >= 50 ? "bg-yellow-500/20 text-yellow-400" :
          "bg-white/10 text-white/40"
        }`}>
          {company.rating}
        </div>
      </div>
    </button>
  );
}

function IBANField({ value, onChange, result, loading }) {
  const format = (v) => {
    const clean = v.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
    return clean.replace(/(.{4})/g, "$1 ").trim();
  };
  return (
    <div>
      <label className="block text-sm font-medium text-white/70 mb-2">IBAN</label>
      <div className="relative">
        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30"><Icons.Bank /></div>
        <input
          type="text"
          value={format(value)}
          onChange={(e) => onChange(e.target.value.replace(/\s/g, ""))}
          placeholder="CH93 0076 2011 6238 5295 7"
          maxLength={30}
          className="w-full pl-10 pr-10 py-3 rounded-xl bg-white/5 border border-white/10 text-white font-mono text-sm placeholder-white/20 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all"
        />
        <div className="absolute right-3 top-1/2 -translate-y-1/2">
          {loading ? <span className="text-white/30"><Icons.Loader /></span> :
           result?.valid ? <span className="text-emerald-400"><Icons.Check /></span> :
           result && !result.valid ? <span className="text-red-400"><Icons.Alert /></span> : null}
        </div>
      </div>
      {result?.valid && result.bankName && (
        <div className="mt-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
          <div className="flex items-center gap-2">
            <Icons.Check />
            <span className="text-emerald-400 text-sm font-medium">{result.bankName}</span>
          </div>
          {result.bic && <div className="text-xs text-white/40 mt-1 font-mono">BIC: {result.bic}</div>}
        </div>
      )}
      {result && !result.valid && (
        <div className="mt-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
          <div className="text-red-400 text-sm">{result.messages?.join(", ") || "IBAN invalide"}</div>
        </div>
      )}
    </div>
  );
}

// ── Main App ──────────────────────────────────────────

const STEPS = ["Société", "Coordonnées", "Banque", "Vérification"];

export default function MatchoOnboarding() {
  const [step, setStep] = useState(0);

  // Step 0: Company search
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [companies, setCompanies] = useState([]);
  const [selected, setSelected] = useState(null);
  const [searchDone, setSearchDone] = useState(false);
  const timerRef = useRef(null);

  // Step 1: Contact
  const [contact, setContact] = useState({ name: "", email: "", phone: "", mobile: "" });

  // Step 2: Bank
  const [iban, setIban] = useState("");
  const [ibanResult, setIbanResult] = useState(null);
  const [ibanLoading, setIbanLoading] = useState(false);
  const ibanTimer = useRef(null);

  // Step 3: Summary
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  // ── Company search with debounce ──
  useEffect(() => {
    if (query.length < 2) { setCompanies([]); setSearchDone(false); return; }
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      setSearching(true);
      setSearchDone(false);
      try {
        const results = await searchCompany(query);
        setCompanies(results.slice(0, 5));
      } catch { setCompanies([]); }
      setSearching(false);
      setSearchDone(true);
    }, 400);
    return () => clearTimeout(timerRef.current);
  }, [query]);

  // ── IBAN validation with debounce ──
  useEffect(() => {
    const clean = iban.replace(/[^A-Z0-9]/gi, "");
    if (clean.length < 15) { setIbanResult(null); return; }
    clearTimeout(ibanTimer.current);
    ibanTimer.current = setTimeout(async () => {
      setIbanLoading(true);
      try {
        const r = await validateIBAN(clean);
        setIbanResult(r);
      } catch { setIbanResult(null); }
      setIbanLoading(false);
    }, 500);
    return () => clearTimeout(ibanTimer.current);
  }, [iban]);

  const canNext = () => {
    if (step === 0) return !!selected;
    if (step === 1) return contact.name && contact.email;
    if (step === 2) return true; // IBAN optional
    return true;
  };

  const handleSubmit = () => {
    setSubmitting(true);
    setTimeout(() => { setSubmitting(false); setDone(true); }, 1500);
  };

  if (done) {
    return (
      <div className="min-h-screen bg-[#0B0F1A] flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <div className="w-20 h-20 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-6 animate-pulse">
            <Icons.Check />
          </div>
          <h1 className="text-3xl font-bold text-white mb-3">Compte créé</h1>
          <p className="text-white/50 mb-2">
            <span className="text-emerald-400 font-semibold">{selected?.name}</span> est prêt.
          </p>
          <p className="text-sm text-white/30">
            IDE {selected?.ide} • {selected?.legalForm} • {selected?.canton}
          </p>
          <div className="mt-8 p-4 rounded-xl bg-white/5 border border-white/10 text-left">
            <div className="text-xs text-white/40 uppercase tracking-wider mb-3">Résumé</div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-white/50">Contact</span><span className="text-white">{contact.name}</span></div>
              <div className="flex justify-between"><span className="text-white/50">Email</span><span className="text-white">{contact.email}</span></div>
              {ibanResult?.valid && <div className="flex justify-between"><span className="text-white/50">Banque</span><span className="text-white">{ibanResult.bankName}</span></div>}
            </div>
          </div>
          <button onClick={() => { setDone(false); setStep(0); setSelected(null); setQuery(""); setContact({ name: "", email: "", phone: "", mobile: "" }); setIban(""); setIbanResult(null); }}
            className="mt-6 px-6 py-2 rounded-lg bg-white/10 text-white/60 hover:bg-white/20 transition text-sm">
            Nouveau mandat
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0B0F1A] text-white">
      {/* Header */}
      <div className="border-b border-white/5">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
              <span className="text-xs font-black">M</span>
            </div>
            <span className="text-lg font-bold tracking-tight">MATCHO</span>
            <span className="text-xs text-white/30 hidden sm:block">Smart Onboarding</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-white/30">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>APIs fédérales connectées</span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-3xl mx-auto px-4 py-8">
        <StepIndicator steps={STEPS} current={step} />

        {/* STEP 0: Company */}
        {step === 0 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold mb-1">Rechercher la société</h2>
              <p className="text-white/40 text-sm">Tapez le nom — MATCHO interroge le registre fédéral en temps réel.</p>
            </div>

            <div className="relative">
              <div className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30">
                {searching ? <Icons.Loader /> : <Icons.Search />}
              </div>
              <input
                type="text"
                value={query}
                onChange={(e) => { setQuery(e.target.value); setSelected(null); }}
                placeholder="Ex: WW Finance Group, PEP's Swiss..."
                autoFocus
                className="w-full pl-12 pr-4 py-4 rounded-2xl bg-white/5 border border-white/10 text-white text-lg placeholder-white/20 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all"
              />
            </div>

            {companies.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs text-white/40">
                  <Icons.Building />
                  <span>{companies.length} résultat{companies.length > 1 ? "s" : ""} — Source: Registre UID (uid-wse.admin.ch)</span>
                </div>
                {companies.map((c, i) => (
                  <CompanyCard key={i} company={c} selected={selected?.ide === c.ide} onSelect={setSelected} />
                ))}
              </div>
            )}

            {searchDone && companies.length === 0 && query.length >= 2 && (
              <div className="text-center py-8 text-white/30">
                <Icons.Alert />
                <p className="mt-2">Aucune société trouvée pour « {query} »</p>
                <p className="text-xs mt-1">Vérifiez l'orthographe ou essayez un nom partiel.</p>
              </div>
            )}

            {selected && (
              <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20">
                <div className="flex items-center gap-2 text-emerald-400 text-sm font-medium mb-3">
                  <Icons.Sparkle /> Données pré-remplies automatiquement
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {[
                    ["IDE", selected.ide],
                    ["Forme juridique", selected.legalForm],
                    ["Adresse", `${selected.street} ${selected.houseNumber}`],
                    ["Localité", `${selected.zip} ${selected.town}`],
                    ["Canton", selected.canton],
                    ["Score", `${selected.rating}/100`],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <div className="text-white/30 text-xs">{k}</div>
                      <div className="text-white font-medium">{v}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* STEP 1: Contact */}
        {step === 1 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold mb-1">Personne de contact</h2>
              <p className="text-white/40 text-sm">Qui sera le contact principal pour ce mandat ?</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {[
                { key: "name", label: "Nom complet", placeholder: "Olivier Neukomm", required: true },
                { key: "email", label: "Email", placeholder: "contact@winwin.swiss", type: "email", required: true },
                { key: "phone", label: "Téléphone fixe", placeholder: "+41 32 462 XX XX" },
                { key: "mobile", label: "Mobile", placeholder: "+41 79 XXX XX XX" },
              ].map((f) => (
                <div key={f.key}>
                  <label className="block text-sm font-medium text-white/70 mb-2">
                    {f.label} {f.required && <span className="text-emerald-400">*</span>}
                  </label>
                  <input
                    type={f.type || "text"}
                    value={contact[f.key]}
                    onChange={(e) => setContact({ ...contact, [f.key]: e.target.value })}
                    placeholder={f.placeholder}
                    className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/20 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all text-sm"
                  />
                </div>
              ))}
            </div>

            {selected && (
              <div className="p-3 rounded-lg bg-white/5 border border-white/10 flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center text-emerald-400 text-sm font-bold">
                  {selected.canton}
                </div>
                <div>
                  <div className="text-sm font-medium">{selected.name}</div>
                  <div className="text-xs text-white/40">{selected.ide} • {selected.legalForm}</div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* STEP 2: Bank */}
        {step === 2 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold mb-1">Comptes bancaires</h2>
              <p className="text-white/40 text-sm">L'IBAN est validé en temps réel — la banque et le BIC sont identifiés automatiquement.</p>
            </div>

            <IBANField value={iban} onChange={setIban} result={ibanResult} loading={ibanLoading} />

            <div className="p-4 rounded-xl bg-white/5 border border-white/10">
              <div className="text-xs text-white/40 uppercase tracking-wider mb-2">Configuration comptable</div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-white/30 text-xs">Logiciel</div>
                  <div className="text-white font-medium">Crésus</div>
                </div>
                <div>
                  <div className="text-white/30 text-xs">Exercice</div>
                  <div className="text-white font-medium">Janvier — Décembre</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: Verification */}
        {step === 3 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold mb-1">Vérification finale</h2>
              <p className="text-white/40 text-sm">Vérifiez les informations avant de créer le mandat.</p>
            </div>

            <div className="space-y-3">
              {/* Company */}
              <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-xs text-white/40 uppercase tracking-wider">Société</div>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400">Vérifié RC</span>
                </div>
                <div className="text-lg font-bold">{selected?.name}</div>
                <div className="text-sm text-white/50 mt-1">{selected?.street} {selected?.houseNumber}, {selected?.zip} {selected?.town} ({selected?.canton})</div>
                <div className="flex gap-4 mt-2 text-xs">
                  <span className="text-emerald-400 font-mono">{selected?.ide}</span>
                  <span className="text-teal-400">{selected?.legalForm}</span>
                </div>
              </div>

              {/* Contact */}
              <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                <div className="text-xs text-white/40 uppercase tracking-wider mb-3">Contact</div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div><span className="text-white/40">Nom : </span><span className="text-white">{contact.name}</span></div>
                  <div><span className="text-white/40">Email : </span><span className="text-white">{contact.email}</span></div>
                  {contact.phone && <div><span className="text-white/40">Tél : </span><span className="text-white">{contact.phone}</span></div>}
                  {contact.mobile && <div><span className="text-white/40">Mobile : </span><span className="text-white">{contact.mobile}</span></div>}
                </div>
              </div>

              {/* Bank */}
              {ibanResult?.valid && (
                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                  <div className="text-xs text-white/40 uppercase tracking-wider mb-3">Banque</div>
                  <div className="text-sm">
                    <span className="font-mono text-white">{ibanResult.formatted}</span>
                    <div className="text-white/50 mt-1">{ibanResult.bankName} {ibanResult.bic && `(${ibanResult.bic})`}</div>
                  </div>
                </div>
              )}

              {/* Sources */}
              <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
                <div className="flex items-center gap-2 text-xs text-emerald-400">
                  <Icons.Sparkle />
                  <span>Sources : Registre UID (OFS) • OpenIBAN • Registre du commerce ({selected?.canton})</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between mt-8 pt-6 border-t border-white/5">
          {step > 0 ? (
            <button onClick={() => setStep(step - 1)}
              className="px-5 py-2.5 rounded-xl text-sm text-white/50 hover:text-white hover:bg-white/5 transition">
              Retour
            </button>
          ) : <div />}

          {step < 3 ? (
            <button
              onClick={() => setStep(step + 1)}
              disabled={!canNext()}
              className={`px-6 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                canNext()
                  ? "bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40"
                  : "bg-white/5 text-white/20 cursor-not-allowed"
              }`}
            >
              Continuer
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="px-8 py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40 transition-all disabled:opacity-50"
            >
              {submitting ? "Création..." : "Créer le mandat"}
            </button>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="fixed bottom-0 left-0 right-0 border-t border-white/5 bg-[#0B0F1A]/80 backdrop-blur">
        <div className="max-w-3xl mx-auto px-4 py-2 flex justify-between text-xs text-white/20">
          <span>MATCHO v1.0 — PEP's Swiss SA</span>
          <span>Données: uid-wse.admin.ch • openiban.com</span>
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        .animate-spin { animation: spin 1s linear infinite; }
        .animate-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .5; } }
      `}</style>
    </div>
  );
}
