"""Arelle XBRL Validation API."""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from .validator import validate_xbrl


app = FastAPI(
    title="Arelle XBRL Validation API",
    description="Validates XBRL instances against the AMSF/Strix taxonomy",
    version="1.0.0",
)


@app.post("/validate")
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
