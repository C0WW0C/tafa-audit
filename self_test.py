#!/usr/bin/env python3
"""TAFA V10 quick self-test (health + 1 cycle + API)."""
from __future__ import annotations
import json, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    results = []
    def check(name, cond, detail=""):
        results.append(cond)
        print(("PASS" if cond else "FAIL"), name, detail)

    r = subprocess.run([sys.executable, str(ROOT / "health_v10.py")], cwd=str(ROOT))
    check("health_v10", r.returncode == 0)

    sys.path.insert(0, str(ROOT))
    from core.engine_v10 import TAFAEngineV10
    from core import status_bridge
    e = TAFAEngineV10()
    e.start()
    e.run_cycle()
    st = e.status()
    check("price", st.get("last_price") is not None, str(st.get("last_price")))
    check("signal", st.get("last_signal") is not None, str(st.get("last_signal")))
    status_bridge.publish({**st, "running": True})
    e.stop()

    p = subprocess.Popen([sys.executable, str(ROOT / "web" / "server.py")], cwd=str(ROOT),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.2)
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/api/status", timeout=3) as resp:
            data = json.loads(resp.read().decode())
        check("api_price", data.get("last_price") is not None, str(data.get("last_price")))
        version = str(data.get("version") or "")
        check("api_version", "V10" in version or version == "TAFA_X_ULTIMATE_FINAL", version)
    finally:
        p.terminate()
        try:
            p.wait(timeout=2)
        except Exception:
            p.kill()

    failed = sum(1 for x in results if not x)
    print(f"=== {len(results)-failed}/{len(results)} passed ===")
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
