# cliniq — Delivery Plan

**Version:** 1.0  
**Date:** 2026-05-19  
**Ref:** docs/Health_Skill_Assessment.md §7 + docs/PRD.md

---

## Phases at a Glance

| Phase | Name | Weeks | Deliverable |
|-------|------|-------|-------------|
| 0 | OCR Foundation | 1–2 | pdfplumber + pytesseract pipeline; test corpus |
| 0-CI | CI/CD Bootstrap | 1 | Green pipeline, coverage gate, release workflow |
| 1 | Prompt Library + Schemas | 3–4 | Pydantic models; prompts tested against Claude API |
| 2 | Ollama Adapter + CLI | 5–6 | `cliniq extract` working end-to-end; accuracy baseline |
| 3 | MCP Server | 7 | `cliniq serve` + Claude Desktop integration test |
| 4 | QA & Accuracy Tuning | 8–10 | 20+ doc corpus; >= 90% medication precision |
| 5 | Additional Adapters | 11–13 | Claude / OpenAI / Gemini adapters (parallel) |
| 6 | Windows Installer | 14 | Zero-install `.exe` for GPs |
| 7 | GP Persona *(optional)* | 15–19 | Multi-patient index; FHIR R4 |

---

## Phase 0 — OCR Foundation (Weeks 1–2)

**Goal:** Reliable text extraction from any clinical PDF before any LLM work begins.

### Tasks

- [x] `P0-01` — Verify `pdfplumber` text-layer detection on 5 born-digital sample PDFs
- [x] `P0-02` — Verify `pytesseract` OCR path on 5 scanned sample PDFs (300 DPI)
- [x] `P0-03` — Implement `LOW_OCR_CONFIDENCE` flagging (threshold: mean conf < 60)
- [x] `P0-04` — Implement `HANDWRITTEN_SECTION` detection and marker injection
- [x] `P0-05` — Build initial test corpus: 5 born-digital + 5 scanned (anonymised via presidio or synthetic via Faker+reportlab)
- [x] `P0-06` — Write ground-truth JSON for all 10 corpus docs
- [x] `P0-07` — `tests/test_ingestion.py`: parametrised tests against corpus; assert text non-empty + flag correctness
- [x] `P0-08` — Image preprocessing pipeline before Tesseract: grayscale conversion, contrast enhancement, sharpening, binarisation (Otsu threshold); exposed as `preprocess_image()` in `cliniq/ingestion/preprocessing.py`
- [x] `P0-09` — Add structured logging to ingestion pipeline: log per-page OCR fallback decisions, Tesseract mean confidence scores, and any caught exceptions using Python `logging` module; no `print()` statements anywhere in `src/cliniq/ingestion/`
- [x] `P0-10` — Fix release smoke-test: install Tesseract on all three OS runners (apt / brew / choco) and upgrade smoke-test from `cliniq --help` to `read_pdf()` call on a fixture PDF (exercises full ingestion + Tesseract path)

### Acceptance Criteria

- [x] `read_pdf()` returns non-empty text for all 5 born-digital corpus PDFs without invoking OCR
- [x] `read_pdf()` invokes pytesseract for all 5 scanned corpus PDFs and returns non-empty text
- [x] Pages with mean OCR confidence < 60 carry `LOW_OCR_CONFIDENCE` flag
- [x] Pages producing no extractable text carry `[HANDWRITTEN — review manually]` marker
- [x] All 10 corpus PDFs have corresponding ground-truth JSON in `test_corpus/*/ground_truth/`
- [x] `pytest tests/test_ingestion.py` passes parametrised against all 10 corpus docs with zero failures
- [x] No corpus PDF causes an unhandled exception
- [x] `preprocess_image()` improves or maintains Tesseract confidence vs. raw image on scanned corpus (mean conf delta >= 0)
- [x] Ingestion pipeline emits `logging.DEBUG` records for OCR fallback decisions and confidence scores; no `print()` in `src/cliniq/ingestion/`

