#!/usr/bin/env python3
"""
UMBRA — Deploy Jelastic Infomaniak
Alternative Python au script bash (fonctionne sur Windows/Mac/Linux)
Usage: python3 deploy.py
"""

import os, sys, json, urllib.request, urllib.error, getpass, time, webbrowser, subprocess

INFOMANIAK_TOKEN = os.getenv("INFOMANIAK_TOKEN", 
    "uvGxaRxguScs9RMH0_lS_swPKilo3Vc2aex3ATgKiigRMsYB2zP8eOWNuIPN1nMKF3j30b6kthsQry_P")
JELASTIC_SERVICE_ID = "10299"
JPS_URL = "https://raw.githubusercontent.com/O-N-2950/umbra/main/manifest.jps"

def call(method, url, data=None, token=None):
    headers = {"Content-Type": "application/json", "User-Agent": "UMBRA/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        url, 
        data=json.dumps(data).encode() if data else None,
        headers=headers, 
        method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

print("\n🌑 UMBRA — Déploiement Jelastic Infomaniak")
print("=" * 55)

# 1. Vérifier le token
print("\n1. Vérification compte Infomaniak...")
profile = call("GET", "https://api.infomaniak.com/1/profile", token=INFOMANIAK_TOKEN)
if not profile.get("data"):
    print("❌ Token invalide")
    sys.exit(1)
email = profile["data"]["email"]
print(f"✅ Connecté: {email}")

# 2. Collecter les clés
print("\n2. Configuration UMBRA...")
gemini_key = os.getenv("GEMINI_API_KEY") or getpass.getpass("🔑 Clé Gemini (aistudio.google.com/apikey): ")
resend_key  = os.getenv("RESEND_API_KEY")  or getpass.getpass("📧 Clé Resend (resend.com/api-keys): ")
stripe_key  = os.getenv("STRIPE_SECRET_KEY") or input("💳 Clé Stripe (optionnel): ").strip()
env_name    = os.getenv("ENV_NAME", "umbra-prod")
print(f"🌐 Environnement: {env_name}")

# 3. Ouvrir le dashboard Jelastic
jelastic_url = f"https://manager.infomaniak.com/v3/ng/jelastic/{JELASTIC_SERVICE_ID}"
jps_import_url = f"{jelastic_url}?tab=marketplace&action=import&jpsurl={urllib.request.quote(JPS_URL)}"

print("\n3. Ouverture du dashboard Jelastic...")
print("=" * 55)
print(f"\nURL directe d'import JPS:\n{jps_import_url}\n")
print("Remplir le formulaire avec:")
print(f"  - Gemini API Key: {gemini_key[:8]}***")
print(f"  - Resend API Key: {resend_key[:6]}***")
print(f"  - Domaine: {env_name}.jcloud.ik-server.com")
print()

# Ouvrir le navigateur
try:
    webbrowser.open(jps_import_url)
    print("✅ Navigateur ouvert → Marketplace → Import")
except:
    print(f"Ouvrir manuellement: {jelastic_url}")

# 4. Attendre que l'URL réponde
print("\n4. Vérification déploiement...")
app_url = f"https://{env_name}.jcloud.ik-server.com"
print(f"URL cible: {app_url}")
print("En attente (jusqu'à 5 min)...")

for i in range(20):
    time.sleep(15)
    try:
        req = urllib.request.Request(f"{app_url}/ping", method="GET")
        with urllib.request.urlopen(req, timeout=10) as r:
            if r.status == 200:
                d = json.loads(r.read())
                print(f"\n✅ UMBRA UP! → {app_url}")
                print(f"   Réponse: {d}")
                
                # Configurer GitHub variable
                gh_token = os.getenv("GITHUB_TOKEN", "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")
                result = call("PUT",
                    "https://api.github.com/repos/O-N-2950/umbra/actions/variables/JELASTIC_APP_URL",
                    {"name": "JELASTIC_APP_URL", "value": app_url},
                    token=gh_token
                )
                print("✅ GitHub Actions variable JELASTIC_APP_URL configurée")
                break
    except Exception as e:
        print(f"  [{i+1}] En attente... ({e})")
else:
    print("\nTimeout — vérifier le dashboard Jelastic")
    print(f"  → {jelastic_url}")
