# Bridgeform — Delivery Plan

**Version:** 0.1-DRAFT  
**Date:** 2026-05-20  
**Ref:** docs/BRIDGEFORM_PRD.md  
**Status:** Draft — blocked on Q1–Q7 in PRD §9

---

## Phases at a Glance

| Phase | Name | Deliverable |
|-------|------|-------------|
| BF-1 | EntitySpec + Registry skeleton | `EntitySpec`, `FieldSpec`, `ExtractorRegistry` with injected adapter; Python API only |
| BF-2 | PromptCompiler + SchemaBuilder | Auto-generated prompts and Pydantic models from `EntitySpec` |
| BF-3 | YAML / TOML config loader | Load entity specs from files; zero-Python entity definition |
| BF-4 | Evaluation harness | Golden-file tests; precision/recall measurement against ground truth |
| BF-5 | Cliniq migration | Replace `cliniq/extraction/prompts/` with Bridgeform YAML specs |

---

## Phase BF-1 — EntitySpec + Registry Skeleton

**Goal:** Minimal Python API that allows registering an entity with a hand-authored prompt and schema, and extracting instances from text. Equivalent to what Cliniq does today, but via a clean interface instead of hardcoded modules.

**Unblocked by:** PRD Q6 (relationship to Cliniq engine) must be answered before BF-5, but BF-1 can proceed as standalone.

### Tasks

- [ ] `BF-1-01` — Define `FieldSpec` dataclass: `name`, `type`, `description`, `required`, `enum_values`, `constraints`
- [ ] `BF-1-02` — Define `EntitySpec` dataclass: `name`, `description`, `fields: list[FieldSpec]`
- [ ] `BF-1-03` — Implement `ExtractorRegistry` with `register(spec, adapter, prompt, model)` (Option A — human-authored prompt + existing model passed in)
- [ ] `BF-1-04` — Implement `ExtractorRegistry.extract(entity_name, doc_text)` → `list[BaseModel]`
- [ ] `BF-1-05` — Per-item ValidationError handling: catch, log warning, skip; return partial results
- [ ] `BF-1-06` — `ExtractorRegistry.list_entities()` → `list[str]`
- [ ] `BF-1-07` — Injectable adapter interface: `LLMAdapter` protocol with `complete_json(system, user, schema)`
- [ ] `BF-1-08` — Unit tests: register a mock entity + mock adapter; assert extract() returns validated instances; assert bad items are skipped and warned
- [ ] `BF-1-09` — `pyproject.toml` scaffold; `pip install -e .` succeeds; `ruff`, `mypy`, `pytest` all green

### Acceptance Criteria

- [ ] `registry.register(spec, adapter, prompt=..., model=...)` succeeds for a minimal spec
- [ ] `registry.extract("medication", sample_text)` returns `list[BaseModel]` with at least one item on happy-path fixture
- [ ] `registry.list_entities()` returns `["medication"]`
- [ ] Invalid LLM response items are skipped with `WARNING` log; extraction does not raise
- [ ] `pytest` passes with mock adapter; no live LLM calls required

---

## Phase BF-2 — PromptCompiler + SchemaBuilder

**Goal:** Derive the system prompt and Pydantic model automatically from `EntitySpec`. Human-authored prompts become optional.

**Blocked by:** PRD Q2 (type inference), Q4 (multi-LLM compatibility). Proceed with conservative defaults if unresolved.

### Tasks

- [ ] `BF-2-01` — Implement `SchemaBuilder.build(spec)`: map `FieldSpec.type` → Python type; create Pydantic model with `model_config = ConfigDict(frozen=True)`
- [ ] `BF-2-02` — `SchemaBuilder` always appends `citation: str | None` field
- [ ] `BF-2-03` — `SchemaBuilder.build()` is deterministic (same spec → same class name + fields)
- [ ] `BF-2-04` — Implement `PromptCompiler.compile(spec)`: generate system prompt string from spec name, description, and field rules
- [ ] `BF-2-05` — Prompt template sections: header (entity purpose) + field rules (one line per field) + null-handling footer + citation instruction + JSON array instruction
- [ ] `BF-2-06` — `ExtractorRegistry.register(spec, adapter)` (without explicit prompt/model) uses `PromptCompiler` + `SchemaBuilder` automatically
- [ ] `BF-2-07` — `PromptCompiler` accepts `template_overrides: dict[str, str]` to replace any section
- [ ] `BF-2-08` — Unit tests: compile prompt from a 3-field spec; assert field names appear in output; assert null-handling instruction present
- [ ] `BF-2-09` — Unit tests: build schema from a 3-field spec; assert field types correct; assert `citation` present; assert `frozen=True`
- [ ] `BF-2-10` — Golden-file test: compile prompt for `medication` spec; compare against reference string (detect unintended prompt regressions)

### Acceptance Criteria

- [ ] `PromptCompiler.compile(medication_spec)` produces a string containing all field names and null-handling instruction
- [ ] `SchemaBuilder.build(medication_spec)` returns a class whose instances validate a sample medication dict
- [ ] `registry.register(spec, adapter)` (no prompt arg) calls compiler + builder internally
- [ ] Generated prompt passes a mock-adapter round-trip: mock returns a valid JSON array → validated instances returned

---

## Phase BF-3 — YAML / TOML Config Loader

**Goal:** Entity types fully described in config files. No Python required to define a new entity.

**Blocked by:** PRD Q1 (config format must be decided), Q5 (schema versioning strategy).

### Tasks

