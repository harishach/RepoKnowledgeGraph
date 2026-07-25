from dataclasses import dataclass
from typing import Any

@dataclass
class Tool:
    name: str
    description: str
    inputSchema: dict[str, Any]

@dataclass
class TextContent:
    type: str
    text: str
