#!/usr/bin/env python3
"""
UMBRA — Infomaniak Jelastic Cloud Deployment Script
====================================================
Pattern identique à SwissRH (scripts/deploy-jelastic.py).
Execute depuis GitHub Actions (réseau ouvert vers Jelastic).

Usage:
  JELASTIC_TOKEN=xxx GEMINI_API_KEY=xxx python3 scripts/deploy-jelastic.py
"""

import urllib.request
import urllib.parse
import json
import ssl
import sys
import os
import time

# ─── Config ──────────────────────────────────────────────────
JELASTIC_TOKEN = os.environ.get("JELASTIC_TOKEN", "")
JELASTIC_BASE  = "https://3pxsmf7oa31n.infomaniak.jcloud-ver-jpc.ik-server.com"
APP_ID         = "jelastic"
ENV_NAME       = "umbra-prod"
GITHUB_REPO    = "https://github.com/O-N-2950/umbra"
GITHUB_BRANCH  = "main"

# ─── Variables d'environnement UMBRA ─────────────────────────
import secrets as pysecrets
REQUIRED_VARS = {
    "ENVIRONMENT":    "production",
    "APP_NAME":       "UMBRA",
    "APP_VERSION":    "1.0.0",
    "PORT":           "8000",
    "FLAG_FACTURATION": "false",
    "POSTHOG_HOST":   "https://eu.i.posthog.com",
}

SECRET_VARS = ["GEMINI_API_KEY", "RESEND_API_KEY", "STRIPE_SECRET_KEY",
               "SENTRY_DSN", "POSTHOG_API_KEY", "GA4_MEASUREMENT_ID"]

# ─── Helpers ─────────────────────────────────────────────────
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def api(path, params=None):
    p = {"appid": APP_ID, "session": JELASTIC_TOKEN, **(params or {})}
    url = f"{JELASTIC_BASE}/1.0/{path}?{urllib.parse.urlencode(p)}"
    try:
        resp = urllib.request.urlopen(urllib.request.Request(url), timeout=30, context=ctx)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"result": 99, "error": str(e)}

def api_post(path, params=None):
    p = {"appid": APP_ID, "session": JELASTIC_TOKEN, **(params or {})}
    body = urllib.parse.urlencode(p).encode()
    req = urllib.request.Request(
        f"{JELASTIC_BASE}/1.0/{path}", data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=120, context=ctx)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"result": 99, "error": str(e)}

def ok(r, step):
    if r.get("result") == 0:
        print(f"  OK {step}")
        return True
    print(f"  FAIL {step}: {json.dumps(r)[:300]}")
    return False