### Definition of Done

- [x] All task checkboxes in this phase are checked
- [x] `ruff check`, `ruff format --check`, `mypy` pass with zero errors
- [x] `pytest --cov-fail-under=80` passes; no regressions vs. previous phase
- [x] Remote CI green on `main` for all matrix legs (Python 3.11 + 3.12)
- [x] No PHI, real names, NHS numbers, or API keys in any committed file or CI log
- [x] `PLAN.md` task checkboxes updated to reflect actual state
- [ ] **Human approval received before phase is marked complete**

---

## Phase 1 — Prompt Library + JSON Schemas (Weeks 3–4)

**Goal:** Locked extraction contract — prompts + schemas are the stable interface all adapters implement against.

### Tasks

- [x] `P1-00` — Fix Phase 0 code-review findings (severity order): (a) CRITICAL: wrap pytesseract calls in `ocr_page()` with try/except — unhandled exceptions crash full ingestion; (b) CRITICAL: wrap `pdfplumber.open()` loop in `read_pdf()` with try/except — corrupted PDF gives raw traceback with no context; (c) HIGH: replace `page: object` with `pdfplumber.page.Page` type in `ocr_page()` signature — defeats mypy; (d) HIGH: use context-manager to restore logger level in `_run_ingestion()` (local_test.py) — global mutation is race-prone in parallel test runs
- [x] `P1-01` — Finalise Pydantic models: `MedicalNote`, `Contact`, `Appointment`, `Medication`, `Symptom`
- [x] `P1-02` — Write extraction prompt for `medical_note` (outpatient letter template)
- [x] `P1-03` — Write extraction prompt for `medical_note` (discharge summary template)
- [x] `P1-04` — Write extraction prompt for `medical_note` (lab report template)
- [x] `P1-05` — Write extraction prompt for `medication` + `contact` + `appointment`
- [x] `P1-06` — Test all prompts against Claude API (fastest feedback loop; not the shipping backend)
- [ ] `P1-07` — Add source-sentence citation field to medication + diagnosis extraction ← in progress
- [ ] `P1-08` — `tests/test_prompts.py`: golden-file tests — run prompt on fixture text, assert schema validates + key fields match ground truth

### Acceptance Criteria

- [ ] All five Pydantic models (`MedicalNote`, `Contact`, `Appointment`, `Medication`, `Symptom`) validate without error on their respective ground-truth JSON fixtures
- [ ] Each schema field has a type annotation and a default or `Field(...)` — no bare `Any`
- [ ] Prompts for outpatient letter, discharge summary, and lab report each return valid `MedicalNote` via Claude API
- [ ] Every medication and diagnosis extraction includes a non-empty `source` sentence verbatim from the input text
- [ ] Golden-file tests (`tests/test_prompts.py`) pass on all prompt families against Claude API
- [ ] A schema breaking change (field rename/removal) requires a version bump — enforced by test

### Definition of Done

- [x] All task checkboxes in this phase are checked
- [x] `ruff check`, `ruff format --check`, `mypy` pass with zero errors
- [ ] `pytest --cov-fail-under=80` passes; no regressions vs. previous phase
- [ ] Remote CI green on `main` for all matrix legs (Python 3.11 + 3.12)
- [ ] Schemas declared frozen — no breaking changes without explicit version bump
- [ ] No PHI, real names, NHS numbers, or API keys in any committed file or CI log
- [ ] `PLAN.md` task checkboxes updated to reflect actual state
- [ ] **Human approval received before phase is marked complete**

---

## Phase 2 — Ollama Adapter + CLI (Weeks 5–6)

**Goal:** Working `cliniq extract` command using local Ollama backend; accuracy measured.

### Tasks

