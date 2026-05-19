"""Tests for extraction prompt stubs."""

from __future__ import annotations

from unittest.mock import MagicMock

from cliniq.extraction.prompts import extract_all
from cliniq.extraction.prompts.appointment import extract_appointments
from cliniq.extraction.prompts.contact import extract_contacts
from cliniq.extraction.prompts.medical_note import extract_medical_note
from cliniq.extraction.prompts.medication import extract_medications


def _stub_args():
    doc = MagicMock()
    adapter = MagicMock()
    result = MagicMock()
    return doc, adapter, result


def test_extract_all_calls_each_prompt() -> None:
    doc, adapter, result = _stub_args()
    # Should not raise even though all are stubs
    extract_all(doc, adapter, result)


def test_extract_contacts_no_raise() -> None:
    extract_contacts(*_stub_args())


def test_extract_medications_no_raise() -> None:
    extract_medications(*_stub_args())


def test_extract_appointments_no_raise() -> None:
    extract_appointments(*_stub_args())


def test_extract_medical_note_no_raise() -> None:
    extract_medical_note(*_stub_args())
