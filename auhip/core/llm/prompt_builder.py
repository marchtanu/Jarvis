import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Centralized prompt assembly engine. Loads core executive rules from user/identity.md
    and binds active machine operational state directly into context headers.
    """

    @staticmethod
    def load_identity() -> str:
        """Loads master instruction sets from persistent identity specification profile."""
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        identity_path = os.path.join(project_root, "user", "identity.md")
        try:
            with open(identity_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.debug("Successfully resolved primary persistent identity prompt profile.")
            return content
        except Exception as e:
            logger.error(f"Failed to resolve identity.md file: {e}")
            return "You are AUHIP, an executive local-first operating system assistant."

    @staticmethod
    def build_system_prompt(current_mode: str = "VOICE_MODE") -> str:
        """
        Combines baseline instructions alongside immediate execution state flags
        to instruct models cleanly.
        """
        identity_text = PromptBuilder.load_identity()
        
        mode_header = f"=== CURRENT EXECUTION STATE: {current_mode} ===\n"
        return f"{identity_text}\n\n{mode_header}"
