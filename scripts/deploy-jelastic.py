#!/usr/bin/env python3
"""UMBRA — Jelastic Deploy avec diagnostic complet"""

import urllib.request, urllib.parse, json, ssl, sys, os, time
import secrets as pysecrets

JELASTIC_TOKEN = os.environ.get("JELASTIC_TOKEN", "")
BASE           = "https://app.jpc.infomaniak.com"
APP_ID         = "cluster"
ENV_PREFIX     = "umbra"
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

def list_envs():
    """Liste TOUS les envs avec statut détaillé."""
    r = api("environment/control/rest/getenvs")
    out = []
    if r.get("result") == 0:
        for info in r.get("infos", []):
            env = info.get("env", {})
            out.append({
                "name": env.get("envName", "?"),
                "status": env.get("status", "?"),
                "domain": env.get("domain", "?"),
                "info": info
            })
    return out

def main():
    if not JELASTIC_TOKEN:
        sys.exit("JELASTIC_TOKEN requis")

    print("=== UMBRA -> Jelastic (diagnostic complet) ===")
    print()
    
    # 1. État de TOUS les envs
    print("1. Etat de tous les environnements:")
    envs = list_envs()
    for e in envs:
        print(f"   {e['name']:20} status={e['status']} domain={e['domain']}")
    
    umbra = next((e for e in envs if ENV_PREFIX in e["name"]), None)
    
    # 2. Créer si absent — avec réponse COMPLÈTE loggée
    if not umbra:
        print()
        print("2a. Regions disponibles...")
        r = api("environment/control/rest/getregions")
        region_name = None
        if r.get("result") == 0:
            # La réponse contient array de regions avec uniqueName + domains
            regions = r.get("array", []) or r.get("regions", [])
            for reg in regions:
                uname = reg.get("uniqueName", "?")
                domain = ""
                hgs = reg.get("hardNodeGroups", [])
                for hg in hgs:
                    domain = hg.get("vfsDomain", "") or domain
                is_default = reg.get("isDefault", False)
                print(f"   Region: {uname} | default={is_default} | {domain}")
                if region_name is None or is_default:
                    region_name = uname
        else:
            print(f"   getregions: {json.dumps(r)[:300]}")
        
        if not region_name:
            # Fallback: omettre la region (laisser Jelastic choisir)
            region_name = None
            print("   Aucune region — on omet le parametre")
        else:
            print(f"   Region retenue: {region_name}")
        
        print()
        print("2. Creation umbra-prod...")
        env_def = {"shortdomain": "umbra-prod"}
        if region_name:
            env_def["region"] = region_name
        nodes = [
            {"nodeType": "nodejs", "tag": "22", "count": 1,
             "fixedCloudlets": 2, "flexibleCloudlets": 12, "nodeGroup": "cp"},
            {"nodeType": "postgresql", "tag": "16", "count": 1,
             "fixedCloudlets": 2, "flexibleCloudlets": 8, "nodeGroup": "sqldb"},
        ]
        r = api("environment/control/rest/createenvironment", {
            "env": json.dumps(env_def), "nodes": json.dumps(nodes),
        }, post=True, timeout=300)
        
        # LOG COMPLET de la réponse
        print(f"   REPONSE COMPLETE: {json.dumps(r)[:1500]}")
        
        # Vérifier le result EXTERNE et INTERNE
        inner = r.get("response", {})
        if r.get("result") != 0 or (isinstance(inner, dict) and inner.get("result", 0) != 0):
            err = inner.get("error", "") if isinstance(inner, dict) else ""
            sys.exit(f"Creation echouee: result_ext={r.get('result')} result_int={inner.get('result') if isinstance(inner,dict) else '?'} err={err}")
        
        # La réponse contient peut-être le vrai nom + node passwords
        resp = r.get("response", r)
        env_obj = resp.get("env", {})
        real_name = env_obj.get("envName", "umbra-prod")
        print(f"   Nom retourne: {real_name}")
        
        # Extraire les passwords des nodes si présents
        for n in resp.get("nodes", []):
            print(f"   Node: {n.get('nodeGroup')} id={n.get('id')} pass={'OUI' if n.get('password') else 'non'}")
        
        # 3. Polling jusqu'à ce que l'env apparaisse (max 5 min)
        print()
        print("3. Polling apparition env (max 5 min)...")
        for i in range(10):
            time.sleep(30)
            envs = list_envs()
            names = [e["name"] for e in envs]
            print(f"   [{(i+1)*30}s] envs: {names}")
            umbra = next((e for e in envs if ENV_PREFIX in e["name"]), None)
            if umbra:
                print(f"   TROUVE: {umbra['name']} status={umbra['status']}")
                break
        
        if not umbra:
            print()
            print("L'env n'apparait jamais dans getenvs — la creation async echoue.")
            print("Verifier le dashboard Jelastic: quota cloudlets? region? billing?")
            sys.exit(1)
    else:
        print(f"   -> umbra trouve: {umbra['name']} status={umbra['status']}")
    
    # 4. Attendre que le status soit running (1)
    env_name = umbra["name"]
    for i in range(10):
        if str(umbra["status"]) in ("1", "running"):
            break
        print(f"   Status={umbra['status']}, attente 30s...")
        time.sleep(30)
        envs = list_envs()
        umbra = next((e for e in envs if e["name"] == env_name), umbra)
    
    info = umbra["info"]
    domain = umbra["domain"]
    nodes = info.get("nodes", [])
    cp_node = next((n for n in nodes if n.get("nodeGroup") == "cp"), None)
    db_node = next((n for n in nodes if n.get("nodeGroup") == "sqldb"), None)
    
    print()
    print(f"4. Env pret: {env_name}")
    print(f"   Domain: {domain}")
    print(f"   cp: {cp_node.get('id') if cp_node else '?'} | db: {db_node.get('id') if db_node else '?'}")

    # 5. Variables
    print()
    print("5. Variables...")
    db_ip = db_node.get("intIP", "") if db_node else ""
    env_vars = {
        "ENVIRONMENT": "production", "APP_NAME": "UMBRA", "PORT": "8000",
        "FLAG_FACTURATION": "false", "POSTHOG_HOST": "https://eu.i.posthog.com",
        "JWT_SECRET": pysecrets.token_hex(32),
        "ENCRYPTION_KEY": pysecrets.token_hex(32),
    }
    for k in ["GEMINI_API_KEY", "RESEND_API_KEY", "STRIPE_SECRET_KEY"]:
        v = os.environ.get(k, "")
        if v: env_vars[k] = v
    r = api("environment/control/rest/addcontainerenvvars", {
        "envName": env_name, "nodeGroup": "cp", "vars": json.dumps(env_vars),
    }, post=True)
    print(f"   addvars: result={r.get('result')}")

    # 6. Deploy
    print()
    print("6. Deploy code...")
    if cp_node:
        cmd = (
            "cd /home/jelastic && rm -rf umbra && "
            f"git clone --depth 1 -b {GITHUB_BRANCH} {GITHUB_REPO}.git umbra 2>&1 | tail -1; "
            "cd umbra/backend && python3 --version; "
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

    print()
    print(f"=== https://{domain}/ping ===")

if __name__ == "__main__":
    main()
