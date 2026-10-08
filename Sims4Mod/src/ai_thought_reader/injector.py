from functools import wraps
import inspect
from ai_thought_reader.logger import log, log_exception


def inject(target_object, target_function_name):
    """
    Safely injects / wraps a function or method in a class or module.
    The decorated function must take (original, *args, **kwargs).
    """
    def _inject_decorator(target_function):
        try:
            if hasattr(target_object, target_function_name):
                original_function = getattr(target_object, target_function_name)
            else:
                log(f"[INJECT] Target '{target_object}' has no attribute '{target_function_name}'", level="WARNING")
                return target_function

            @wraps(original_function)
            def _wrapped_function(*args, **kwargs):
                return target_function(original_function, *args, **kwargs)

            if inspect.ismethod(original_function):
                setattr(target_object, target_function_name, classmethod(_wrapped_function))
            else:
                setattr(target_object, target_function_name, _wrapped_function)

            log(f"[INJECT] Successfully injected into {target_object.__name__ if hasattr(target_object, '__name__') else str(target_object)}.{target_function_name}")
            return _wrapped_function
        except Exception as e:
            log_exception(f"Failed to inject into {target_function_name}", e)
            return target_function

    return _inject_decorator
