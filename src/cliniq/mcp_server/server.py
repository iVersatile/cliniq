"""MCP server exposing cliniq tools to any LLM client."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("cliniq")


@app.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="extract_document",
            description="Extract structured health records from a PDF file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {"type": "string", "description": "Absolute path to the PDF"},
                    "backend": {"type": "string", "default": "ollama"},
                },
                "required": ["pdf_path"],
            },
        ),
        types.Tool(
            name="list_medications",
            description="List all medications extracted from a records directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "records_dir": {"type": "string"},
                },
                "required": ["records_dir"],
            },
        ),
        types.Tool(
            name="get_timeline",
            description="Return a chronological timeline of medical notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "records_dir": {"type": "string"},
                },
                "required": ["records_dir"],
            },
        ),
    ]


@app.call_tool()  # type: ignore[untyped-decorator]
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    from cliniq.adapters import get_adapter
    from cliniq.extraction.engine import ExtractionEngine

    match name:
        case "extract_document":
            pdf = Path(arguments["pdf_path"])
            adapter = get_adapter(arguments.get("backend", "ollama"))
            engine = ExtractionEngine(adapter=adapter)
            result = engine.process(pdf)
            msg = f"Extracted {len(result.notes)} note(s) from {pdf.name}"
            return [types.TextContent(type="text", text=msg)]
        case _:
            return [types.TextContent(type="text", text=f"Tool '{name}' not yet implemented")]


async def _serve() -> None:
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


def run_server(port: int = 8765) -> None:
    import asyncio

    asyncio.run(_serve())
