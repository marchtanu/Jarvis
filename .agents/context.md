# Jarvis Project Context

## The Vision
The ultimate goal of this project is to build an **Executive Operating System for Life Optimization**. 
It is not meant to be a simple chatbot or a novelty voice assistant. It is designed to be a "Second Brain" that:
- Manages information and orchestrates tasks.
- Assists in strategic decision making.
- Monitors behavior and improves execution consistency.
- Acts proactively rather than reactively.

## The Persona
The assistant operates under an Elite Executive Assistant archetype defined in `user/identity.md`. 
Key traits:
- Direct, logical, high signal-to-noise communication.
- Prioritizes correctness and strategic value over emotional comfort.
- Acts as a cognitive compression layer to reduce chaos and focus the user.

## System Architecture (Current State)
We are currently in **Phase 1 (Foundation)**.

### 1. The Core Loop
The system runs via `main.py` which initializes an asynchronous event loop (`qasync`) tying together a PyQt6 GUI and backend background tasks.

### 2. Audio Processing Pipeline
- `Microphone`: Captures audio chunks.
- `SnapDetector`: Listens for a double-snap physical trigger to wake the system.
- `SpeechRecognizer`: Uses local Vosk models to transcribe spoken audio into text.

### 3. The State Machine (`jarvis/core/state_machine.py`)
Manages transitions: 
`STANDBY` -> `SNAP_DETECTED` -> `WAITING_WAKE_WORD` (listens for "daddy home") -> `COMMAND_MODE`

### 4. The LLM Brain (`jarvis/core/agent.py`)
Replaced the old static command registry.
When in `COMMAND_MODE`, transcribed text is sent to the `JarvisAgent`. 
The Agent uses **Google's Gemini Flash** via raw REST API (using `aiohttp` to bypass deprecated SDKs). It uses `identity.md` as a system instruction and utilizes **Function Calling** to trigger local Python tools defined in `jarvis/skills/`.

### 5. Event Bus (`jarvis/core/event_bus.py`)
Decouples components. The State Machine, Agent, and Audio layers publish events (e.g., `STATE_CHANGED`, `JARVIS_RESPONSE`, `HOME_ACTIVATED`). The GUI subscribes to these events to update the UI without blocking the main thread.

## Future Roadmap (Phases 2-4)
Refer to `skills/ai-agent.md` for the full roadmap, which includes multi-agent coordination, deep Notion/Calendar integration, behavioral tracking, and autonomous workflows.
