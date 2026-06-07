#!/usr/bin/env python3
"""UMBRA — Jelastic Deploy — création env (région auto-détectée)"""

import urllib.request, urllib.parse, json, ssl, sys, os, time
import secrets as pysecrets

JELASTIC_TOKEN = os.environ.get("JELASTIC_TOKEN", "")
BASE           = "https://app.jpc.infomaniak.com"
APP_ID         = "cluster"
GITHUB_REPO    = "https://github.com/O-N-2950/umbra"
GITHUB_BRANCH  = "main"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

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
    """Vérifie result externe ET interne."""
    if r.get("result") != 0:
        return False, r.get("error", json.dumps(r)[:150])
    inner = r.get("response", {})
    if isinstance(inner, dict) and inner.get("result", 0) != 0:
        return False, inner.get("error", json.dumps(inner)[:150])
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

def try_create(env_def, nodes):
    r = api("environment/control/rest/createenvironment", {
        "env": json.dumps(env_def), "nodes": json.dumps(nodes),
    }, post=True, timeout=300)
    success, err = inner_ok(r)
    return success, err, r

def main():
    if not JELASTIC_TOKEN:
        sys.exit("JELASTIC_TOKEN requis")

    print("=== UMBRA -> Jelastic ===")
    
    # 1. Env existant ?
    envs = list_envs()
    umbra = next((e for e in envs if "umbra" in e["name"]), None)
    
    if not umbra:
        # 2. Log COMPLET de getregions pour comprendre la structure
        print("\n2. Structure getregions (JSON complet):")
        r = api("environment/control/rest/getregions")
        print(json.dumps(r)[:3000])
        
        # Extraire les hardNodeGroups uniqueName
        hng_names = []
        for reg in (r.get("array", []) or []):
            for hng in reg.get("hardNodeGroups", []):
                un = hng.get("uniqueName", "")
                if un:
                    hng_names.append(un)
        print(f"\n   hardNodeGroups: {hng_names}")
        
        nodes = [
            {"nodeType": "nodejs", "tag": "22", "count": 1,
             "fixedCloudlets": 2, "flexibleCloudlets": 12, "nodeGroup": "cp"},
            {"nodeType": "postgresql", "tag": "16", "count": 1,
             "fixedCloudlets": 2, "flexibleCloudlets": 8, "nodeGroup": "sqldb"},
        ]
        
        # 3. Tentatives de création dans l'ordre:
        # a) sans region, b) avec chaque hardNodeGroup, c) avec hostGroup
        attempts = [("sans region", {"shortdomain": "umbra-prod"})]
        for hn in hng_names:
            attempts.append((f"region={hn}", {"shortdomain": "umbra-prod", "region": hn}))
            attempts.append((f"hostGroup={hn}", {"shortdomain": "umbra-prod", "hostGroup": hn}))
        
        created = False
        for label, env_def in attempts:
            print(f"\n3. Tentative creation ({label})...")
            success, err, full = try_create(env_def, nodes)
            if success:
                print(f"   OK — creation lancee ({label})")
                created = True
                break
            else:
                print(f"   ECHEC: {err[:200]}")
        
        if not created:
            sys.exit("\nToutes les tentatives ont echoue")
        
        # 4. Polling
        print("\n4. Polling (max 5 min)...")
        for i in range(10):
            time.sleep(30)
            envs = list_envs()
            umbra = next((e for e in envs if "umbra" in e["name"]), None)
            status = umbra["status"] if umbra else "absent"
            print(f"   [{(i+1)*30}s] umbra: {status}")
            if umbra and str(umbra["status"]) == "1":
                break
        
        if not umbra:
            sys.exit("Env jamais apparu")
    
    env_name = umbra["name"]
    domain = umbra["domain"]
    info = umbra["info"]
    nodes_list = info.get("nodes", [])
    cp_node = next((n for n in nodes_list if n.get("nodeGroup") == "cp"), None)
    db_node = next((n for n in nodes_list if n.get("nodeGroup") == "sqldb"), None)
    
    print(f"\n5. Env: {env_name} | domain: {domain} | status: {umbra['status']}")
    print(f"   cp={cp_node.get('id') if cp_node else '?'} db={db_node.get('id') if db_node else '?'}")

    # 6. Variables
    print("\n6. Variables...")
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

    # 7. Deploy code
    print("\n7. Deploy code...")
    if cp_node:
        cmd = (
            "cd /home/jelastic && rm -rf umbra && "
            f"git clone --depth 1 -b {GITHUB_BRANCH} {GITHUB_REPO}.git umbra 2>&1 | tail -1; "
            "cd umbra/backend && (python3 --version 2>&1); "
            "pip3 install --user --no-cache-dir -r requirements.txt 2>&1 | tail -2; "
            "export PATH=$HOME/.local/bin:$PATH; "
            "(pkill -f uvicorn 2>/dev/null || true); sleep 2; "
            "nohup python3 -m uvicorn umbra_main:app --host 0.0.0.0 --port 8000 --workers 2 "
            "> /tmp/umbra.log 2>&1 & "
            "sleep 15 && (curl -sf http://localhost:8000/ping && echo UMBRA_UP) "
            "|| (echo ---LOGS--- && tail -30 /tmp/umbra.log)"
        )
        r = api("environment/control/rest/execcmdbyid", {
            "envName": env_name, "nodeId": cp_node["id"],
            "commandList": json.dumps([{"command": cmd, "params": ""}])
        }, post=True, timeout=400)
        if r.get("result") == 0:
            for resp in r.get("responses", []):
                print(f"   {resp.get('out','')[-900:]}")
        else:
            print(f"   ExecCmd: {json.dumps(r)[:250]}")

    print(f"\n=== https://{domain}/ping ===")

if __name__ == "__main__":
    main()
