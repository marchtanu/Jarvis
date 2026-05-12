from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from auhip.core.llm.types import LLMRequest, LLMResponse


class BaseLLMProvider(ABC):
    """
    Abstract interface for swappable neural reasoning providers (Local / Cloud).
    Enforces non-blocking execution yielding strictly parsed JSON object outputs.
    """

    @abstractmethod
    async def generate_structured(self, request: LLMRequest) -> LLMResponse:
        """
        Processes a prompt alongside active chat context to output a strongly-typed
        intent decision structure. Must handle inner session execution safely.
        """
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        """
        Validates internal availability/reachability asynchronously before dispatch.
        """
        pass
