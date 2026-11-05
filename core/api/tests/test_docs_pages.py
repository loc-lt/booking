"""The browsable docs at /api/docs: served locally, off by default, never outside the repo."""

import re

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db  # ATOMIC_REQUESTS opens a transaction per request


@pytest.fixture
def client():
    return Client()


def test_hub_lists_api_pages_and_markdown(client):
    page = client.get("/api/docs").content.decode()
    for link in ("/api/docs/swagger", "/api/docs/redoc", "/api/openapi.yaml"):
        assert link in page
    assert "/api/docs/view/repo/docs/api.md" in page
    assert client.get("/api/v1/docs").url == "/api/docs"


def test_contract_and_markdown_are_served(client):
    contract = client.get("/api/openapi.yaml")
    assert contract.status_code == 200
    assert b"openapi: 3.1.0" in b"".join(contract.streaming_content)
    assert client.get("/api/docs/view/repo/docs/api.md").status_code == 200
    raw = client.get("/api/docs/raw/repo/docs/api.md")
    assert raw["Content-Type"].startswith("text/markdown")


@pytest.mark.parametrize(
    "path",
    [
        "/api/docs/raw/repo/../../../../etc/passwd",
        "/api/docs/raw/repo/core/api/app/settings/base.py",  # not a served type
        "/api/docs/raw/repo/core/api/.venv/pyvenv.cfg",
        "/api/docs/raw/nope/README.md",
        "/api/docs/raw/workspace/postman/local.postman_environment.json",  # tokens: never
    ],
)
def test_nothing_outside_the_whitelist(client, path):
    assert client.get(path).status_code == 404


def test_off_unless_enabled(client, settings):
    settings.API_DOCS = {**settings.API_DOCS, "ENABLED": False}
    assert client.get("/api/docs").status_code == 404
    assert client.get("/api/openapi.yaml").status_code == 404


def test_swagger_copy_of_the_contract_makes_auto_filled_headers_optional(client):
    text = client.get("/api/docs/openapi.swagger.yaml").content.decode()

    def block(name):
        found = re.search(rf"\n    {name}:\n(?:      .*\n)+", text)
        return found.group(0)

    assert "required: false" in block("TenantId")
    assert "required: false" in block("IdempotencyKey")
    assert "required: true" in block("BookingId")  # everything else untouched
    assert "example:" not in block("Uuid")
    page = client.get("/api/docs/swagger").content.decode()
    # The option itself (not the comment explaining why it is gone) breaks Swagger UI 5.
    assert not re.search(r"^\s+parameterMacro:", page, re.M)
