# Jarvis Architecture Reference (For AI Agents)

> **Purpose:** This document gives any AI coding assistant instant context to work on this project
> efficiently without re-analyzing the entire codebase. Read this FIRST before making changes.

---

## Quick Reference

| Aspect | Detail |
|---|---|
| **Language** | Python 3.12+ |
| **GUI Framework** | PyQt6 with qasync (async bridge) |
| **Event System** | Custom async EventBus (pub/sub) |
| **Speech** | Vosk (local, primary) + Google Cloud (fallback) |
| **Vision** | MediaPipe (Hands + FaceMesh) via OpenCV |
| **AI Brain** | Google Gemini Flash (REST API, function calling) |
| **Entry Point** | `main.py` |

---

## File Map

```
main.py                          ← Entry point: creates QApp, event loop, wires components
├── jarvis/core/
│   ├── config.py                ← Dataclass with all constants (audio, phrases, timeouts)
│   ├── event_bus.py             ← Singleton async pub/sub system
│   ├── agent.py                 ← LLM brain: local keyword router + Gemini function-calling
│   └── state_machine.py         ← Central FSM: all state transitions, gesture handlers
├── jarvis/audio/
│   ├── microphone.py            ← sounddevice InputStream wrapper
│   ├── snap_detector.py         ← Adaptive threshold snap detection
│   └── speech_recognition.py    ← Vosk + Google Cloud hybrid recognizer
├── jarvis/vision/
│   ├── worker.py                ← QTimer-driven frame processor, mode router
│   ├── camera.py                ← Threaded cv2.VideoCapture with zoom
│   ├── tracker.py               ← MediaPipe Hands wrapper
│   ├── gesture_engine.py        ← Static gesture classifier (fist, palm, peace, etc.)
│   ├── motion_engine.py         ← Motion trajectory detector (swipe, push/pull)
│   ├── eye_tracker.py           ← MediaPipe FaceMesh eye/iris extraction
│   ├── gaze_estimator.py        ← Iris-position-based gaze direction
│   ├── blink_detector.py        ← EAR-based blink detection (single/double/long)
│   ├── attention_engine.py      ← Behavioral state from gaze + blink patterns
│   ├── calibration.py           ← Gaze calibration with outlier trimming
│   └── types.py                 ← TypedDicts for EyeData, BlinkData, GazeData, etc.
├── jarvis/gui/
│   ├── theme.py                 ← Color tokens, state colors, global stylesheet
│   ├── main_window.py           ← QMainWindow: layout + event-to-UI bridge
│   └── components/
│       ├── nav_bar.py           ← Top bar: logo, status badge, clock, last command
│       ├── left_panel.py        ← State panel + mic status + snap dots
│       ├── center_panel.py      ← Waveform + vision + transcript + response
│       ├── right_panel.py       ← Command history + active commands
│       ├── state_panel.py       ← Custom-painted state indicator with breathing glow
│       ├── vision_panel.py      ← Camera feed display + data overlays
│       ├── waveform_widget.py   ← Real-time audio energy visualization
│       ├── transcript_panel.py  ← Live speech transcript (USER / JARVIS)
│       ├── response_panel.py    ← Jarvis response display
│       ├── history_panel.py     ← Command execution history list
│       ├── active_commands_panel.py ← Mode-aware command list with glow animations
│       ├── last_command_widget.py   ← Fading last-action indicator in nav bar
│       └── debug_panel.py       ← Developer tools: mode buttons, feature toggles, hw selectors
├── jarvis/skills/
│   ├── __init__.py              ← Exports all skill functions
│   ├── home_automation.py       ← activate_home_mode()
│   ├── system_controls.py       ← sleep_mode, system_status, volume, browser
│   └── information.py           ← tell_time, search_web, get_help
├── jarvis/commands/
│   └── registry.py              ← LEGACY: unused CommandRegistry (can be deleted)
└── user/
    └── identity.md              ← Persona definition for LLM system prompt
```

---

## State Machine (8 States)

```
STANDBY ──[2 snaps]──→ SNAP_DETECTED ──[2nd snap]──→ WAITING_WAKE_WORD
                                                        │
                                              ["daddy home"]
                                                        ↓
                                                   VOICE_MODE ←─── (always returns here)
                                                    │      │
                                        ["open camera"]  ["control on"]
                                                    ↓      ↓
                                             CAMERA_MODE  CONTROL_MODE
                                                    │      │
                                           [peace_sign]  [rock_sign]
                                                    ↓      ↓
                                             (→ VOICE)  (→ CAMERA)
                                                        
VOICE_MODE/CAMERA_MODE ──["goodbye jojo"]──→ SLEEP
SLEEP ──[2 snaps + "exit"]──→ SHUTDOWN
SLEEP ──[open_palm → fist]──→ SHUTDOWN (emergency, 5s cooldown)
```

