"""Write ExtractionResult to a human-readable Markdown file."""

from __future__ import annotations

from pathlib import Path


def write_markdown(result, output_dir: Path) -> None:  # type: ignore[no-untyped-def]
    stem = result.source.stem
    dest = output_dir / stem
    dest.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [f"# {stem}\n"]

    for note in result.notes:
        lines.append(f"## {note.type.value.replace('_', ' ').title()} — {note.date}")
        if note.summary:
            lines.append(f"\n{note.summary}\n")
        if note.diagnoses:
            lines.append("### Diagnoses")
            for d in note.diagnoses:
                lines.append(f"- {d.label} ({d.code})")
        if note.flags:
            for flag in note.flags:
                lines.append(f"\n⚠️  {flag.value.replace('_', ' ').title()}")
        lines.append("\n---")

    (dest / "summary.md").write_text("\n".join(lines))
