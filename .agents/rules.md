# auhip AI Agent Rules

These rules govern how AI coding assistants should interact with and modify the auhip project.

> **Start here:** Read `.agents/architecture.md` for the full file map, state machine, and event bus reference.

## 1. Architectural Philosophy
- **Infrastructure First:** Do not prioritize flashy UI over reliable infrastructure. 
- **Modular Design:** Skills should be modular and contained within `auhip/skills/`. The `auhip/core/agent.py` acts as the primary outward-facing agent bridge, delegating logic to `auhip/core/llm/router.py`.
- **Event-Driven:** The system relies on an Event Bus (`event_bus.py`). UI updates and core state transitions should be broadcast via events rather than tightly coupled direct calls.
- **Single Publisher Rule:** Each event type should have one canonical publisher. Do NOT add secondary publishers (e.g., GestureEngine and VisionWorker both publishing GESTURE_DETECTED).

## 2. Coding Standards
- **Asynchronous Execution:** Most core functionality (especially speech and LLM processing) is async. Use `asyncio` appropriately. UI events are bridged to the async loop via `qasync`.
- **Power States (Flow):**
  - **Cold Activation**: 2 snaps + "daddy home" (GUI hidden -> GUI Open/Voice Mode).
  - **Sleep Mode**: "goodbye jojo" (GUI Open -> GUI Open/Sleep Mode). In Sleep Mode, auhip only responds to 2 snaps followed by either "daddy home" (to resume) or "exit" (to shut down).
  - **Exit**: 2 snaps + "exit" from SLEEP only. Or emergency gesture (open_palm → fist) in SLEEP only.
- **Typing:** Use Python type hints for all new functions and methods.
- **Logging:** Use the standard Python `logging` module. Do not use plain `print()` statements in core logic.

## 3. Speech Recognition Engine
- **Primary Engine:** Use **Vosk** (Local) for all real-time command processing. This ensures low latency and offline functionality.
- **Fallback:** Google Cloud recognition is used automatically when Vosk doesn't match a valid command (via the `validator` callback pattern).
- **Streaming:** Prioritize streaming recognition to ensure auhip reacts while the user is speaking.

## 4. Vision System Rules
- **Event Publishing:** Only `VisionWorker._publish_events()` may publish `GESTURE_DETECTED` and `MOTION_DETECTED`. The engines (`GestureEngine`, `MotionEngine`) are pure classifiers that return `(type, confidence)` — they must NOT publish events themselves.
- **No Background Loops for Actions:** Do not create persistent `asyncio` loops for gesture-based actions. All actions should be event-driven through `StateMachine.on_gesture_detected()`.
- **Mode Isolation:** VisionWorker checks `_vision_mode` to route processing. Camera Mode = gesture + motion. Control Mode = cursor control. Sleep = emergency-only at 10 FPS.
- **Snap Detector Lifecycle:** Must be `start()` in STANDBY/SLEEP, `stop()` in all active modes (VOICE/CAMERA/CONTROL).

## 5. Modifying the "Brain"
- Core routing is managed by `auhip/core/llm/router.py` utilizing the `ToolManager` and swappable local/cloud models.
- When updating `auhip/core/agent.py`, ensure that the system prompt (`user/identity.md`) remains the primary source of truth for the assistant's persona.
- Tools exposed to the LLM must have clear, concise descriptions registered via `ToolSchema` to ensure the model understands when to invoke them safely.
- When adding a new voice command: add to `ToolManager` registration in `_register_all_tools()` AND `_local_route()` mapping AND `is_valid_command()` keywords for fast local fallback.

## 6. UI / GUI Guidelines
- The GUI (`auhip/gui/main_window.py`) must remain minimal, clean, and Apple-like. 
- Avoid overwhelming the UI with text. Prioritize high information density with low cognitive load.
- The UI should primarily react to `STATE_CHANGED`, `AUHIP_RESPONSE`, and `HOME_ACTIVATED` events.
- All colors must come from `auhip/gui/theme.py` constants — no hardcoded hex values in component files.

