from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)


@dataclass
class Message:
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class LLMResponse:
    intent: str
    confidence: float
    requires_tool: bool
    tool_name: Optional[str]
    tool_args: Dict[str, Any]
    response: str
    escalate: bool
    raw_response: str = ""
    provider_used: str = "local"


@dataclass
class LLMRequest:
    prompt: str
    history: List[Message] = field(default_factory=list)
    available_tools: List[ToolSchema] = field(default_factory=list)
    require_structured: bool = True
