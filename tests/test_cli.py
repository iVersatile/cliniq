"""Tests for the CLI layer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cliniq.cli import main


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output


def test_extract_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["extract", "--help"])
    assert result.exit_code == 0
    assert "PDFS_DIR" in result.output or "pdfs" in result.output.lower()


def test_extract_empty_dir(tmp_path: Path) -> None:
    runner = CliRunner()
    # Patch the lazy imports inside extract()
    with patch("cliniq.adapters.get_adapter", return_value=MagicMock()):
        with patch("cliniq.extraction.engine.ExtractionEngine", return_value=MagicMock()):
            result = runner.invoke(main, ["extract", str(tmp_path)])
    assert result.exit_code == 0


def test_extract_processes_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    out_dir = tmp_path / "out"

    mock_result = MagicMock()
    mock_engine = MagicMock()
    mock_engine.process.return_value = mock_result

    runner = CliRunner()
    with patch("cliniq.adapters.get_adapter", return_value=MagicMock()):
        with patch("cliniq.extraction.engine.ExtractionEngine", return_value=mock_engine):
            result = runner.invoke(main, ["extract", str(tmp_path), "--output", str(out_dir)])

    assert result.exit_code == 0
    mock_engine.process.assert_called_once_with(pdf)
    mock_result.write.assert_called_once()
