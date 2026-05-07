# Jarvis AI Agent Rules

These rules govern how AI coding assistants should interact with and modify the Jarvis project.

## 1. Architectural Philosophy
- **Infrastructure First:** Do not prioritize flashy UI over reliable infrastructure. 
- **Modular Design:** Skills should be modular and contained within `jarvis/skills/`. The `jarvis/core/agent.py` acts as the router/brain.
- **Event-Driven:** The system relies on an Event Bus (`event_bus.py`). UI updates and core state transitions should be broadcast via events rather than tightly coupled direct calls.

## 2. Coding Standards
- **Asynchronous Execution:** Most core functionality (especially speech and LLM processing) is async. Use `asyncio` appropriately. UI events are bridged to the async loop via `qasync`.
- **Power States (Flow):**
  - **Cold Activation**: 2 snaps + "daddy home" (GUI hidden -> GUI Open/Command Mode).
  - **Sleep Mode**: "goodbye jojo" (GUI Open -> GUI Open/Sleep Mode). In Sleep Mode, Jarvis only responds to 2 snaps followed by either "daddy home" (to resume) or "exit" (to shut down).
  - **Exit**: 2 snaps + "exit" (GUI Open -> Termination).
- **Typing:** Use Python type hints for all new functions and methods.
- **Logging:** Use the standard Python `logging` module. Do not use plain `print()` statements in core logic.

## 3. Modifying the "Brain"
- When updating `jarvis/core/agent.py`, ensure that the system prompt (`user/identity.md`) remains the primary source of truth for the assistant's persona.
- Tools exposed to the LLM must have clear, concise descriptions in the `tools_schema` to ensure the model understands when to invoke them.

## 4. UI / GUI Guidelines
- The GUI (`jarvis/gui/main_window.py`) must remain minimal, clean, and Apple-like. 
- Avoid overwhelming the UI with text. Prioritize high information density with low cognitive load.
- The UI should primarily react to `STATE_CHANGED`, `JARVIS_RESPONSE`, and `HOME_ACTIVATED` events.
