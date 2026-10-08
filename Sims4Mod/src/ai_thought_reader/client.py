import json
import http.client
import threading
from typing import Callable
from ai_thought_reader.logger import log, log_exception

BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 8765


def _is_en() -> bool:
    try:
        from ai_thought_reader.localization import get_game_language
        return (get_game_language() == "en")
    except Exception:
        return False


def _safe_dispatch(callback: Callable[[str, bool], None], result: str, success: bool):
    """
    Dispatches callback strictly to the Sims 4 main simulation thread via main_thread queue.
    Prevents thread race conditions and distributor desynchronization.
    """
    if not callable(callback):
        return
    try:
        from ai_thought_reader.main_thread import run_on_main_thread
        run_on_main_thread(callback, result, success)
    except Exception:
        try:
            callback(result, success)
        except Exception as e:
            log_exception("Fallback callback execution error in client.py", e)


def request_ai_thought_async(prompt: str, sim_name: str, callback: Callable[[str, bool], None]):
    """
    Sends an asynchronous HTTP request to the local AI Bridge on 127.0.0.1:8765.
    Runs in a background thread to prevent freezing the game simulation.
    All callbacks are routed to the main simulation thread.
    """
    thread = threading.Thread(
        target=_worker_request,
        args=(prompt, sim_name, callback),
        daemon=True,
        name="AIThoughtReader-Worker",
    )
    thread.start()


def check_bridge_health() -> tuple:
    """Checks if AI Bridge is running on localhost."""
    try:
        conn = http.client.HTTPConnection(BRIDGE_HOST, BRIDGE_PORT, timeout=2)
        conn.request("GET", "/health", headers={"Connection": "close"})
        resp = conn.getresponse()
        if resp.status == 200:
            data = json.loads(resp.read().decode("utf-8"))
            conn.close()
            return True, data.get("message", "OK")
        conn.close()
        return False, f"HTTP {resp.status}"
    except Exception as e:
        return False, str(e)


def _worker_request(prompt: str, sim_name: str, callback: Callable[[str, bool], None]):
    log(f"Connecting to AI Bridge on http://{BRIDGE_HOST}:{BRIDGE_PORT} for '{sim_name}'...")

    try:
        conn = http.client.HTTPConnection(BRIDGE_HOST, BRIDGE_PORT, timeout=120)
        payload = {
            "prompt": prompt,
            "sim_name": sim_name,
        }
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(body_bytes)),
            "Connection": "close",
        }

        conn.request("POST", "/chat", body=body_bytes, headers=headers)
        resp = conn.getresponse()
        resp_data = resp.read().decode("utf-8")

        try:
            resp_json = json.loads(resp_data)
        except Exception:
            resp_json = {}

        if resp.status == 200 and resp_json.get("success"):
            thought = resp_json.get("thought", "")
            log(f"Received thought for {sim_name}: '{thought}'")
            _safe_dispatch(callback, thought, True)
        else:
            is_en = _is_en()
            def_err = f"Bridge error (HTTP {resp.status})" if is_en else f"Ошибка моста (HTTP {resp.status})"
            err_msg = resp_json.get("error") or resp_json.get("thought") or def_err
            log(f"Bridge error: {err_msg}", level="ERROR")
            _safe_dispatch(callback, err_msg, False)

        conn.close()

    except ConnectionRefusedError as e:
        is_en = _is_en()
        err_msg = "⏳ AI Bridge is launching in console... Please repeat in a few seconds." if is_en else "⏳ AI Bridge запускается в отдельной консоли... Пожалуйста, повторите действие через несколько секунд."
        log(f"AI Bridge offline (Connection refused). Triggering automatic console startup...", level="WARNING")
        try:
            from ai_thought_reader.bridge_autostart import ensure_bridge_running_async
            ensure_bridge_running_async()
        except Exception:
            pass
        _safe_dispatch(callback, err_msg, False)

    except TimeoutError as e:
        is_en = _is_en()
        err_msg = "⏳ AI response timed out (2 min). The server might be slow or overloaded." if is_en else "⏳ Время ожидания ответа от нейросети истекло (таймаут 2 мин). Возможно, медленный интернет или сервер ИИ перегружен."
        log(f"Timeout while waiting for AI Bridge response: {e}", level="WARNING")
        _safe_dispatch(callback, err_msg, False)

    except OSError as e:
        win_err = getattr(e, "winerror", None) or getattr(e, "errno", None)
        err_str = str(e).lower()
        is_en = _is_en()
        if win_err == 10061:
            err_msg = "⏳ AI Bridge is launching in console... Please repeat in a few seconds." if is_en else "⏳ AI Bridge запускается в отдельной консоли... Пожалуйста, повторите действие через несколько секунд."
            try:
                from ai_thought_reader.bridge_autostart import ensure_bridge_running_async
                ensure_bridge_running_async()
            except Exception:
                pass
        elif win_err == 10054:
            err_msg = "⚠️ Connection to AI Bridge was interrupted. Please wait a moment and try again." if is_en else "⚠️ Соединение с AI Bridge было прервано. Подождите пару секунд и повторите попытку."
        elif "timed out" in err_str:
            err_msg = "⏳ AI response timed out (2 min). The server might be slow or overloaded." if is_en else "⏳ Время ожидания ответа от нейросети истекло (таймаут 2 мин). Возможно, медленный интернет или сервер ИИ перегружен."
        else:
            err_msg = f"⚠️ Network error connecting to AI Bridge: {e}" if is_en else f"⚠️ Сетевая ошибка при связи с AI Bridge: {e}"
        log(f"Could not connect to AI Bridge (127.0.0.1:{BRIDGE_PORT}): {e}", level="WARNING")
        _safe_dispatch(callback, err_msg, False)

    except Exception as e:
        is_en = _is_en()
        err_msg = f"Unexpected error communicating with AI: {e}" if is_en else f"Непредвиденная ошибка связи с AI: {e}"
        log_exception("Error in _worker_request", e)
        _safe_dispatch(callback, err_msg, False)


