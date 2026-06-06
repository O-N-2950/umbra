#!/usr/bin/env python3
"""UMBRA — Jelastic Infomaniak Deploy (final)"""

import urllib.request, urllib.parse, json, ssl, sys, os, time
import secrets as pysecrets

JELASTIC_TOKEN = os.environ.get("JELASTIC_TOKEN", "")
BASE           = "https://app.jpc.infomaniak.com"
APP_ID         = "cluster"
ENV_PREFIX     = "umbra-prod"
GITHUB_REPO    = "https://github.com/O-N-2950/umbra"
GITHUB_BRANCH  = "main"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def api(path, params=None, post=False, timeout=60):
    p = {"appid": APP_ID, "session": JELASTIC_TOKEN, **(params or {})}
    try:
        if post:
            body = urllib.parse.urlencode(p).encode()
            req = urllib.request.Request(f"{BASE}/1.0/{path}", data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"})
        else:
            url = f"{BASE}/1.0/{path}?{urllib.parse.urlencode(p)}"
            req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except:
            return {"result": 99, "http": e.code}
    except Exception as e:
        return {"result": 99, "error": str(e)[:100]}

def ok(r, step):
    if r.get("result") == 0:
        print(f"  OK {step}")
        return True
    print(f"  FAIL {step}: {json.dumps(r)[:250]}")
    return False

def find_env():
    """Trouve l'env umbra par préfixe dans getenvs (nom exact)."""
    r = api("environment/control/rest/getenvs")
    if r.get("result") != 0:
        return None, None
    for info in r.get("infos", []):
        env = info.get("env", {})
        name = env.get("envName", "")
        if name.startswith(ENV_PREFIX) or name.startswith("umbra"):
            return name, info
    return None, None

def main():
    if not JELASTIC_TOKEN:
        print("ERREUR: JELASTIC_TOKEN requis")
        sys.exit(1)

    print("=== UMBRA -> Jelastic Infomaniak ===")
    print()

    # 1. Chercher l'env umbra (créé lors du run précédent)
    print("1. Recherche env umbra...")
    env_name, env_info = find_env()
    
    if not env_name:
        print("   Pas trouve — creation...")
        env_def = {"region": "default", "shortdomain": ENV_PREFIX}
        nodes = [
            {"nodeType": "nodejs", "tag": "22", "count": 1,
             "fixedCloudlets": 2, "flexibleCloudlets": 12, "nodeGroup": "cp"},
            {"nodeType": "postgresql", "tag": "16", "count": 1,
             "fixedCloudlets": 2, "flexibleCloudlets": 8, "nodeGroup": "sqldb"},
        ]
        r = api("environment/control/rest/createenvironment", {
            "env": json.dumps(env_def), "nodes": json.dumps(nodes),
        }, post=True, timeout=300)
        if not ok(r, "Creation"):
            sys.exit(1)
        # La réponse de création contient le nom + les nodes avec passwords
        resp_env = r.get("response", {}).get("env", {}) or r.get("env", {})
        env_name = resp_env.get("envName", ENV_PREFIX)
        print(f"   Cree: {env_name}")
        print("   Attente 90s...")
        time.sleep(90)
        env_name, env_info = find_env()
    
    if not env_name:
        print("ERREUR: env introuvable apres creation")
        sys.exit(1)
    
    print(f"   Env: {env_name}")
    env = env_info.get("env", {})
    domain = env.get("domain", "")
    status = env.get("status", "?")
    print(f"   Domain: {domain} | status: {status}")
    
    nodes = env_info.get("nodes", [])
    cp_node = next((n for n in nodes if n.get("nodeGroup") == "cp"), None)
    db_node = next((n for n in nodes if n.get("nodeGroup") == "sqldb"), None)
    print(f"   Node cp: {cp_node.get('id') if cp_node else '?'}")
    print(f"   Node db: {db_node.get('id') if db_node else '?'} intIP={db_node.get('intIP') if db_node else '?'}")

    # 2. Variables d'environnement
    print()
    print("2. Variables...")
    db_ip = db_node.get("intIP", "127.0.0.1") if db_node else "127.0.0.1"
    
    env_vars = {
        "ENVIRONMENT": "production",
        "APP_NAME": "UMBRA",
        "PORT": "8000",
        "FLAG_FACTURATION": "false",
        "POSTHOG_HOST": "https://eu.i.posthog.com",
        "JWT_SECRET": os.environ.get("JWT_SECRET") or pysecrets.token_hex(32),
        "ENCRYPTION_KEY": os.environ.get("ENCRYPTION_KEY") or pysecrets.token_hex(32),
    }
    for k in ["GEMINI_API_KEY", "RESEND_API_KEY", "STRIPE_SECRET_KEY", "SENTRY_DSN", "POSTHOG_API_KEY"]:
        v = os.environ.get(k, "")
        if v:
            env_vars[k] = v

    r = api("environment/control/rest/addcontainerenvvars", {
        "envName": env_name, "nodeGroup": "cp", "vars": json.dumps(env_vars),
    }, post=True)
    ok(r, f"{len(env_vars)} variables")

    # 3. Setup DB umbra
    print()
    print("3. Base de donnees...")
    if db_node:
        r = api("environment/control/rest/execcmdbyid", {
            "envName": env_name, "nodeId": db_node["id"],
            "commandList": json.dumps([{
                "command": "psql -U webadmin -c \"CREATE DATABASE umbra\" 2>&1 || echo DB_EXISTS",
                "params": ""
            }])
        }, post=True, timeout=60)
        if r.get("result") == 0:
            for resp in r.get("responses", []):
                print(f"   {resp.get('out','')[:150]}")
        else:
            print(f"   createdb: {json.dumps(r)[:150]}")

    # 4. Deploy code
    print()
    print("4. Deploy code UMBRA...")
    if cp_node:
        node_id = cp_node["id"]
        cmd = (
            "cd /home/jelastic && rm -rf umbra && "
            f"git clone --depth 1 -b {GITHUB_BRANCH} {GITHUB_REPO}.git umbra 2>&1 | tail -1; "
            "cd umbra/backend && "
            "(python3 --version || echo NO_PYTHON); "
            "(pip3 --version >/dev/null 2>&1 || (curl -sS https://bootstrap.pypa.io/get-pip.py | python3 - --user 2>&1 | tail -1)); "
            "export PATH=$HOME/.local/bin:$PATH; "
            "pip3 install --user --no-cache-dir -r requirements.txt 2>&1 | tail -2; "
            "(pkill -f uvicorn 2>/dev/null || true); sleep 2; "
            "nohup python3 -m uvicorn umbra_main:app --host 0.0.0.0 --port 8000 --workers 2 "
            "> /tmp/umbra.log 2>&1 & "
            "sleep 15 && (curl -sf http://localhost:8000/ping && echo UMBRA_UP) "
            "|| (echo ---LOGS--- && tail -30 /tmp/umbra.log)"
        )
        r = api("environment/control/rest/execcmdbyid", {
            "envName": env_name, "nodeId": node_id,
            "commandList": json.dumps([{"command": cmd, "params": ""}])
        }, post=True, timeout=400)
        if r.get("result") == 0:
            for resp in r.get("responses", []):
                print(f"   stdout: {resp.get('out','')[-900:]}")
                if resp.get("errOut"):
                    print(f"   stderr: {resp.get('errOut','')[-300:]}")
        else:
            print(f"   ExecCmd: {json.dumps(r)[:250]}")

    # 5. SSL + résultat
    print()
    print("5. Activation SSL integre...")
    r = api("environment/control/rest/editenvsettings", {
        "envName": env_name,
        "settings": json.dumps({"sslstate": True})
    }, post=True)
    ok(r, "SSL")

    print()
    print("=" * 50)
    print(f"UMBRA DEPLOYE: https://{domain}")
    print(f"Health: https://{domain}/ping")
    print("=" * 50)

if __name__ == "__main__":
    main()
