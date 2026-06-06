#!/usr/bin/env python3
"""
UMBRA — Jelastic Infomaniak Deploy (multi-endpoint + diagnostic)
Pattern SwissRH/PLACIO. Execute depuis GitHub Actions.
"""

import urllib.request, urllib.parse, json, ssl, sys, os, time
import secrets as pysecrets

JELASTIC_TOKEN = os.environ.get("JELASTIC_TOKEN", "")
ENV_NAME       = "umbra-prod"
GITHUB_REPO    = "https://github.com/O-N-2950/umbra"
GITHUB_BRANCH  = "main"

# Endpoints candidats (PLACIO utilisait app.jpc, SwissRH utilisait 3pxsmf7oa31n)
ENDPOINTS = [
    ("https://app.jpc.infomaniak.com", "jelastic"),
    ("https://app.jpc.infomaniak.com", "3pxsmf7oa31n"),
    ("https://3pxsmf7oa31n.infomaniak.jcloud-ver-jpc.ik-server.com", "jelastic"),
    ("https://3pxsmf7oa31n.infomaniak.jcloud-ver-jpc.ik-server.com", "3pxsmf7oa31n"),
    ("https://jca.infomaniak.com", "jelastic"),
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE = None
APP_ID = None

def raw_call(base, appid, path, params=None, post=False):
    p = {"appid": appid, "session": JELASTIC_TOKEN, **(params or {})}
    try:
        if post:
            body = urllib.parse.urlencode(p).encode()
            req = urllib.request.Request(f"{base}/1.0/{path}", data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"})
        else:
            url = f"{base}/1.0/{path}?{urllib.parse.urlencode(p)}"
            req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=20, context=ctx)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except:
            return {"result": 99, "http": e.code}
    except Exception as e:
        return {"result": 99, "error": str(e)[:80]}

def api(path, params=None):
    return raw_call(BASE, APP_ID, path, params)

def api_post(path, params=None):
    return raw_call(BASE, APP_ID, path, params, post=True)

def ok(r, step):
    if r.get("result") == 0:
        print(f"  OK {step}")
        return True
    print(f"  FAIL {step}: {json.dumps(r)[:250]}")
    return False

def main():
    global BASE, APP_ID
    
    if not JELASTIC_TOKEN:
        print("ERREUR: JELASTIC_TOKEN requis")
        sys.exit(1)

    print("=== UMBRA -> Jelastic Infomaniak ===")
    print()
    print("0. Diagnostic endpoints...")
    
    for base, appid in ENDPOINTS:
        r = raw_call(base, appid, "users/rest/getinfo")
        result = r.get("result", "?")
        status = "VALIDE" if result == 0 else f"result={result} {r.get('error', r.get('http',''))}"
        print(f"   {base} (appid={appid}): {status}")
        if result == 0:
            BASE, APP_ID = base, appid
            print(f"   >>> ENDPOINT RETENU: {BASE} appid={APP_ID}")
            print(f"   User: {r.get('email', r.get('uid', '?'))}")
            break
    
    if not BASE:
        print()
        print("=" * 60)
        print("AUCUN ENDPOINT NE VALIDE LE TOKEN — TOKEN EXPIRE")
        print("=" * 60)
        print()
        print("Pour regenerer le token Jelastic (2 min):")
        print("  1. Ouvrir https://manager.infomaniak.com/v3/ng/jelastic/10299")
        print("     (clic sur ton produit Jelastic Cloud)")
        print("  2. Dans le dashboard Jelastic: clic sur ton avatar (haut droite)")
        print("     -> Settings -> Access Tokens -> Add Access Token")
        print("     -> Cocher toutes les permissions -> Generate")
        print("  3. Copier le token et mettre a jour:")
        print("     - Le fichier projet Claude 'token_full_access_JELASTIC_CLOUD_INFOMANIAK'")
        print("     - Le secret GitHub: gh secret set JELASTIC_TOKEN")
        print()
        sys.exit(1)

    # 2. Environnements
    print()
    print("2. Environnements existants...")
    r = api("environment/rest/getenvs")
    envs = r.get("envs", []) or r.get("infos", [])
    names = [e.get("env", {}).get("envName") for e in envs]
    print(f"   Envs: {names}")
    env_exists = ENV_NAME in names

    if not env_exists:
        print(f"   Creation {ENV_NAME}...")
        topology = {
            "shortdomain": ENV_NAME,
            "region": "default",
            "nodes": [
                {"nodeType": "nodejs", "tag": "22", "count": 1,
                 "fixedCloudlets": 2, "flexibleCloudlets": 12, "nodeGroup": "cp"},
                {"nodeType": "postgresql", "tag": "16", "count": 1,
                 "fixedCloudlets": 2, "flexibleCloudlets": 8, "nodeGroup": "sqldb"},
            ]
        }
        r = api_post("environment/rest/createenvironment", {"topology": json.dumps(topology)})
        if not ok(r, f"Env {ENV_NAME} cree"):
            sys.exit(1)
        print("   Attente 60s...")
        time.sleep(60)
    else:
        print(f"   OK {ENV_NAME} existe")

    # 3. Récupérer le node cp + infos DB
    print()
    print("3. Infos environnement...")
    r = api("environment/rest/getenvinfo", {"envName": ENV_NAME})
    nodes = r.get("nodes", [])
    cp_node = next((n for n in nodes if n.get("nodeGroup") == "cp"), None)
    db_node = next((n for n in nodes if n.get("nodeGroup") == "sqldb"), None)
    domain = r.get("env", {}).get("domain", f"{ENV_NAME}.jcloud.ik-server.com")
    print(f"   Domain: {domain}")
    print(f"   Node cp: {cp_node.get('id') if cp_node else '?'}")
    print(f"   Node db: {db_node.get('id') if db_node else '?'} ip={db_node.get('intIP') if db_node else '?'}")

    # 4. Variables d'environnement
    print()
    print("4. Variables...")
    db_ip = db_node.get("intIP", "127.0.0.1") if db_node else "127.0.0.1"
    env_vars = {
        "ENVIRONMENT": "production",
        "APP_NAME": "UMBRA",
        "PORT": "8000",
        "FLAG_FACTURATION": "false",
        "POSTHOG_HOST": "https://eu.i.posthog.com",
        "JWT_SECRET": os.environ.get("JWT_SECRET", pysecrets.token_hex(32)),
        "ENCRYPTION_KEY": os.environ.get("ENCRYPTION_KEY", pysecrets.token_hex(32)),
        "DATABASE_URL": f"postgresql://webadmin@{db_ip}:5432/umbra",
    }
    for k in ["GEMINI_API_KEY", "RESEND_API_KEY", "STRIPE_SECRET_KEY", "SENTRY_DSN", "POSTHOG_API_KEY"]:
        v = os.environ.get(k, "")
        if v:
            env_vars[k] = v
    
    r = api_post("environment/control/rest/addcontainerenvvars", {
        "envName": ENV_NAME, "nodeGroup": "cp", "vars": json.dumps(env_vars),
    })
    ok(r, f"{len(env_vars)} variables")

    # 5. Deploy via ExecCmd (pattern PLACIO: clone + install + run)
    print()
    print("5. Deploy code...")
    if cp_node:
        node_id = cp_node["id"]
        cmd = (
            "cd /home/jelastic && rm -rf umbra && "
            f"git clone --depth 1 -b {GITHUB_BRANCH} {GITHUB_REPO}.git umbra 2>&1 | tail -2 && "
            "cd umbra/backend && "
            "(command -v python3 || sudo apt-get install -y python3 python3-pip) >/dev/null 2>&1; "
            "pip3 install --no-cache-dir -r requirements.txt 2>&1 | tail -2 && "
            "(pkill -f uvicorn || true) && sleep 2 && "
            "nohup python3 -m uvicorn umbra_main:app --host 0.0.0.0 --port 8000 --workers 2 "
            "> /tmp/umbra.log 2>&1 & "
            "sleep 10 && curl -sf http://localhost:8000/ping && echo UMBRA_UP || tail -20 /tmp/umbra.log"
        )
        r = api_post("environment/control/rest/execcmdbyid", {
            "envName": ENV_NAME, "nodeId": node_id,
            "commandList": json.dumps([{"command": cmd, "params": ""}])
        })
        if r.get("result") == 0:
            for resp in r.get("responses", []):
                print(f"   {resp.get('out','')[-600:]}")
        else:
            print(f"   ExecCmd: {json.dumps(r)[:250]}")

    print()
    print(f"=== TERMINE — https://{domain}/ping ===")

if __name__ == "__main__":
    main()
