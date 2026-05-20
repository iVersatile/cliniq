# cliniq — Product Requirements Document

**Version:** 1.1  
**Date:** 2026-05-20  
**Status:** Living document — updated to reflect agent-based orchestration direction (see §2a)

---

## 1. Problem

Medical records are scattered across paper letters, scanned PDFs, and printed lab reports. Patients cannot search, filter, or track their own health history. GPs spend significant time summarising referral letters that contain clinically relevant information already in text form.

---

## 2. Product Vision

`cliniq` is a standalone, offline-first Python package that ingests PDF medical records and produces structured, human-readable output — a timeline, contact list, medication log, and appointment history — without any PHI leaving the device.

---

## 2a. Architectural Direction (updated 2026-05-20)

This section records the architectural framing agreed during design review. It does not change v1 scope but governs how future phases are designed.

### OCR as standalone skill

Tesseract/pdfplumber ingestion runs unconditionally as a pre-processing step and produces `DocumentText` (full text + per-page flags). This is a discrete, reusable skill. It does not change in the new architecture.

### Extraction tools replace fixed pipeline

The current `extract_all()` fixed pipeline — which calls `extract_medications()`, `extract_conditions()`, etc. in sequence — is replaced over time by individually invokable extraction tools. Each tool accepts `(doc_text, adapter)` and returns a typed list. An orchestration layer (agent or simple loop) decides which tools to call.

This removes the assumption that every entity is always extracted from every document. An agent can choose to extract only medications from a prescription letter, or only conditions from a discharge summary.

### Bridgeform as extraction tool compiler

The hardcoded per-entity prompt + schema modules (`cliniq/extraction/prompts/medication.py`, etc.) are replaced by Bridgeform, a standalone library that compiles YAML entity specs into LLM prompts, Pydantic schemas, and registered extractor callables. See `docs/BRIDGEFORM_PRD.md` and `docs/BRIDGEFORM_PLAN.md`.

Cliniq ships domain-specific YAML entity specs and consumes Bridgeform as a library. Adding a new entity type requires only a new `.yaml` file — no Python changes.

### Agent orchestration (future)

Phase 3+ (MCP server) exposes extraction tools as MCP-callable tools. A future agentic layer can invoke these tools dynamically based on document type, prior extraction results, or user query. This is not a v1 requirement but the architecture must not preclude it.

### Layered architecture summary

```
Layer 1 — Ingestion skill (stable):
  pdfplumber + Tesseract → DocumentText

Layer 2 — Extraction tools (evolving → Bridgeform-driven):
  extract_medications(doc, adapter) → list[Medication]
  extract_conditions(doc, adapter)  → list[Condition]
  ...each tool independently invokable

Layer 3 — Orchestration (current: simple loop; future: agent):
  decides which tools to call, aggregates results

Layer 4 — Output (stable):
  JSON + Markdown writers per entity type
```

---

---

## 3. Personas

| Persona | Goal | Key constraint |
|---------|------|----------------|
| **Patient (self)** | Clean readable health timeline from own records | Non-technical; wants install-and-run UX |
| **GP / Clinician** | Summarise referral letters for multiple patients | Windows machine; no cloud; needs structured, filterable data |
| **Researcher** *(future)* | Cohort data extraction | Enterprise; FHIR export; out of scope v1 |

---

## 4. Scope

### In scope — v1

- PDF ingestion: born-digital (pdfplumber) + scanned image (pytesseract/Tesseract 5)
- LLM-backed extraction via pluggable adapter (Ollama default)
- Six output schemas: `medical_note`, `contact`, `appointment`, `medication`, `symptom`, `condition`
- JSON + Markdown output (importable by any AI tool)
- CLI: `cliniq extract <dir> --output <dir> --backend ollama`
- MCP server with tools: `extract_document`, `list_medications`, `get_timeline`
- Ollama adapter (local, CPU-only, no API key)
- Windows installer bundling Ollama + Python + cliniq (Phase 6)

