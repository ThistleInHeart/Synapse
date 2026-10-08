import os
import time
import traceback

LOG_FILE_PATH = os.path.expanduser(r"~\Documents\Electronic Arts\The Sims 4\ai_mind_reader.log")


def log(message: str, level: str = "INFO"):
    """Appends a timestamped log entry to the mod log file."""
    try:
        os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{level}] {message}\n")
    except Exception:
        pass


def log_exception(context_msg: str, exc: Exception):
    """Logs an exception with its full traceback."""
    try:
        os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [ERROR] {context_msg}: {exc}\n")
            f.write(traceback.format_exc())
            f.write("\n")
    except Exception:
        pass
