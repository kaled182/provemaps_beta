"""
Deprecation warnings system for legacy code identification.

Sprint 1, Week 2 - Legacy Code Removal Schedule
Marks legacy-style code with warnings to prepare for Sprint 2 removal.

Usage:
    from inventory.deprecation import deprecated, warn_deprecated
    
    @deprecated(version="3.0", alternative="use_new_function()")
    def old_function():
        pass
    
    # Or manually:
    warn_deprecated("This pattern is deprecated", version="3.0")
"""

import logging
import warnings
import functools
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ==============================================================================
# Deprecation Warning Configuration
# ==============================================================================

# Set to True to convert deprecation warnings to errors (useful in CI/tests)
DEPRECATION_AS_ERROR = False

# Set to True to log deprecation warnings (in addition to warnings module)
LOG_DEPRECATIONS = True


class DeprecationWarning(UserWarning):
    """Custom deprecation warning for MapProveFiber legacy code."""
    pass


# ==============================================================================
# Core Functions
# ==============================================================================

def warn_deprecated(
    message: str,
    version: str = "3.0",
    stacklevel: int = 2,
    category: type = DeprecationWarning,
) -> None:
    """
    Issue a deprecation warning.
    
    Args:
        message: Deprecation message
        version: Version when feature will be removed
        stacklevel: How many levels up the stack to report (default: 2)
        category: Warning category (default: DeprecationWarning)
    
    Example:
        warn_deprecated(
            "coordinates field is deprecated, use path instead",
            version="3.0"
        )
    """
    full_message = f"[DEPRECATED - will be removed in v{version}] {message}"
    
    if LOG_DEPRECATIONS:
        logger.warning(full_message)
    
    if DEPRECATION_AS_ERROR:
        raise DeprecationWarning(full_message)
    else:
        warnings.warn(full_message, category, stacklevel=stacklevel)


def deprecated(
    version: str = "3.0",
    alternative: Optional[str] = None,
    reason: Optional[str] = None,
) -> Callable:
    """
    Decorator to mark functions/methods as deprecated.
    
    Args:
        version: Version when function will be removed
        alternative: Suggested alternative function/method
        reason: Reason for deprecation
    
    Example:
        @deprecated(version="3.0", alternative="new_function()")
        def old_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            message = f"{func.__module__}.{func.__name__}() is deprecated"
            
            if reason:
                message += f": {reason}"
            
            if alternative:
                message += f". Use {alternative} instead"
            
            warn_deprecated(message, version=version, stacklevel=3)
            
            return func(*args, **kwargs)
        
        # Mark function as deprecated (for introspection)
        wrapper.__deprecated__ = True
        wrapper.__deprecated_version__ = version
        wrapper.__deprecated_alternative__ = alternative
        
        return wrapper
    return decorator


# ==============================================================================
# Specific Deprecation Markers
# ==============================================================================

def warn_field_deprecated(field_name: str, model_name: str, alternative: str) -> None:
    """
    Warn about deprecated model field usage.
    
    Example:
        warn_field_deprecated("coordinates", "FiberCable", "path")
    """
    warn_deprecated(
        f"Model field {model_name}.{field_name} is deprecated. Use {alternative} instead",
        version="3.0",
        stacklevel=3,
    )


def warn_endpoint_deprecated(endpoint: str, alternative: str) -> None:
    """
    Warn about deprecated API endpoint usage.
    
    Example:
        warn_endpoint_deprecated("/api/old/", "/api/v2/new/")
    """
    warn_deprecated(
        f"Endpoint {endpoint} is deprecated. Use {alternative} instead",
        version="3.0",
        stacklevel=3,
    )


def warn_method_deprecated(method_name: str, class_name: str, alternative: str) -> None:
    """
    Warn about deprecated method usage.
    
    Example:
        warn_method_deprecated("old_method", "MyClass", "new_method()")
    """
    warn_deprecated(
        f"Method {class_name}.{method_name}() is deprecated. Use {alternative} instead",
        version="3.0",
        stacklevel=3,
    )


# ==============================================================================
# Detection Helpers
# ==============================================================================

def is_deprecated(func: Callable) -> bool:
    """
    Check if a function is marked as deprecated.
    
    Returns:
        True if function has @deprecated decorator
    """
    return getattr(func, "__deprecated__", False)


def get_deprecation_info(func: Callable) -> dict:
    """
    Get deprecation metadata for a function.
    
    Returns:
        Dict with version, alternative, etc. or empty dict if not deprecated
    """
    if not is_deprecated(func):
        return {}
    
    return {
        "deprecated": True,
        "version": getattr(func, "__deprecated_version__", None),
        "alternative": getattr(func, "__deprecated_alternative__", None),
    }


# ==============================================================================
# Context Managers
# ==============================================================================

class suppress_deprecation_warnings:
    """
    Context manager to temporarily suppress deprecation warnings.
    
    Useful in tests or when calling deprecated code intentionally.
    
    Example:
        with suppress_deprecation_warnings():
            old_function()  # No warning issued
    """
    
    def __enter__(self):
        self.old_filters = warnings.filters[:]
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        return self
    
    def __exit__(self, *args):
        warnings.filters[:] = self.old_filters


# ==============================================================================
# Audit Functions
# ==============================================================================

def get_all_deprecated_functions() -> list[dict]:
    """
    Scan inventory module for all @deprecated functions.
    
    Returns:
        List of dicts with function info and deprecation metadata
    
    Note: This is a simple implementation. For production, consider
    using ast module to scan all Python files.
    """
    import inspect
    import inventory
    
    deprecated_items = []
    
    # Scan inventory module
    for name, obj in inspect.getmembers(inventory):
        if inspect.isfunction(obj) and is_deprecated(obj):
            info = get_deprecation_info(obj)
            info["name"] = name
            info["module"] = obj.__module__
            deprecated_items.append(info)
    
    return deprecated_items


# ==============================================================================
# Usage Examples (Documentation)
# ==============================================================================

"""
USAGE PATTERNS:

1. Deprecate a function:
    
    @deprecated(version="3.0", alternative="new_function()")
    def old_function():
        return "legacy behavior"

2. Deprecate a method:
    
    class MyClass:
        @deprecated(version="3.0", reason="Slow implementation")
        def old_method(self):
            pass

3. Manual warning in code:
    
    def process_data(data):
        if 'coordinates' in data:
            warn_field_deprecated('coordinates', 'FiberCable', 'path')
        # ... rest of logic

4. Suppress warnings in tests:
    
    def test_legacy_behavior():
        with suppress_deprecation_warnings():
            result = old_function()
        assert result == "expected"

5. Check if deprecated:
    
    if is_deprecated(some_function):
        logger.warning("Using deprecated function")

6. Audit all deprecated code:
    
    from inventory.deprecation import get_all_deprecated_functions
    
    deprecated = get_all_deprecated_functions()
    for item in deprecated:
        print(f"{item['module']}.{item['name']} -> remove in v{item['version']}")
"""
