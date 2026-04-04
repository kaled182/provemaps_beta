from django.test import TestCase, modify_settings, override_settings
from django.urls import reverse

from setup_app.models import FirstTimeSetup


# settings/test.py strips FirstTimeSetupRedirectMiddleware to avoid stray
# 302s in unrelated tests.  Re-add it here so this class can exercise the
# middleware specifically, while also forcing the first-time flow.
@override_settings(FORCE_FIRST_TIME_FLOW=True)
@modify_settings(MIDDLEWARE={"append": (
    "core.middleware.first_time_setup.FirstTimeSetupRedirectMiddleware"
)})
class FirstTimeSetupRedirectMiddlewareTests(TestCase):
    def test_redirects_to_setup_when_not_configured(self):
        FirstTimeSetup.objects.all().delete()
        response = self.client.get(reverse("maps_view:dashboard_view"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("setup_app:first_time_setup"))

    def test_setup_page_accessible_without_login(self):
        FirstTimeSetup.objects.all().delete()
        response = self.client.get(reverse("setup_app:first_time_setup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Company name", status_code=200)

    def test_does_not_redirect_after_configuration(self):
        FirstTimeSetup.objects.create(
            company_name="Test Co",
            zabbix_url="http://example.com/api_jsonrpc.php",
            auth_type="token",
            zabbix_api_key="abc123",
            configured=True,
        )
        response = self.client.get(reverse("maps_view:dashboard_view"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
        self.assertNotEqual(response.url, reverse("setup_app:first_time_setup"))
