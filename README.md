# repo-kg

`repo-kg` indexes Python repositories into a local SQLite knowledge graph and exposes query tools through an MCP stdio server for editor assistants such as VS Code Copilot.

## Requirements

- Python 3.11 or newer
- `tree-sitter==0.23.2`
- `tree-sitter-python==0.23.6`
- `mcp==1.3.0`
- `pyyaml==6.0.2`

## Install

Create and activate a virtual environment, then install the project dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

If you do not use editable installs, install the pinned dependencies directly:

```bash
python -m pip install tree-sitter==0.23.2 tree-sitter-python==0.23.6 mcp==1.3.0 pyyaml==6.0.2
```

## Index a repository

Run the indexer against any Python repository and write the graph to a SQLite database:

```bash
python -m indexer.run \
  --repo /path/to/python/repo \
  --db ./graph.db \
  --config config.yaml
```

The indexer prints one dot for each indexed file, then a summary such as:

```text
Indexed 312 files | 4821 symbols | 12304 edges | 18.3s
```

Run it again with the same database to skip files whose content hash has not changed.

## Query from Python

You can call the tool handlers directly from Python for smoke tests or scripts:

```python
from pathlib import Path
from indexer.graph_store import GraphStore
from mcp_server.tools.get_symbol import get_symbol
from mcp_server.tools.find_dependencies import find_dependencies
from mcp_server.tools.trace_callers import trace_callers
from mcp_server.tools.get_file_structure import get_file_structure

store = GraphStore(Path("graph.db"))

print(get_symbol(store, "Trainer"))
print(find_dependencies(store, "pkg/trainer.py"))
print(trace_callers(store, "run"))
print(get_file_structure(store, "pkg/trainer.py"))
```

## Run the MCP server

The MCP server reads the database path from `REPO_KG_DB` and communicates over stdio:

```bash
REPO_KG_DB=./graph.db python -m mcp_server.server
```

The server exposes four tools:

- `get_symbol` — find functions, classes, and methods by name.
- `find_dependencies` — list imports, inheritance dependencies, and internal file dependencies for a file.
- `trace_callers` — find symbols that call a function or method name.
- `get_file_structure` — summarize classes, methods, module-level functions, and import count for a file.

## VS Code Copilot setup

This repository includes `.vscode/mcp.json`, which starts the MCP server from the workspace root and uses `${workspaceFolder}/graph.db` as the database.

For another repository, copy `.vscode/mcp.json.template` into that target repository's `.vscode/mcp.json` and replace `REPLACE_WITH_REPO_KG_PATH` with the absolute path to this `repo-kg` checkout.

After indexing a repository and opening VS Code, use Copilot Chat in Agent mode and ask:

```text
@repo-kg what tools are available?
```

Copilot should list the four tools above.
