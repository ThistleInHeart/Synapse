"""
AI Mind Reader Mod for The Sims 4.
Author: Thistle / Antigravity
"""

__version__ = "1.0.0"

try:
    import ai_thought_reader.main
except Exception as e:
    try:
        from ai_thought_reader.logger import log_exception
        log_exception("CRITICAL: Failed to import ai_thought_reader.main", e)
    except Exception:
        pass