### Out of scope — v1

- Handwritten clinical notes (flagged as `[HANDWRITTEN — review manually]`, skipped)
- GPU acceleration (CPU-only throughout)
- Cloud upload of any PHI
- FHIR R4 export (deferred to GP persona phase)
- Multi-patient index / GP persona features
- Claude / OpenAI / Gemini adapters (Phase 5, parallel, optional)

---

## 5. Functional Requirements

### FR-1 Document Ingestion

| ID | Requirement |
|----|-------------|
| FR-1.1 | Detect whether a PDF page has a text layer using pdfplumber |
| FR-1.2 | Extract text directly from text-layer pages (no OCR) |
| FR-1.3 | Fall back to pytesseract OCR for image-only pages at 300 DPI |
| FR-1.4 | Flag pages with mean OCR confidence < 60 as `LOW_OCR_CONFIDENCE` |
| FR-1.5 | Flag pages producing no extractable text as `[HANDWRITTEN — review manually]` |

### FR-2 Extraction Engine

| ID | Requirement |
|----|-------------|
| FR-2.1 | Extract all six schema types from each document |
| FR-2.2 | Every medication and diagnosis must include a verbatim source sentence for traceability |
| FR-2.3 | Adapter is config-selectable at runtime (`--backend ollama`) |
| FR-2.4 | Prompts must instruct the LLM to return null for absent fields, never hallucinate |
| FR-2.5 | Extract `Condition` entities with `status`, `diagnosed_date`, `last_review_date`, and a `history` list of `ConditionEvent` records (date + measurement + notes) |
| FR-2.6 | Populate `Medication.duration_label` (human-readable e.g. "for 2 years") and `Medication.prescribed_by_name` (denormalised prescriber name) from document text |
| FR-2.7 | Each extraction function must be independently invokable as a discrete tool — not only callable via `extract_all()` |
| FR-2.8 | *(Future — Bridgeform)* Entity types are defined by YAML specs compiled by Bridgeform; hardcoded per-entity prompt modules are migration targets, not the end state |

### FR-3 Output

| ID | Requirement |
|----|-------------|
| FR-3.1 | Write per-document JSON files: `medical_note.json`, `contact.json`, `appointment.json`, `medication.json`, `symptom.json`, `condition.json` |
| FR-3.5 | `condition.json` must include full `history` array per condition (drilldown timeline) and `linked_medication_ids` for dashboard cross-reference |
| FR-3.2 | Write a human-readable `summary.md` per document |
| FR-3.3 | All dates in ISO 8601 format (YYYY-MM-DD) |
| FR-3.4 | UUIDs as stable cross-reference IDs between schemas |

### FR-4 CLI

| ID | Requirement |
|----|-------------|
| FR-4.1 | `cliniq extract <pdfs_dir> --output <out_dir> --backend <adapter>` |
| FR-4.2 | `cliniq serve [--port N]` starts MCP server |
| FR-4.3 | Progress output per file; clean error messages without stack traces |

### FR-5 MCP Server

| ID | Requirement |
|----|-------------|
| FR-5.1 | Tool: `extract_document(pdf_path, backend)` |
| FR-5.2 | Tool: `list_medications(records_dir)` |
| FR-5.3 | Tool: `get_timeline(records_dir)` |
| FR-5.4 | Server must work with Claude Desktop, Open WebUI, and any MCP-compatible client |

### FR-7 Container Deployment

| ID | Requirement |
|----|-------------|
| FR-7.1 | `Dockerfile` builds a self-contained cliniq image on `python:3.11-slim` with Tesseract 5 installed via `apt` |
| FR-7.2 | `docker-compose.yml` defines two services: `cliniq` (build: .) and `ollama` (image: `ollama/ollama`), linked so cliniq reaches Ollama without touching the host network |
| FR-7.3 | `OllamaAdapter` reads `OLLAMA_BASE_URL` env var (default `http://localhost:11434`) — no hardcoded host |
| FR-7.4 | `docker run cliniq cliniq --help` exits 0 (smoke test) |
| FR-7.5 | Container image must not embed any PHI, API keys, or real patient data |

