# Health Skill — Feasibility Assessment

**Version:** 0.2  
**Date:** 2026-05-19  
**Status:** Architecture Locked — Ready for Project Setup

---

## 1. Vision & Scope

A standalone, offline-first **Health Skill** that accepts a collection of PDF medical records and produces:

| Output | Format |
|--------|--------|
| Medical Notes | `medical_note.json` + Markdown |
| Clinics & Doctors | `contact.json` |
| Appointment History & Reminders | `appointment.json` |
| Symptoms & Medication Monitor | `symptom.json` · `medication.json` |

**Two primary user personas:**

- **Patient (self)** — manages own records; wants a clean, readable timeline
- **GP / Clinician** — manages multiple patients' records on Windows machines; needs structured, filterable data

**Core constraints:**

- Local-only processing — no cloud upload of PHI ever
- Platform-agnostic output (JSON + Markdown) — importable by any AI tool or app
- CPU-only operation — no GPU requirement (supports home users + GP Windows machines)
- Human-readable formatting: clear sections, bullet lists, grids; noise stripped

---

## 2. OCR & Document Intelligence Layer

> ✅ **Resolved.** See §9 — Decisions Log.

### 2.1 Document Mix (confirmed)

| Type | Proportion | Strategy |
|------|------------|----------|
| Born-digital PDF (text layer present) | ~50% | pdfplumber — extract text directly, no OCR |
| Scanned paper (image-only pages) | ~50% | pytesseract (Tesseract 5) — CPU-native fallback |
| Handwritten clinical notes | <5% (rare) | Flag as `[HANDWRITTEN — review manually]`; skip in v1 |

### 2.2 Chosen Stack

**Two-tier pipeline (CPU-only):**

```
Tier 1 — Structural extraction (always local)
  pdfplumber → detect if text layer exists
    → YES: extract text directly (fast, no OCR)
    → NO:  pytesseract (Tesseract 5) per page image (CPU, proven)
    → output: plain text per page, table cells where detectable

Tier 2 — Clinical NLP (pluggable LLM adapter)
  Ollama (default, local) | Claude | OpenAI | Gemini (all via thin adapters)
    → entity extraction: dates, medications, diagnoses, clinics, contacts
    → output: Health Skill JSON schemas (see §4)
```

**Why pdfplumber + Tesseract, not Docling/Marker?**

| Criterion | Docling/Marker | pdfplumber + Tesseract |
|-----------|---------------|------------------------|
| CPU-only support | Yes, but slow | Yes, fast for text-layer docs |
| Integration complexity | Medium-High | Low |
| Already proven in myHealth | No | Tesseract: Yes |
| Layout/table extraction | Excellent | Adequate for clinical letters |
| Dependency footprint | Heavy (Python ML stack) | Light |

For the 50% born-digital docs (the majority of clinical letters), Docling's layout advantage does not apply — pdfplumber reads the text layer directly with no OCR at all. Tesseract handles the other 50%. Docling/Marker remains an upgrade path if table accuracy proves insufficient.

**Handwriting:** out of scope for v1. Flag with `[HANDWRITTEN — review manually]` in output JSON.

---

## 3. AI Platform Decision

> ✅ **Resolved.** Option E (prompt spec) + Ollama as default adapter.

### Architecture: Option E — Platform-agnostic Prompt Spec

Define Health Skill as a **prompt library + JSON Schema + extraction pipeline spec**. Any LLM plugs in via a thin adapter. No vendor lock-in.

**Default adapter: Ollama (local)**
- Model: `phi-3-mini:3.8b-instruct-q4_K_M` or `llama3.2:3b-instruct-q4_K_M`
- Runs on 8GB RAM, CPU-only, ~8–15s per page section on Apple Silicon; slower on Intel/Windows but usable
- No API key, no internet, no PHI leaves device

**Additional adapters (thin swaps, ~1 week each):**
- Anthropic (Claude API)
- OpenAI (ChatGPT)
- Google Gemini

**Why this is LLM-agnostic:** the MCP server exposes tools (`extract_clinic`, `extract_medications`, etc.). Any LLM with tool-calling (Claude, Gemini, ChatGPT, Ollama + Open WebUI) calls the same tools. One server, any front-end.

### Adapter comparison

| Adapter | Local | Cost | Quality | Effort |
|---------|-------|------|---------|--------|
| Ollama (default) | ✅ | Free | Good (8B) / Better (70B) | 1 week |
| Claude MCP | ❌ | API $ | Best | 1 week |
| OpenAI | ❌ | API $ | Excellent | 1 week |
| Gemini | ❌ | API $ | Excellent | 1 week |

---

## 4. Output Schemas

### 4.1 JSON Schemas

