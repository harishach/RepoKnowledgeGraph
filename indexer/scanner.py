from pathlib import Path
import fnmatch


def should_ignore(path: Path, repo_root: Path, patterns: list[str]) -> bool:
    """Return True if path matches any ignore pattern."""
    rel_path = path.relative_to(repo_root).as_posix()
    return any(fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(rel_path, pattern.removeprefix("**/")) for pattern in patterns)


def scan_repo(repo_root: Path, config: dict) -> list[Path]:
    """
    Walk repo_root recursively.
    Return list of absolute Paths to indexable files.
    Skips files larger than config['max_file_size_kb'] * 1024 bytes.
    Skips files matching any pattern in config['ignore_patterns'].
    Only includes files whose suffix matches a language extension in config['languages'].
    """
    root = repo_root.resolve()
    patterns = config["ignore_patterns"]
    max_size = int(config["max_file_size_kb"]) * 1024
    extensions = {ext for language in config["languages"].values() for ext in language["extensions"]}
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        if should_ignore(path, root, patterns):
            continue
        if path.suffix not in extensions:
            continue
        if path.stat().st_size > max_size:
            continue
        files.append(path)
    return sorted(files)
