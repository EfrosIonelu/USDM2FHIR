# USDM2FHIR

Converts a clinical study design in **USDM** (Unified Study Definitions Model) format into **FHIR** resources (ResearchStudy, Group, Location, EvidenceVariable).

The mappings are stored as JSONata queries in `Map/USDM2FHIR.csv` and can be adjusted to fit different FHIR resource needs.

---

## Project structure

```
USDM2FHIR/
├── app/
│   ├── controllers/
│   │   ├── index_controller.py     # GET /health
│   │   └── transform_controller.py # POST /transform
│   └── services/
│       └── transform_service.py    # Transformation logic (in-memory)
├── Input/                          # Example USDM JSON files
├── Map/
│   └── USDM2FHIR.csv              # JSONata mapping rules
├── CreateFhir.py                   # Core transformation logic
├── ResolveTags.py                  # Tag resolver helper
├── main.py                         # FastAPI entry point
├── Dockerfile
├── Makefile
└── requirements.txt
```

---

## Prerequisites

- Python 3.11+ **or** Docker

---

## Quick start (local)

```bash
# 1. Clone the repo
git clone <repo-url>
cd USDM2FHIR

# 2. Create venv and install dependencies
make setup

# 3. Start the API server
make run
```

The API will be available at `http://localhost:8000`.

---

## Quick start (Docker)

```bash
# Build the image
make docker-build

# Run the container
make docker-run
```

---

## API

### `GET /health`
Returns service status.

```bash
curl http://localhost:8000/health
```
```json
{
  "status": "ok",
  "service": "USDM2FHIR API",
  "timestamp": "2026-07-06T10:00:00Z"
}
```

---

### `POST /transform`
Transforms a USDM JSON payload into a FHIR resource.

**Request body:** raw USDM JSON  
**Response:** FHIR ResearchStudy JSON (or Bundle if multiple studies)

```bash
curl -X POST http://localhost:8000/transform \
  -H "Content-Type: application/json" \
  -d @Input/NCT01750580_limited_tagged_resp.json
```

**Optional query parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `id`      | `123`   | FHIR resource ID |
| `version` | `1`     | FHIR meta.versionId |
| `updated` | today   | FHIR meta.lastUpdated (ISO 8601) |

---

## Command-line usage (without API)

```bash
source venv/bin/activate
python CreateFhir.py \
  --map Map/USDM2FHIR.csv \
  --usdm Input/NCT01750580_limited_tagged_resp.json \
  --output Output/result.json
```

Or via Makefile:
```bash
make execute_example
```

---

## Interactive API docs

When the server is running, open: `http://localhost:8000/docs`

---

## Makefile targets

| Target | Description |
|--------|-------------|
| `make setup` | Create venv and install dependencies |
| `make run` | Start API server (with hot reload) |
| `make execute_example` | Run CLI transformation example |
| `make docker-build` | Build Docker image |
| `make docker-run` | Run Docker container on port 8000 |
| `make docker-stop` | Stop the running container |
