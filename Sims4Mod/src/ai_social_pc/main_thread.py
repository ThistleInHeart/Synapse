import queue
from ai_social_pc.logger import log, log_exception

_MAIN_THREAD_QUEUE = queue.Queue()


def run_on_main_thread(func, *args, **kwargs):
    """
    Safely enqueues a callable to be executed strictly on the Sims 4 main simulation thread.
    Prevents thread race conditions and distributor desynchronization.
    """
    if callable(func):
        _MAIN_THREAD_QUEUE.put((func, args, kwargs))


def process_main_thread_queue():
    """
    Drains all queued actions on the main simulation thread.
    Invoked continuously from Zone.update hook.
    """
    while not _MAIN_THREAD_QUEUE.empty():
        try:
            item = _MAIN_THREAD_QUEUE.get_nowait()
            if item is None:
                break
            func, args, kwargs = item
            func(*args, **kwargs)
        except queue.Empty:
            break
        except Exception as e:
            log_exception("Error in ai_social_pc main thread queue execution", e)
