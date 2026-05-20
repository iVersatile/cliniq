# Bridgeform — Product Requirements Document

**Version:** 0.1-DRAFT  
**Date:** 2026-05-20  
**Status:** Draft — clarification questions outstanding (see §9)

---

## 1. Problem

Extraction systems that pull structured data from unstructured text share a recurring pattern: define the entity, write a system prompt, write a Pydantic schema, wire them together. This pattern is reproduced by hand for every entity type in every project. Prompt quality is inconsistent, schema-prompt alignment drifts silently, and adding a new entity requires touching Python source code even when the business logic is conceptually simple.

Cliniq currently encodes this as hardcoded per-entity functions: `extract_medications()`, `extract_conditions()`, `extract_contacts()`. Adding a new entity type requires writing a new module.

---

## 2. Product Vision

Bridgeform is a general-purpose library that compiles a structured entity specification (YAML, TOML, or Python dataclass) into three artefacts:

1. An LLM system prompt — ready to pass to any completion API
2. A Pydantic model class — for schema validation of the LLM response
3. A registered extractor callable — invokable as a tool/skill by an agent or pipeline

The goal: define a new entity type in a config file, get a working extractor without writing Python.

---

## 3. Target Users

| User | Goal | Entry point |
|------|------|-------------|
| **Cliniq (primary consumer)** | Ship domain-specific entity types (medication, condition, symptom…) as YAML config, not Python modules | Python API / YAML file |
| **Developer building an extraction pipeline** | Register custom entity types without forking the extraction engine | Python API |
| **Domain expert (no-code, future)** | Define entity fields in a structured form and get a working extractor | YAML / TOML config file |

---

## 4. Scope

### In scope — v1 (library, Python-only)

- `EntitySpec` dataclass: name, description, fields with type + description + constraints
- `PromptCompiler`: generates a system prompt from `EntitySpec` using a template
- `SchemaBuilder`: generates a Pydantic model class from `EntitySpec` at runtime
- `ExtractorRegistry`: maps entity type name → callable extractor; supports lookup and iteration
- Python API for registering specs and invoking extractors
- YAML config loader (`bridgeform.load("path/to/spec.yaml")`)
- Output: JSON array of validated entity instances per document

### Out of scope — v1

- Prompt quality evaluation harness (Phase 4)
- Multi-LLM prompt compatibility testing (GPT, Gemini, Claude — different system prompt conventions)
- GUI / web form for spec authoring
- Schema versioning / migration
- Fine-tuned prompt optimisation

---

## 5. Functional Requirements

### FR-B1 EntitySpec

| ID | Requirement |
|----|-------------|
| FR-B1.1 | `EntitySpec` accepts: `name` (str), `description` (str), `fields` (list of `FieldSpec`) |
| FR-B1.2 | `FieldSpec` accepts: `name`, `type` (str — "string", "date", "number", "boolean", "enum", "list"), `description`, `required` (bool), `enum_values` (optional list), `constraints` (optional free text) |
| FR-B1.3 | `EntitySpec` is serialisable to / from YAML with no information loss |
| FR-B1.4 | `EntitySpec` can be declared in Python as a dataclass or loaded from YAML/TOML file |

### FR-B2 PromptCompiler

| ID | Requirement |
|----|-------------|
| FR-B2.1 | `PromptCompiler.compile(spec)` returns a system prompt string |
| FR-B2.2 | Generated prompt instructs the LLM to return a JSON array of objects, one per extracted entity |
| FR-B2.3 | Prompt includes a field-by-field rule block derived from `FieldSpec.description` |
| FR-B2.4 | Prompt includes explicit null-handling instruction: absent fields must be `null`, never hallucinated |
| FR-B2.5 | Prompt includes citation instruction: verbatim source sentence for each entity |
| FR-B2.6 | PromptCompiler accepts an optional `template_overrides` dict to customise prompt sections |

### FR-B3 SchemaBuilder

| ID | Requirement |
|----|-------------|
| FR-B3.1 | `SchemaBuilder.build(spec)` returns a Pydantic `BaseModel` subclass |
| FR-B3.2 | Field types map: string → `str \| None`, date → `date \| None`, number → `float \| None`, boolean → `bool \| None`, enum → `Literal[...] \| None`, list → `list[str]` |
| FR-B3.3 | Generated model is `frozen=True` (immutable) |
| FR-B3.4 | Generated model includes `citation: str \| None` field always |
| FR-B3.5 | `SchemaBuilder.build(spec)` is deterministic: same `EntitySpec` always produces same schema |

### FR-B4 ExtractorRegistry

| ID | Requirement |
|----|-------------|
| FR-B4.1 | `ExtractorRegistry.register(spec, adapter)` compiles prompt + schema and stores them under `spec.name` |
| FR-B4.2 | `ExtractorRegistry.extract(entity_name, doc_text)` calls the registered adapter with the compiled prompt and validates results against the generated schema |
| FR-B4.3 | Per-item validation failures are caught, logged, and skipped — extraction continues |
| FR-B4.4 | `ExtractorRegistry.list_entities()` returns registered entity names |
| FR-B4.5 | Registry is injectable — supports passing a test adapter for unit testing without a live LLM |

