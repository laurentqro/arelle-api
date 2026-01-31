# Arelle XBRL Validation API

Validates XBRL instances against the AMSF/Strix Real Estate AML/CFT taxonomy.

## Quick Start

```bash
# Install dependencies
uv sync

# Run the API
uv run uvicorn app.main:app --reload
```

## Docker

```bash
docker build -t arelle-api .
docker run -p 8000:8000 arelle-api
```

## Usage

### Validate an XBRL file

```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/xml" \
  -d @path/to/your/file.xml
```

### Response

```json
{
  "valid": true,
  "summary": {"errors": 0, "warnings": 2, "info": 5},
  "messages": [
    {
      "severity": "warning",
      "code": "xbrl.5.2.5.2",
      "message": "Duplicate fact values",
      "location": {"line": 142, "column": 8}
    }
  ]
}
```

## API Documentation

Interactive API docs available at `http://localhost:8000/docs` when running.

## Taxonomy Cache

The API expects taxonomy files in `cache/http/amsf.mc/fr/taxonomy/strix/2025/`:

```
cache/http/amsf.mc/fr/taxonomy/strix/2025/
├── strix.xsd                                    # Main schema (copy of below)
├── strix_Real_Estate_AML_CFT_survey_2025.xsd    # Main schema
├── strix_Real_Estate_AML_CFT_survey_2025_cal.xml
├── strix_Real_Estate_AML_CFT_survey_2025_def.xml
├── strix_Real_Estate_AML_CFT_survey_2025_lab.xml
└── strix_Real_Estate_AML_CFT_survey_2025_pre.xml
```

Copy these from your taxonomy source and ensure both `strix.xsd` and the full-named schema exist.
