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
- `SpeechRecognizer`: Uses local Vosk models to transcribe spoken audio into text, with Google Cloud as a fallback for unrecognized words.

### 3. The State Machine (`jarvis/core/state_machine.py`)
Manages transitions: 
`STANDBY` -> `SNAP_DETECTED` -> `WAITING_WAKE_WORD` (listens for "daddy home") -> `VOICE_MODE` -> `CAMERA_MODE` / `CONTROL_MODE` / `SLEEP`

### 4. The LLM Brain (`jarvis/core/agent.py`)
When in `VOICE_MODE`, transcribed text is first checked against a local keyword router.
If no local match, the Agent uses **Google's Gemini Flash** via raw REST API (using `aiohttp`). It uses `identity.md` as a system instruction and utilizes **Function Calling** to trigger local Python tools defined in `jarvis/skills/`.

### 5. Vision System (`jarvis/vision/`)
- `VisionWorker`: Orchestrates camera feed, hand/eye tracking on a QTimer.
- `GestureEngine`: Detects static hand gestures (open_palm, fist, peace_sign, rock_sign, etc.)
- `MotionEngine`: Detects dynamic hand motions (swipes, push/pull).
- `EyeTracker` + `GazeEstimator` + `BlinkDetector` + `AttentionEngine`: Eye-based interaction pipeline.

### 6. Event Bus (`jarvis/core/event_bus.py`)
Decouples components. The State Machine, Agent, Vision, and Audio layers publish events (e.g., `STATE_CHANGED`, `JARVIS_RESPONSE`, `GESTURE_DETECTED`). The GUI subscribes to these events to update the UI without blocking the main thread.

## Future Roadmap (Phases 2-4)
Refer to `skills/ai-agent.md` for the full roadmap, which includes multi-agent coordination, deep Notion/Calendar integration, behavioral tracking, and autonomous workflows.
