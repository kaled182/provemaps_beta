"""
Tests for deprecation warning system.

Sprint 1, Week 2 - Legacy Code Removal Schedule
Validates deprecation marking and warning system.

⚠️ IMPORTANTE: Testes devem ser executados sob Docker
Executar: docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_deprecation.py -v
"""

import warnings
import pytest
from django.test import RequestFactory, TestCase

from inventory.deprecation import (
    deprecated,
    warn_deprecated,
    warn_field_deprecated,
    warn_endpoint_deprecated,
    warn_method_deprecated,
    is_deprecated,
    get_deprecation_info,
    suppress_deprecation_warnings,
    DeprecationWarning,
)


class DeprecationDecoratorTest(TestCase):
    """Test @deprecated decorator functionality."""

    def test_deprecated_decorator_marks_function(self):
        """@deprecated should mark function as deprecated."""
        
        @deprecated(version="3.0")
        def test_function():
            return "result"
        
        self.assertTrue(is_deprecated(test_function))
        self.assertEqual(test_function.__deprecated__, True)

    def test_deprecated_decorator_preserves_function_behavior(self):
        """@deprecated should not change function behavior."""
        
        @deprecated(version="3.0")
        def add(a, b):
            return a + b
        
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = add(2, 3)
        
        self.assertEqual(result, 5)

    def test_deprecated_decorator_issues_warning(self):
        """@deprecated should issue warning when function is called."""
        
        @deprecated(version="3.0", alternative="new_function()")
        def old_function():
            return "old"
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            old_function()
            
            self.assertEqual(len(w), 1)
            self.assertIn("deprecated", str(w[0].message).lower())
            self.assertIn("3.0", str(w[0].message))
            self.assertIn("new_function()", str(w[0].message))

    def test_deprecated_with_reason(self):
        """@deprecated should include reason in warning message."""
        
        @deprecated(version="3.0", reason="Performance issues")
        def slow_function():
            pass
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            slow_function()
            
            self.assertIn("Performance issues", str(w[0].message))

    def test_get_deprecation_info(self):
        """get_deprecation_info() should return deprecation metadata."""
        
        @deprecated(version="3.5", alternative="better_func()")
        def test_func():
            pass
        
        info = get_deprecation_info(test_func)
        
        self.assertEqual(info["deprecated"], True)
        self.assertEqual(info["version"], "3.5")
        self.assertEqual(info["alternative"], "better_func()")

    def test_get_deprecation_info_non_deprecated(self):
        """get_deprecation_info() should return empty dict for normal functions."""
        
        def normal_function():
            pass
        
        info = get_deprecation_info(normal_function)
        
        self.assertEqual(info, {})


class DeprecationWarningTest(TestCase):
    """Test warn_deprecated and specific warning functions."""

    def test_warn_deprecated_issues_warning(self):
        """warn_deprecated() should issue a warning."""
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warn_deprecated("Test deprecation", version="2.5")
            
            self.assertEqual(len(w), 1)
            self.assertIn("Test deprecation", str(w[0].message))
            self.assertIn("2.5", str(w[0].message))

    def test_warn_field_deprecated(self):
        """warn_field_deprecated() should format field deprecation warning."""
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warn_field_deprecated("coordinates", "FiberCable", "path")
            
            self.assertEqual(len(w), 1)
            message = str(w[0].message)
            self.assertIn("coordinates", message)
            self.assertIn("FiberCable", message)
            self.assertIn("path", message)

    def test_warn_endpoint_deprecated(self):
        """warn_endpoint_deprecated() should format endpoint deprecation warning."""
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warn_endpoint_deprecated("/api/old/", "/api/v2/new/")
            
            self.assertEqual(len(w), 1)
            message = str(w[0].message)
            self.assertIn("/api/old/", message)
            self.assertIn("/api/v2/new/", message)

    def test_warn_method_deprecated(self):
        """warn_method_deprecated() should format method deprecation warning."""
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warn_method_deprecated("old_method", "MyClass", "new_method()")
            
            self.assertEqual(len(w), 1)
            message = str(w[0].message)
            self.assertIn("old_method", message)
            self.assertIn("MyClass", message)
            self.assertIn("new_method()", message)


class SuppressDeprecationTest(TestCase):
    """Test suppress_deprecation_warnings context manager."""

    def test_suppress_deprecation_warnings(self):
        """suppress_deprecation_warnings should prevent warnings."""
        
        @deprecated(version="3.0")
        def deprecated_func():
            return "result"
        
        # Without suppression - should warn
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            deprecated_func()
            self.assertEqual(len(w), 1)
        
        # With suppression - should not warn
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with suppress_deprecation_warnings():
                deprecated_func()
            self.assertEqual(len(w), 0)

    def test_suppress_context_restores_filters(self):
        """Context manager should restore warning filters after exit."""
        
        original_filters = warnings.filters[:]
        
        with suppress_deprecation_warnings():
            # Filters changed inside context
            self.assertNotEqual(warnings.filters, original_filters)
        
        # Filters restored after exit
        self.assertEqual(warnings.filters, original_filters)


