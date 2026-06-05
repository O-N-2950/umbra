#!/bin/bash
# ═══════════════════════════════════════════════════════════
# UMBRA — Deploy Jelastic Cloud Infomaniak
# Usage: ./deploy.sh
# Prérequis: curl, jq (brew install jq || apt install jq)
# ═══════════════════════════════════════════════════════════

set -euo pipefail

INFOMANIAK_TOKEN="${INFOMANIAK_TOKEN:-uvGxaRxguScs9RMH0_lS_swPKilo3Vc2aex3ATgKiigRMsYB2zP8eOWNuIPN1nMKF3j30b6kthsQry_P}"
JELASTIC_SERVICE_ID="10299"
ACCOUNT_ID="1897366"
JPS_URL="https://raw.githubusercontent.com/O-N-2950/umbra/main/manifest.jps"

# Couleurs
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

echo ""
echo -e "${BLUE}🌑 UMBRA — Déploiement Jelastic Cloud Infomaniak${NC}"
echo "═══════════════════════════════════════════════════════"
echo ""

# ── 1. Vérifier les prérequis ────────────────────────────────
echo -e "${YELLOW}1. Vérification des prérequis...${NC}"
command -v curl >/dev/null || { echo "❌ curl requis"; exit 1; }
command -v jq >/dev/null || { echo "⚠️  jq non trouvé — brew install jq"; }
echo -e "${GREEN}✅ Prérequis OK${NC}"

