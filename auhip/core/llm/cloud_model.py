import asyncio
import json
import logging
import os
import aiohttp
from typing import Dict, Any, Optional

from auhip.core.llm.base import BaseLLMProvider
from auhip.core.llm.config import llm_config
from auhip.core.llm.response_parser import ResponseParser
from auhip.core.llm.types import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """
    Cloud escalation adapter wrapping Google Gemini REST APIs. Intended purely for high-end
    complex reasoning queries exceeding local model bandwidth. Implements exponential backoff.
    """

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model = llm_config.CLOUD_MODEL_NAME
        self.timeout = aiohttp.ClientTimeout(total=llm_config.CLOUD_TIMEOUT_SECONDS)
        
        # Determine internal activation state safely
        self.configured = bool(self.api_key and self.api_key.strip() not in ("", "your-api-key-here"))

    async def is_healthy(self) -> bool:
        return self.configured

    async def generate_structured(self, request: LLMRequest) -> LLMResponse:
        if not self.configured:
            logger.error("Cloud fallback layer missing credentials. Aborting escalation.")
            return LLMResponse(
                intent="error",
                confidence=0.0,
                requires_tool=False,
                tool_name=None,
                tool_args={},
                response="Cloud model unconfigured. Cannot escalate.",
                escalate=False,
                provider_used="cloud"
            )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        # Inject structural schemas to enforce structured JSON adherence from Gemini
        schema_guidance = (
            "You are the cloud escalation layer of AUHIP. Analyze the task and return a decision "
            "strictly formatted as a valid JSON object matching this structure precisely:\n"
            "{\n"
            '  "intent": "string",\n'
            '  "confidence": float,\n'
            '  "requires_tool": boolean,\n'
            '  "tool_name": "string or null",\n'
            '  "tool_args": {},\n'
            '  "response": "string",\n'
            '  "escalate": false\n'
            "}\n"
            "Provide ONLY the JSON output without raw markdown fences or conversational preambles."
        )

        contents = []
        # Transform history structures to Gemini REST specs
        for msg in request.history:
            role = "model" if msg.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        # Inject final user command alongside instruction wrapper
        final_text = f"{request.prompt}\n\n{schema_guidance}" if request.require_structured else request.prompt
        contents.append({"role": "user", "parts": [{"text": final_text}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.1
            }
        }

        last_error = None
        for attempt in range(llm_config.CLOUD_MAX_RETRIES):
            try:
                headers = {"Content-Type": "application/json"}
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.post(url, headers=headers, json=payload) as resp:
                        if resp.status != 200:
                            err_text = await resp.text()
                            logger.error(f"Gemini API failure ({resp.status}): {err_text}")
                            if resp.status == 429:
                                # Exponential rate-limit cooloff
                                await asyncio.sleep(2 ** attempt)
                                continue
                            raise RuntimeError(f"Cloud execution error: {resp.status}")

                        data = await resp.json()
                        candidates = data.get("candidates", [])
                        if not candidates:
                            raise ValueError("Received empty answer array from Cloud model.")

                        part = candidates[0].get("content", {}).get("parts", [{}])[0]
                        raw_text = part.get("text", "")
                        
                        return ResponseParser.parse_structured(raw_text, provider="cloud")

            except asyncio.TimeoutError:
                last_error = "Cloud processing timed out."
                logger.warning(f"Gemini timeout on try {attempt + 1}. Backing off...")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Cloud adapter exception on try {attempt + 1}: {e}")
                await asyncio.sleep(0.5)

        return LLMResponse(
            intent="error",
            confidence=0.0,
            requires_tool=False,
            tool_name=None,
            tool_args={},
            response="External neural core unavailable after multiple retries.",
            escalate=False,
            raw_response=str(last_error),
            provider_used="cloud"
        )
