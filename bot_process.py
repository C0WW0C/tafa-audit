# ============================================================
# TAFA V10 — Bot process control (start / stop / status)
# Used by Streamlit control_panel.py (Elite Panel Control)
# ============================================================
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import threading
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LOGS = ROOT / "logs"
PID_FILE = DATA / "bot.pid"

_RUN_CANDIDATES = [
    ROOT / "run_v10.py",
    ROOT / "run_elite_final_paper.py",
    ROOT / "run_paper_demo.py",
]

_lock = threading.RLock()   # ✅ thread safety


def run_script() -> Path:
    for p in _RUN_CANDIDATES:
        if p.exists():
            return p
    return ROOT / "run_v10.py"


def is_running() -> bool:
    with _lock:
        if not PID_FILE.exists():
            return False
        try:
            pid = int(PID_FILE.read_text(encoding="utf-8").strip())
        except Exception:
            return False

        try:
            os.kill(pid, 0)
        except Exception:
            return False

        # Linux/Unix : vérifier la ligne de commande
        try:
            args = Path(f"/proc/{pid}/cmdline").read_text(encoding="utf-8", errors="ignore")
            name = run_script().name
            return name in args or "run_v10" in args or "run_elite" in args or "run_paper" in args
        except Exception:
            # Windows : on considère que le processus existe
            if os.name == "nt":
                return True
            return False


def read_pid() -> Optional[int]:
    with _lock:
        try:
            if PID_FILE.exists():
                return int(PID_FILE.read_text(encoding="utf-8").strip())
        except Exception:
            pass
        return None


