import logging
from typing import List, Dict, Any, Optional
from auhip.core.llm.config import llm_config
from auhip.core.llm.types import Message

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Intelligent historical state compressor. Estimates token constraints, enforces
    rolling window retention limits, filters redundant duplicates, and prioritizes active tasks.
    """

    def __init__(self):
        self._history: List[Message] = []

    def append(self, message: Message):
        """Add new interaction context to the working window queue."""
        # Check simple duplication of immediate consecutive turns
        if self._history and self._history[-1].role == message.role and self._history[-1].content == message.content:
            logger.debug("Filtered redundant identical sequential message context.")
            return

        self._history.append(message)
        self._compress()

    def get_context(self) -> List[Message]:
        """Expose current prioritized execution context ready for routing injection."""
        return self._history.copy()

    def clear(self):
        """Purge stored interactions cleanly."""
        self._history.clear()
        logger.debug("Active conversational buffer purged.")

    def _estimate_tokens(self, text: str) -> int:
        """Heuristic token footprint calculation (~4 chars per token)."""
        return len(text) // 4

    def _compress(self):
        """
        Maintains token constraints by trimming the tail interactions cleanly
        while preserving initial critical instructions or persistent active state indicators.
        """
        # Truncate overall length based on config hardcaps
        if len(self._history) > llm_config.MAX_HISTORY_MESSAGES:
            logger.info("Context length constraint triggered. Pruning oldest conversational turns.")
            # Keep system prompts if placed at index 0
            start_idx = 1 if self._history and self._history[0].role == "system" else 0
            excess = len(self._history) - llm_config.MAX_HISTORY_MESSAGES
            self._history = self._history[:start_idx] + self._history[start_idx + excess:]

        # Maintain budget constraints safely
        total_tokens = sum(self._estimate_tokens(m.content) for m in self._history)
        if total_tokens > llm_config.TOKEN_BUDGET_ESTIMATE:
            logger.warning(f"Estimated token footprint ({total_tokens}) exceeds budget cap. Compressing memory window.")
            while total_tokens > llm_config.TOKEN_BUDGET_ESTIMATE and len(self._history) > 2:
                # Remove oldest user/assistant interactions dynamically
                pop_idx = 1 if self._history[0].role == "system" else 0
                popped = self._history.pop(pop_idx)
                total_tokens -= self._estimate_tokens(popped.content)
