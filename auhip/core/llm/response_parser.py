import json
import logging
import re
from typing import Dict, Any, Optional
from auhip.core.llm.types import LLMResponse

logger = logging.getLogger(__name__)


class ResponseParser:
    """
    Robust JSON extraction engine capable of stripping markdown fenced wrappers,
    repairing syntax errors, and projecting natural text fallback into valid structs.
    """

    @staticmethod
    def parse_structured(raw_text: str, provider: str = "local") -> LLMResponse:
        text = raw_text.strip()
        
        # 1. Try stripping code blocks if model wrapped the JSON
        if "```" in text:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
            else:
                # Fallback: remove all triple backtick markers manually
                text = re.sub(r"```[a-z]*", "", text).strip()

        # 2. Attempt raw JSON validation
        try:
            data = json.loads(text)
            return LLMResponse(
                intent=data.get("intent", "chat"),
                confidence=float(data.get("confidence", 1.0)),
                requires_tool=bool(data.get("requires_tool", False)),
                tool_name=data.get("tool_name"),
                tool_args=data.get("tool_args", {}),
                response=data.get("response", ""),
                escalate=bool(data.get("escalate", False)),
                raw_response=raw_text,
                provider_used=provider
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Malformed structured JSON received from {provider}: {e}. Activating heuristic projection.")
            
            # Heuristic intent extraction for broken responses
            intent = "chat"
            requires_tool = False
            tool_name = None
            tool_args = {}
            escalate = False
            
            lower_text = text.lower()
            if "search" in lower_text or "google" in lower_text:
                intent = "search_web"
                requires_tool = True
                tool_name = "search_web"
                # Strip intent triggers to find possible query
                query = text
                for marker in ["search for", "search", "google"]:
                    if marker in lower_text:
                        query = text[lower_text.find(marker) + len(marker):].strip()
                        break
                tool_args = {"query": query if query else "latest AI developments"}
            elif "complex" in lower_text or "escalate" in lower_text:
                escalate = True
                
            return LLMResponse(
                intent=intent,
                confidence=0.5, # Low confidence ensures proper safety escalation checking
                requires_tool=requires_tool,
                tool_name=tool_name,
                tool_args=tool_args,
                response=text,
                escalate=escalate,
                raw_response=raw_text,
                provider_used=provider
            )