**medical_note.json**
```json
{
  "id": "note_uuid",
  "date": "2025-03-14",
  "source_file": "letter_2025-03-14.pdf",
  "clinic": "contact_uuid",
  "clinician": "contact_uuid",
  "type": "outpatient_letter | discharge_summary | lab_report | radiology | gp_note | prescription | other",
  "summary": "Brief human-readable summary (1-3 sentences)",
  "diagnoses": [{ "code": "J45.9", "system": "ICD-10", "label": "Asthma, unspecified" }],
  "medications": ["medication_uuid"],
  "next_appointment": "appointment_uuid",
  "flags": ["HANDWRITTEN_SECTION", "LOW_OCR_CONFIDENCE"],
  "raw_text": "...",
  "sections": {
    "presenting_complaint": "...",
    "examination": "...",
    "investigations": "...",
    "plan": "..."
  }
}
```

**contact.json** — clinic name, address, phone, speciality (reuses myHealth schema)

**appointment.json** — date, clinic_id, clinician_id, reason, status (past/upcoming), reminder_at

**medication.json** — name, dose, frequency, start_date, end_date, prescribed_by

**symptom.json** — symptom, first_noted, last_noted, severity_trend, linked_notes[]

### 4.2 Human-readable Markdown Output (example)

```
## Outpatient Letter — 14 March 2025
Clinic:     Royal Free Hospital, Cardiology
Clinician:  Dr. A. Shah
Summary:    Follow-up for hypertension. BP controlled on current regimen.
            Annual echo recommended.

### Diagnoses
- Hypertension (I10) — ongoing

### Medications
- Amlodipine 5mg once daily (continue)

### Plan
- Annual echocardiogram — book via GP
- Follow-up in 12 months

---
⚠️  Page 2 contains handwritten annotation — review manually
```

---

## 5. Architecture

```
+-------------------------------------------------------------+
|              Health Skill — Standalone Python Package        |
|                   (pip install health-skill)                 |
+------------------------------+------------------------------+
                               |
              +----------------v-----------------+
              |         Document Ingestion        |
              |  pdfplumber → detect text layer   |
              |  pytesseract fallback for images  |
              +----------------+-----------------+
                               |
              +----------------v-----------------+
              |        Extraction Engine          |
              |   Prompt Library + JSON Schema    |
              |  +-----------------------------+  |
              |  |      LLM Adapter (config)   |  |
              |  |  Ollama (default, local)    |  |
              |  |  Claude | OpenAI | Gemini   |  |
              |  +-----------------------------+  |
              +----------------+-----------------+
                               |
         +---------------------+---------------------+
         |                     |                     |
+--------v-------+   +---------v-------+   +--------v--------+
|  Output Writer  |   |   MCP Server    |   |  CLI Interface  |
|  JSON + .md     |   |  (any LLM can   |   |  health-skill   |
|  importable by  |   |   call tools)   |   |  extract *.pdf  |
|  myHealth etc.  |   |                 |   |                 |
+-----------------+   +-----------------+   +-----------------+
```

**myHealth integration path (Option C):** Health Skill runs as a local MCP server. myHealth (or any LLM client) calls its tools over IPC. No file import/export required for tight integration.

---

## 6. Feasibility Assessment

### 6.1 Technical Feasibility

| Component | Status | Notes |
|-----------|--------|-------|
| PDF text extraction | ✅ Ready | pdfplumber — production grade |
| OCR (image PDFs) | ✅ Ready | Tesseract 5, CPU-native, already proven in myHealth |
| Table extraction | Adequate | pdfplumber handles simple tables; complex lab tables may need QA |
| Handwriting | ⏭ Deferred | Out of scope v1; flag-and-skip |
| Clinical NLP (Ollama) | 🟡 Good enough | 8B models handle typed clinical text; improve as models grow |
| JSON Schema output | ✅ Ready | Structured-output / function-calling in all major APIs |
| MCP server | ✅ Ready | fastmcp / mcp-python — 1 week to working server |
| CPU-only deployment | ✅ Ready | All chosen tools CPU-native |

### 6.2 Market Fit

| Persona | Pain | Willingness to pay |
|---------|------|--------------------|
| Patient (self) | Scattered paper records; no timeline | Medium (£5–15/month or one-time) |
| GP (multi-patient, Windows) | Summarising lengthy referral letters | High (£20–50/month) |
| Researcher | Cohort data extraction | Very high (enterprise) |

### 6.3 Build Time Estimate (revised)

| Phase | Scope | Estimate |
|-------|-------|----------|
| 0 — OCR pipeline | pdfplumber + pytesseract, page routing | 1–2 weeks |
| 1 — Prompt library + JSON schema | Core extraction prompts, Pydantic models | 2 weeks |
| 2 — Ollama adapter + CLI | Default local adapter, `health-skill` CLI | 1–2 weeks |
| 3 — MCP server | Expose tools over MCP protocol | 1 week |
| 4 — QA on real documents | Build corpus, measure accuracy, tune prompts | 2–3 weeks |
| 5 — Additional adapters | Claude / OpenAI / Gemini (1 week each) | 1–3 weeks |
| 6 — Windows installer | NSIS/Inno Setup bundling Ollama + Python + health-skill | 1 week |
| **Total (patient persona + Ollama + Windows)** | | **9–14 weeks** |
| + GP persona features | Multi-patient index, comparison views | +3–5 weeks |

