"""Tests for JSON and Markdown writers."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from cliniq.extraction.engine import ExtractionResult
from cliniq.output.json_writer import write_result
from cliniq.output.markdown_writer import write_markdown
from cliniq.schemas.medical_note import Diagnosis, MedicalNote, NoteFlag, NoteType


@pytest.fixture()
def empty_result(tmp_path: Path) -> ExtractionResult:
    return ExtractionResult(source=tmp_path / "sample.pdf")


@pytest.fixture()
def result_with_note(tmp_path: Path) -> ExtractionResult:
    r = ExtractionResult(source=tmp_path / "report.pdf")
    r.notes.append(
        MedicalNote(
            date=date(2025, 6, 1),
            source_file="report.pdf",
            type=NoteType.GP_NOTE,
            summary="Routine checkup.",
            diagnoses=[Diagnosis(code="I10", label="Hypertension")],
        )
    )
    return r


def test_json_writer_creates_five_files(tmp_path: Path, empty_result: ExtractionResult) -> None:
    write_result(empty_result, tmp_path)
    dest = tmp_path / "sample"
    for name in ("medical_note", "contact", "appointment", "medication", "symptom"):
        assert (dest / f"{name}.json").exists()


def test_json_writer_note_roundtrip(tmp_path: Path, result_with_note: ExtractionResult) -> None:
    write_result(result_with_note, tmp_path)
    dest = tmp_path / "report" / "medical_note.json"
    data = json.loads(dest.read_text())
    assert len(data) == 1
    assert data[0]["diagnoses"][0]["code"] == "I10"


def test_markdown_writer_creates_summary(tmp_path: Path, empty_result: ExtractionResult) -> None:
    write_markdown(empty_result, tmp_path)
    assert (tmp_path / "sample" / "summary.md").exists()


def test_markdown_writer_note_content(tmp_path: Path, result_with_note: ExtractionResult) -> None:
    write_markdown(result_with_note, tmp_path)
    content = (tmp_path / "report" / "summary.md").read_text()
    assert "Hypertension" in content
    assert "I10" in content


def test_markdown_writer_flags(tmp_path: Path, empty_result: ExtractionResult) -> None:
    empty_result.notes.append(
        MedicalNote(
            date=date(2025, 1, 1),
            source_file="sample.pdf",
            flags=[NoteFlag.LOW_OCR_CONFIDENCE],
        )
    )
    write_markdown(empty_result, tmp_path)
    content = (tmp_path / "sample" / "summary.md").read_text()
    assert "Low Ocr Confidence" in content
