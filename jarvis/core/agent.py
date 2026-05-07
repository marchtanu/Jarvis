import os
import json
import logging
import asyncio
from typing import Dict, Callable

from dotenv import load_dotenv
import aiohttp

from jarvis.skills import (
    activate_home_mode, sleep_mode, system_status,
    open_browser, tell_time, volume_up, volume_down,
    mute_volume, search_web, get_help
)

logger = logging.getLogger(__name__)

# Load env variables from .env file at project root
load_dotenv()


class JarvisAgent:
    """
    The LLM Brain of Jarvis using Google Gemini via raw REST API.
    Reads identity.md to build a system prompt, then routes voice commands
    through Gemini (function-calling) or falls back to local skill matching.
    """

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")

        if not self.api_key or self.api_key.strip() in ("", "your-api-key-here"):
            logger.warning("GOOGLE_API_KEY not configured. Running in local fallback mode.")
            self.client = None
        else:
            self.client = True # Flag to indicate AI mode
            self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={self.api_key}"
            self.system_prompt = self._build_system_prompt()
            
            # Mapping for manual dispatch
            self.available_tools: Dict[str, Callable] = {
                "activate_home_mode": activate_home_mode,
                "sleep_mode":          sleep_mode,
                "system_status":       system_status,
                "open_browser":        open_browser,
                "tell_time":           tell_time,
                "volume_up":           volume_up,
                "volume_down":         volume_down,
                "mute_volume":         mute_volume,
                "search_web":          search_web,
                "get_help":            get_help,
            }

            # Gemini tool schema
            self.tools_schema = [{
                "functionDeclarations": [
                    {
                        "name": "activate_home_mode",
                        "description": "Run when the user arrives home. Sets the mood and confirms readiness."
                    },
                    {
                        "name": "sleep_mode",
                        "description": "Enter sleep/standby. Called when the user dismisses Jarvis for the night."
                    },
                    {
                        "name": "system_status",
                        "description": "Return current CPU usage, RAM usage, and network status."
                    },
                    {
                        "name": "open_browser",
                        "description": "Open the system's default web browser."
                    },
                    {
                        "name": "tell_time",
                        "description": "Return the current local time."
                    },
                    {
                        "name": "volume_up",
                        "description": "Increase system audio volume by one step."
                    },
                    {
                        "name": "volume_down",
                        "description": "Decrease system audio volume by one step."
                    },
                    {
                        "name": "mute_volume",
                        "description": "Toggle system audio mute."
                    },
                    {
                        "name": "search_web",
                        "description": "Search Google for a query and open the results in the browser.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "query": {
                                    "type": "STRING",
                                    "description": "The search query string."
                                }
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "get_help",
                        "description": "Lists all available commands and their descriptions."
                    }
                ]
            }]

            self.conversation_history = []
            logger.info("Gemini AI REST client initialised.")

    def _build_system_prompt(self) -> str:
        """Compose the system prompt from a preamble + the full identity.md."""
        preamble = (
            "You are Jarvis, an elite executive AI assistant. "
            "The following profile defines your persona, communication style, "
            "and responsibilities. Internalise it completely.\n\n"
            "OPERATIONAL RULES:\n"
            "- Address the user as 'Master' unless context suggests otherwise.\n"
            "- Be direct, concise, and high signal-to-noise. No fluff.\n"
            "- Prioritise correctness over agreement. Challenge weak reasoning.\n"
            "- When a tool is available and relevant, USE IT without asking permission.\n"
            "- After executing a tool, report the result in one short sentence.\n"
            "- If no tool applies, respond conversationally but keep it brief.\n\n"
            "=== USER IDENTITY PROFILE ===\n"
        )
        identity = self._load_identity()
        return preamble + identity

    def _load_identity(self) -> str:
        """Load user/identity.md relative to the project root."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        identity_path = os.path.join(project_root, "user", "identity.md")
        try:
            with open(identity_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info(f"Loaded identity profile ({len(content)} chars).")
            return content
        except Exception as e:
            logger.error(f"Could not load identity.md: {e}")
            return "(No identity profile found.)"

    async def execute(self, user_text: str) -> str:
        """Route a transcribed voice command through the LLM or local fallback."""
        if not self.client:
            return await self._fallback_execute(user_text)
        
        try:
            self.conversation_history.append({"role": "user", "parts": [{"text": user_text}]})
            
            # Keep history manageable (last 10 turns)
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]

            payload = {
                "systemInstruction": {"parts": [{"text": self.system_prompt}]},
                "contents": self.conversation_history,
                "tools": self.tools_schema,
            }

            headers = {"Content-Type": "application/json"}

            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Gemini API error ({resp.status}): {error_text}")
                        return await self._fallback_execute(user_text)
                    
                    data = await resp.json()

            if "candidates" not in data or not data["candidates"]:
                return "I received an empty response from my neural core."

            part = data["candidates"][0]["content"]["parts"][0]
            
            if "functionCall" in part:
                call = part["functionCall"]
                name = call["name"]
                args = call.get("args", {})
                
                logger.info(f"Gemini requested tool: {name}")
                func = self.available_tools.get(name)
                
                if func:
                    result = await func(**args)
                    
                    # Append assistant's function call
                    self.conversation_history.append({
                        "role": "model",
                        "parts": [{"functionCall": call}]
                    })
                    
                    # Send result back
                    self.conversation_history.append({
                        "role": "function",
                        "parts": [{"functionResponse": {"name": name, "response": {"result": str(result)}}}]
                    })
                    
                    payload["contents"] = self.conversation_history
                    async with aiohttp.ClientSession() as session:
                        async with session.post(self.api_url, headers=headers, json=payload) as resp:
                            if resp.status == 200:
                                followup_data = await resp.json()
                                if "candidates" in followup_data:
                                    final_text = followup_data["candidates"][0]["content"]["parts"][0].get("text", "")
                                    self.conversation_history.append({"role": "model", "parts": [{"text": final_text}]})
                                    return final_text
                            return f"Tool executed successfully: {result}"

            text = part.get("text", "")
            self.conversation_history.append({"role": "model", "parts": [{"text": text}]})
            return text

        except Exception as e:
            logger.error(f"Gemini execution error: {e}")
            return await self._fallback_execute(user_text)

    async def _fallback_execute(self, user_text: str) -> str:
        """Local keyword dispatch when AI is unavailable."""
        text = user_text.lower()

        mapping = [
            (["volume up"],               volume_up),
            (["volume down"],             volume_down),
            (["mute"],                    mute_volume),
            (["time", "what time"],       tell_time),
            (["status", "cpu", "ram"],    system_status),
            (["open browser", "browser"], open_browser),
            (["sleep", "goodbye"],        sleep_mode),
            (["help", "commands"],        get_help),
        ]

        for keywords, func in mapping:
            if any(kw in text for kw in keywords):
                result = await func()
                return f"{result} [Fallback mode — add GOOGLE_API_KEY to .env to enable AI]"

        if "search" in text or "google" in text:
            for kw in ("search for", "search", "google"):
                if kw in text:
                    query = text.split(kw, 1)[-1].strip()
                    if query:
                        result = await search_web(query)
                        return f"{result} [Fallback mode]"

        return (
            "Running in fallback mode — API unavailable. "
            "Check your GOOGLE_API_KEY or connection."
        )