- [ ] `P2-01` — Implement `OllamaAdapter.complete_json()` with JSON extraction fallback (find `{...}` in response)
- [ ] `P2-02` — Wire `ExtractionEngine` prompts → adapter → schema validation
- [ ] `P2-03` — Implement `json_writer.py` and `markdown_writer.py` (currently stubs)
- [ ] `P2-04` — Implement `cli.py extract` command with per-file progress output
- [ ] `P2-05` — Test Ollama with `phi3:mini` on full corpus; record precision/recall per field
- [ ] `P2-06` — Tune prompts based on Ollama accuracy results
- [ ] `P2-07` — `tests/test_cli.py`: integration test — run `cliniq extract` on corpus dir; assert output JSON exists + validates

### Acceptance Criteria

- [ ] `cliniq extract ./test_corpus --output /tmp/out --backend ollama` completes without unhandled exception on all 10 corpus docs
- [ ] Output directory contains `medical_note.json`, `contact.json`, `appointment.json`, `medication.json`, `symptom.json` for each processed PDF
- [ ] Every output JSON validates against its Pydantic schema
- [ ] `summary.md` is written for each PDF and is human-readable
- [ ] Medication name + dose precision >= 80% measured against ground-truth corpus (10 docs)
- [ ] Precision/recall baseline recorded in `docs/accuracy_report.md`
- [ ] `pytest tests/test_cli.py` passes — output files exist and validate
- [ ] `cliniq --help` and `cliniq extract --help` display correct usage

### Definition of Done

- [x] All task checkboxes in this phase are checked
- [x] `ruff check`, `ruff format --check`, `mypy` pass with zero errors
- [ ] `pytest --cov-fail-under=80` passes; no regressions vs. previous phase
- [ ] Remote CI green on `main` for all matrix legs (Python 3.11 + 3.12)
- [ ] `docs/accuracy_report.md` committed with baseline numbers
- [ ] No PHI, real names, NHS numbers, or API keys in any committed file or CI log
- [ ] `PLAN.md` task checkboxes updated to reflect actual state
- [ ] **Human approval received before phase is marked complete**

---

## Phase 3 — MCP Server (Week 7)

**Goal:** `cliniq serve` exposes tools consumable by Claude Desktop, Open WebUI, and any MCP client.

### Tasks

- [ ] `P3-01` — Implement `extract_document` tool (calls `ExtractionEngine.process`)
- [ ] `P3-02` — Implement `list_medications` tool (reads `medication.json` files from records dir)
- [ ] `P3-03` — Implement `get_timeline` tool (sorts `medical_note.json` by date; returns Markdown)
- [ ] `P3-04` — Wire `cli.py serve` to start MCP server via stdio transport
- [ ] `P3-05` — Integration test: connect Claude Desktop to `cliniq serve`; call `extract_document` on a test PDF
- [ ] `P3-06` — `tests/test_mcp_server.py`: unit tests for each tool handler

### Acceptance Criteria

- [ ] `cliniq serve` starts without error; process remains alive until SIGINT
- [ ] `extract_document(pdf_path)` tool returns structured summary for a test PDF
- [ ] `list_medications(records_dir)` tool returns a JSON array of medication objects
- [ ] `get_timeline(records_dir)` tool returns a date-sorted Markdown timeline
- [ ] Claude Desktop can call all three tools over stdio transport and display results
- [ ] At least one additional MCP client (Open WebUI or Zed) confirmed working
- [ ] `pytest tests/test_mcp_server.py` passes all tool handler unit tests
- [ ] Tool input validation rejects missing required fields with a clear error message (no stack trace)

### Definition of Done

- [x] All task checkboxes in this phase are checked
- [x] `ruff check`, `ruff format --check`, `mypy` pass with zero errors
- [ ] `pytest --cov-fail-under=80` passes; no regressions vs. previous phase
- [ ] Remote CI green on `main` for all matrix legs (Python 3.11 + 3.12)
- [ ] MCP integration tested against ≥ 2 clients (Claude Desktop + one other)
- [ ] No PHI, real names, NHS numbers, or API keys in any committed file or CI log
- [ ] `PLAN.md` task checkboxes updated to reflect actual state
- [ ] **Human approval received before phase is marked complete**

