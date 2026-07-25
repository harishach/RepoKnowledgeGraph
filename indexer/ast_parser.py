from pathlib import Path
from dataclasses import dataclass, field
from tree_sitter import Language, Parser, Node
import tree_sitter_python as tspython
import ast


PY_LANGUAGE = Language(tspython.language())


@dataclass
class ParsedSymbol:
    name: str
    qualified_name: str
    symbol_type: str
    start_line: int
    end_line: int
    signature: str | None = None
    docstring: str | None = None


@dataclass
class ParsedEdge:
    from_qualified_name: str
    to_name: str
    edge_type: str
    to_file: str | None = None


@dataclass
class ParseResult:
    symbols: list[ParsedSymbol] = field(default_factory=list)
    edges: list[ParsedEdge] = field(default_factory=list)


def _segment(lines: list[str], node: ast.AST) -> str:
    lineno = getattr(node, "lineno", 1)
    return lines[lineno - 1].strip() if 0 < lineno <= len(lines) else ""


def _docstring(node: ast.AST) -> str | None:
    doc = ast.get_docstring(node, clean=True)
    return None if doc is None else doc[:300]


def _call_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _base_name(base: ast.AST) -> str | None:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        parts = [base.attr]
        value = base.value
        while isinstance(value, ast.Attribute):
            parts.append(value.attr)
            value = value.value
        if isinstance(value, ast.Name):
            parts.append(value.id)
        return ".".join(reversed(parts))
    return None


def _add_calls(result: ParseResult, qualified_name: str, node: ast.AST) -> None:
    seen: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            name = _call_name(child.func)
            if name is not None and name not in seen:
                seen.add(name)
                result.edges.append(ParsedEdge(qualified_name, name, "calls"))


def parse_file(file_path: Path) -> ParseResult:
    """
    Parse a Python file and extract symbols and edges.
    Returns ParseResult with all symbols and edges found.
    On any parse error, return empty ParseResult (do not raise).
    """
    try:
        text = file_path.read_text(encoding="utf-8")
        tree = ast.parse(text)
    except Exception:
        return ParseResult()

    result = ParseResult()
    lines = text.splitlines() or [""]
    module_name = file_path.stem
    result.symbols.append(ParsedSymbol(module_name, module_name, "module", 1, len(lines)))

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.edges.append(ParsedEdge(module_name, alias.name, "imports"))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                to_name = f"{module}.{alias.name}" if module else alias.name
                result.edges.append(ParsedEdge(module_name, to_name, "imports"))
        elif isinstance(node, ast.ClassDef):
            class_qn = node.name
            result.symbols.append(ParsedSymbol(node.name, class_qn, "class", node.lineno, getattr(node, "end_lineno", node.lineno), _segment(lines, node), _docstring(node)))
            for base in node.bases:
                name = _base_name(base)
                if name is not None:
                    result.edges.append(ParsedEdge(class_qn, name, "inherits"))
            for child in node.body:
                if isinstance(child, ast.FunctionDef):
                    qn = f"{node.name}.{child.name}"
                    result.symbols.append(ParsedSymbol(child.name, qn, "method", child.lineno, getattr(child, "end_lineno", child.lineno), _segment(lines, child), _docstring(child)))
                    _add_calls(result, qn, child)
        elif isinstance(node, ast.FunctionDef):
            result.symbols.append(ParsedSymbol(node.name, node.name, "function", node.lineno, getattr(node, "end_lineno", node.lineno), _segment(lines, node), _docstring(node)))
            _add_calls(result, node.name, node)
    return result
