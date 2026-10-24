from typing import Protocol

class LLMClient(Protocol):
    async def send(self, prepared): ...