### FR-B5 YAML Loader

| ID | Requirement |
|----|-------------|
| FR-B5.1 | `bridgeform.load(path)` accepts a `.yaml` or `.toml` file and returns an `EntitySpec` |
| FR-B5.2 | `bridgeform.load_dir(path)` loads all spec files in a directory and registers them |
| FR-B5.3 | YAML parse errors surface as `BridgeformConfigError` with file path and line number |

---

## 6. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Portability** | Zero LLM vendor dependency — works with any adapter implementing `complete_json(system, user, schema)` |
| **Python** | >= 3.11 |
| **Dependencies** | Pydantic >= 2.0; PyYAML; no other mandatory runtime deps |
| **Testing** | 80%+ coverage; mock adapter for all unit tests — no live LLM calls in CI |
| **Extensibility** | Custom prompt templates replaceable without forking the library |

---

## 7. Architecture Sketch

```
EntitySpec (YAML / Python)
        │
        ▼
PromptCompiler ──► system_prompt (str)
        │
SchemaBuilder  ──► DynamicModel (Pydantic class)
        │
ExtractorRegistry
        │  register(spec, adapter)
        │  extract(name, doc_text) ──► list[DynamicModel]
        │
LLMAdapter (injected)
  complete_json(system, user, schema)
```

Cliniq as consumer:

```
cliniq/entity_specs/
  medication.yaml
  condition.yaml
  symptom.yaml
  contact.yaml
  appointment.yaml
        │
        ▼
bridgeform.load_dir("entity_specs/")  ──► ExtractorRegistry
        │
ExtractionAgent.run(doc_text)
  for entity in registry.list_entities():
      results[entity] = registry.extract(entity, doc_text)
```

---

## 8. Evolution Path (Options A → C)

| Option | Description | Complexity | Status |
|--------|-------------|------------|--------|
| **A — Registered** | Human-authored prompt + schema registered as `EntitySpec` | Low | Exists in Cliniq today (hardcoded) |
| **B — Auto-prompt** | Prompt auto-generated from `FieldSpec.description`; schema still generated | Medium | Bridgeform v1 target |
| **C — YAML-only** | Full entity type defined in YAML; zero Python required | High | Bridgeform v1 end state |

---

## 9. Clarification Questions

These must be resolved before v1 implementation begins.

**Q1 — Minimum viable config format**  
Should the v1 YAML schema be fixed (Bridgeform-owned) or pluggable? If Cliniq ships domain YAMLs and another consumer ships different YAMLs, can they coexist without a shared registry format? Or is one canonical `entity_spec.schema.yaml` the constraint?

**Q2 — Type inference depth**  
For `type: "date"`, should Bridgeform infer `datetime.date` vs `datetime.datetime` from the description (e.g. "ISO 8601 date" vs "timestamp"), or should the spec author always be explicit? Implicit inference risks wrong Python types silently.

**Q3 — Prompt quality evaluation**  
How do we measure whether a generated prompt is as good as a hand-authored one? Minimum bar for v1: golden-file tests where generated prompt + real LLM → validates schema. Or is a richer evaluation harness (precision/recall against ground truth) a v1 requirement?

**Q4 — Multi-LLM prompt compatibility**  
Different LLMs respond differently to "return JSON array only — no prose, no markdown fences." Should Bridgeform ship prompt templates per LLM family (Ollama/llama, Claude, GPT), or assume a single template works well enough for v1?

**Q5 — Schema versioning**  
If a YAML spec changes (field added, type changed), existing extracted JSON may not validate. Is schema migration a v1 concern, or deferred? A broken migration could silently corrupt a patient's record.

**Q6 — Relationship to Cliniq extraction engine**  
Does Bridgeform replace `cliniq/extraction/prompts/` entirely (preferred), or is it an optional path alongside handcrafted prompts? Keeping both paths means two sources of truth for prompt logic.

**Q7 — Agent integration contract**  
When an extraction agent calls `registry.extract(entity_name, doc_text)`, should it receive raw validated instances, or a richer result envelope (confidence, skipped_count, warnings)? This affects how agents decide whether to retry or escalate.

---

## 10. Open Decisions

| Decision | Options | Default assumption |
|----------|---------|-------------------|
| Package name | `bridgeform`, `entityform`, `specbridge` | **bridgeform** |
| Standalone repo vs Cliniq sub-package | Standalone (publishable separately) | **Standalone** |
| Prompt template format | Jinja2 vs f-string vs dict-based | **f-string for v1; Jinja2 if templates grow complex** |
| Registry scope | Global singleton vs injected instance | **Injected instance (testable)** |
