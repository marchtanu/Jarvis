# Jarvis Assistant

A Python-based personal assistant with double-snap activation and offline voice command recognition.

## Features
- **Real-time Listening**: Continuous microphone monitoring.
- **Double-Snap Trigger**: Robust energy-based detection for "armed" mode.
- **Offline Voice Recognition**: Powered by Vosk for low-latency, private STT.
- **Event-Driven Architecture**: Decoupled modules using an asynchronous event bus.
- **FSM Management**: Clean state transitions (IDLE -> SNAP_1 -> ARMED -> LISTENING -> EXECUTING).

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Download Vosk Model**:
   - Go to [Alphacephei Vosk Models](https://alphacephei.com/vosk/models).
   - Download a small English model (e.g., `vosk-model-small-en-us-0.15`).
   - Extract it into the project root and rename the folder to `model` (or update `VOSK_MODEL_PATH` in `jarvis/core/config.py`).

## Usage

Run the main script:
```bash
python main.py
```

1. System starts in **IDLE** mode.
2. Snap once -> **SNAP_1_DETECTED**.
3. Snap again within 2 seconds -> **ARMED** & **LISTENING**.
4. Speak "daddy home" -> Executes action.

## Configuration

Adjust thresholds in `jarvis/core/config.py`:
- `SNAP_THRESHOLD_MULTIPLIER`: Increase if getting false positives; decrease if snaps aren't detected.
- `SNAP_REFRACTORY_PERIOD`: Time to wait after a snap before listening for another (prevents double-triggering on one snap).
- `COMMAND_TIMEOUT`: How long to listen for a voice command.

## Architecture

- `/audio`: Microphone stream, snap detector, and speech recognition logic.
- `/core`: Event bus, configuration, and state machine.
- `/commands`: Action registry and automation functions.
