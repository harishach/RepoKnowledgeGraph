from indexer.graph_store import GraphStore


def get_symbol(store: GraphStore, name: str) -> dict:
    """
    Search symbols by name (exact match first, then partial).
    If multiple results, return all.
    If none found, return {"error": "Symbol not found: <name>"}.
    """
    rows = store.get_symbol(name)
    if not rows:
        return {"error": f"Symbol not found: {name}"}
    return {"results": [{"name": r["name"], "qualified_name": r["qualified_name"], "symbol_type": r["symbol_type"], "file": r["file"], "lines": f"{r['start_line']}-{r['end_line']}", "signature": r["signature"], "docstring": r["docstring"]} for r in rows]}