### Key State Rules
- **STANDBY/SLEEP**: Only snaps are processed. Voice and gestures ignored.
- **VOICE_MODE**: Always-listening voice. Snap detector OFF. No gesture processing.
- **CAMERA_MODE**: Gestures active. Voice disabled (except temp-voice via index finger up).
- **CONTROL_MODE**: Cursor control via hand. Voice disabled. Only rock_sign exits.
- **PROCESSING**: Transient sub-state of VOICE_MODE while agent executes.
- **SLEEP**: Low-power. Emergency gesture active. Snaps wake. Camera at 10 FPS.

---

## Event Bus — Critical Events

### State Transitions
| Event | Publisher | Subscriber | Purpose |
|---|---|---|---|
| `STATE_CHANGED` | StateMachine | MainWindow | Update UI state indicator |
| `MODE_CHANGED` | StateMachine | MainWindow, DebugPanel, ActiveCommandsPanel | Auto-show vision, update command list |
| `HOME_ACTIVATED` | StateMachine | MainWindow | Show/raise the GUI window |
| `APP_EXIT` | StateMachine | MainWindow | Close application |

### Audio
| Event | Publisher | Subscriber | Purpose |
|---|---|---|---|
| `SNAP_DETECTED` | SnapDetector | StateMachine, MainWindow | Snap trigger chain |
| `SPEECH_RECOGNIZED` | StateMachine | MainWindow | Display transcribed text |

### Vision
| Event | Publisher | Subscriber | Purpose |
|---|---|---|---|
| `SET_VISION_MODE` | StateMachine | VisionWorker | Switch camera/control/sleep/none |
| `GESTURE_DETECTED` | VisionWorker | StateMachine | Route gesture to handler |
| `MOTION_DETECTED` | VisionWorker | StateMachine | Route motion to handler |
| `TEMP_VOICE_START/END` | VisionWorker | StateMachine | Camera mode temp voice |
| `CANCEL_ALL` | VisionWorker | StateMachine | Two-hand open palm cancel |

### Agent Commands
| Event | Publisher | Subscriber | Purpose |
|---|---|---|---|
| `ENTER_CAMERA_MODE` | Agent | StateMachine | Voice command → camera |
| `ENTER_CONTROL_MODE` | Agent | StateMachine | Voice command → control |
| `EXIT_SUB_MODE` | Agent | StateMachine | Voice command → exit sub-mode |

---

## Adding a New Voice Command

1. **Add skill function** in `jarvis/skills/` (async, returns str)
2. **Export** in `jarvis/skills/__init__.py`
3. **Register in Agent** (`jarvis/core/agent.py`):
   - Add to `self.available_tools` dict
   - Add to `self.tools_schema` (Gemini function declaration)
   - Add keyword(s) to `_local_route()` mapping for instant local dispatch
   - Add keyword(s) to `is_valid_command()` for speech fallback validation

## Adding a New Gesture

1. **Add detection logic** in `jarvis/vision/gesture_engine.py` → `detect_static_gesture()`
2. **Handle in StateMachine** → `on_gesture_detected()` or `_handle_camera_gesture()`
3. **Update ActiveCommandsPanel** → add to `mode_commands` dict
4. **Update FEATURES.md** → add to gesture reference tables

---

## Common Pitfalls

> [!WARNING]
> **Do NOT publish events from inside GestureEngine or MotionEngine.**
> VisionWorker._publish_events() is the ONLY place that should publish 
> GESTURE_DETECTED and MOTION_DETECTED events. The engines are pure 
> detection functions that return (type, confidence) tuples.

> [!WARNING]  
> **Do NOT create background loops for gesture-based actions.**
> The old _volume_control_loop() caused double-fires. All gesture actions
> should be event-driven through the state machine's on_gesture_detected() handler.

> [!IMPORTANT]
> **Snap detector lifecycle matters.** It must be:
> - `start()` in STANDBY and SLEEP (for activation)
> - `stop()` in VOICE_MODE, CAMERA_MODE, CONTROL_MODE (prevents false triggers during speech/gesture)
> - `start()` again when entering SLEEP

> [!IMPORTANT]
> **State machine transitions must be idempotent.** Always check `self.state` 
> before transitioning. The async nature means multiple events can arrive 
> between state checks. Guard with `if self.state != expected: return`.

---

## Design System

- **Canvas:** Warm cream `#F8F5F0` (Claude-inspired)
- **Cards:** Pure white `#FFFFFF` with `1px solid #E6DFD8` borders, `12px` radius
- **Accent:** Coral `#CC785C` — used for active states, highlights, primary buttons
- **Dark surfaces:** `#1C1A18` for debug panel and code-like areas
- **Typography:** Inter font family, tight letter-spacing (-0.1px for headers)
- **State colors:** Mapped in `theme.py:STATE_COLORS` — amber for snap, coral for listening, green for camera, blue for control
