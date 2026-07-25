from indexer.graph_store import GraphStore


def _internal_path(import_name: str, files: set[str]) -> str | None:
    parts = import_name.split(".")
    candidates = ["/".join(parts) + ".py"]
    if len(parts) > 1:
        candidates.append("/".join(parts[:-1]) + ".py")
    for candidate in candidates:
        if candidate in files:
            return candidate
    return None


def find_dependencies(store: GraphStore, file_path: str) -> dict:
    """
    Return all imports and inheritance dependencies for a file.
    If file not in index, return {"error": "File not indexed: <path>"}.
    Resolve which imports are internal (path exists in files table).
    """
    data = store.get_file_imports(file_path)
    if not data:
        return {"error": f"File not indexed: {file_path}"}
    imports = sorted({e["to_name"] for e in data["edges"] if e["edge_type"] == "imports"})
    inherits = sorted({e["to_name"] for e in data["edges"] if e["edge_type"] == "inherits"})
    file_rows = store.conn.execute("SELECT path FROM files").fetchall()
    files = {str(row["path"]) for row in file_rows}
    internal = sorted({p for item in imports if (p := _internal_path(item, files)) is not None})
    return {"file": file_path, "imports": imports, "inherits": inherits, "internal_dependencies": internal}