### 6.4 Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| OCR fails on handwritten sections | High | Low (v1) | Flag as [HANDWRITTEN]; deferred |
| LLM hallucinates medications/dosages | Medium | High | Require source text citation per field; confidence threshold |
| GDPR / data residency (EU, GP use) | High | High | Ollama local-only default; never default to cloud for GP |
| PDF format variation across NHS trusts | High | Medium | Test corpus; measure per-type accuracy before shipping |
| 8B model quality gap on clinical abbreviations | Medium | Medium | Prompt tuning; user can switch to larger model or cloud adapter |
| Ollama install friction for home users | Medium | Medium | Windows installer bundles everything (Phase 6) |
| pdfplumber table extraction inadequate | Low | Medium | Upgrade path to Docling/Marker if tables prove insufficient |

---

## 7. Phased Roadmap (revised)

### Phase 0 — OCR Foundation (weeks 1–2)
- Scaffold Python package structure
- Implement pdfplumber text-layer detection
- Implement pytesseract fallback for image-only pages
- Build test corpus: 10 anonymised PDFs (5 born-digital, 5 scanned) with ground-truth JSON

### Phase 1 — Extraction Spec (weeks 3–4)
- Define JSON schemas (Pydantic models) — these are the contract
- Write prompt library for each document type (letter, lab, discharge, prescription)
- Test prompts against Claude API first (fastest feedback loop); then port to Ollama

### Phase 2 — Ollama Adapter + CLI (weeks 5–6)
- Implement Ollama adapter (phi-3-mini / llama3.2 3B Q4 default)
- CLI: `health-skill extract ./pdfs/ --output ./records/ --backend ollama`
- Measure extraction accuracy against ground-truth corpus

### Phase 3 — MCP Server (week 7)
- Implement MCP server with tools: `extract_document`, `list_clinics`, `list_medications`, `get_timeline`
- Test with Claude Desktop + Ollama + Open WebUI

### Phase 4 — QA & Accuracy Tuning (weeks 8–10)
- Expand corpus to 20+ documents
- Precision/recall per field per document type
- Tune prompts; add fallback heuristics

### Phase 5 — Additional Adapters (weeks 11–13, parallel)
- Claude adapter (1 week)
- OpenAI adapter (1 week)
- Gemini adapter (1 week)

### Phase 6 — Windows Installer (week 14)
- Bundle: Ollama Windows binary + Python + health-skill
- NSIS or Inno Setup installer
- Target: GP Windows machines, zero manual setup

### Phase 7 — GP Persona (weeks 15–19, optional)
- Multi-patient index (patient_id namespacing)
- Cross-patient medication/diagnosis aggregation
- FHIR R4 JSON export (if required by GP workflow)

---

## 8. Test Corpus Strategy

**Goal:** 10–20 anonymised PDFs with ground-truth JSON before Phase 2 completes.

**Anonymisation options:**

| Option | Tool | Best for | Effort |
|--------|------|----------|--------|
| **A — Redact real docs** | presidio (Microsoft, Apache-2) | Born-digital PDFs | Low — NER detects names, DOB, NHS#, addresses |
| **B — Synthetic generation** | Faker + reportlab | Scanned simulation (print → scan) | Low — full ground truth for free |

**Recommended:** Use both. Presidio for the 5 born-digital docs; Faker+reportlab for 5 synthetic scanned-simulation docs (print them, photograph/scan, add to corpus). Gives realistic ground truth without manual annotation.

**Corpus structure:**
```
test_corpus/
├── born_digital/
│   ├── invoice_001.pdf
│   ├── discharge_001.pdf
│   └── ground_truth/
│       ├── invoice_001.json
│       └── discharge_001.json
└── scanned/
    ├── scan_001.pdf
    └── ground_truth/
        └── scan_001.json
```

---

## 9. Decisions Log

All open questions from v0.1 resolved:

| Question | Decision |
|----------|----------|
| PDF corpus composition | ~50% born-digital, ~50% scanned, <5% handwritten |
| Handwriting support | Deferred — v1 flags and skips; olmOCR not needed |
| GPU requirement | None — CPU-only throughout (home users + GP Windows) |
| OCR tool | pdfplumber (text-layer) + pytesseract/Tesseract (images) |
| Deployment model | Standalone Python package (not bundled into myHealth) |
| First LLM backend | Ollama (local-first) |
| Additional backends | Claude, OpenAI, Gemini — thin adapters, ~1 week each |
| LLM-agnostic? | Yes — MCP server + prompt spec; any tool-calling LLM works |
| myHealth integration | Option C: MCP server (IPC, no file import/export) |
| Test corpus | Real docs anonymised via presidio + synthetic via Faker+reportlab |
| Windows packaging | Bundled installer (Inno Setup/NSIS) — zero-install UX for GPs |
| FHIR output | Deferred to GP persona phase; JSON + Markdown sufficient for v1 |
