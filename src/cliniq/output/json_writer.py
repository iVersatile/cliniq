"""Write ExtractionResult to per-type JSON files in output_dir."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_result(result, output_dir: Path) -> None:  # type: ignore[no-untyped-def]
    stem = result.source.stem
    dest = output_dir / stem
    dest.mkdir(parents=True, exist_ok=True)

    def _dump(name: str, items: list[Any]) -> None:
        data = [i.model_dump(mode="json") for i in items]
        (dest / f"{name}.json").write_text(json.dumps(data, indent=2, default=str))

    _dump("medical_note", result.notes)
    _dump("contact", result.contacts)
    _dump("appointment", result.appointments)
    _dump("medication", result.medications)
    _dump("symptom", result.symptoms)
