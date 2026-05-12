import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class LLMConfig:
    # Local Model Settings (Primary Intelligence)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    LOCAL_MODEL_NAME: str = os.getenv("LOCAL_MODEL_NAME", "qwen3:4b") # Alternative: phi4-mini
    LOCAL_TIMEOUT_SECONDS: float = float(os.getenv("LOCAL_TIMEOUT_SECONDS", "8.0"))
    LOCAL_MAX_RETRIES: int = int(os.getenv("LOCAL_MAX_RETRIES", "2"))
    
    # Cloud Escalation Settings (Fallback Layer)
    CLOUD_MODEL_NAME: str = os.getenv("CLOUD_MODEL_NAME", "gemini-flash-latest")
    CLOUD_TIMEOUT_SECONDS: float = float(os.getenv("CLOUD_TIMEOUT_SECONDS", "15.0"))
    CLOUD_MAX_RETRIES: int = int(os.getenv("CLOUD_MAX_RETRIES", "3"))
    
    # Orchestration / Escalation Thresholds
    ESCALATION_CONFIDENCE_THRESHOLD: float = float(os.getenv("ESCALATION_CONFIDENCE_THRESHOLD", "0.70"))
    MAX_HISTORY_MESSAGES: int = int(os.getenv("MAX_HISTORY_MESSAGES", "12"))
    TOKEN_BUDGET_ESTIMATE: int = int(os.getenv("TOKEN_BUDGET_ESTIMATE", "4096"))
    
    # Tool Execution & Security Constraints
    SANDBOX_ALLOWED_DIRS: List[str] = field(default_factory=lambda: [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
        os.path.expanduser("~")
    ])


llm_config = LLMConfig()
