import os
import json
import logging
import asyncio
from typing import Dict, Callable

from dotenv import load_dotenv
import aiohttp

from auhip.skills import (
    activate_home_mode, sleep_mode, system_status,
    open_browser, tell_time, volume_up, volume_down,
    mute_volume, search_web, get_help
)

logger = logging.getLogger(__name__)

# Load env variables from .env file at project root
load_dotenv()


class AuhipAgent:
    """
    The hybrid local-first brain of AUHIP. Uses swappable local and cloud LLMs
    orchestrated through the HybridLLMRouter and centralized ToolManager.
    """

    def __init__(self):
        from auhip.core.llm import ContextManager, HybridLLMRouter, ToolManager, ToolSchema
        
        self.tool_manager = ToolManager()
        self.context_manager = ContextManager()
        self.router = HybridLLMRouter(self.tool_manager, self.context_manager)
        
        # Backward compatibility flag
        self.client = True

        # Register tools cleanly
        self._register_all_tools()
        logger.info("Hybrid local-first orchestration layer initialised.")

    def _register_all_tools(self):
        from auhip.core.llm import ToolSchema
        
        self.tool_manager.register_tool(
            ToolSchema("activate_home_mode", "Run when the user arrives home. Sets the mood and confirms readiness."),
            activate_home_mode
        )
        self.tool_manager.register_tool(
            ToolSchema("sleep_mode", "Enter sleep/standby. Called when the user dismisses auhip for the night."),
            sleep_mode
        )
        self.tool_manager.register_tool(
            ToolSchema("system_status", "Return current CPU usage, RAM usage, and network status."),
            system_status
        )
        self.tool_manager.register_tool(
            ToolSchema("open_browser", "Open the system's default web browser."),
            open_browser
        )
        self.tool_manager.register_tool(
            ToolSchema("tell_time", "Return the current local time."),
            tell_time
        )
        self.tool_manager.register_tool(
            ToolSchema("volume_up", "Increase system audio volume by one step."),
            volume_up
        )
        self.tool_manager.register_tool(
            ToolSchema("volume_down", "Decrease system audio volume by one step."),
            volume_down
        )
        self.tool_manager.register_tool(
            ToolSchema("mute_volume", "Toggle system audio mute."),
            mute_volume
        )
        self.tool_manager.register_tool(
            ToolSchema(
                "search_web", 
                "Search Google for a query and open the results in the browser.",
                parameters={"query": {"type": "string", "description": "The search query string."}},
                required=["query"]
            ),
            search_web
        )
        self.tool_manager.register_tool(
            ToolSchema("get_help", "Lists all available commands and their descriptions."),
            get_help
        )

    def set_mode(self, mode: str):
        """Pass updated active context mode down to hybrid routing layer."""
        self.router.set_mode(mode)

    async def execute(self, user_text: str) -> str:
        """Route a transcribed voice command. Checks local skills first to minimize LLM usage."""
        
        # 1. Try local routing first to minimize latency
        local_response = await self._local_route(user_text)
        if local_response:
            logger.info(f"Local skill matched for: '{user_text}'")
            return local_response

        # 2. Dispatch to Hybrid LLM Router
        try:
            return await self.router.execute(user_text)
        except Exception as e:
            logger.error(f"Router core execution error: {e}")
            return "Error in neural orchestration layer. Please check logs."

    def is_valid_command(self, user_text: str) -> bool:
        """
        Check if the text contains any local skill keywords or wake words.
        Used by the speech fallback system to decide when to try Google Cloud.
        """
        if not user_text:
            return False
            
        text = user_text.lower()
        
        # Check against all keywords in local mapping
        # We extract them from the mapping structure for consistency
        keywords_to_check = [
            "volume up", "volume down", "mute", "time", "what time",
            "status", "cpu", "ram", "open browser", "browser",
            "sleep", "goodbye", "goodnight", "good night", "good bye", "goodbye jojo", "goodnight jojo", "help", "commands",
            "vision up", "vison up", "camera up", "start camera", "turn on camera",
            "vision on", "activate vision", "open vision", "vision panel",
            "show vision", "open camera", "camera open", "camera mode",
            "vision off", "vison off", "camera off", "stop camera", "turn off camera",
            "close vision", "deactivate vision", "hide vision", "close camera",
            "eyes up", "eye up", "eyes on", "eye on", "track eye", "track eyes",
            "activate eye", "start eye", "enable eye",
            "eyes off", "eye off", "eyes down", "eye down",
            "stop eye", "deactivate eye", "disable eye",
            "hands up", "hand up", "hands on", "hand on", "track hand", "track hands",
            "activate hand", "start hand", "enable hand",
            "hands down", "hand down", "hands off", "hand off",
            "stop hand", "deactivate hand", "disable hand",
            "full window", "full screen", "maximize window", "maximize",
            "minimize window", "minimize screen", "minimize",
            "control on", "control mode", "start control",
            "enable control", "cursor control", "cursor mode",
            "control off", "stop control", "disable control",
            "exit control", "exit control mode",
            "two hands", "multi hand", "double hands", "activate two hand",
            "one hand", "single hand", "one hand track", "default hand",
            "search", "google"
        ]
        
        if any(kw in text for kw in keywords_to_check):
            return True
            
        # Check core config phrases
        from auhip.core.config import config
        if config.WAKE_PHRASE in text or config.EXIT_PHRASE in text or config.SHUTDOWN_PHRASE in text:
            return True
            
        return False

    async def _local_route(self, user_text: str):
        """Local keyword dispatch to bypass LLM for common commands."""
        text = user_text.lower()
        
        async def vision_on():
            from auhip.core.event_bus import event_bus
            await event_bus.publish("ENTER_CAMERA_MODE", {})
            return "Entering camera mode."

        async def vision_off():
            from auhip.core.event_bus import event_bus
            await event_bus.publish("EXIT_SUB_MODE", {})
            return "Exiting camera mode."

        async def toggle_fullscreen():
            from auhip.core.event_bus import event_bus
            await event_bus.publish("TOGGLE_FULLSCREEN", {})
            return "Toggling full screen mode."

        async def minimize_window():
            from auhip.core.event_bus import event_bus
            await event_bus.publish("MINIMIZE_WINDOW", {})
            return "Minimizing auhip window."

        async def eye_on():
            from auhip.core.event_bus import event_bus
            await event_bus.publish("SET_EYE_STATE", {"state": True})
            return "Eye tracking activated."

        async def eye_off():
            from auhip.core.event_bus import event_bus
            await event_bus.publish("SET_EYE_STATE", {"state": False})
            return "Eye tracking deactivated."

        async def hand_on():
            from auhip.core.event_bus import event_bus
            await event_bus.publish("SET_HAND_STATE", {"state": True})
            return "Hand tracking activated."

        async def hand_off():
            from auhip.core.event_bus import event_bus
            await event_bus.publish("SET_HAND_STATE", {"state": False})
            return "Hand tracking deactivated."

        async def control_on():
            from auhip.core.event_bus import event_bus
            await event_bus.publish("ENTER_CONTROL_MODE", {})
            return "Entering control mode."

        async def control_off():
            from auhip.core.event_bus import event_bus
            await event_bus.publish("EXIT_SUB_MODE", {})
            return "Exiting control mode."

        async def multi_hand_on():
            from auhip.core.event_bus import event_bus
            await event_bus.publish("SET_MULTI_HAND", {"state": True})
            return "Two-hand tracking activated."

        async def multi_hand_off():
            from auhip.core.event_bus import event_bus
            await event_bus.publish("SET_MULTI_HAND", {"state": False})
            return "Single-hand tracking activated."

        mapping = [
            (["volume up"],               volume_up),
            (["volume down"],             volume_down),
            (["mute"],                    mute_volume),
            (["time", "what time"],       tell_time),
            (["status", "cpu", "ram"],    system_status),
            (["open browser", "browser"], open_browser),
            (["sleep", "goodbye", "goodnight", "good night", "good bye", "goodbye jojo", "goodnight jojo"], sleep_mode),
            (["help", "commands"],        get_help),
            (["vision up", "vison up", "camera up", "start camera", "turn on camera",
              "vision on", "activate vision", "open vision", "vision panel",
              "show vision", "open camera", "camera open", "camera mode"], vision_on),
            (["vision off", "vison off", "camera off", "stop camera", "turn off camera",
              "close vision", "deactivate vision", "hide vision", "close camera"], vision_off),
            (["eyes up", "eye up", "eyes on", "eye on", "track eye", "track eyes",
              "activate eye", "start eye", "enable eye"], eye_on),
            (["eyes off", "eye off", "eyes down", "eye down",
              "stop eye", "deactivate eye", "disable eye"], eye_off),
            (["hands up", "hand up", "hands on", "hand on", "track hand", "track hands",
              "activate hand", "start hand", "enable hand"], hand_on),
            (["hands down", "hand down", "hands off", "hand off",
              "stop hand", "deactivate hand", "disable hand"], hand_off),
            (["full window", "full screen", "maximize window", "maximize"], toggle_fullscreen),
            (["minimize window", "minimize screen", "minimize"], minimize_window),
            (["control on", "control mode", "start control",
              "enable control", "cursor control", "cursor mode"], control_on),
            (["control off", "stop control", "disable control",
              "exit control", "exit control mode"], control_off),
            (["two hands", "multi hand", "double hands", "activate two hand"], multi_hand_on),
            (["one hand", "single hand", "one hand track", "default hand"], multi_hand_off),
        ]

        for keywords, func in mapping:
            if any(kw in text for kw in keywords):
                return await func()

        if "search" in text or "google" in text:
            for kw in ("search for", "search", "google"):
                if kw in text:
                    query = text.split(kw, 1)[-1].strip()
                    if query:
                        return await search_web(query)

        return None
