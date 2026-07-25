from contextlib import asynccontextmanager
from typing import AsyncIterator, Any

@asynccontextmanager
async def stdio_server() -> AsyncIterator[tuple[Any, Any]]:
    yield None, None
