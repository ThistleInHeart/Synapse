"""
Synapse Bridge Autostart Manager for The Sims 4.
Automatically verifies if the Synapse AI Bridge is running on port 8765,
and if not, seamlessly launches the bridge executable with an open console.
"""

import os
import sys
import time
import socket
import threading
from typing import Optional, Callable
from ai_thought_reader.logger import log, log_exception

DEFAULT_PORT = 8765
CREATE_NEW_CONSOLE = 0x00000010

_autostart_lock = threading.Lock()
_last_launch_attempt = 0.0
_is_launching = False


def is_bridge_running(host: str = "127.0.0.1", port: int = DEFAULT_PORT, timeout: float = 0.5) -> bool:
    """
    Lightning-fast check if the AI Bridge HTTP port is actively listening.
    Takes 1-5 milliseconds on localhost.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(timeout)
        result = s.connect_ex((host, port))
        return (result == 0)
    except Exception:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def find_bridge_executable() -> Optional[str]:
    """
    Locates the Synapse AI Bridge executable on the player's system.
    1. Checks the user's ai_mod_config.json ('bridge_path').
    2. Searches known standard folders (Desktop\\Synapse, Desktop\\AI BRIDGE, Mods\\Synapse).
    3. Checks for ai_bridge.py as a script fallback.
    """
    # 1. Check user configuration
    try:
        from ai_thought_reader.config import load_config
        cfg = load_config()
        cfg_path = cfg.get("bridge_path", "").strip()
        if cfg_path and os.path.isfile(cfg_path):
            return cfg_path
    except Exception:
        pass

    user_home = os.path.expanduser("~")

    # 2. Check candidate executable paths (prefer Synapse.exe launcher which dynamically executes latest ai_bridge.py)
    candidates = [
        os.path.join(user_home, "Desktop", "Synapse", "Synapse.exe"),
        os.path.join(user_home, "Desktop", "Synapse", "ai_bridge.exe"),
        os.path.join(user_home, "Desktop", "AI BRIDGE", "ai_bridge.exe"),
        os.path.join(user_home, "Documents", "Electronic Arts", "The Sims 4", "Mods", "Synapse", "ai_bridge.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path

    # 3. Check for standalone Python script if exe is missing
    py_candidates = [
        os.path.join(user_home, "Desktop", "Synapse", "ai_bridge.py"),
        os.path.join(user_home, "Desktop", "AI BRIDGE", "ai_bridge.py"),
    ]
    for path in py_candidates:
        if os.path.isfile(path):
            return path

    return None


def launch_bridge(target_path: Optional[str] = None) -> bool:
    """
    Launches the bridge in an independent, visible Windows console.
    Returns True if the process launch command succeeded.
    """
    global _last_launch_attempt, _is_launching

    with _autostart_lock:
        now = time.time()
        # Debounce: avoid launching multiple times within 8 seconds
        if now - _last_launch_attempt < 8.0:
            log(f"[AUTOSTART] Debounce active: last launch was {now - _last_launch_attempt:.1f}s ago. Skipping.")
            return False

        if not target_path:
            target_path = find_bridge_executable()

        if not target_path or not os.path.isfile(target_path):
            log(f"[AUTOSTART] Could not locate AI Bridge executable on disk. (Target: {target_path})", level="WARNING")
            return False

        _last_launch_attempt = now
        _is_launching = True

    try:
        log(f"[AUTOSTART] Launching Synapse AI Bridge from '{target_path}'...")
        target_norm = os.path.normpath(target_path)
        work_dir = os.path.dirname(target_norm)

        # Launch .exe executable with a dedicated console window
        if target_norm.lower().endswith(".exe"):
            try:
                import subprocess
                cmd_args = [target_norm]
                # If running Synapse.exe, supply --bridge flag to launch bridge console directly
                if os.path.basename(target_norm).lower() == "synapse.exe":
                    cmd_args.append("--bridge")

                subprocess.Popen(
                    cmd_args,
                    cwd=work_dir,
                    creationflags=CREATE_NEW_CONSOLE,
                )
                log(f"[AUTOSTART] Successfully spawned process with CREATE_NEW_CONSOLE: {cmd_args}")
                return True
            except Exception as ex_sub:
                log(f"[AUTOSTART] subprocess.Popen failed ({ex_sub}), falling back to os.startfile...", level="WARNING")
                try:
                    os.startfile(target_norm)
                    log(f"[AUTOSTART] Successfully started bridge via os.startfile: {target_norm}")
                    return True
                except Exception as ex_os:
                    log_exception("os.startfile also failed", ex_os)
                    return False

        # Launch .py script via python / cmd
        elif target_norm.lower().endswith(".py"):
            try:
                import subprocess
                subprocess.Popen(
                    ["cmd.exe", "/c", "start", "python", target_norm],
                    cwd=work_dir,
                    creationflags=CREATE_NEW_CONSOLE,
                )
                log(f"[AUTOSTART] Successfully spawned python script via cmd: {target_norm}")
                return True
            except Exception as ex_py:
                log_exception("Failed to launch python script bridge", ex_py)
                return False

    except Exception as e:
        log_exception("Error in launch_bridge", e)
        return False
    finally:
        _is_launching = False

    return False


def ensure_bridge_running_async(on_ready: Optional[Callable[[bool], None]] = None):
    """
    Non-blocking async worker that checks port 8765, launches the bridge if needed,
    and waits until port 8765 responds or timeout expires.
    Zero game simulation freezes.
    """
    thread = threading.Thread(
        target=_ensure_bridge_worker,
        args=(on_ready,),
        daemon=True,
        name="Synapse-BridgeAutostart",
    )
    thread.start()


def _ensure_bridge_worker(on_ready: Optional[Callable[[bool], None]]):
    try:
        # Check config setting
        try:
            from ai_thought_reader.config import load_config
            cfg = load_config()
            if not cfg.get("autostart_bridge", True):
                log("[AUTOSTART] Autostart disabled in ai_mod_config.json ('autostart_bridge': false).")
                if on_ready:
                    on_ready(is_bridge_running())
                return
        except Exception:
            pass

        # 1. Quick initial ping
        if is_bridge_running():
            log("[AUTOSTART] AI Bridge is already running and ready on port 8765.")
            if on_ready:
                on_ready(True)
            return

        log("[AUTOSTART] AI Bridge is offline (port 8765 not responding). Triggering autostart...")
        launched = launch_bridge()
        if not launched:
            if on_ready:
                on_ready(False)
            return

        # 2. Poll for readiness (wait up to 10 seconds for the bridge to open the port)
        start_wait = time.time()
        while time.time() - start_wait < 10.0:
            time.sleep(0.5)
            if is_bridge_running():
                log(f"[AUTOSTART] AI Bridge is UP and listening on port 8765! (Ready in {time.time() - start_wait:.1f}s)")
                if on_ready:
                    on_ready(True)
                return

        log("[AUTOSTART] Bridge launched, but port 8765 timed out after 10s. It might still be loading in console.", level="WARNING")
        if on_ready:
            on_ready(False)

    except Exception as e:
        log_exception("Error in _ensure_bridge_worker", e)
        if on_ready:
            on_ready(False)
