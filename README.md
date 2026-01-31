# Arelle XBRL Validation API

A Python HTTP API that validates XBRL instance documents against the AMSF/Strix Real Estate AML/CFT taxonomy using [Arelle](https://arelle.org/).

## Quick Start

```bash
# Install dependencies
uv sync

# Start the server
uv run uvicorn app.main:app --port 8000

# Validate an XBRL file
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/xml" \
  --data-binary @your_file.xml
```

## API

### POST /validate

Validates an XBRL instance document against the bundled taxonomy.

**Request:**
- Content-Type: `application/xml`
- Body: Raw XML content of the XBRL instance

**Response:**
```json
{
  "valid": false,
  "summary": {
    "errors": 2,
    "warnings": 1,
    "info": 3
  },
  "messages": [
    {
      "severity": "error",
      "code": "xbrl:schemaImportMissing",
      "message": "Instance facts missing schema concept definition: strix:a1101",
      "location": { "line": 106, "column": null }
    },
    {
      "severity": "warning",
      "code": "arelle:duplicateFact",
      "message": "Duplicate fact values for concept strix:A1101"
    },
    {
      "severity": "info",
      "code": "info",
      "message": "validated in 0.29 seconds"
    }
  ]
}
```

**Severity levels:**
- `error` - Validation failures that must be fixed
- `warning` - Issues that should be reviewed
- `info` - Informational messages (load time, etc.)

## How It Works

### Validation Flow

```
┌─────────────────┐      POST /validate       ┌─────────────────┐
│                 │      (XML body)           │                 │
│   Your App      │ ──────────────────────────│   Arelle API    │
│   (immo_crm)    │                           │                 │
│                 │ ◄─────────────────────────│                 │
└─────────────────┘      JSON response        └────────┬────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │     Arelle      │
                                              │   (Python lib)  │
                                              └────────┬────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │  Local Cache    │
                                              │   (taxonomy)    │
                                              └─────────────────┘
```

1. Your app sends XBRL content via HTTP POST
2. API writes content to a temp file (Arelle requires file paths)
3. Arelle validates against the cached taxonomy
4. Validation messages are parsed and returned as JSON
5. Temp file is cleaned up

### Offline Mode

The API runs in **offline mode** - it never fetches files from the internet. All taxonomy files must be pre-cached locally. This ensures:
- Fast, consistent validation times
- No network dependency
- Controlled taxonomy versions

## Taxonomy Cache

### How Arelle Caches Work

Arelle converts URLs to filesystem paths. When your XBRL references:

```xml
<link:schemaRef xlink:href="http://amsf.mc/fr/taxonomy/strix/2025/strix.xsd"/>
```

Arelle looks for the file at:

```
{cache_dir}/http/amsf.mc/fr/taxonomy/strix/2025/strix.xsd
```

The URL is converted to a path:
- Protocol (`http`) becomes the first directory
- Host (`amsf.mc`) becomes the next directory
- Path (`/fr/taxonomy/strix/2025/strix.xsd`) becomes the remaining path

### Current Cache Structure

```
cache/
└── http/
    └── amsf.mc/
        └── fr/
            └── taxonomy/
                └── strix/
                    └── 2025/
                        ├── strix.xsd                                    # Referenced by XBRL instance
                        ├── strix_Real_Estate_AML_CFT_survey_2025.xsd    # Actual schema
                        ├── strix_Real_Estate_AML_CFT_survey_2025_cal.xml
                        ├── strix_Real_Estate_AML_CFT_survey_2025_def.xml
                        ├── strix_Real_Estate_AML_CFT_survey_2025_lab.xml
                        └── strix_Real_Estate_AML_CFT_survey_2025_pre.xml
```

### Adding or Updating Taxonomy Files

1. Determine the URL your XBRL instance references (check `<link:schemaRef>`)
2. Create the corresponding directory structure under `cache/`
3. Copy your taxonomy files there
4. Ensure filenames match what the schema/linkbases reference

**Example:** If your XBRL references `https://example.com/tax/2025/schema.xsd`:

```bash
mkdir -p cache/https/example.com/tax/2025
cp schema.xsd cache/https/example.com/tax/2025/
```

## Docker

```bash
# Build
docker build -t arelle-api .

# Run
docker run -p 8000:8000 arelle-api
```

The Docker image includes the taxonomy cache, so no additional setup is needed.

## Development

### Project Structure

```
arelle_api/
├── app/
│   ├── __init__.py
│   ├── main.py         # FastAPI application
│   └── validator.py    # Arelle wrapper
├── cache/              # Pre-cached taxonomy files
│   └── http/
│       └── amsf.mc/...
├── taxonomy/           # Original taxonomy files (reference)
├── Dockerfile
├── pyproject.toml
└── README.md
```

### Running Locally

```bash
# Install dependencies
uv sync

# Run with auto-reload
uv run uvicorn app.main:app --reload --port 8000

# API docs available at
open http://localhost:8000/docs
```

### Testing

```bash
# Test with a valid XBRL file
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/xml" \
  --data-binary @/path/to/your/instance.xml

# Test with inline XML
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/xml" \
  -d '<?xml version="1.0"?><xbrl>...</xbrl>'
```

## Troubleshooting

### "Could not load file from local filesystem"

The taxonomy URL in your XBRL doesn't match the cache structure. Check:
1. What URL does your XBRL's `<link:schemaRef>` use?
2. Does that path exist under `cache/`?

### "Instance facts missing schema concept definition"

Possible causes:
1. **Namespace mismatch** - Your XBRL uses a different namespace than the taxonomy defines
2. **Missing taxonomy files** - Schema or linkbases not in cache
3. **Wrong filenames** - Linkbases reference files that don't exist

### Arelle Thread Safety

Arelle uses global state and is **not thread-safe**. The API runs with a single worker to avoid concurrency issues. For high-throughput scenarios, run multiple API instances behind a load balancer.

## Integration Example (Rails)

```ruby
class XbrlValidator
  API_URL = ENV.fetch("ARELLE_API_URL", "http://localhost:8000")

  def self.validate(xml_string)
    response = Net::HTTP.post(
      URI("#{API_URL}/validate"),
      xml_string,
      "Content-Type" => "application/xml"
    )

    JSON.parse(response.body)
  end
end

# Usage
result = XbrlValidator.validate(survey.to_xbrl)

if result["valid"]
  puts "XBRL is valid!"
else
  result["messages"].each do |msg|
    next if msg["severity"] == "info"
    puts "#{msg['severity'].upcase}: #{msg['message']}"
  end
end
```