---

## Phase 4 — QA & Accuracy Tuning (Weeks 8–10)

**Goal:** Ship-quality accuracy on real-world clinical documents.

### Tasks

- [ ] `P4-01` — Expand corpus to 20+ documents (mix of letter types, trusts, layouts)
- [ ] `P4-02` — Add prescription and radiology report types to corpus
- [ ] `P4-03` — Measure precision/recall per field per document type; log in `docs/accuracy_report.md`
- [ ] `P4-04` — Identify top-5 failure modes; tune prompts per failure mode
- [ ] `P4-05` — Add fallback heuristics for common extraction failures (e.g., regex date extraction when LLM returns null)
- [ ] `P4-06` — Rerun full corpus; verify medication precision >= 90%

### Acceptance Criteria

- [ ] Corpus expanded to ≥ 20 documents covering: outpatient letter, discharge summary, lab report, prescription, radiology report
- [ ] Corpus includes documents from ≥ 3 different NHS trusts / layouts
- [ ] Medication name + dose precision >= 90% on full 20-doc corpus
- [ ] Top-5 failure modes identified, each with a corresponding prompt fix or heuristic
- [ ] `docs/accuracy_report.md` updated with per-field, per-document-type precision/recall table
- [ ] No field regression vs. Phase 2 baseline (no metric goes down without documented reason)
- [ ] Fallback heuristics (e.g., regex date extraction) covered by dedicated unit tests

### Definition of Done

- [x] All task checkboxes in this phase are checked
- [x] `ruff check`, `ruff format --check`, `mypy` pass with zero errors
- [ ] `pytest --cov-fail-under=80` passes; no regressions vs. previous phase
- [ ] Remote CI green on `main` for all matrix legs (Python 3.11 + 3.12)
- [ ] `docs/accuracy_report.md` committed — all metrics visible, no placeholders
- [ ] Corpus anonymisation verified — presidio scan on all new docs before commit
- [ ] No PHI, real names, NHS numbers, or API keys in any committed file or CI log
- [ ] `PLAN.md` task checkboxes updated to reflect actual state
- [ ] **Human approval received before phase is marked complete**

---

## Phase 5 — Additional Adapters (Weeks 11–13, parallel)

**Goal:** Cloud adapter options for users who prefer API quality over local privacy.

### Tasks (each adapter ~1 week, can run in parallel)

- [ ] `P5-01` — `adapters/claude.py`: Anthropic SDK, structured output via tool use
- [ ] `P5-02` — `adapters/openai.py`: OpenAI SDK, JSON mode
- [ ] `P5-03` — `adapters/gemini.py`: Google Generative AI SDK
- [ ] `P5-04` — `tests/test_adapters.py`: parametrised adapter contract tests (mock HTTP)
- [ ] `P5-05` — Document adapter configuration in `docs/adapters.md`

### Acceptance Criteria

- [ ] `adapters/claude.py`, `adapters/openai.py`, `adapters/gemini.py` all implement `LLMAdapter` ABC without type errors
- [ ] Parametrised adapter contract tests (`tests/test_adapters.py`) pass for all three adapters using mocked HTTP
- [ ] `cliniq extract --backend claude` runs end-to-end on the 10-doc corpus; output validates against schemas
- [ ] Each adapter reads its API key from an environment variable — never from a hardcoded default
- [ ] Missing API key raises a clear `EnvironmentError` with the expected variable name, not an HTTP 401 stack trace
- [ ] `docs/adapters.md` documents setup steps and environment variables for each adapter

### Definition of Done