---

## 6. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Privacy** | No PHI transmitted over network when using Ollama backend |
| **Performance** | Process a 10-page born-digital PDF in < 30s on CPU (Apple Silicon); scanned < 90s |
| **Platform** | macOS, Linux, Windows 10+; Docker (linux/amd64 and linux/arm64) |
| **Python** | >= 3.11 |
| **Accuracy** | >= 90% precision on medication name + dose extraction measured against ground-truth corpus |
| **Packaging** | `pip install cliniq` installs all dependencies; Tesseract documented as system prerequisite; Docker Compose as an alternative zero-prereq deployment path |

---

## 7. Acceptance Criteria (v1 ship gate)

- [ ] `cliniq extract ./test_corpus/born_digital/ --output /tmp/out` completes without error
- [ ] `cliniq extract ./test_corpus/scanned/ --output /tmp/out` completes without error
- [ ] Output JSON validates against all six Pydantic schemas (including `condition`)
- [ ] Handwritten-annotation PDFs produce `HANDWRITTEN_SECTION` flag, not a crash
- [ ] Medication extraction precision >= 90% on ground-truth corpus (20+ docs)
- [ ] `cliniq serve` starts MCP server; Claude Desktop can call `extract_document`
- [ ] `pip install cliniq` succeeds on macOS, Linux, Windows with Python 3.11+
- [ ] No PHI written to logs at any log level
- [ ] `docker build -t cliniq .` succeeds on a clean checkout
- [ ] `docker run --rm cliniq cliniq --help` exits 0
- [ ] `docker compose up` starts cliniq + ollama; `cliniq extract` reaches Ollama at `http://ollama:11434`

---

## 8. CI/CD Requirements

### Pipeline Triggers

| Event | Pipeline |
|-------|----------|
| PR opened / push to any branch | `ci` — lint, type-check, unit tests |
| Push to `main` | `ci` + `build` — wheel build, install smoke test |
| Tag `v*.*.*` | `ci` + `build` + `release` — PyPI publish |

### Required Checks (all must pass before merge)

| Check | Tool | Fail condition |
|-------|------|----------------|
| Lint | `ruff check src/ tests/` | Any lint error |
| Format | `ruff format --check src/ tests/` | Any formatting diff |
| Type check | `mypy src/cliniq` | Any type error |
| Unit tests | `pytest tests/ --cov=cliniq` | Any failure or coverage < 80% |
| Build | `pip install -e . && cliniq --help` | Install or CLI import failure |

### FR-6 CI/CD Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-6.1 | All checks run on Python 3.11 and 3.12 (matrix) |
| FR-6.2 | Test run must complete in < 5 minutes on standard GitHub-hosted runner |
| FR-6.3 | No secrets or PHI in CI logs at any verbosity level |
| FR-6.4 | Wheel artifact published to PyPI on semver tag via trusted publisher (OIDC, no token in secrets) |
| FR-6.5 | `pip install cliniq` smoke test runs on macOS, Linux, Windows in release pipeline |
| FR-6.6 | `docker build -t cliniq .` runs as a required check on every PR (build must succeed; no push required on PRs) |
| FR-6.7 | On semver tag, Docker image is built and pushed to `ghcr.io` alongside the PyPI release |

### Acceptance Criteria (CI/CD gate)

- [ ] PR CI green on first push for a clean scaffold commit
- [ ] Coverage report posted as PR comment
- [ ] Release pipeline produces `cliniq-x.y.z-py3-none-any.whl` and publishes to PyPI
- [ ] No `ANTHROPIC_API_KEY`, NHS numbers, or real patient names appear in any CI log
- [ ] Docker build check passes on every PR without pushing an image
- [ ] Tagged release pushes `ghcr.io/…/cliniq:x.y.z` and `ghcr.io/…/cliniq:latest`
