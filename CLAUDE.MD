# CLAUDE.MD — Guide for LLMs working in this project

## What the project does

**USDM2FHIR** converts JSON files in **USDM** format (Unified Study Definition Model — CDISC standard for clinical studies) into **FHIR** resources (Fast Healthcare Interoperability Resources — HL7 standard).

The transformation is driven by a CSV mapping file (`Map/USDM2FHIR.csv`) that links JSONata paths from USDM to FHIR fields. The output is a `ResearchStudy` FHIR resource with `Group`, `Location`, and `EvidenceVariable` resources embedded in `contained`.

---

## Project structure

```
USDM2FHIR/
├── main.py                        # FastAPI app — registers routers
├── CreateFhir.py                  # Core transformation logic (Parse_jsonata, create_fhir_resource)
├── ResolveTags.py                 # Resolves inline tags from USDM texts
├── requirements.txt               # Python dependencies
├── Makefile                       # Build/run commands (see Commands section)
├── Dockerfile                     # Docker container
│
├── app/
│   ├── controllers/
│   │   ├── index_controller.py    # GET /health
│   │   └── transform_controller.py# POST /transform  — main endpoint
│   ├── services/
│   │   └── transform_service.py   # Transformation logic without file I/O
│   └── command/
│       ├── jsonata_inspect.py     # CLI: metadata about a JSONata path
│       └── jsonata_query.py       # CLI: actual value at a JSONata path
│
├── Map/
│   └── USDM2FHIR.csv             # USDM → FHIR mapping file
│
├── Input/                         # ⚠️ DO NOT read these files directly — see rule below
│   ├── NCT01750580_limited_tagged_resp.json   # Default input file (USDM)
│   └── CDISC_Pilot_Study_v4_FIXED.json
│
└── Output/                        # Generated results
```

---

## ⚠️ Critical rule for large JSON files

**Never read files from `Input/` or `Output/` directly.** They are large JSON files (tens of thousands of lines) that consume all tokens without benefit.

Use the CLI commands below instead to query precisely what you need.

**Rule for collections (arrays):** read only the first element — `array[0]` — unless you explicitly need another one.

---

## Makefile commands

All commands run with the Python from the virtualenv (`venv/bin/python`).

```bash
# Initial setup — creates venv and installs dependencies
make setup

# Start the FastAPI API on port 8000
make run

# Run the transformation CLI example
make execute_example

# Docker
make docker-build
make docker-run
make docker-stop
make docker-push
```

---

## CLI commands for JSON exploration (for LLMs)

The default input file for both commands is `Input/NCT01750580_limited_tagged_resp.json`.

### 1. `jsonata-inspect` — structure of a path

Returns **metadata** about the result: type, length, keys, key types, sample — without returning the actual data.

```bash
# Via Makefile
make jsonata-inspect EXPR="study.versions"
make jsonata-inspect EXPR="study.versions[0].studyDesigns[0]" FLAGS="--json"

# Direct
venv/bin/python -m app.command.jsonata_inspect "study.versions"
venv/bin/python -m app.command.jsonata_inspect "study.versions[0]" --json
venv/bin/python -m app.command.jsonata_inspect "study.versions[0]" --raw   # also includes the raw result
```

**When to use:** when you don't know the structure of a field, how many elements an array has, or what keys an object has.

---

### 2. `jsonata-query` — actual value at a path

Returns the **actual result** of the JSONata expression, truncated to **250 characters** if too large. When truncated, it shows a hint to use `jsonata-inspect` to refine the expression.

```bash
# Via Makefile
make jsonata-query EXPR="study.versions[0].versionIdentifier"
make jsonata-query EXPR="study.versions[0].studyDesigns[0].name" FLAGS="--json"

# Direct
venv/bin/python -m app.command.jsonata_query "study.studyTitle"
venv/bin/python -m app.command.jsonata_query "study.versions[0].versionIdentifier" --json
```

**When to use:** when you already know the path and want the concrete value.

---

### Recommended exploration workflow

```
1. jsonata-query  →  if result is truncated (>250 chars)  →  follow the hint
2. jsonata-inspect →  explore structure, find keys and types
3. jsonata-query  →  with a more specific expression  →  full result
```

**Practical example:**
```bash
# 1. Try directly
make jsonata-query EXPR="study"
# → truncated, hint: use jsonata-inspect

# 2. Inspect the structure
make jsonata-inspect EXPR="study" FLAGS="--json"
# → see that it has key "versions" of type array[1]

# 3. Go deeper
make jsonata-inspect EXPR="study.versions[0]" FLAGS="--json"
# → see object keys: studyDesigns, studyTitle, versionIdentifier etc.

# 4. Extract the desired value
make jsonata-query EXPR="study.versions[0].versionIdentifier"
```

---

## REST API

Started with `make run` → `http://localhost:8000`

| Method | Path         | Description                                    |
|--------|--------------|------------------------------------------------|
| GET    | `/health`    | Health check                                   |
| POST   | `/transform` | Transform USDM JSON (body) → FHIR JSON         |

**POST /transform** — optional query parameters:
- `id` (default `"123"`) — FHIR resource ID
- `version` (default `"1"`) — FHIR versionId
- `updated` — ISO 8601 timestamp for `meta.lastUpdated`

---

## Local setup and run

```bash
# 1. Setup venv + dependencies
make setup

# 2. Activate venv (optional for interactive terminal)
source venv/bin/activate

# 3. Start API
make run
```

---

## Technologies used

- **Python 3.13** + **FastAPI** + **uvicorn**
- **jsonata-python** — JSONata expression evaluation on JSON data
- **pandas** — CSV mapping file processing
- **Click** — CLI commands
- **Docker** — containerisation, registry: `ghcr.io/efrosionelu/usdm2fhir`
