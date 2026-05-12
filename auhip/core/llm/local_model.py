import asyncio
import json
import logging
import aiohttp
from typing import Dict, Any, Optional

from auhip.core.llm.base import BaseLLMProvider
from auhip.core.llm.config import llm_config
from auhip.core.llm.response_parser import ResponseParser
from auhip.core.llm.types import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """
    Fully non-blocking asynchronous REST adapter communicating directly with local Ollama
    instances. Enforces JSON output formats and embeds circuit breaking timeouts.
    """

    def __init__(self):
        self.base_url = llm_config.OLLAMA_BASE_URL.rstrip("/")
        self.model = llm_config.LOCAL_MODEL_NAME
        self.timeout = aiohttp.ClientTimeout(total=llm_config.LOCAL_TIMEOUT_SECONDS)

    async def is_healthy(self) -> bool:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2.0)) as session:
                async with session.get(f"{self.base_url}/api/tags") as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def generate_structured(self, request: LLMRequest) -> LLMResponse:
        url = f"{self.base_url}/api/chat"
        
        # Inject structural instructions ensuring strict compliance
        schema_guidance = (
            "Output your entire decision strictly as a valid JSON object matching this schema exactly:\n"
            "{\n"
            '  "intent": "string (classified core task)",\n'
            '  "confidence": float (0.0 to 1.0),\n'
            '  "requires_tool": boolean,\n'
            '  "tool_name": "string (name of targeted skill or null)",\n'
            '  "tool_args": { "arg_name": "value" },\n'
            '  "response": "string (short concise message to display/speak)",\n'
            '  "escalate": boolean (true if complexity requires external high-end reasoning)\n'
            "}\n"
            "Do NOT include any surrounding conversational commentary or text outside the JSON structure."
        )

        messages = []
        # Compile existing historical context
        for msg in request.history:
            messages.append({"role": msg.role, "content": msg.content})

        # Append execution intent targeting this action
        final_prompt = f"{request.prompt}\n\n{schema_guidance}" if request.require_structured else request.prompt
        messages.append({"role": "user", "content": final_prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.1 # Absolute precision, deterministic classification
            }
        }
        
        # Append tool declarations if native execution wrappers are active
        if request.available_tools:
            tools_mapped = []
            for t in request.available_tools:
                tools_mapped.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": {
                            "type": "object",
                            "properties": t.parameters,
                            "required": t.required
                        }
                    }
                })
            payload["tools"] = tools_mapped

        last_error = None
        for attempt in range(llm_config.LOCAL_MAX_RETRIES):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.post(url, json=payload) as resp:
                        if resp.status != 200:
                            err_text = await resp.text()
                            logger.error(f"Local core REST rejection ({resp.status}): {err_text}")
                            raise RuntimeError(f"Ollama execution error: {resp.status}")
                        
                        data = await resp.json()
                        raw_text = data.get("message", {}).get("content", "")
                        
                        # Extract tools if returned directly by Ollama format
                        tool_calls = data.get("message", {}).get("tool_calls", [])
                        if tool_calls and not raw_text:
                            # Project native function response directly into AUHIP structure
                            call = tool_calls[0]["function"]
                            return LLMResponse(
                                intent=call["name"],
                                confidence=0.95,
                                requires_tool=True,
                                tool_name=call["name"],
                                tool_args=call.get("arguments", {}),
                                response=f"Executing {call['name']}...",
                                escalate=False,
                                raw_response=json.dumps(data),
                                provider_used="local"
                            )

                        return ResponseParser.parse_structured(raw_text, provider="local")

            except asyncio.TimeoutError:
                last_error = "Execution timed out."
                logger.warning(f"Ollama runtime stall on attempt {attempt + 1}. Retrying...")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Ollama connection error on attempt {attempt + 1}: {e}")
                await asyncio.sleep(0.2)

        # Total local core failure triggers escalation hook flag safely
        logger.error(f"Local primary model failed after {llm_config.LOCAL_MAX_RETRIES} attempts. Triggering cloud fallback.")
        return LLMResponse(
            intent="error",
            confidence=0.0,
            requires_tool=False,
            tool_name=None,
            tool_args={},
            response="Neural execution timed out.",
            escalate=True, # Escalate safely to ensure seamless continuity
            raw_response=str(last_error),
            provider_used="local"
        )