- [x] All task checkboxes in this phase are checked
- [x] `ruff check`, `ruff format --check`, `mypy` pass with zero errors
- [ ] `pytest --cov-fail-under=80` passes; no regressions vs. previous phase
- [ ] Remote CI green on `main` for all matrix legs (Python 3.11 + 3.12)
- [ ] API keys never appear in test output, CI logs, or committed fixtures
- [ ] No PHI, real names, NHS numbers, or API keys in any committed file or CI log
- [ ] `PLAN.md` task checkboxes updated to reflect actual state
- [ ] **Human approval received before phase is marked complete**

---

## Phase 6 — Windows Installer (Week 14)

**Goal:** Zero-install UX for GPs on Windows machines.

### Tasks

- [ ] `P6-01` — Test full pipeline on Windows 10/11 (VM or CI)
- [ ] `P6-02` — Bundle: Ollama Windows binary + Python 3.11 embedded + cliniq wheel
- [ ] `P6-03` — Build Inno Setup installer; include Tesseract Windows binary
- [ ] `P6-04` — Installer creates `cliniq` shortcut + registers PATH
- [ ] `P6-05` — Smoke test installer on clean Windows VM: `cliniq extract` runs without any manual setup

### Acceptance Criteria

- [ ] Installer `.exe` produced by Inno Setup; file size < 500 MB
- [ ] Installer runs silently on a clean Windows 10 VM with no pre-installed Python, Ollama, or Tesseract
- [ ] `cliniq extract ./test_corpus --output ./out --backend ollama` completes successfully after install
- [ ] `cliniq serve` starts on the installed Windows build
- [ ] Uninstaller cleanly removes all installed components
- [ ] Windows CI smoke test in `.github/workflows/release.yml` passes on `windows-latest` runner

### Definition of Done

- [x] All task checkboxes in this phase are checked
- [x] `ruff check`, `ruff format --check`, `mypy` pass with zero errors
- [ ] `pytest --cov-fail-under=80` passes; no regressions vs. previous phase
- [ ] Remote CI green on `main` for all matrix legs (Python 3.11 + 3.12)
- [ ] Installer tested on Windows 10 **and** Windows 11 (VM or CI)
- [ ] No PHI, real names, NHS numbers, or API keys in installer bundle or build logs
- [ ] `PLAN.md` task checkboxes updated to reflect actual state
- [ ] **Human approval received before phase is marked complete**

---

## Phase 7 — GP Persona (Weeks 15–19, optional)

**Goal:** Multi-patient record management for clinical use.

### Tasks

- [ ] `P7-01` — Patient namespace: `--patient-id` flag; records stored under `records/<patient_id>/`
- [ ] `P7-02` — Cross-patient medication aggregation view
- [ ] `P7-03` — Cross-patient diagnosis frequency report
- [ ] `P7-04` — FHIR R4 JSON export for `MedicalNote` and `Medication`
- [ ] `P7-05` — Role-based output filtering (GP view vs. patient view)

### Acceptance Criteria

- [ ] `--patient-id` flag namespaces all output under `records/<patient_id>/`; cross-patient file collision is impossible
- [ ] Cross-patient medication aggregation view returns deduplicated medication list across all patients
- [ ] Cross-patient diagnosis frequency report ranks diagnoses by occurrence count
- [ ] FHIR R4 JSON for `MedicalNote` and `Medication` validates against official FHIR R4 schema
- [ ] GP view omits patient-private annotations; patient view omits clinical workflow fields
- [ ] Multi-patient index survives addition/removal of individual patient record sets without data loss

### Definition of Done

- [x] All task checkboxes in this phase are checked
- [x] `ruff check`, `ruff format --check`, `mypy` pass with zero errors
- [ ] `pytest --cov-fail-under=80` passes; no regressions vs. previous phase
- [ ] Remote CI green on `main` for all matrix legs (Python 3.11 + 3.12)
- [ ] GDPR / data residency review completed — no cross-patient data leak possible via API
- [ ] FHIR R4 output validated against official HL7 FHIR validator
- [ ] No PHI, real names, NHS numbers, or API keys in any committed file or CI log
- [ ] `PLAN.md` task checkboxes updated to reflect actual state
- [ ] **Human approval received before phase is marked complete**