# ── 2. Vérifier le token Infomaniak ─────────────────────────
echo ""
echo -e "${YELLOW}2. Vérification du compte Infomaniak...${NC}"
PROFILE=$(curl -sf -H "Authorization: Bearer $INFOMANIAK_TOKEN" \
  "https://api.infomaniak.com/1/profile" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data']['email'])" 2>/dev/null || echo "ERREUR")

if [ "$PROFILE" = "ERREUR" ]; then
  echo -e "${RED}❌ Token Infomaniak invalide${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Connecté: $PROFILE${NC}"

# ── 3. Collecter les paramètres ──────────────────────────────
echo ""
echo -e "${YELLOW}3. Configuration UMBRA...${NC}"
echo ""

# Gemini API Key
if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo -n "🔑 Clé API Google Gemini (aistudio.google.com/apikey): "
  read -rs GEMINI_API_KEY; echo ""
fi

# Resend API Key
if [ -z "${RESEND_API_KEY:-}" ]; then
  echo -n "📧 Clé API Resend (resend.com/api-keys) [re_...]: "
  read -rs RESEND_API_KEY; echo ""
fi

# Stripe (optionnel)
if [ -z "${STRIPE_SECRET_KEY:-}" ]; then
  echo -n "💳 Clé Stripe (optionnel, Entrée pour ignorer): "
  read -rs STRIPE_SECRET_KEY; echo ""
fi

# Nom de l'environnement
ENV_NAME="${ENV_NAME:-umbra-prod}"
echo -e "🌐 Nom environnement: ${GREEN}$ENV_NAME${NC}"

# ── 4. Récupérer le token de session Jelastic ────────────────
echo ""
echo -e "${YELLOW}4. Connexion à Jelastic Infomaniak...${NC}"

# L'API Jelastic native d'Infomaniak utilise app.infomaniak.com
# On obtient le token via l'API REST Infomaniak
JELASTIC_SESSION=$(curl -sf \
  -H "Authorization: Bearer $INFOMANIAK_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST \
  "https://api.infomaniak.com/1/jelastic/$JELASTIC_SERVICE_ID/token" 2>/dev/null || echo "")

# Si l'endpoint token n'existe pas, utiliser l'approche directe via app.infomaniak.com
if [ -z "$JELASTIC_SESSION" ] || echo "$JELASTIC_SESSION" | grep -q "method_not_found"; then
  echo -e "${YELLOW}⚠️  API token direct non disponible — utilisation du dashboard web${NC}"
  echo ""
  echo "═══════════════════════════════════════════════════════"
  echo -e "${BLUE}📋 ÉTAPES MANUELLES REQUISES (2 min)${NC}"
  echo "═══════════════════════════════════════════════════════"
  echo ""
  echo "1. Ouvrir: https://manager.infomaniak.com/v3/ng/jelastic/$JELASTIC_SERVICE_ID"
  echo ""
  echo "2. Cliquer: Marketplace → Import → JPS URL"
  echo ""
  echo "3. Coller cette URL:"
  echo -e "   ${GREEN}$JPS_URL${NC}"
  echo ""
  echo "4. Remplir les champs:"
  echo -e "   - Gemini API Key: ${YELLOW}[votre clé]${NC}"
  echo -e "   - Resend API Key: ${YELLOW}[votre clé]${NC}"
  echo -e "   - Domaine: ${YELLOW}${ENV_NAME}.jcloud.ik-server.com${NC}"
  echo ""
  echo "5. Cliquer Install → attendre ~3 min"
  echo ""
  
  # Ouvrir le navigateur automatiquement si possible
  JELASTIC_URL="https://manager.infomaniak.com/v3/ng/jelastic/$JELASTIC_SERVICE_ID"
  if command -v open >/dev/null 2>&1; then
    echo -e "${YELLOW}→ Ouverture automatique du navigateur...${NC}"
    open "$JELASTIC_URL"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$JELASTIC_URL"
  fi
  
  echo ""
  echo "═══════════════════════════════════════════════════════"
  echo -e "${YELLOW}Variables à sauvegarder pour le formulaire JPS:${NC}"
  echo ""
  echo "GEMINI_API_KEY=$GEMINI_API_KEY"
  [ -n "$RESEND_API_KEY" ] && echo "RESEND_API_KEY=$RESEND_API_KEY"
  [ -n "$STRIPE_SECRET_KEY" ] && echo "STRIPE_SECRET_KEY=$STRIPE_SECRET_KEY"
  echo "ENV_NAME=$ENV_NAME"
  echo ""
  
  exit 0
fi

echo -e "${GREEN}✅ Session Jelastic obtenue${NC}"

# ── 5. Installer le JPS via API Jelastic ────────────────────
echo ""
echo -e "${YELLOW}5. Installation UMBRA sur Jelastic...${NC}"

INSTALL_RESULT=$(curl -sf \
  -H "Authorization: Bearer $INFOMANIAK_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST \
  -d "{
    \"jps\": \"$JPS_URL\",
    \"envName\": \"$ENV_NAME\",
    \"settings\": {
      \"geminiApiKey\": \"$GEMINI_API_KEY\",
      \"resendApiKey\": \"$RESEND_API_KEY\",
      \"stripeSecretKey\": \"$STRIPE_SECRET_KEY\",
      \"appDomain\": \"${ENV_NAME}.jcloud.ik-server.com\"
    }
  }" \
  "https://api.infomaniak.com/1/jelastic/$JELASTIC_SERVICE_ID/install" || echo "")

if echo "$INSTALL_RESULT" | grep -q "success"; then
  echo -e "${GREEN}✅ Installation déclenchée !${NC}"
  APP_URL="https://${ENV_NAME}.jcloud.ik-server.com"
  echo ""
  echo "🌑 UMBRA déployé sur Jelastic Infomaniak !"
  echo "URL: $APP_URL"
  echo ""
  
  # Attendre et vérifier
  echo -e "${YELLOW}Attente démarrage (~3 min)...${NC}"
  for i in $(seq 1 20); do
    sleep 15
    STATUS=$(curl -sf --max-time 10 -o /dev/null -w "%{http_code}" "$APP_URL/ping" 2>/dev/null || echo "000")
    echo "  Tentative $i: HTTP $STATUS"
    [ "$STATUS" = "200" ] && {
      echo -e "${GREEN}✅ UMBRA UP! → $APP_URL${NC}"
      
      # Configurer les variables GitHub Actions
      echo ""
      echo "Configuration GitHub Actions variable JELASTIC_APP_URL..."
      curl -sf -X PUT \
        -H "Authorization: token ${GITHUB_TOKEN:-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}" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"JELASTIC_APP_URL\", \"value\": \"$APP_URL\"}" \
        "https://api.github.com/repos/O-N-2950/umbra/actions/variables/JELASTIC_APP_URL" \
        && echo -e "${GREEN}✅ GitHub variable configurée${NC}" || true
      
      break
    }
  done
else
  echo -e "${RED}❌ Installation échouée${NC}"
  echo "$INSTALL_RESULT" | head -5
fi
