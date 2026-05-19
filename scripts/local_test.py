"""Local test gate — run before pushing or tagging.

Usage:
    uv run python scripts/local_test.py

Checks (in order):
  1. CLI sanity  — `cliniq --help` exits 0
  2. Ingestion   — sample PDFs in samplepdf/Upload*.pdf  (skipped if absent)
  3. Ingestion   — committed fixture PDF (always runs)
  4. Logging     — DEBUG records emitted during ingestion
  5. Test suite  — pytest with 80% coverage gate
  6. Docker      — `docker build` + `docker run --help` smoke (skipped if Docker absent)
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SAMPLE_DIR = PROJECT_ROOT / "samplepdf"
FIXTURE_PDF = PROJECT_ROOT / "test_corpus" / "real_world" / "ccl_mri_request_001_mock.pdf"

_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_RESET = "\033[0m"
_BOLD = "\033[1m"

_failures: list[str] = []


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _pass(label: str) -> None:
    print(f"  {_GREEN}PASS{_RESET}  {label}")


def _fail(label: str, detail: str = "") -> None:
    msg = f"{label}: {detail}" if detail else label
    _failures.append(msg)
    print(f"  {_RED}FAIL{_RESET}  {label}" + (f"\n        {detail}" if detail else ""))


def _skip(label: str, reason: str) -> None:
    print(f"  {_YELLOW}SKIP{_RESET}  {label}  ({reason})")


def _section(title: str) -> None:
    print(f"\n{_BOLD}── {title} ──{_RESET}")


# ---------------------------------------------------------------------------
# 1. CLI sanity
# ---------------------------------------------------------------------------


def check_cli_help() -> None:
    _section("CLI sanity")
    result = subprocess.run(
        ["cliniq", "--help"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        _fail("cliniq --help", f"exit {result.returncode}")
        return
    if "extract" not in result.stdout:
        _fail("cliniq --help", "'extract' not found in help output")
        return
    _pass("cliniq --help exits 0 and lists 'extract'")


# ---------------------------------------------------------------------------
# 2 + 3. Ingestion
# ---------------------------------------------------------------------------


class _DebugLogger:
    """Context manager: attaches handler + forces DEBUG, then restores state."""

    def __init__(self, logger: logging.Logger, handler: logging.Handler) -> None:
        self._logger = logger
        self._handler = handler
        self._old_level = logging.NOTSET

    def __enter__(self) -> None:
        self._old_level = self._logger.level
        self._logger.setLevel(logging.DEBUG)
        self._logger.addHandler(self._handler)

    def __exit__(self, *_: object) -> None:
        self._logger.removeHandler(self._handler)
        self._logger.setLevel(self._old_level)


def _run_ingestion(pdf: Path, handler: _ListHandler) -> tuple[int, int]:
    """Return (total_pages, ocr_pages). Raises on failure."""
    from cliniq.ingestion.pdf_reader import read_pdf

    with _DebugLogger(logging.getLogger("cliniq"), handler):
        doc = read_pdf(pdf)

    total = len(doc.pages)
    ocr = sum(1 for p in doc.pages if p.via_ocr)
    return total, ocr


def check_ingestion_sample_pdfs() -> None:
    _section("Ingestion — sample PDFs (samplepdf/Upload*.pdf)")
    uploads = sorted(SAMPLE_DIR.glob("Upload*.pdf")) if SAMPLE_DIR.exists() else []
    if not uploads:
        _skip("sample PDF ingestion", "no samplepdf/Upload*.pdf found")
        return

    for pdf in uploads:
        handler = _ListHandler()
        try:
            total, ocr = _run_ingestion(pdf, handler)
            _pass(f"{pdf.name}  →  {total} page(s), {ocr} via OCR")
        except Exception as exc:  # noqa: BLE001
            _fail(f"{pdf.name}", str(exc))


def check_ingestion_fixture() -> None:
    _section("Ingestion — committed fixture")
    if not FIXTURE_PDF.exists():
        _fail("fixture PDF missing", str(FIXTURE_PDF))
        return

    handler = _ListHandler()
    try:
        total, ocr = _run_ingestion(FIXTURE_PDF, handler)
        _pass(f"{FIXTURE_PDF.name}  →  {total} page(s), {ocr} via OCR")
    except Exception as exc:  # noqa: BLE001
        _fail(FIXTURE_PDF.name, str(exc))


# ---------------------------------------------------------------------------
# 4. Logging verification
# ---------------------------------------------------------------------------


def check_logging() -> None:
    _section("Logging")
    if not FIXTURE_PDF.exists():
        _skip("logging check", "fixture PDF missing")
        return

    handler = _ListHandler()
    _run_ingestion(FIXTURE_PDF, handler)

    messages = [r.getMessage() for r in handler.records]

    def _assert_any(substring: str, label: str) -> None:
        if any(substring in m for m in messages):
            _pass(label)
        else:
            _fail(label, f"no record containing '{substring}'")

    _assert_any("read_pdf: opening", "opening log emitted")
    _assert_any("read_pdf: done", "done log emitted")

    page_decision = any(("text-layer" in m or "no text layer" in m) for m in messages)
    if page_decision:
        _pass("per-page decision log emitted")
    else:
        _fail("per-page decision log", "no 'text-layer' or 'no text layer' record found")

    warnings = [r for r in handler.records if r.levelno >= logging.WARNING]
    if warnings:
        _pass(f"low-confidence warning present ({len(warnings)} record(s))")
    else:
        _skip("low-confidence warning", "no low-confidence page in fixture (expected)")


# ---------------------------------------------------------------------------
# 5. Test suite
# ---------------------------------------------------------------------------


def check_test_suite() -> None:
    _section("Test suite (pytest --cov 80%)")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "--cov=cliniq",
            "--cov-fail-under=80",
            "-q",
            "--tb=short",
        ],
        cwd=PROJECT_ROOT,
    )
    if result.returncode == 0:
        _pass("pytest passed with ≥ 80% coverage")
    else:
        _fail("pytest", f"exit {result.returncode}")


# ---------------------------------------------------------------------------
# 6. Docker smoke
# ---------------------------------------------------------------------------

_DOCKER_IMAGE = "cliniq-local-test"


def check_docker_build() -> None:
    _section("Docker smoke (build + run --help)")

    has_docker = subprocess.run(
        ["docker", "info"],
        capture_output=True,
    ).returncode == 0
    if not has_docker:
        _skip("docker build", "Docker daemon not available")
        return

    build = subprocess.run(
        ["docker", "build", "-t", _DOCKER_IMAGE, "."],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    if build.returncode != 0:
        _fail("docker build", build.stderr.splitlines()[-1] if build.stderr else "non-zero exit")
        return
    _pass("docker build succeeded")

    run = subprocess.run(
        ["docker", "run", "--rm", _DOCKER_IMAGE, "cliniq", "--help"],
        capture_output=True,
        text=True,
    )
    if run.returncode != 0:
        _fail("docker run --help", f"exit {run.returncode}")
        return
    if "extract" not in run.stdout:
        _fail("docker run --help", "'extract' not in help output")
        return
    _pass("docker run --rm cliniq --help exits 0 and lists 'extract'")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    print(f"\n{_BOLD}cliniq — local test gate{_RESET}")
    print(f"project root: {PROJECT_ROOT}")

    check_cli_help()
    check_ingestion_sample_pdfs()
    check_ingestion_fixture()
    check_logging()
    check_test_suite()
    check_docker_build()

    print()
    if _failures:
        print(f"{_RED}{_BOLD}FAILED{_RESET} — {len(_failures)} check(s) failed:")
        for f in _failures:
            print(f"  • {f}")
        sys.exit(1)
    else:
        print(f"{_GREEN}{_BOLD}ALL CHECKS PASSED{_RESET}")


if __name__ == "__main__":
    main()
