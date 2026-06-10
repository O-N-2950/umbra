"""
UMBRA — PII Shield
═══════════════════════════════════════════════════════════════
Anonymise un texte de CV AVANT tout envoi vers un LLM externe.
Garantie nLPD : aucune donnée nominative ne quitte la Suisse en clair.

Stratégie :
  1. Détection PII par patterns (email, téléphone CH, IBAN, AVS, URLs)
  2. Détection noms propres (heuristique + liste d'entreprises connues)
  3. Remplacement par jetons réversibles ([NOM_1], [EMAIL_1]...)
  4. Re-substitution possible après analyse (mapping gardé en RAM, jamais persisté)

Défense prompt-injection :
  - Neutralise les séquences d'instruction connues dans le CV.
"""
from __future__ import annotations
import re
import logging

logger = logging.getLogger("umbra.pii")

# ── Patterns PII (Suisse) ────────────────────────────────────────────────────
RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
RE_PHONE_CH = re.compile(
    r"(?:(?:\+41|0041|0)\s?)?(?:\(0\))?\s?[1-9]\d(?:[\s.\-]?\d{2,3}){3}\b"
)
RE_IBAN = re.compile(r"\bCH\d{2}[\s]?(?:\d{4}[\s]?){4}\d{1}\b", re.IGNORECASE)
RE_AVS = re.compile(r"\b756\.\d{4}\.\d{4}\.\d{2}\b")  # N° AVS suisse
RE_URL = re.compile(r"https?://[^\s]+|linkedin\.com/[^\s]+", re.IGNORECASE)
RE_DOB = re.compile(r"\b(0[1-9]|[12]\d|3[01])[./](0[1-9]|1[0-2])[./](19|20)\d{2}\b")
# NPA suisse (4 chiffres) suivi d'une localité : masque la ville exacte (désanonymisante
# dans un village). Ex: "2300 La Chaux-de-Fonds", "1201 Genève", "2000 Neuchâtel".
RE_NPA_CITY = re.compile(
    r"\b(\d{4})\s+([A-ZÀ-Ý][a-zà-ÿ]+(?:[-\s](?:la|le|les|de|du|des|aux?|sur|sous)?[-\s]?[A-ZÀ-Ýa-zà-ÿ]+){0,4})"
)
# Adresse de rue : "Rue/Av./Chemin ... <numéro>" — la rue + numéro localisent précisément.
RE_STREET = re.compile(
    r"(?i)\b((?:rue|avenue|av\.|chemin|ch\.|route|rte|impasse|place|pl\.|quai|allée|sentier|ruelle)"
    r"\s+[^\n,;]{2,40}?\s+\d+[a-z]?)\b"
)

# ── Anti prompt-injection : motifs d'instruction à neutraliser ────────────────
INJECTION_PATTERNS = [
    r"(?i)ignore\s+(?:tes|les|toutes?\s+les?|previous|above|prior|all|any)\s+(?:instructions?|consignes?|règles?|prompts?)",
    r"(?i)ignore\s+(?:all|any|the)\s+(?:previous|above|prior|preceding)",
    r"(?i)(?:disregard|forget|oublie)\s+(?:everything|all|tout|the\s+above|previous|prior)",
    r"(?i)(?:tu\s+es|you\s+are)\s+(?:maintenant|now)\s+(?:un|a|une)",
    r"(?i)system\s*(?:prompt|message|:)",
    r"(?i)(?:give|donne|attribue)\s+(?:me|moi)?\s*(?:the\s+)?(?:maximum|highest|max)\s*(?:score|rating|note)",
    r"(?i)(?:score|note|rating)\s*(?:=|:|de|maximum\s+de|maximal\s+de)?\s*(?:100|max|maximum|parfait)",
    r"(?i)donne[\s-]*moi\s+(?:le\s+)?(?:score|note|maximum)",
    r"(?i)(?:classe|classify|rate)\s+(?:moi|me|this)\s+(?:comme|as)\s+(?:a-?player|excellent|parfait)",
    r"(?i)nouvelle?\s+(?:instruction|consigne|règle|tâche)",
    r"(?i)new\s+(?:instruction|task|rule|prompt)",
    r"(?i)</?(?:system|user|assistant|instruction)>",
]


