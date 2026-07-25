from typing import Any

def safe_load(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current_section: str | None = None
    current_subsection: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if not raw.startswith(' ') and stripped.endswith(':'):
            current_section = stripped[:-1]
            result[current_section] = {} if current_section == 'languages' else []
            current_subsection = None
        elif not raw.startswith(' ') and ':' in stripped:
            key, value = stripped.split(':', 1)
            result[key] = int(value.strip()) if value.strip().isdigit() else value.strip()
        elif current_section == 'ignore_patterns' and stripped.startswith('- '):
            result[current_section].append(stripped[2:].strip('"'))
        elif current_section == 'languages' and raw.startswith('  ') and stripped.endswith(':'):
            current_subsection = stripped[:-1]
            result[current_section][current_subsection] = {}
        elif current_section == 'languages' and current_subsection and 'extensions:' in stripped:
            start = stripped.index('[') + 1
            end = stripped.index(']')
            vals = [v.strip().strip('"') for v in stripped[start:end].split(',') if v.strip()]
            result[current_section][current_subsection]['extensions'] = vals
    return result
