# Jarvis Skills Registry

This document outlines the capabilities (tools) exposed to the LLM Brain and how to add new ones.

## Current Skills

### `home_automation.py`
- `activate_home_mode()`: Triggered to set the environment when the user arrives home. 

### `system_controls.py`
- `sleep_mode()`: Puts the assistant to sleep.
- `system_status()`: Uses `psutil` to return real-time CPU and RAM percentage.
- `open_browser()`: Opens the system's default web browser.
- `volume_up()` / `volume_down()` / `mute_volume()`: Uses `pyautogui` to simulate media keys.

### `information.py`
- `tell_time()`: Returns the current system time formatted nicely.
- `search_web(query)`: Takes a query argument, URL-encodes it, and opens a Google search in the browser.
- `get_help()`: Returns a list of all available commands and their descriptions.

---

## How to Add a New Skill

To add a new skill to Jarvis, follow these 3 steps:

1. **Write the Skill Function**
   Create a new async function in the appropriate module inside `jarvis/skills/` (or create a new module).
   ```python
   # jarvis/skills/weather.py
   async def get_weather(location: str) -> str:
       # implementation
       return f"The weather in {location} is..."
   ```

2. **Export the Skill**
   Add the function to `jarvis/skills/__init__.py`.
   ```python
   from .weather import get_weather
   __all__ = [..., "get_weather"]
   ```

3. **Register the Skill in the LLM Brain**
   Open `jarvis/core/agent.py`.
   - Add the function to the imports.
   - Add it to `self.available_tools` mapping.
   - Define its JSON Schema in `self.tools_schema` so the OpenAI model knows how and when to call it.
   ```json
   {
       "type": "function",
       "function": {
           "name": "get_weather",
           "description": "Get the current weather for a specified location.",
           "parameters": {
               "type": "object",
               "properties": {
                   "location": {"type": "string", "description": "The city name"}
               },
               "required": ["location"]
           }
       }
   }
   ```
