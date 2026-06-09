#!/usr/bin/env python3
"""Diagnostic régions Jelastic Infomaniak + localisation env UMBRA."""
import urllib.request, urllib.parse, json, ssl, os

TOKEN = os.environ.get("JELASTIC_TOKEN", "")
BASE = "https://app.jpc.infomaniak.com"
APP_ID = "cluster"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def api(path, params=None):
    p = {"appid": APP_ID, "session": TOKEN, **(params or {})}
    url = f"{BASE}/1.0/{path}?{urllib.parse.urlencode(p)}"
    try:
        resp = urllib.request.urlopen(urllib.request.Request(url), timeout=30, context=ctx)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"result": 99, "error": str(e)[:150]}

print("=== REGIONS DISPONIBLES (JSON complet) ===")
r = api("environment/control/rest/getregions")
print(json.dumps(r, indent=1)[:4000])

print("\n=== ENV umbra-prod : localisation ===")
r = api("environment/control/rest/getenvs")
for info in r.get("infos", []):
    env = info.get("env", {})
    name = env.get("envName", "")
    if "umbra" in name:
        print(f"Env: {name}")
        print(f"  domain: {env.get('domain')}")
        print(f"  hardwareNodeGroup: {env.get('hardwareNodeGroup')}")
        print(f"  region: {env.get('region')}")
        for n in info.get("nodes", []):
            print(f"  node {n.get('id')}: hnGroup={n.get('hardwareNodeGroup')} host={n.get('host')} dockerName={n.get('nodeType')}")
