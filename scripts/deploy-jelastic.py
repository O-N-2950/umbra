#!/usr/bin/env python3
"""UMBRA — Jelastic Deploy v2 : node Docker python:3.12-slim"""

import urllib.request, urllib.parse, json, ssl, sys, os, time
import secrets as pysecrets

JELASTIC_TOKEN = os.environ.get("JELASTIC_TOKEN", "")
BASE           = "https://app.jpc.infomaniak.com"
APP_ID         = "cluster"
GITHUB_REPO    = "https://github.com/O-N-2950/umbra"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

DOCKER_CMD = (
    "bash -c \'"
    "apt-get update -qq 2>/dev/null; apt-get install -y -qq git curl 2>/dev/null; "
    "rm -rf /app/umbra; "
    "git clone --depth 1 -b main https://github.com/O-N-2950/umbra.git /app/umbra && "
    "cd /app/umbra/backend && "
    "pip install --no-cache-dir -r requirements.txt && "
    "exec python -m uvicorn umbra_main:app --host 0.0.0.0 --port 8000 --workers 2"
    "\'"
)

def api(path, params=None, post=False, timeout=120):
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

def inner_ok(r):
    if r.get("result") != 0:
        return False, str(r.get("error", json.dumps(r)[:150]))
    inner = r.get("response", {})
    if isinstance(inner, dict) and inner.get("result", 0) != 0:
        return False, str(inner.get("error", json.dumps(inner)[:150]))
    return True, ""

def list_envs():
    r = api("environment/control/rest/getenvs")
    out = []
    if r.get("result") == 0:
        for info in r.get("infos", []):
            env = info.get("env", {})
            out.append({"name": env.get("envName", "?"), "status": env.get("status", "?"),
                        "domain": env.get("domain", "?"), "info": info})
    return out

