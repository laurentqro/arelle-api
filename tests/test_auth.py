"""Bearer-token authentication on /validate (health stays open).

The service runs on the production network and validates client XBRL
instances, so /validate must require a shared bearer token read from the
ARELLE_API_TOKEN environment variable. /health stays open for liveness probes.

The authorized-path tests stub out the real Arelle run (validate_xbrl) so they
exercise only the auth layer, not taxonomy loading.
"""

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.validator import ValidationResult


TOKEN = "s3cr3t-shared-token"
XML_BODY = "<?xml version='1.0'?><xbrl/>"
XML_HEADERS = {"Content-Type": "application/xml"}


@pytest.fixture
def client(monkeypatch):
    """A test client with a known token configured and Arelle stubbed.

    validate_xbrl is replaced with a stub that returns a clean verdict, so the
    authorized path returns 200 without invoking Arelle or loading taxonomy.
    """
    monkeypatch.setenv("ARELLE_API_TOKEN", TOKEN)
    monkeypatch.setattr(
        main, "validate_xbrl", lambda xml_content: ValidationResult(valid=True)
    )
    return TestClient(main.app)


def auth(token):
    return {"Authorization": f"Bearer {token}", **XML_HEADERS}


# --- /validate auth ---------------------------------------------------------


def test_validate_without_authorization_header_is_401(client):
    response = client.post("/validate", content=XML_BODY, headers=XML_HEADERS)
    assert response.status_code == 401


def test_validate_with_wrong_token_is_401(client):
    response = client.post("/validate", content=XML_BODY, headers=auth("wrong"))
    assert response.status_code == 401


def test_validate_with_malformed_authorization_header_is_401(client):
    # Right token value but missing the "Bearer " scheme prefix.
    headers = {"Authorization": TOKEN, **XML_HEADERS}
    response = client.post("/validate", content=XML_BODY, headers=headers)
    assert response.status_code == 401


def test_validate_with_correct_token_validates_as_before(client):
    response = client.post("/validate", content=XML_BODY, headers=auth(TOKEN))
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["summary"] == {"errors": 0, "warnings": 0, "info": 0}


def test_authorization_runs_before_body_validation(client):
    # An unauthenticated request is rejected even when the body is malformed,
    # so auth gates access before any request parsing or Arelle work.
    response = client.post("/validate", content="not xml", headers={})
    assert response.status_code == 401


# --- fail-closed when unconfigured ------------------------------------------


def test_validate_fails_closed_when_token_env_unset(monkeypatch):
    # No ARELLE_API_TOKEN configured: the endpoint must refuse, not allow all.
    monkeypatch.delenv("ARELLE_API_TOKEN", raising=False)
    monkeypatch.setattr(
        main, "validate_xbrl", lambda xml_content: ValidationResult(valid=True)
    )
    client = TestClient(main.app)

    response = client.post("/validate", content=XML_BODY, headers=auth(TOKEN))
    assert response.status_code == 401


def test_validate_fails_closed_when_token_env_blank(monkeypatch):
    # An empty token is treated as unconfigured: still fail closed.
    monkeypatch.setenv("ARELLE_API_TOKEN", "")
    monkeypatch.setattr(
        main, "validate_xbrl", lambda xml_content: ValidationResult(valid=True)
    )
    client = TestClient(main.app)

    response = client.post("/validate", content=XML_BODY, headers=auth(""))
    assert response.status_code == 401


# --- /health stays open -----------------------------------------------------


def test_health_requires_no_auth_when_token_set(monkeypatch):
    monkeypatch.setenv("ARELLE_API_TOKEN", TOKEN)
    client = TestClient(main.app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_requires_no_auth_when_token_unset(monkeypatch):
    # Liveness probes must work even before the secret is wired.
    monkeypatch.delenv("ARELLE_API_TOKEN", raising=False)
    client = TestClient(main.app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
