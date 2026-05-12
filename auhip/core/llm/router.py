import asyncio
import logging
from typing import Dict, Any, Optional, List

from auhip.core.llm.base import BaseLLMProvider
from auhip.core.llm.cloud_model import GeminiProvider
from auhip.core.llm.context_manager import ContextManager
from auhip.core.llm.escalation import EscalationManager
from auhip.core.llm.local_model import OllamaProvider
from auhip.core.llm.prompt_builder import PromptBuilder
from auhip.core.llm.tool_manager import ToolManager
from auhip.core.llm.types import LLMRequest, LLMResponse, Message, ToolSchema

logger = logging.getLogger(__name__)


class HybridLLMRouter:
    """
    Central production-grade asynchronous routing engine orchestrating local-first neural
    execution, tool encapsulation, context pruning, and automated fallback escalation logic.
    """

    def __init__(self, tool_manager: ToolManager, context_manager: ContextManager):
        self.tool_manager = tool_manager
        self.context_manager = context_manager
        
        # Swappable neural backend adapters
        self.local_provider: BaseLLMProvider = OllamaProvider()
        self.cloud_provider: BaseLLMProvider = GeminiProvider()
        
        self.current_mode: str = "VOICE_MODE"

    def set_mode(self, mode: str):
        """Update current operational machine context tracking."""
        self.current_mode = mode
        logger.debug(f"Hybrid router execution context transitioned to: {mode}")

    async def execute(self, user_text: str) -> str:
        """
        Orchestrates an end-to-end command request. Prioritizes local engine inference,
        triggers sandboxed internal tool execution, and falls back to cloud providers safely.
        """
        prompt = user_text.strip()
        if not prompt:
            return ""

        logger.info(f"Dispatching intent processing for prompt: '{prompt}'")

        # 1. Update working context window with system rules and new user command
        sys_text = PromptBuilder.build_system_prompt(self.current_mode)
        
        # Ensure system instructions are present as absolute baseline context
        current_ctx = self.context_manager.get_context()
        if not current_ctx or current_ctx[0].role != "system":
            self.context_manager.append(Message(role="system", content=sys_text))
            
        self.context_manager.append(Message(role="user", content=prompt))

        # 2. Prepare structured target generation payload request
        req = LLMRequest(
            prompt=prompt,
            history=self.context_manager.get_context(),
            available_tools=self.tool_manager.get_schemas(),
            require_structured=True
        )

        # 3. Layer 1 — Attempt primary local execution engine routing
        response: Optional[LLMResponse] = None
        is_local_ok = await self.local_provider.is_healthy()
        
        if is_local_ok:
            logger.debug("Local neural core reachable. Initiating fast layer 1 parsing.")
            response = await self.local_provider.generate_structured(req)
        else:
            logger.warning("Local engine status checks failed. Prompting direct external escalation routing.")

        # 4. Layer 3 — Evaluate internal escalation boundaries
        if not response or EscalationManager.should_escalate(response, prompt):
            logger.info("Escalating reasoning request to Layer 3 cloud neural infrastructure.")
            
            # Verify status reachability before invoking external APIs
            if await self.cloud_provider.is_healthy():
                cloud_resp = await self.cloud_provider.generate_structured(req)
                if cloud_resp.intent != "error" or not response:
                    response = cloud_resp
            else:
                logger.error("Cloud provider unreachable. Relying on local layer fallback projection.")

        # Safety catchall for total neural connection failure
        if not response:
            return "Neural processing error. Command execution aborted safely."

        logger.info(f"Finalized structural resolution: Intent='{response.intent}', Confidence={response.confidence:.2f}, Tool={response.tool_name}")

        # 5. Layer 2 — Execute declared tool safely if requested
        final_answer = response.response
        if response.requires_tool and response.tool_name:
            # Preserve deterministic tool intent inside conversational flow context
            self.context_manager.append(Message(role="assistant", content=f"Triggering skill: {response.tool_name}"))
            
            tool_result = await self.tool_manager.execute(response.tool_name, response.tool_args)
            
            # Append isolated tool result directly into interaction buffers
            res_str = str(tool_result)
            self.context_manager.append(Message(role="tool", content=res_str, name=response.tool_name))
            
            # Cleanly merge text returns to optimize user responsiveness feedback
            if not final_answer or final_answer in ("Executing tool...", "Searching web..."):
                final_answer = res_str
            else:
                final_answer = f"{final_answer} Result: {res_str}"
        else:
            # Record final pure language message context directly
            if final_answer:
                self.context_manager.append(Message(role="assistant", content=final_answer))

        return final_answer or "Execution complete."