def main():
    if not JELASTIC_TOKEN:
        sys.exit("JELASTIC_TOKEN requis")

    print("=== UMBRA -> Jelastic v2 (Docker python:3.12) ===")
    
    envs = list_envs()
    umbra = next((e for e in envs if "umbra" in e["name"]), None)
    
    # 1. Si l'env existe avec un node nodejs → le détruire (Python 3.9 incompatible)
    if umbra:
        info = umbra["info"]
        nodes_list = info.get("nodes", [])
        cp = next((n for n in nodes_list if n.get("nodeGroup") == "cp"), {})
        node_type = cp.get("nodeType", "")
        print(f"1. Env existant: {umbra['name']} | cp nodeType={node_type}")
        
        if node_type != "docker":
            print(f"   Node {node_type} (Python systeme) — install pip + run en place")
            # Pas de suppression (deleteenv exige password compte) — on utilise le node tel quel
    
    # 2. Créer avec node docker python:3.12-slim
    if not umbra:
        print()
        print("2. Creation umbra-prod (docker python:3.12-slim + postgres16)...")
        env_def = {"shortdomain": "umbra-prod", "sslstate": True}
        nodes = [
            {
                "nodeType": "docker",
                "count": 1,
                "fixedCloudlets": 3,
                "flexibleCloudlets": 16,
                "nodeGroup": "cp",
                "displayName": "UMBRA API",
                "image": "python:3.12-slim",
                "cmd": DOCKER_CMD,
                "env": {"PORT": "8000"},
            },
            {
                "nodeType": "postgresql",
                "tag": "16",
                "count": 1,
                "fixedCloudlets": 2,
                "flexibleCloudlets": 8,
                "nodeGroup": "sqldb",
                "displayName": "UMBRA DB",
            },
        ]
        r = api("environment/control/rest/createenvironment", {
            "env": json.dumps(env_def), "nodes": json.dumps(nodes),
        }, post=True, timeout=300)
        s, e = inner_ok(r)
        if not s:
            print(f"   ECHEC docker: {e[:300]}")
            print(f"   REPONSE: {json.dumps(r)[:800]}")
            sys.exit(1)
        print("   OK creation lancee (l'image se telecharge + build ~3-5 min)")
        
        # 3. Polling
        print()
        print("3. Polling (max 7 min)...")
        for i in range(14):
            time.sleep(30)
            envs = list_envs()
            umbra = next((e for e in envs if "umbra" in e["name"]), None)
            status = umbra["status"] if umbra else "absent"
            print(f"   [{(i+1)*30}s] umbra: status={status}")
            if umbra and str(umbra["status"]) == "1":
                break
        
        if not umbra or str(umbra["status"]) != "1":
            sys.exit("Env pas running apres 7 min — verifier dashboard")
    
    env_name = umbra["name"]
    domain = umbra["domain"]
    info = umbra["info"]
    nodes_list = info.get("nodes", [])
    cp_node = next((n for n in nodes_list if n.get("nodeGroup") == "cp"), None)
    db_node = next((n for n in nodes_list if n.get("nodeGroup") == "sqldb"), None)
    
    print()
    print(f"4. Env: {env_name} | https://{domain}")
    print(f"   cp={cp_node.get('id') if cp_node else '?'} ({cp_node.get('nodeType','?') if cp_node else ''})")
    print(f"   db={db_node.get('id') if db_node else '?'} intIP={db_node.get('intIP','?') if db_node else ''}")

    # 5. Variables d'environnement (avant le démarrage final)
    print()
    print("5. Variables...")
    env_vars = {
        "ENVIRONMENT": "production", "APP_NAME": "UMBRA", "PORT": "8000",
        "FLAG_FACTURATION": "false", "POSTHOG_HOST": "https://eu.i.posthog.com",
        "JWT_SECRET": pysecrets.token_hex(32),
        "ENCRYPTION_KEY": pysecrets.token_hex(32),
    }
    if db_node and db_node.get("intIP"):
        env_vars["DATABASE_URL"] = f"postgresql://webadmin@{db_node['intIP']}:5432/umbra"
    for k in ["GEMINI_API_KEY", "RESEND_API_KEY", "STRIPE_SECRET_KEY"]:
        v = os.environ.get(k, "")
        if v: env_vars[k] = v
    r = api("environment/control/rest/addcontainerenvvars", {
        "envName": env_name, "nodeGroup": "cp", "vars": json.dumps(env_vars),
    }, post=True)
    s, e = inner_ok(r)
    print(f"   vars: {'OK' if s else e[:150]}")
    
    # 6. Déploiement du code via ExecCmd (clone + pip + uvicorn)
    print()
    print("6. Deploiement code (clone + ensurepip + uvicorn)...")
    if cp_node:
        node_id = cp_node["id"]
        deploy_cmd = (
            "cd /home/jelastic 2>/dev/null || cd /home; "
            "rm -rf umbra; "
            "git clone --depth 1 -b main https://github.com/O-N-2950/umbra.git umbra 2>&1 | tail -1; "
            "cd umbra/backend; "
            "echo PYVER: $(python3 --version 2>&1); "
            # Installer pip (node nodejs = Python systeme sans pip)
            "python3 -m pip --version 2>/dev/null || python3 -m ensurepip --upgrade 2>&1 | tail -1; "
            "export PATH=$HOME/.local/bin:$PATH; "
            "python3 -m pip install --user --no-cache-dir -q -r requirements.txt 2>&1 | tail -4; "
            # Verifier que le code se compile en Python 3.9 (detecte SyntaxError 3.10+)
            "echo SYNTAX_CHECK:; python3 -c \\"import py_compile,glob,sys; [py_compile.compile(f,doraise=True) for f in glob.glob('**/*.py',recursive=True)]\\" 2>&1 | tail -5 && echo SYNTAX_OK; "
            "(pkill -f uvicorn 2>/dev/null || true); sleep 2; "
            "nohup python3 -m uvicorn umbra_main:app --host 0.0.0.0 --port 8000 --workers 2 > /tmp/umbra.log 2>&1 & "
            "sleep 20; "
            "(curl -sf http://localhost:8000/ping && echo ___UMBRA_UP___) || (echo ___FAIL_LOGS___; tail -40 /tmp/umbra.log)"
        )
        r = api("environment/control/rest/execcmdbyid", {
            "envName": env_name, "nodeId": node_id,
            "commandList": json.dumps([{"command": deploy_cmd, "params": ""}])
        }, post=True, timeout=420)
        if r.get("result") == 0:
            for resp in r.get("responses", []):
                out = resp.get("out", "")
                print("   --- sortie node ---")
                for ln in out.split("\n"):
                    if ln.strip():
                        print(f"   {ln[:200]}")
        else:
            print(f"   ExecCmd erreur: {json.dumps(r)[:300]}")

    # 7. Vérifier que l'app répond publiquement
    print()
    print("7. Verification publique...")
    app_up = False
    for i in range(8):
        time.sleep(20)
        try:
            req = urllib.request.Request(f"https://{domain}/ping")
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                if resp.status == 200:
                    print(f"   [{(i+1)*20}s] PING OK — UMBRA EN LIGNE")
                    app_up = True
                    break
        except Exception as ex:
            print(f"   [{(i+1)*20}s] {str(ex)[:50]}")
    
    print()
    print("=" * 55)
    if app_up:
        print(f"UMBRA DEPLOYE SUR JELASTIC INFOMANIAK (SUISSE)")
    else:
        print("Env cree — app pas encore up (pip install peut durer)")
    print(f"URL:    https://{domain}")
    print(f"Health: https://{domain}/ping")
    print(f"App:    https://{domain}/app")
    print("=" * 55)

if __name__ == "__main__":
    main()
