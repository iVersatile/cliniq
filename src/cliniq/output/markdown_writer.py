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

    if result.conditions:
        lines.append("\n## Conditions\n")
        for cond in result.conditions:
            meta: list[str] = [f"**Status:** {cond.status.value}"]
            if cond.diagnosed_date:
                meta.append(f"**Diagnosed:** {cond.diagnosed_date}")
            if cond.last_review_date:
                meta.append(f"**Last review:** {cond.last_review_date}")
            lines.append(f"### {cond.name}")
            lines.append("  ".join(meta))
            if cond.history:
                lines.append("\n| Date | Measurement | Notes |")
                lines.append("| --- | --- | --- |")
                for ev in cond.history:
                    date_str = str(ev.event_date) if ev.event_date else ""
                    meas = ev.measurement or ""
                    notes = ev.notes or ""
                    lines.append(f"| {date_str} | {meas} | {notes} |")
            lines.append("")

    (dest / "summary.md").write_text("\n".join(lines))
