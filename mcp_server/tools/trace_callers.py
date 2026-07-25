from indexer.graph_store import GraphStore


def trace_callers(store: GraphStore, function_name: str) -> dict:
    """
    Find all symbols that have a 'calls' edge to function_name.
    Match on both exact name and qualified_name suffix.
    If none found, return {"callers": [], "message": "No callers found for <name>"}.
    """
    rows = store.get_callers(function_name)
    callers = [{"symbol": r["symbol"], "file": r["file"], "line": r["line"]} for r in rows]
    result = {"function": function_name, "callers": callers}
    if not callers:
        result["message"] = f"No callers found for {function_name}"
    return result
