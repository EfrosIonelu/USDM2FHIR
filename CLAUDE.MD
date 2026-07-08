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
│   ├── config/
│   │   └── mappings/              # ✏️ EDIT HERE — one YAML file per FHIR path group
│   │       ├── 01_condition.yaml
│   │       ├── 02_identifier.yaml
│   │       ├── 03_label.yaml
│   │       ├── 04_classifier.yaml
│   │       ├── 05_objective.yaml
│   │       ├── 06_purpose_type.yaml
│   │       ├── 07_phase.yaml
│   │       ├── 08_progress_status.yaml
│   │       ├── 09_comparison_group.yaml
│   │       ├── 10_site.yaml
│   │       ├── 11_recruitment.yaml
│   │       ├── 12_eligibility_criteria.yaml
│   │       ├── 13_eligibility_group.yaml
│   │       ├── 14_evidence_variable.yaml
│   │       ├── 15_study_design.yaml
│   │       └── 16_extension.yaml
│   └── command/
│       ├── jsonata_inspect.py     # CLI: metadata about a JSONata path
│       ├── jsonata_query.py       # CLI: actual value at a JSONata path
│       └── yaml_to_csv.py         # CLI: merge YAML files → Map/USDM2FHIR.csv
│
├── Map/
│   └── USDM2FHIR.csv             # ⚠️ AUTO-GENERATED — do not edit directly, edit the YAML files
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

# ✏️  WORKFLOW: edit a YAML file in app/config/mappings/, then:
make yaml-to-csv          # regenerates Map/USDM2FHIR.csv from all YAML files

# Run the transformation CLI example
make execute_example

# Start the FastAPI API on port 8000
make run

# Docker
make docker-build
make docker-run
make docker-stop
make docker-push
```

---

## YAML mapping files (how to add/edit mappings)

**Never edit `Map/USDM2FHIR.csv` directly** — it is auto-generated.

Mappings live in `app/config/mappings/`, one YAML file per FHIR path group,
named with a numeric prefix so they merge in the right order.

### YAML file format

```yaml
description: "Human-readable description of this group"

mappings:
  - item: "Row name (shown in CSV)"
    usdm_path: |
      study.versions.studyDesigns.(
        ... JSONata expression — no escaping needed, use " naturally ...
      )
    fhir_resource: ResearchStudy          # or Group, Group-all, Location, EvidenceVariable
    fhir_path: extension                  # dot-separated FHIR path
    fhir_index: extension                 # grouping key for array indexing (optional)
    usdm_class: PopulationDefinition      # USDM class name (optional, documentation only)
    usdm_attribute: plannedAge            # USDM attribute name (optional, documentation only)
```

**Key advantage of YAML over CSV:** JSONata expressions with `"` quotes, `{}`, `[]`
are written naturally — no `""` escaping needed.

### After editing any YAML file, regenerate the CSV:

```bash
make yaml-to-csv
# or directly:
venv/bin/python -m app.command.yaml_to_csv
```

Optional flags:
```bash
make yaml-to-csv MAPPINGS_DIR=app/config/mappings OUTPUT=Map/USDM2FHIR.csv
```

### Adding a new mapping group

1. Create `app/config/mappings/NN_my_group.yaml` (choose the next number)
2. Fill in the `mappings:` list following the format above
3. Run `make yaml-to-csv`
4. Run `make execute_example` to verify

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