# ─── Main ────────────────────────────────────────────────────
def main():
    if not JELASTIC_TOKEN:
        print("ERREUR: JELASTIC_TOKEN requis")
        print("  -> manager.infomaniak.com -> Jelastic -> Settings -> API")
        sys.exit(1)

    print("=== UMBRA -> Infomaniak Jelastic Cloud ===")
    print(f"Platform: {JELASTIC_BASE}")
    print(f"Env: {ENV_NAME}")
    print()

    # 1. Vérifier le token
    print("1. Verification token...")
    r = api("users/rest/getinfo")
    if not ok(r, "Token valide"):
        print()
        print("LE TOKEN JELASTIC EST EXPIRE OU INVALIDE.")
        print("Regenerer un token:")
        print("  1. https://manager.infomaniak.com/v3/ng/jelastic/10299")
        print("  2. Dashboard Jelastic -> Settings (icone utilisateur) -> API -> Generate Token")
        print("  3. Mettre a jour le secret GitHub JELASTIC_TOKEN")
        sys.exit(1)
    print(f"   User: {r.get('uid', '?')} | email: {r.get('email', '?')}")

    # 2. Vérifier/créer l'environnement
    print()
    print("2. Verification environnement...")
    r = api("environment/rest/getenvs")
    envs = r.get("envs", [])
    print(f"   Environnements existants: {[e.get('env',{}).get('envName') for e in envs]}")
    env_exists = any(e.get("env", {}).get("envName") == ENV_NAME for e in envs)

    if not env_exists:
        print(f"   Creation de {ENV_NAME} (Docker python + PostgreSQL 16)...")
        topology = {
            "shortdomain": ENV_NAME,
            "region": "default",
            "nodes": [
                {
                    "nodeType": "nodejs",
                    "tag": "22",
                    "count": 1,
                    "fixedCloudlets": 2,
                    "flexibleCloudlets": 12,
                    "nodeGroup": "cp",
                    "displayName": "UMBRA API",
                },
                {
                    "nodeType": "postgresql",
                    "tag": "16",
                    "count": 1,
                    "fixedCloudlets": 2,
                    "flexibleCloudlets": 8,
                    "nodeGroup": "sqldb",
                    "displayName": "UMBRA DB",
                }
            ]
        }
        r = api_post("environment/rest/createenvironment",
                     {"topology": json.dumps(topology)})
        if not ok(r, f"Environnement {ENV_NAME} cree"):
            # Essayer avec topologie docker
            print("   Retry avec node docker python...")
            topology["nodes"][0] = {
                "nodeType": "docker",
                "count": 1,
                "fixedCloudlets": 2,
                "flexibleCloudlets": 12,
                "nodeGroup": "cp",
                "displayName": "UMBRA API",
                "image": "python:3.12-slim",
            }
            r = api_post("environment/rest/createenvironment",
                         {"topology": json.dumps(topology)})
            if not ok(r, f"Environnement {ENV_NAME} cree (docker)"):
                sys.exit(1)
        # Attendre que l'env soit prêt
        print("   Attente demarrage env (60s)...")
        time.sleep(60)
    else:
        print(f"   OK {ENV_NAME} existe deja")

    # 3. Variables d'environnement
    print()
    print("3. Variables d'environnement...")
    
    # Générer JWT_SECRET et ENCRYPTION_KEY si premiers deploy
    all_vars = dict(REQUIRED_VARS)
    all_vars["JWT_SECRET"] = os.environ.get("JWT_SECRET", pysecrets.token_hex(32))
    all_vars["ENCRYPTION_KEY"] = os.environ.get("ENCRYPTION_KEY", pysecrets.token_hex(32))
    
    for k in SECRET_VARS:
        v = os.environ.get(k, "")
        if v:
            all_vars[k] = v

    # AddContainerEnvVars (toutes d'un coup)
    r = api_post("environment/control/rest/addcontainerenvvars", {
        "envName": ENV_NAME,
        "nodeGroup": "cp",
        "vars": json.dumps(all_vars),
    })
    if not ok(r, f"{len(all_vars)} variables posees"):
        # Fallback: une par une avec addenv (vieux endpoint)
        for k, v in all_vars.items():
            r = api_post("environment/rest/addenv", {
                "envName": ENV_NAME, "name": k, "value": v,
            })
            ok(r, f"Var {k}")

    # 4. Déploiement depuis GitHub
    print()
    print("4. Deploiement depuis GitHub...")
    r = api_post("environment/rest/deployscript", {
        "envName": ENV_NAME,
        "repo": GITHUB_REPO,
        "branch": GITHUB_BRANCH,
        "hooks": json.dumps({
            "build": "cd backend && pip install --no-cache-dir -r requirements.txt",
            "run": "cd backend && sh entrypoint.sh"
        })
    })
    if not ok(r, "Deploiement declenche"):
        print("   Tentative via ExecCmd direct sur le node...")
        # Récupérer le nodeId du groupe cp
        r2 = api("environment/rest/getenvinfo", {"envName": ENV_NAME})
        nodes = r2.get("nodes", [])
        cp_node = next((n for n in nodes if n.get("nodeGroup") == "cp"), None)
        if cp_node:
            node_id = cp_node["id"]
            print(f"   Node cp: {node_id}")
            cmd = (
                "cd /home/jelastic && "
                "rm -rf umbra && "
                f"git clone --depth 1 -b {GITHUB_BRANCH} {GITHUB_REPO}.git umbra && "
                "cd umbra/backend && "
                "pip install --no-cache-dir -r requirements.txt 2>&1 | tail -3 && "
                "(pkill -f uvicorn || true) && sleep 2 && "
                "nohup python -m uvicorn umbra_main:app --host 0.0.0.0 --port 8000 --workers 2 "
                "> /tmp/umbra.log 2>&1 & "
                "sleep 8 && curl -sf http://localhost:8000/ping && echo UMBRA_UP"
            )
            r3 = api_post("environment/control/rest/execcmdbyid", {
                "envName": ENV_NAME,
                "nodeId": node_id,
                "commandList": json.dumps([{"command": cmd, "params": ""}])
            })
            ok(r3, "ExecCmd deploy")
            if r3.get("result") == 0:
                for resp in r3.get("responses", []):
                    print(f"   stdout: {resp.get('out','')[-500:]}")

    # 5. Info finale
    print()
    print("5. Verification environnement...")
    r = api("environment/rest/getenvinfo", {"envName": ENV_NAME})
    if r.get("result") == 0:
        env = r.get("env", {})
        domain = env.get("domain", "?")
        print(f"   Domain: {domain}")
        print()
        print("=== DEPLOIEMENT TERMINE ===")
        print(f"URL: https://{domain}")
        print(f"Health: https://{domain}/ping")
    else:
        print(f"   getenvinfo: {json.dumps(r)[:200]}")

if __name__ == "__main__":
    main()
