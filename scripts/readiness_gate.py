#!/usr/bin/env python3
"""
scripts/readiness_gate.py — Gate GO/NO-GO avant mise en production de Merito (pattern soluris).

Vérifie, SANS rien modifier :
  1. claims       — scripts/check_claims.py (exit 0)
  2. ping         — GET {base}/ping == 200
  3. health       — GET {base}/health == 200 & status=healthy
  4. health_deep  — GET {base}/health/deep : critical ⇒ NO-GO ; degraded ⇒ WARN
  5. home         — GET {base}/ contient « Merito » (front vivant)
  6. register_dry — OPTIONS/schema de /api/v1/auth/register accessible (API vivante)

Usage :
  python3 scripts/readiness_gate.py https://merito-prod.jcloud-ver-jpc.ik-server.com
  python3 scripts/readiness_gate.py https://merito.ch --json

Exit 0 = GO · exit 1 = NO-GO (≥1 check bloquant KO).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BLOCKING = {"claims", "ping", "health", "health_deep_critical", "home"}


def http(url: str, timeout: int = 12):
    req = urllib.request.Request(url, headers={"User-Agent": "merito-readiness-gate"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), round((time.perf_counter() - t0) * 1000)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), round((time.perf_counter() - t0) * 1000)
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}", round((time.perf_counter() - t0) * 1000)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    base = sys.argv[1].rstrip("/")
    as_json = "--json" in sys.argv
    results, failures, warns = {}, [], []

    # 1. claims
    p = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_claims.py")],
                       capture_output=True, text=True)
    results["claims"] = {"ok": p.returncode == 0,
                         "detail": (p.stdout or p.stderr).strip().splitlines()[:3]}
    if p.returncode != 0:
        failures.append("claims")

    # 2. ping
    code, _, ms = http(f"{base}/ping")
    results["ping"] = {"ok": code == 200, "http": code, "ms": ms}
    if code != 200:
        failures.append("ping")

    # 3. health
    code, body, ms = http(f"{base}/health")
    healthy = False
    try:
        healthy = code == 200 and json.loads(body).get("status") == "healthy"
    except Exception:  # noqa: BLE001
        pass
    results["health"] = {"ok": healthy, "http": code, "ms": ms}
    if not healthy:
        failures.append("health")

    # 4. health deep
    code, body, ms = http(f"{base}/health/deep")
    deep_status, deep_checks = "unknown", {}
    try:
        d = json.loads(body)
        deep_status = d.get("status", "unknown")
        deep_checks = {k: v.get("status") for k, v in d.get("checks", {}).items()}
    except Exception:  # noqa: BLE001
        pass
    results["health_deep"] = {"ok": deep_status == "healthy", "status": deep_status,
                              "http": code, "ms": ms, "checks": deep_checks}
    if deep_status in ("critical", "unknown"):
        failures.append("health_deep_critical")
    elif deep_status == "degraded":
        warns.append("health_deep degraded: " + ", ".join(k for k, v in deep_checks.items() if v != "ok"))

    # 5. home
    code, body, ms = http(f"{base}/")
    home_ok = code == 200 and "erito" in body  # Merito / merito
    results["home"] = {"ok": home_ok, "http": code, "ms": ms}
    if not home_ok:
        failures.append("home")

    # 6. API vivante (schéma register présent dans l'OpenAPI)
    code, body, ms = http(f"{base}/openapi.json")
    api_ok = code == 200 and "/api/v1/auth/register" in body
    results["register_dry"] = {"ok": api_ok, "http": code, "ms": ms}
    if not api_ok:
        warns.append("openapi/register introuvable")

    go = not failures
    if as_json:
        print(json.dumps({"go": go, "failures": failures, "warnings": warns,
                          "results": results}, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'═' * 52}\n  READINESS GATE — {base}\n{'═' * 52}")
        for name, r in results.items():
            flag = "✅" if r.get("ok") else ("🟨" if name not in BLOCKING and name != "health_deep" else "❌")
            extra = f"  http={r.get('http')} {r.get('ms')}ms" if "http" in r else ""
            print(f"  {flag} {name:<14}{extra}")
            if name == "health_deep" and r.get("checks"):
                for k, v in r["checks"].items():
                    print(f"        · {k}: {v}")
        for w in warns:
            print(f"  ⚠️  {w}")
        print(f"{'─' * 52}\n  {'🟢 GO' if go else '🔴 NO-GO — ' + ', '.join(failures)}\n")
    sys.exit(0 if go else 1)


if __name__ == "__main__":
    main()
