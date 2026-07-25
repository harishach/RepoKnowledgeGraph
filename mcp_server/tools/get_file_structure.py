from indexer.graph_store import GraphStore


def get_file_structure(store: GraphStore, file_path: str) -> dict:
    """
    Return the structural skeleton of a file: all classes with their methods,
    all module-level functions, and import count.
    If file not in index, return {"error": "File not indexed: <path>"}.
    """
    symbols = store.get_file_symbols(file_path)
    if not symbols:
        return {"error": f"File not indexed: {file_path}"}
    deps = store.get_file_imports(file_path)
    edges = deps.get("edges", []) if deps else []
    inherits_by_class: dict[str, list[str]] = {}
    for edge in edges:
        if edge["edge_type"] == "inherits":
            row = store.conn.execute("SELECT qualified_name FROM symbols WHERE id = ?", (edge["from_id"],)).fetchone()
            if row is not None:
                inherits_by_class.setdefault(str(row["qualified_name"]), []).append(edge["to_name"])
    classes = []
    for symbol in symbols:
        if symbol["symbol_type"] == "class":
            methods = [{"name": s["name"], "lines": f"{s['start_line']}-{s['end_line']}"} for s in symbols if s["symbol_type"] == "method" and s["qualified_name"].startswith(f"{symbol['qualified_name']}.")]
            classes.append({"name": symbol["name"], "inherits": inherits_by_class.get(symbol["qualified_name"], []), "methods": methods})
    functions = [s["name"] for s in symbols if s["symbol_type"] == "function"]
    imports_count = len([e for e in edges if e["edge_type"] == "imports"])
    return {"file": file_path, "classes": classes, "module_level_functions": functions, "imports_count": imports_count}