- [ ] `BF-3-01` — Define canonical YAML schema for `EntitySpec` (draft in `docs/entity_spec_schema.yaml`)
- [ ] `BF-3-02` — Implement `bridgeform.load(path: str | Path) -> EntitySpec`; raise `BridgeformConfigError` on parse failure with file + line
- [ ] `BF-3-03` — Implement `bridgeform.load_dir(path) -> list[EntitySpec]`; load all `.yaml` / `.toml` files
- [ ] `BF-3-04` — TOML support via `tomllib` (stdlib >= 3.11)
- [ ] `BF-3-05` — `BridgeformConfigError` carries `file_path`, `line_number`, `message`
- [ ] `BF-3-06` — Unit tests: load valid YAML → `EntitySpec` matches expected; load invalid YAML → `BridgeformConfigError`
- [ ] `BF-3-07` — Write example specs: `medication.yaml`, `condition.yaml` mirroring current Cliniq entity shapes
- [ ] `BF-3-08` — `load_dir` test: directory with 2 specs → 2 `EntitySpec` objects; skips non-yaml files

### Acceptance Criteria

- [ ] `bridgeform.load("medication.yaml")` returns `EntitySpec` with correct name and fields
- [ ] Malformed YAML raises `BridgeformConfigError` with actionable message
- [ ] `bridgeform.load_dir("entity_specs/")` loads all specs in one call
- [ ] Example YAML files are self-documenting (comments on every field)

### Example YAML format (draft — subject to Q1)

```yaml
# bridgeform entity spec v1
name: medication
description: >
  A medication prescribed, continued, or stopped during a clinical encounter.
  Do not include medications mentioned only as allergies.
fields:
  - name: drug_name
    type: string
    description: "Drug name as written (generic preferred; brand in parentheses if present)"
    required: true
  - name: dose
    type: string
    description: "Dose string exactly as written (e.g. '5 mg', '10 mg/5 mL')"
    required: false
  - name: start_date
    type: date
    description: "ISO 8601 initiation date if explicitly stated"
    required: false
  - name: status
    type: enum
    enum_values: [active, stopped, changed]
    description: "Current prescription status"
    required: false
```

---

## Phase BF-4 — Evaluation Harness

**Goal:** Measure generated-prompt quality against hand-authored prompts. Required before Cliniq migration.

**Blocked by:** PRD Q3 (evaluation depth).

### Tasks

- [ ] `BF-4-01` — Design ground-truth fixture format: input text + expected entity list per entity type
- [ ] `BF-4-02` — Implement `bridgeform.eval.run(registry, fixtures_dir, adapter)` → precision/recall per field per entity type
- [ ] `BF-4-03` — CLI: `bridgeform eval --specs entity_specs/ --fixtures eval_fixtures/ --backend ollama`
- [ ] `BF-4-04` — Baseline: run eval on Cliniq's existing 10-doc corpus with hand-authored prompts; record numbers
- [ ] `BF-4-05` — Run eval with auto-generated prompts; compare delta vs baseline
- [ ] `BF-4-06` — Pass/fail threshold: auto-generated prompt precision >= hand-authored - 5% (configurable)

### Acceptance Criteria

- [ ] Eval runner produces per-field precision/recall table
- [ ] Baseline numbers for hand-authored prompts recorded in `docs/bridgeform_eval_baseline.md`
- [ ] Auto-generated prompt precision within 5% of hand-authored baseline on medication + condition

---

## Phase BF-5 — Cliniq Migration

**Goal:** Replace `cliniq/extraction/prompts/*.py` with Bridgeform YAML specs. Cliniq becomes a consumer.

**Blocked by:** BF-1 through BF-4 complete; PRD Q6 resolved.

### Tasks

- [ ] `BF-5-01` — Write YAML specs for all six Cliniq entity types (medication, condition, symptom, contact, appointment, medical_note)
- [ ] `BF-5-02` — Replace `cliniq/extraction/prompts/__init__.py` `extract_all()` with `registry.extract()` loop
- [ ] `BF-5-03` — Delete hardcoded prompt modules (`medication.py`, `condition.py`, etc.) — replace with YAML
- [ ] `BF-5-04` — Verify all existing `tests/test_golden.py` and `tests/test_prompts.py` still pass
- [ ] `BF-5-05` — Update `cliniq` `pyproject.toml` to add `bridgeform` as dependency
- [ ] `BF-5-06` — Update `docs/PRD.md` FR-2 to reflect config-driven extraction

### Acceptance Criteria

- [ ] `cliniq extract` produces identical output before and after migration on 10-doc corpus
- [ ] No handcrafted prompt Python modules remain in `cliniq/extraction/prompts/`
- [ ] `pytest --cov-fail-under=80` passes with no regressions
- [ ] Adding a new entity type requires only a new `.yaml` file — zero Python changes

---

## Cross-Cutting Concerns

### Testing strategy

- All phases: mock adapter in CI — no live LLM calls
- BF-4 eval: requires Ollama with phi3:mini running locally (same constraint as Cliniq P2-05)
- Golden-file tests: generated prompts checked against reference strings to detect regressions

### Dependency on Cliniq

Bridgeform is designed as a standalone library. It does not import from `cliniq`. Cliniq imports from Bridgeform (BF-5 onwards). This direction prevents circular dependency.

### Version compatibility

Bridgeform YAML spec format is versioned (`spec_version: 1`). Breaking changes to the spec format require a major version bump. Migration guide required before breaking changes.
