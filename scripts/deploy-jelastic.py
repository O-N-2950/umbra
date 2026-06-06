#!/usr/bin/env python3
"""
UMBRA — Jelastic Infomaniak Deploy
appid=cluster + paths environment/control/rest/* (API Virtuozzo correcte)
"""

import urllib.request, urllib.parse, json, ssl, sys, os, time
import secrets as pysecrets

JELASTIC_TOKEN = os.environ.get("JELASTIC_TOKEN", "")
BASE           = "https://app.jpc.infomaniak.com"
APP_ID         = "cluster"
ENV_NAME       = "umbra-prod"
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

def main():
    if not JELASTIC_TOKEN:
        print("ERREUR: JELASTIC_TOKEN requis")
        sys.exit(1)

    print("=== UMBRA -> Jelastic Infomaniak ===")
    print(f"Endpoint: {BASE} appid={APP_ID}")
    print()

    # 1. Lister les environnements (le vrai path API)
    print("1. Environnements existants...")
    r = api("environment/control/rest/getenvs")
    if r.get("result") != 0:
        # Diagnostiquer les variantes de path
        print(f"   getenvs: {json.dumps(r)[:200]}")
        for path in [
            "environment/control/rest/getenvs",
            "env/control/rest/getenvs",
            "environment/environment/rest/getenvs",
        ]:
            r2 = api(path)
            print(f"   {path}: result={r2.get('result')} {str(r2.get('error',''))[:80]}")
            if r2.get("result") == 0:
                r = r2
                break
    
    if r.get("result") != 0:
        print()
        print("Le token est reconnu mais n'a pas acces a environment.Control")
        print("-> Regenerer un token avec TOUTES les permissions:")
        print("   Dashboard Jelastic -> avatar -> Settings -> Access Tokens")
        print("   -> Add -> Scope: All -> Generate")
        sys.exit(1)
    
    envs = r.get("infos", [])
    names = [e.get("env", {}).get("envName") for e in envs]
    print(f"   Envs existants: {names}")
    env_exists = ENV_NAME in names

    # 2. Créer l'environnement si besoin
    if not env_exists:
        print(f"\n2. Creation {ENV_NAME} (nodejs22 + postgres16)...")
        env_def = {
            "region": "default",
            "shortdomain": ENV_NAME,
        }
        nodes = [
            {"nodeType": "nodejs", "tag": "22", "count": 1,
             "fixedCloudlets": 2, "flexibleCloudlets": 12, "nodeGroup": "cp"},
            {"nodeType": "postgresql", "tag": "16", "count": 1,
             "fixedCloudlets": 2, "flexibleCloudlets": 8, "nodeGroup": "sqldb"},
        ]
        r = api("environment/control/rest/createenvironment", {
            "env": json.dumps(env_def),
            "nodes": json.dumps(nodes),
        }, post=True, timeout=300)
        if not ok(r, f"Creation {ENV_NAME}"):
            sys.exit(1)
        print("   Attente demarrage 90s...")
        time.sleep(90)
    else:
        print(f"   OK {ENV_NAME} existe deja")

    # 3. Infos env
    print("\n3. Infos environnement...")
    r = api("environment/control/rest/getenvinfo", {"envName": ENV_NAME})
    if not ok(r, "getenvinfo"):
        sys.exit(1)
    nodes = r.get("nodes", [])
    env_info = r.get("env", {})
    domain = env_info.get("domain", f"{ENV_NAME}.jcloud.ik-server.com")
    cp_node = next((n for n in nodes if n.get("nodeGroup") == "cp"), None)
    db_node = next((n for n in nodes if n.get("nodeGroup") == "sqldb"), None)
    print(f"   Domain: {domain}")
    print(f"   Node cp: {cp_node.get('id') if cp_node else '?'}")
    print(f"   Node db: {db_node.get('id') if db_node else '?'} intIP={db_node.get('intIP') if db_node else '?'}")
    
    # Mot de passe DB depuis la creation (si fourni)
    db_password = ""
    for n in nodes:
        if n.get("nodeGroup") == "sqldb":
            db_password = n.get("password", "")

    # 4. Variables d'environnement
    print("\n4. Variables d'environnement...")
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
    if db_password:
        env_vars["DATABASE_URL"] = f"postgresql://webadmin:{db_password}@{db_ip}:5432/umbra"
    
    for k in ["GEMINI_API_KEY", "RESEND_API_KEY", "STRIPE_SECRET_KEY", "SENTRY_DSN", "POSTHOG_API_KEY"]:
        v = os.environ.get(k, "")
        if v:
            env_vars[k] = v

    r = api("environment/control/rest/addcontainerenvvars", {
        "envName": ENV_NAME, "nodeGroup": "cp", "vars": json.dumps(env_vars),
    }, post=True)
    ok(r, f"{len(env_vars)} variables posees")

    # 5. Deploy code via ExecCmd
    print("\n5. Deploy code (clone + install + run)...")
    if cp_node:
        node_id = cp_node["id"]
        cmd = (
            "cd /home/jelastic && rm -rf umbra && "
            f"git clone --depth 1 -b {GITHUB_BRANCH} {GITHUB_REPO}.git umbra 2>&1 | tail -1 && "
            "cd umbra/backend && "
            "which python3 && python3 --version; "
            "pip3 install --no-cache-dir -r requirements.txt 2>&1 | tail -2 && "
            "(pkill -f uvicorn 2>/dev/null || true) && sleep 2 && "
            "nohup python3 -m uvicorn umbra_main:app --host 0.0.0.0 --port 8000 --workers 2 "
            "> /tmp/umbra.log 2>&1 & "
            "sleep 12 && (curl -sf http://localhost:8000/ping && echo \" UMBRA_UP\") "
            "|| (echo LOGS: && tail -25 /tmp/umbra.log)"
        )
        r = api("environment/control/rest/execcmdbyid", {
            "envName": ENV_NAME, "nodeId": node_id,
            "commandList": json.dumps([{"command": cmd, "params": ""}])
        }, post=True, timeout=300)
        if r.get("result") == 0:
            for resp in r.get("responses", []):
                out = resp.get("out", "")
                err = resp.get("errOut", "")
                print(f"   stdout: {out[-700:]}")
                if err:
                    print(f"   stderr: {err[-300:]}")
        else:
            print(f"   ExecCmd: {json.dumps(r)[:300]}")

    print()
    print(f"=== https://{domain}/ping ===")

if __name__ == "__main__":
    main()
