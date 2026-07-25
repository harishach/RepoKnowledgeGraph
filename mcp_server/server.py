import asyncio
import os
import json
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from indexer.graph_store import GraphStore
from mcp_server.tools.get_symbol import get_symbol
from mcp_server.tools.find_dependencies import find_dependencies
from mcp_server.tools.trace_callers import trace_callers
from mcp_server.tools.get_file_structure import get_file_structure


def create_server(db_path: Path) -> Server:
    store = GraphStore(db_path)
    store.init_schema()
    app = Server("repo-kg")

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="get_symbol",
                description="Look up a function, class or method by name. Returns location, signature, and docstring. Use this before reading a file to check if a symbol exists.",
                inputSchema={"type": "object", "properties": {"name": {"type": "string", "description": "Symbol name to search for"}}, "required": ["name"]}
            ),
            Tool(
                name="find_dependencies",
                description="Get all imports and inheritance dependencies of a file. Use this before modifying a file to understand its dependency surface.",
                inputSchema={"type": "object", "properties": {"file_path": {"type": "string", "description": "Relative path to the file"}}, "required": ["file_path"]}
            ),
            Tool(
                name="trace_callers",
                description="Find all functions that call a given function. Use this before changing a function signature to understand blast radius.",
                inputSchema={"type": "object", "properties": {"function_name": {"type": "string", "description": "Function or method name to trace"}}, "required": ["function_name"]}
            ),
            Tool(
                name="get_file_structure",
                description="Get the structural skeleton of a file: all classes, methods, and module-level functions with line ranges. Use this instead of reading the full file.",
                inputSchema={"type": "object", "properties": {"file_path": {"type": "string", "description": "Relative path to the file"}}, "required": ["file_path"]}
            ),
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        dispatch = {
            "get_symbol": lambda a: get_symbol(store, a["name"]),
            "find_dependencies": lambda a: find_dependencies(store, a["file_path"]),
            "trace_callers": lambda a: trace_callers(store, a["function_name"]),
            "get_file_structure": lambda a: get_file_structure(store, a["file_path"]),
        }
        if name not in dispatch:
            result = {"error": f"Unknown tool: {name}"}
        else:
            try:
                result = dispatch[name](arguments)
            except Exception as e:
                result = {"error": str(e)}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    return app


async def run_server(db_path: Path) -> None:
    app = create_server(db_path)
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main() -> None:
    db_path = Path(os.environ.get("REPO_KG_DB", "graph.db"))
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found: {db_path}\n"
            f"Run indexer first: python -m indexer.run --repo <path> --db {db_path}"
        )
    asyncio.run(run_server(db_path))


if __name__ == "__main__":
    main()
