# Arelle API Design

## Overview

A lightweight Python HTTP API that validates XBRL instances against the pre-bundled AMSF/Strix taxonomy using Arelle.

**Purpose:** Drive development of the `amsf_survey` gem by validating generated XBRL before AMSF submission.

## API Contract

### POST /validate

Validates an XBRL instance document.

**Request:**
```
POST /validate
Content-Type: application/xml

<xbrl>...</xbrl>
```

**Success Response (200 OK):**
```json
{
  "valid": true,
  "summary": {"errors": 0, "warnings": 2, "info": 5},
  "messages": [
    {
      "severity": "warning",
      "code": "xbrl.5.2.5.2",
      "message": "Duplicate fact values for concept strix:A1101",
      "location": {"line": 142, "column": 8}
    }
  ]
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "Invalid XML: unclosed tag at line 23"
}
```

## Project Structure

```
arelle_api/
├── app/
│   ├── main.py           # FastAPI app with /validate endpoint
│   └── validator.py      # Arelle wrapper logic
├── taxonomy/             # AMSF/Strix taxonomy files
│   ├── strix_Real_Estate_AML_CFT_survey_2025_cal.xml
│   ├── strix_Real_Estate_AML_CFT_survey_2025_def.xml
│   ├── strix_Real_Estate_AML_CFT_survey_2025_lab.xml
│   └── strix_Real_Estate_AML_CFT_survey_2025_pre.xml
├── Dockerfile
├── requirements.txt      # arelle-release, fastapi, uvicorn
└── README.md
```

## Technical Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| API framework | FastAPI | Simple, fast, auto-generates OpenAPI docs |
| Server | Uvicorn (single worker) | Arelle is not thread-safe |
| Validation engine | Arelle | Industry-standard XBRL validator |
| Taxonomy | Pre-bundled | Fast validation, works offline |
| Request format | POST XML body | Simple, files are small (<1MB) |
| Response format | Structured JSON | Easy to process in Rails |
| Deployment | Docker | Isolates Python/Arelle dependencies |

## Request Flow

```
immo_crm                     arelle_api
    │                            │
    │  POST /validate            │
    │  (XML body)                │
    ├───────────────────────────►│
    │                            │
    │                            ├─► Save XML to temp file
    │                            ├─► Run Arelle validation
    │                            ├─► Parse log messages
    │                            ├─► Delete temp file
    │                            │
    │  JSON response             │
    │◄───────────────────────────┤
```

## Usage

**Start the API:**
```bash
docker build -t arelle-api .
docker run -p 8000:8000 arelle-api
```

**Test validation:**
```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/xml" \
  -d @path/to/your/file.xml
```

**From Rails:**
```ruby
response = HTTP.post(
  "http://localhost:8000/validate",
  body: survey.to_xbrl,
  headers: { "Content-Type" => "application/xml" }
)
result = JSON.parse(response.body)
```

## Out of Scope (for now)

- Authentication (local development only)
- Database/history
- Async processing/queue
- Health check endpoint
- Caching
- Batch validation
