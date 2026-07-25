import argparse
import hashlib
import time
from pathlib import Path
import yaml

from indexer.scanner import scan_repo
from indexer.ast_parser import parse_file
from indexer.graph_store import GraphStore, Symbol, Edge


def hash_file(path: Path) -> str:
    """Return sha256 hex digest of file content."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def index_repo(repo_root: Path, db_path: Path, config: dict) -> None:
    """
    Full indexing pipeline:
    1. Init schema
    2. Scan repo for files
    3. For each file:
       a. Compute hash
       b. Skip if hash matches stored hash (already indexed, unchanged)
       c. Parse file → symbols + edges
       d. Upsert file record (cascades delete of old symbols/edges)
       e. Insert new symbols → get qualified_name → id map
       f. Resolve edge from_id using the map, insert edges
    4. Print summary line
    """
    start = time.time()
    root = repo_root.resolve()
    store = GraphStore(db_path)
    store.init_schema()
    skipped_parse = 0
    for file_path in scan_repo(root, config):
        rel_path = file_path.relative_to(root).as_posix()
        file_hash = hash_file(file_path)
        if store.get_file_hash(rel_path) == file_hash:
            continue
        parsed = parse_file(file_path)
        if not parsed.symbols:
            skipped_parse += 1
            continue
        fid = store.upsert_file(rel_path, "python", file_hash)
        symbols = [Symbol(fid, s.name, s.qualified_name, s.symbol_type, s.start_line, s.end_line, s.signature, s.docstring) for s in parsed.symbols]
        sym_id_map = store.insert_symbols(symbols)
        edges: list[Edge] = []
        for edge in parsed.edges:
            from_id = sym_id_map.get(edge.from_qualified_name)
            if from_id is not None:
                edges.append(Edge(from_id, edge.to_name, edge.edge_type, edge.to_file))
        store.insert_edges(edges)
        print(".", end="", flush=True)
    stats = store.get_stats()
    elapsed = time.time() - start
    print()
    print(f"Indexed {stats['files']} files | {stats['symbols']} symbols | {stats['edges']} edges | {elapsed:.1f}s")
    if skipped_parse:
        print(f"Skipped {skipped_parse} files (parse error)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Index a repository into repo-kg graph DB")
    parser.add_argument("--repo", required=True, type=Path, help="Path to repository root")
    parser.add_argument("--db", required=True, type=Path, help="Path to output SQLite DB")
    parser.add_argument("--config", default=Path("config.yaml"), type=Path)
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text())
    index_repo(args.repo, args.db, config)


if __name__ == "__main__":
    main()
