import os
import sys

LOG_FILE_NAME = "ai_social_pc.log"

def _get_log_path():
    try:
        docs = os.path.join(os.path.expanduser("~"), "Documents", "Electronic Arts", "The Sims 4")
        if os.path.exists(docs):
            return os.path.join(docs, LOG_FILE_NAME)
    except Exception:
        pass
    return LOG_FILE_NAME

def log(message: str, level: str = "INFO"):
    formatted = f"[AI Social PC][{level}] {message}"
    try:
        print(formatted)
    except Exception:
        pass
    try:
        log_path = _get_log_path()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def log_exception(context: str, exc: Exception):
    import traceback
    tb = traceback.format_exc()
    log(f"{context}: {exc}\n{tb}", level="ERROR")