class PIIShield:
    """Anonymise et neutralise un texte avant envoi LLM."""

    def __init__(self):
        self._mapping: dict[str, str] = {}
        self._counters: dict[str, int] = {}

    def _token(self, kind: str, original: str) -> str:
        """Génère/réutilise un jeton réversible pour une valeur."""
        if original in self._mapping:
            return self._mapping[original]
        self._counters[kind] = self._counters.get(kind, 0) + 1
        token = f"[{kind}_{self._counters[kind]}]"
        self._mapping[original] = token
        return token

    def neutralize_injection(self, text: str) -> tuple[str, int]:
        """Neutralise les tentatives d'injection. Retourne (texte, nb_neutralisé)."""
        count = 0
        for pat in INJECTION_PATTERNS:
            text, n = re.subn(pat, "[CONTENU_NEUTRALISÉ]", text)
            count += n
        return text, count


    # ── Masquage des noms propres (heuristique sûre) ────────────────────────
    EMPLOYER_TRIGGERS = re.compile(
        r"\b(?:chez|at|pour|employeur|société|entreprise|company|firme)\s+"
        r"([A-ZÀ-Ý][\w&.-]+(?:\s+[A-ZÀ-Ý][\w&.-]+){0,3}"
        r"(?:\s+(?:SA|SARL|AG|GmbH|Sàrl|Ltd|Inc|Group|Groupe))?)",
    )
    # Nom en tête de CV : 2-3 mots capitalisés sur la 1ère ligne non vide
    NAME_HEAD = re.compile(r"^\s*([A-ZÀ-Ý][a-zà-ÿ]+(?:[-\s][A-ZÀ-Ý][a-zà-ÿ]+){1,3})\s*$", re.MULTILINE)

    def _mask_names(self, text: str) -> str:
        """Masque employeurs (après 'chez') et nom en tête de CV."""
        text = self.EMPLOYER_TRIGGERS.sub(
            lambda m: m.group(0).replace(m.group(1), self._token("EMPLOYEUR", m.group(1))),
            text,
        )
        # Nom en tête : seulement la première occurrence trouvée
        m = self.NAME_HEAD.search(text)
        if m:
            text = text.replace(m.group(1), self._token("NOM", m.group(1)), 1)
        return text

    def anonymize(self, text: str) -> dict:
        """
        Anonymise un CV. Retourne :
          - clean: texte anonymisé prêt pour le LLM
          - mapping: dict jeton→original (RAM only, pour ré-identification post-analyse)
          - pii_found: compteurs par type
          - injection_blocked: nb de tentatives d'injection neutralisées
        """
        if not text:
            return {"clean": "", "mapping": {}, "pii_found": {}, "injection_blocked": 0}

        # 1. Neutraliser les injections AVANT tout
        text, inj = self.neutralize_injection(text)

        # 2. Remplacer les PII structurées
        text = RE_AVS.sub(lambda m: self._token("AVS", m.group()), text)
        text = RE_IBAN.sub(lambda m: self._token("IBAN", m.group()), text)
        text = RE_EMAIL.sub(lambda m: self._token("EMAIL", m.group()), text)
        text = RE_URL.sub(lambda m: self._token("URL", m.group()), text)
        text = RE_DOB.sub(lambda m: self._token("DATE_NAISSANCE", m.group()), text)
        text = RE_PHONE_CH.sub(lambda m: self._token("TEL", m.group()), text)
        # Adresse complète : rue+numéro puis NPA+ville (avant le masquage des noms,
        # pour ne pas que la ville soit confondue avec un nom propre).
        text = RE_STREET.sub(lambda m: self._token("ADRESSE", m.group(1)), text)
        text = RE_NPA_CITY.sub(
            lambda m: m.group(0).replace(m.group(2), self._token("LOCALITE", m.group(2))),
            text,
        )
        text = self._mask_names(text)

        pii_found = dict(self._counters)
        reverse = {v: k for k, v in self._mapping.items()}

        logger.info(
            "PII anonymisé: %s | injections neutralisées: %d",
            pii_found, inj
        )

        return {
            "clean": text,
            "mapping": reverse,         # jeton → original (RAM uniquement)
            "pii_found": pii_found,
            "injection_blocked": inj,
        }

    def reidentify(self, text: str, mapping: dict) -> str:
        """Re-substitue les jetons par les valeurs originales (post-analyse)."""
        for token, original in mapping.items():
            text = text.replace(token, original)
        return text


def anonymize_cv(text: str) -> dict:
    """Helper one-shot : anonymise un CV."""
    return PIIShield().anonymize(text)
