from typing import Any, Callable

class Server:
    def __init__(self, name: str) -> None:
        self.name = name
        self._list_tools = None
        self._call_tool = None

    def list_tools(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._list_tools = func
            return func
        return decorator

    def call_tool(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._call_tool = func
            return func
        return decorator

    def create_initialization_options(self) -> dict[str, Any]:
        return {}

    async def run(self, read_stream: Any, write_stream: Any, options: dict[str, Any]) -> None:
        return None