def send_context_to_bridge_async(prompt: str, sim_name: str, callback: Callable[[str, bool], None]):
    """
    Sends an asynchronous HTTP request to the local AI Bridge to display context,
    WITHOUT triggering an LLM response or consuming tokens.
    """
    thread = threading.Thread(
        target=_worker_send_context,
        args=(prompt, sim_name, callback),
        daemon=True,
        name="AIThoughtReader-ContextWorker",
    )
    thread.start()


def _worker_send_context(prompt: str, sim_name: str, callback: Callable[[str, bool], None]):
    log(f"Sending Sim context to Synapse for '{sim_name}' ({len(prompt)} chars)...")
    try:
        conn = http.client.HTTPConnection(BRIDGE_HOST, BRIDGE_PORT, timeout=15)
        payload = {
            "type": "context",
            "prompt": prompt,
            "sim_name": sim_name,
            "only_context": True,
        }
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(body_bytes)),
            "Connection": "close",
        }

        conn.request("POST", "/context", body=body_bytes, headers=headers)
        resp = conn.getresponse()
        resp_data = resp.read().decode("utf-8")

        try:
            resp_json = json.loads(resp_data)
        except Exception:
            resp_json = {}

        if resp.status == 200 and resp_json.get("success"):
            _safe_dispatch(callback, "OK", True)
        else:
            is_en = _is_en()
            def_err = f"Bridge error (HTTP {resp.status})" if is_en else f"Ошибка моста (HTTP {resp.status})"
            err_msg = resp_json.get("error") or def_err
            _safe_dispatch(callback, err_msg, False)
        conn.close()

    except ConnectionRefusedError as e:
        is_en = _is_en()
        err_msg = "⏳ AI Bridge is launching in console... Please repeat in a few seconds." if is_en else "⏳ AI Bridge запускается в отдельной консоли... Пожалуйста, повторите действие через несколько секунд."
        log(f"AI Bridge offline during context send. Triggering automatic console startup...", level="WARNING")
        try:
            from ai_thought_reader.bridge_autostart import ensure_bridge_running_async
            ensure_bridge_running_async()
        except Exception:
            pass
        _safe_dispatch(callback, err_msg, False)

    except Exception as e:
        is_en = _is_en()
        err_msg = f"Network error connecting to AI Bridge: {e}" if is_en else f"Сетевая ошибка при связи с AI Bridge: {e}"
        log_exception("Error in _worker_send_context", e)
        _safe_dispatch(callback, err_msg, False)
