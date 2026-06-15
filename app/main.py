"""Arelle XBRL Validation API.

Deployment note: this service must run a single Uvicorn worker (`--workers 1`,
set in the Dockerfile CMD). Arelle relies on process-global state and is not
thread-safe, so multiple workers in one process corrupt validation. This is an
accepted v1 constraint; scale by running multiple single-worker instances
behind a load balancer.
"""

import os
import secrets

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .validator import validate_xbrl


# The shared bearer token is read from the environment, never hard-coded.
# This is the name of the Kamal secret the bos Arelle client (task 1.12) will
# send. When it is unset (or blank) the service fails closed: /validate refuses
# every request rather than running open on the production network.
TOKEN_ENV_VAR = "ARELLE_API_TOKEN"

# auto_error=False: handle the missing-credentials case ourselves so a missing
# Authorization header and a wrong token both return a uniform 401 (FastAPI's
# default would 403 the missing header).
_bearer_scheme = HTTPBearer(auto_error=False)


def require_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    """Reject the request unless it carries the configured bearer token.

    Fails closed: if the token is not configured, no request is authorized.
    """
    expected = os.environ.get(TOKEN_ENV_VAR, "")
    presented = credentials.credentials if credentials else ""
    # Constant-time comparison avoids leaking the token via timing. An unset or
    # blank expected token can never match a presented credential, so the
    # service refuses all requests until the secret is wired.
    if not expected or not secrets.compare_digest(presented, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")


app = FastAPI(
    title="Arelle XBRL Validation API",
    description="Validates XBRL instances against the AMSF/Strix taxonomy",
    version="1.0.0",
)


@app.get("/health")
async def health():
    """Liveness probe for deployment tooling. Intentionally unauthenticated."""
    return {"status": "ok"}


@app.post("/validate", dependencies=[Depends(require_bearer_token)])
async def validate(request: Request):
    """Validate an XBRL instance document.

    Send the XML content as the request body with Content-Type: application/xml
    """
    content_type = request.headers.get("content-type", "")
    if "xml" not in content_type.lower():
        raise HTTPException(
            status_code=400,
            detail="Content-Type must be application/xml",
        )

    try:
        body = await request.body()
        xml_content = body.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid UTF-8 encoding in request body",
        )

    if not xml_content.strip():
        raise HTTPException(
            status_code=400,
            detail="Empty request body",
        )

    try:
        result = validate_xbrl(xml_content)
        return JSONResponse(content=result.to_dict())
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Validation failed: {str(e)}",
        )
