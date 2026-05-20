"""Orchestrates ingestion → prompts → adapter → schema validation → output."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cliniq.adapters.base import LLMAdapter
from cliniq.ingestion.pdf_reader import DocumentText, read_pdf
from cliniq.schemas import Appointment, Condition, Contact, MedicalNote, Medication, Symptom


@dataclass
class ExtractionResult:
    source: Path
    notes: list[MedicalNote] = field(default_factory=list)
    contacts: list[Contact] = field(default_factory=list)
    appointments: list[Appointment] = field(default_factory=list)
    medications: list[Medication] = field(default_factory=list)
    symptoms: list[Symptom] = field(default_factory=list)
    conditions: list[Condition] = field(default_factory=list)

    def write(self, output_dir: Path) -> None:
        from cliniq.output.json_writer import write_result
        from cliniq.output.markdown_writer import write_markdown

        write_result(self, output_dir)
        write_markdown(self, output_dir)


class ExtractionEngine:
    def __init__(self, adapter: LLMAdapter) -> None:
        self.adapter = adapter

    def process(self, pdf_path: Path) -> ExtractionResult:
        doc: DocumentText = read_pdf(pdf_path)
        result = ExtractionResult(source=pdf_path)
        from cliniq.extraction.prompts import extract_all

        extract_all(doc, self.adapter, result)
        return result
