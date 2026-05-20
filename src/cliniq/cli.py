"""CLI entrypoint: cliniq extract <pdfs_dir> --output <out_dir> --backend ollama"""

from pathlib import Path

import click


@click.group()
def main() -> None:
    pass


@main.command()
@click.argument("pdfs_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), default=Path("./records"))
@click.option(
    "--backend",
    default="ollama",
    show_default=True,
    type=click.Choice(["ollama", "claude", "openai", "gemini"]),
)
def extract(pdfs_dir: Path, output: Path, backend: str) -> None:
    """Extract health records from PDFs in PDFS_DIR."""
    from cliniq.adapters import get_adapter
    from cliniq.extraction.engine import ExtractionEngine

    output.mkdir(parents=True, exist_ok=True)
    try:
        adapter = get_adapter(backend)
    except NotImplementedError as exc:
        raise click.ClickException(str(exc)) from exc
    engine = ExtractionEngine(adapter=adapter)

    pdfs = list(pdfs_dir.glob("*.pdf"))
    click.echo(f"Processing {len(pdfs)} PDFs → {output}")
    for pdf in pdfs:
        results = engine.process(pdf)
        results.write(output)
        click.echo(f"  ✓ {pdf.name}")


@main.command("serve")
@click.option("--port", default=8765, show_default=True)
def serve_mcp(port: int) -> None:
    """Start the MCP server."""
    from cliniq.mcp_server.server import run_server

    run_server(port=port)
