import logging
from typing import Dict, Any, Optional
from auhip.core.llm.config import llm_config
from auhip.core.llm.types import LLMResponse

logger = logging.getLogger(__name__)


class EscalationManager:
    """
    Decides when task complexity demands fallback from lightweight local AI logic models
    to high-bandwidth external neural infrastructure.
    """

    @staticmethod
    def should_escalate(response: LLMResponse, prompt_text: str) -> bool:
        """
        Evaluates heuristic indicators, specific intent targets, and neural confidence
        metrics to determine layer promotion necessity.
        """
        # 1. Check explicit model self-reported escalation routing flag
        if response.escalate:
            logger.info("Local engine requested external escalation explicitly.")
            return True

        # 2. Check confidence metric thresholds
        if response.confidence < llm_config.ESCALATION_CONFIDENCE_THRESHOLD:
            logger.warning(f"Local routing confidence ({response.confidence}) below acceptable threshold ({llm_config.ESCALATION_CONFIDENCE_THRESHOLD}). Triggering escalation.")
            return True

        # 3. Check for specific highly complex prompt patterns
        lower_prompt = prompt_text.lower()
        complex_triggers = [
            "write code", "generate code", "refactor", "architect",
            "plan architecture", "deep analysis", "complex algorithm",
            "multimodal", "analyze image"
        ]
        
        for trigger in complex_triggers:
            if trigger in lower_prompt:
                logger.info(f"Detected advanced intent string target '{trigger}'. Escalating task execution scope.")
                return True

        return False