class DeprecationIntegrationTest(TestCase):
    """Integration tests for deprecation system."""

    def test_deprecated_function_still_callable(self):
        """Deprecated functions should remain fully functional."""
        
        @deprecated(version="3.0")
        def calculate(x, y):
            return x * y
        
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = calculate(5, 7)
        
        self.assertEqual(result, 35)

    def test_deprecated_method_in_class(self):
        """@deprecated should work on class methods."""
        
        class TestClass:
            @deprecated(version="3.0", alternative="new_method()")
            def old_method(self):
                return "old behavior"
            
            def new_method(self):
                return "new behavior"
        
        obj = TestClass()
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = obj.old_method()
            
            self.assertEqual(result, "old behavior")
            self.assertEqual(len(w), 1)
            self.assertIn("new_method()", str(w[0].message))

    def test_multiple_deprecation_warnings(self):
        """Multiple calls should issue multiple warnings."""
        
        @deprecated(version="3.0")
        def func():
            pass
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            func()
            func()
            func()
            
            # Should have 3 warnings
            self.assertEqual(len(w), 3)


class DeprecationAuditTest(TestCase):
    """Test audit and introspection functions."""

    def test_is_deprecated_true(self):
        """is_deprecated() should return True for deprecated functions."""
        
        @deprecated(version="3.0")
        def deprecated_func():
            pass
        
        self.assertTrue(is_deprecated(deprecated_func))

    def test_is_deprecated_false(self):
        """is_deprecated() should return False for normal functions."""
        
        def normal_func():
            pass
        
        self.assertFalse(is_deprecated(normal_func))

    def test_deprecation_info_complete(self):
        """get_deprecation_info() should return all metadata."""
        
        @deprecated(
            version="4.0",
            alternative="super_new_function()",
            reason="Old implementation is slow"
        )
        def old_func():
            pass
        
        info = get_deprecation_info(old_func)
        
        self.assertEqual(info["deprecated"], True)
        self.assertEqual(info["version"], "4.0")
        self.assertEqual(info["alternative"], "super_new_function()")


# ==============================================================================
# Real-world Usage Examples (Documentation)
# ==============================================================================

class DeprecationUsageExamplesTest(TestCase):
    """Examples of how to use deprecation system in real code."""

    def test_example_deprecated_api_endpoint(self):
        """Example: Mark deprecated API endpoint."""
        
        from rest_framework.decorators import api_view
        from rest_framework.response import Response
        
        @api_view(['GET'])
        @deprecated(version="3.0", alternative="/api/v2/sites/")
        def old_sites_endpoint(request):
            warn_endpoint_deprecated("/api/sites/", "/api/v2/sites/")
            # ... legacy implementation
            return Response({"message": "old endpoint"})
        
        # When called, issues deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Simulated call — api_view requires a real HttpRequest, not None
            request = RequestFactory().get('/api/sites/')
            old_sites_endpoint(request)

            # Should have at least 1 warning
            self.assertGreater(len(w), 0)

    def test_example_deprecated_model_field_access(self):
        """Example: Warn when accessing deprecated model field."""
        
        class FiberCable:
            """Simplified model for example."""
            
            def __init__(self):
                self._coordinates = {"old": "data"}
                self.path = "new_data"
            
            @property
            def coordinates(self):
                """Deprecated: Use path field instead."""
                warn_field_deprecated("coordinates", "FiberCable", "path")
                return self._coordinates
        
        cable = FiberCable()
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = cable.coordinates  # Access deprecated field
            
            self.assertEqual(len(w), 1)
            self.assertIn("coordinates", str(w[0].message))
            self.assertIn("path", str(w[0].message))

    def test_example_suppress_in_tests(self):
        """Example: Suppress warnings when testing legacy code."""
        
        @deprecated(version="3.0")
        def legacy_function():
            return "legacy result"
        
        # Test the legacy function without noise
        with suppress_deprecation_warnings():
            result = legacy_function()
            self.assertEqual(result, "legacy result")
            # No warnings issued


"""
DEPRECATION TRACKING REPORT:

Run this command to generate a report of all deprecated code:

    python manage.py shell <<EOF
    from inventory.deprecation import get_all_deprecated_functions
    
    deprecated = get_all_deprecated_functions()
    print(f"\n{'='*60}")
    print(f"DEPRECATED CODE REPORT")
    print(f"{'='*60}\n")
    
    for item in deprecated:
        print(f"📍 {item['module']}.{item['name']}()")
        print(f"   Remove in: v{item['version']}")
        if item['alternative']:
            print(f"   Use instead: {item['alternative']}")
        print()
    
    print(f"Total deprecated items: {len(deprecated)}")
    EOF

INTEGRATION WITH SPRINT 4:

When planning deprecation removals in Sprint 4, combine metrics with deprecation warnings:

    1. Check usage: inventory_endpoint_usage_total{endpoint="/api/old/"}
    2. Check warnings: grep "DEPRECATED" logs/django.log
    3. Decision: If usage=0 AND warnings logged → safe to remove

"""
