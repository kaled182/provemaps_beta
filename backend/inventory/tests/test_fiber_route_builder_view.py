"""EV-0084 — o Projeto de rede serve sempre o SPA; o construtor legado saiu."""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.test import RequestFactory

from inventory.views import fiber_route_builder


@pytest.mark.django_db
@pytest.mark.parametrize("query", ["", "?legacy=1"])
def test_always_serves_spa(query):
    request = RequestFactory().get(f"/Network/NetworkDesign/{query}")
    request.user = get_user_model().objects.create_user(username="noc", password="x")
    config = MagicMock(google_maps_api_key="K")
    with (
        patch("inventory.views.get_runtime_config", return_value=config),
        patch("inventory.views.render") as render,
    ):
        render.return_value = MagicMock(status_code=200)
        fiber_route_builder(request)
    assert render.call_args[0][1] == "spa.html"
    assert render.call_args[0][2] == {"GOOGLE_MAPS_API_KEY": "K"}


def test_legacy_template_is_gone():
    with pytest.raises(TemplateDoesNotExist):
        get_template("inventory/fiber_route_builder.html")