---

---

## Phase 0-CI — CI/CD Bootstrap (Week 1, parallel with Phase 0)

**Goal:** Green pipeline from day one; every commit is verified.

### Tasks

- [x] `CI-01` — Create `.github/workflows/ci.yml`: triggers on PR + push; runs ruff lint, ruff format check, mypy, pytest
- [x] `CI-02` — Matrix: Python 3.11 + 3.12
- [x] `CI-03` — Add `pytest-cov` coverage gate: fail if coverage < 80%
- [ ] `CI-04` — Post coverage report as PR comment via `coverage-comment-action`
- [x] `CI-05` — Create `.github/workflows/release.yml`: triggers on `v*.*.*` tag
- [ ] `CI-06` — Release pipeline: build wheel with `hatch build`; smoke-test `pip install dist/*.whl && cliniq --help` on macOS + Linux + Windows runners
- [ ] `CI-07` — Configure PyPI trusted publisher (OIDC) — no API token stored in secrets
- [x] `CI-08` — Add `ruff.toml` / `mypy.ini` section to `pyproject.toml` (already present); verify no false positives on scaffold
- [ ] `CI-09` — Branch protection rule on `main`: require CI green + 1 review before merge

### Acceptance Criteria

- [x] `.github/workflows/ci.yml` triggers on PR and push; all steps pass on scaffold commit
- [x] Matrix covers Python 3.11 and 3.12 — both legs green
- [x] Coverage gate rejects any commit that drops below 80%
- [ ] `.github/workflows/release.yml` triggers on `v*.*.*` tag; wheel builds and smoke-tests on macOS + Linux + Windows
- [ ] PyPI trusted publisher configured (OIDC) — no `PYPI_TOKEN` secret stored
- [ ] Branch protection active on `main`: CI required + 1 review before merge
- [x] CI run completes in < 5 minutes on a standard GitHub-hosted runner
- [ ] Coverage badge URL documented in repo (to be added to README when created)

### Definition of Done

- [ ] All task checkboxes in this phase are checked
- [x] Workflows committed and visible in `.github/workflows/`
- [x] Remote CI green on first real commit post-scaffold
- [ ] Branch protection rule active — verified by attempting a direct push to `main` (should be rejected)
- [x] No secrets stored as GitHub Actions secrets except those explicitly required (none at this stage)
- [x] `PLAN.md` task checkboxes updated to reflect actual state
- [x] **Human approval received before phase is marked complete**

---

## Risk Watch

| Risk | Phase | Mitigation |
|------|-------|------------|
| Ollama 3B model quality gap on clinical abbreviations | P2 | Prompt tuning; user can switch to larger model |
| pdfplumber inadequate on complex lab tables | P4 | Upgrade path to Docling/Marker if QA reveals systematic failure |
| PDF format variation across NHS trusts | P4 | Corpus must include docs from ≥ 3 different trusts |
| Tesseract install friction on Windows | P6 | Bundle Tesseract binary in installer |
| LLM hallucinates medication dose | P1–P4 | Source-sentence citation mandatory per field; confidence flag |
| **Gap: pages with text layer + embedded images silently drop image content** | P0–P4 | `read_pdf()` uses pdfplumber text layer when present and skips raster images on the same page (e.g. header logos, scan inserts, chart images). Options to close: (a) extract `page.images` separately via pdfplumber and pass each image region through `ocr_page()` alongside the text layer; (b) replace pdfplumber extraction with Docling or Marker for full hybrid text+image extraction; (c) post-process with a vision model on image regions after text extraction. Deferring to Phase 4 QA unless a P1 fixture reveals extraction failures caused by this gap. |

---

## Definition of Done (each phase)

1. All phase tasks checked off
2. `pytest` passes with no regressions
3. No PHI in logs (grep `tests/` + `src/` for real names/DOBs before commit)
4. PLAN.md updated — task checkboxes reflect actual state