def start_bot() -> Dict[str, Any]:
    with _lock:
        DATA.mkdir(parents=True, exist_ok=True)
        LOGS.mkdir(parents=True, exist_ok=True)
        if is_running():
            return {"ok": True, "message": "Bot déjà actif", "pid": read_pid(), "already": True}

        script = run_script()
        if not script.exists():
            return {"ok": False, "message": f"Script introuvable: {script.name}"}

        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        # ✅ FIX Windows : forcer UTF-8 sur la console du sous-processus
        env["PYTHONIOENCODING"] = "utf-8"
        log_path = LOGS / "bot_start.log"
        log_f = open(log_path, "ab", buffering=0)
        try:
            # ✅ FIX Windows : CREATE_NEW_PROCESS_GROUP isole le bot du groupe de signaux
            # de Streamlit (qui envoie CTRL_C_EVENT à tout son groupe au rechargement).
            # DETACHED_PROCESS empêche l'héritage de la console.
            if os.name == "nt":
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                DETACHED_PROCESS = 0x00000008
                creation_flags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
                proc = subprocess.Popen(
                    [sys.executable, str(script)],
                    cwd=str(ROOT),
                    env=env,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    creationflags=creation_flags,
                )
            else:
                proc = subprocess.Popen(
                    [sys.executable, str(script)],
                    cwd=str(ROOT),
                    env=env,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
        except Exception as exc:
            log_f.close()
            return {"ok": False, "message": f"Échec du lancement: {exc}"}
        finally:
            log_f.close()

        ok = False
        for _ in range(16):
            time.sleep(0.25)
            if is_running():
                ok = True
                break
            if proc.poll() is not None:
                break

        tail = ""
        try:
            if log_path.exists():
                tail = log_path.read_bytes()[-800:].decode("utf-8", errors="replace").strip()
        except Exception:
            pass

        if ok:
            return {
                "ok": True,
                "message": f"Bot démarré ({script.name})",
                "pid": read_pid(),
                "script": script.name,
            }
        if proc.poll() is not None:
            return {
                "ok": False,
                "message": f"Bot a quitté (code {proc.returncode}). Voir logs/bot_start.log",
                "log_tail": tail[-300:],
                "script": script.name,
            }
        return {
            "ok": True,
            "message": f"Bot lancé ({script.name}) — PID en cours d’écriture",
            "script": script.name,
            "log_tail": tail[-200:],
        }


def stop_bot() -> Dict[str, Any]:
    with _lock:
        stopped = False
        pid = read_pid()
        if pid:
            try:
                if os.name == "nt":
                    # ✅ FIX Windows : CTRL_C_EVENT sur le groupe de processus
                    try:
                        os.kill(pid, signal.CTRL_BREAK_EVENT)
                    except Exception:
                        os.kill(pid, signal.SIGTERM)
                else:
                    try:
                        os.killpg(pid, signal.SIGTERM)
                    except Exception:
                        os.kill(pid, signal.SIGTERM)
                stopped = True
            except ProcessLookupError:
                stopped = True
            except Exception:
                pass

            for _ in range(10):
                time.sleep(0.2)
                try:
                    os.kill(pid, 0)
                except Exception:
                    break
            else:
                try:
                    if os.name == "nt":
                        subprocess.call(["taskkill", "/F", "/PID", str(pid)],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        try:
                            os.killpg(pid, signal.SIGKILL)
                        except Exception:
                            os.kill(pid, signal.SIGKILL)
                    stopped = True
                except Exception:
                    pass

        # Processus restants — pgrep sur Linux, tasklist sur Windows
        script_name = run_script().name
        if os.name == "nt":
            try:
                out = subprocess.check_output(
                    ["tasklist", "/FI", f"IMAGENAME eq python.exe", "/FO", "CSV"],
                    text=True, errors="replace",
                )
                for line in out.strip().splitlines()[1:]:
                    parts = line.strip('"').split('","')
                    if len(parts) >= 2:
                        try:
                            sp = int(parts[1])
                            if sp != os.getpid() and sp != pid:
                                subprocess.call(["taskkill", "/F", "/PID", str(sp)],
                                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                stopped = True
                        except Exception:
                            pass
            except Exception:
                pass
        else:
            try:
                out = subprocess.check_output(
                    ["pgrep", "-f", str(ROOT / script_name)],
                    text=True,
                )
                for line in out.strip().splitlines():
                    try:
                        sp = int(line.strip())
                        if sp != os.getpid():
                            os.kill(sp, signal.SIGTERM)
                            stopped = True
                    except Exception:
                        pass
            except Exception:
                pass

        try:
            if PID_FILE.exists():
                PID_FILE.unlink()
        except Exception:
            pass

        try:
            from core.status_bridge import publish
            publish({"running": False, "state": "STOPPED"}, merge=True)
        except Exception:
            pass

        return {
            "ok": True,
            "message": "Bot arrêté." if stopped or not is_running() else "Aucun bot actif trouvé.",
            "running": is_running(),
        }


def status_snapshot() -> Dict[str, Any]:
    with _lock:
        from core import status_bridge

        data = status_bridge.read() or {}
        if not isinstance(data, dict):
            data = {}
        data = dict(data)
        alive = is_running()
        age = None
        ts = data.get("updated_at")
        if isinstance(ts, (int, float)) and ts > 0:
            age = max(0.0, time.time() - float(ts))
        bridge_fresh = bool(data.get("running")) and age is not None and age < 45
        data["running"] = bool(alive or bridge_fresh)
        data["pid"] = read_pid()
        data["pid_alive"] = alive
        data["script"] = run_script().name
        data["heartbeat_age_s"] = age
        data["bridge_path"] = str(status_bridge.STATUS_FILE)
        data.setdefault("mode", "PAPER")
        data["state"] = "RUNNING" if data["running"] else "STOPPED"

        perf = data.get("performance") if isinstance(data.get("performance"), dict) else {}
        paper = data.get("paper") if isinstance(data.get("paper"), dict) else {}
        paper = dict(paper)
        if paper.get("equity") in (None, 0) and perf.get("equity") is not None:
            paper["equity"] = perf.get("equity")
        if paper.get("session_pnl") is None and perf.get("session_pnl") is not None:
            paper["session_pnl"] = perf.get("session_pnl")
        if paper.get("session_return_pct") is None and perf.get("session_return_pct") is not None:
            paper["session_return_pct"] = perf.get("session_return_pct")
        data["paper"] = paper

        ai = data.get("ai") if isinstance(data.get("ai"), dict) else {}
        if not ai.get("signal") and data.get("last_signal"):
            ai = dict(ai)
            ai.setdefault("signal", data.get("last_signal"))
            data["ai"] = ai
        return data