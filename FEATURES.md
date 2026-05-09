# Jarvis AI Assistant — Mode Reference & Interaction Flow

> **Design Principle:** Only one primary interaction system dominates at a time — Voice, Camera, or Cursor Control. This prevents input conflicts, false triggers, and resource overload.

---

## State Hierarchy

```
STANDBY
├── [2 snaps + "daddy home"] ──→ VOICE MODE
│       ├── ["open camera"] ──→ CAMERA MODE  (returns to Voice on "camera off")
│       └── ["control on"]  ──→ CONTROL MODE (returns to Voice on "control off")
│
└── ["goodbye jojo" / "goodnight"] ──→ SLEEP MODE
        └── [2 snaps + "daddy home"] ──→ VOICE MODE

EMERGENCY (works in ALL states)
└── [open_palm → fist] ──→ EXIT PROGRAM
```

---

## Mode 1 — Standby

**Activated by:** `python main.py`

**Purpose:** Low-power passive listening. Ignores all voice commands and gestures except activation triggers.

### Accepted Inputs

| Input | Action |
|---|---|
| Snap × 2 + **"daddy home"** | → Voice Mode |
| Snap × 2 + **"exit"** (exact) | → Shutdown (only from Sleep → Snap flow) |

### Rules
- All other voice commands → ignored
- All other gestures → ignored (emergency gesture not active in Standby)
- Camera feed not active

---

## Mode 2 — Voice Mode

**Activated by:** 2 snaps + "daddy home"

**On Enter:** GUI opens, always-listening voice recognition starts.

### Available Voice Commands

| Phrase(s) | Action |
|---|---|
| `"vision up"` / `"open camera"` / `"camera open"` | → Activate Camera Mode |
| `"control on"` / `"control mode"` / `"cursor mode"` | → Activate Control Mode |
| `"goodbye jojo"` / `"goodnight"` | → Sleep Mode |
| `"exit"` / `"terminate program"` | → Blocked in Voice Mode (must sleep first) |
| `"help"` / `"commands"` | List all commands, modes, gestures |
| `"volume up"` | Increase system volume |
| `"volume down"` | Decrease system volume |
| `"mute"` | Toggle mute |
| `"time"` / `"what time"` | Read current time |
| `"status"` / `"cpu"` / `"ram"` | System resource report |
| `"browser"` / `"open browser"` | Open default browser |
| `"search [query]"` / `"google [query]"` | Web search |
| `"eye up"` / `"eye off"` | Toggle eye tracking |
| `"hand up"` / `"hand off"` | Toggle hand tracking |
| `"full screen"` / `"maximize"` | Toggle fullscreen |
| `"minimize"` / `"minimize window"` | Minimize Jarvis to taskbar |

### Rules
- Always-listening voice recognition **active**
- Gestures not processed (except global emergency)

---

## Mode 3 — Camera Mode

**Activated by:** voice command `"open camera"` from Voice Mode

**On Enter:** Camera feed opens. Always-listening voice **disabled**.

### Temporary Voice Activation (Index Finger Up)

| Gesture | Effect |
|---|---|
| Raise **index finger only** (`one_index_up`) | Voice listening activates while finger is up |
| Lower index finger | Voice listening stops |

While temporarily listening, you can say:
- `"camera off"` → return to Voice Mode
- `"goodbye jojo"` / `"goodnight"` → Sleep Mode
- `"exit"` → Shutdown
- Any other command → processed normally

### Camera Gestures

| Gesture | Action | Notes |
|---|---|---|
| **Thumb + Index + Middle up** | Volume Up | Hold to increase, shake upward to speed up |
| **Thumb + Index + Middle down** | Volume Down | Hold to decrease, shake downward to speed up |
| **Thumb + Index + Middle right** | Next Track | Point right |
| **Thumb + Index + Middle left** | Previous Track | Point left |
| **Open Palm → Fist** | Play / Pause | Must complete within 1.5s |
| **Index finger up only** | Temp voice ON | While held |

### Rules
- Always-listening voice: **disabled**
- All Control Mode cursor gestures: **inactive**
- Emergency gesture (`open_palm → fist` for exit) still active globally

---

## Mode 4 — Control Mode

**Activated by:** voice command `"control on"` from Voice Mode

**On Enter:** Cursor control via hand gestures. All Camera Mode gestures disabled. Voice disabled.

### Control Mode Gestures

| Gesture | Action | Notes |
|---|---|---|
| **Thumb + Index + Middle up** | Move cursor | Cursor follows hand position |
| **Index + Middle tap Thumb** (quick) | Mouse click | Release within 0.6s |
| **Index + Middle hold Thumb** (≥0.6s) | Hold click / Drag | `mouseDown` while held, `mouseUp` on release |
| **Rock sign** (Index + Pinky up, thumb down) | Exit → Voice Mode | 1.5s cooldown |

### Deactivation
- **Gesture:** `rock_sign` (index + pinky up, thumb down) → returns to Voice Mode

### Rules
- Always-listening voice: **disabled** (prevents gesture + voice command conflicts)
- Camera Mode gestures: **all disabled**
- Emergency gesture (`open_palm → fist`) still active globally

---

## Mode 5 — Sleep Mode

**Activated by:** `"goodbye jojo"` or `"goodnight"` from any active mode

**Purpose:** Low-activity standby with GUI visible. Extends Standby Mode rules.

### Accepted Inputs

| Input | Action |
|---|---|
| Snap × 2 + **"daddy home"** | → Voice Mode |
| Snap × 2 + **"exit"** | → Shutdown |
| `open_palm → fist` | → Exit program (global override) |

### Rules
- Identical to Standby: only snaps and emergency gesture processed
- GUI remains visible
- Camera feed stops
- Voice recognition: paused

---

## Global Emergency Override

Works in **Sleep Mode only** to terminate.

| Gesture | Action | Cooldown |
|---|---|---|
| `open_palm → fist` (within 1.0s) | Immediately exit the program | 5s cooldown |

- **5-second** cooldown between triggers
- Only active in **Sleep Mode** — prevents accidental exits during gesture control

---

## Transition Summary

```
[start]          → STANDBY
STANDBY          → VOICE MODE     (2 snaps + "daddy home")
VOICE MODE       → CAMERA MODE    ("open camera" / "vision up")
VOICE MODE       → CONTROL MODE   ("control on")
VOICE MODE       → SLEEP          ("goodbye jojo" / "goodnight")
CAMERA MODE      → VOICE MODE     (peace_sign gesture / "camera off")
CAMERA MODE      → SLEEP          ("goodbye jojo" while index up)
CONTROL MODE     → CAMERA MODE    (rock_sign gesture / "control off")
SLEEP            → VOICE MODE     (2 snaps + "daddy home")
SLEEP            → SHUTDOWN       (2 snaps + "exit")
SLEEP            → SHUTDOWN       (open_palm → fist, 5s cooldown)
```

---

## Full Gesture Reference

### Emergency (Sleep Mode Only)
| Gesture | Action |
|---|---|
| `open_palm → fist` | Exit program (5s cooldown) |

### Voice Mode
| Input Type | Trigger | Action |
|---|---|---|
| Voice | "open camera" | → Camera Mode |
| Voice | "control on" | → Control Mode |
| Voice | "goodbye jojo" | → Sleep Mode |
| Voice | "help" | List all commands |

### Camera Mode
| Gesture | Action |
|---|---|
| Index up only | Temp voice on |
| Thumb+Index+Middle up | Volume up (hold), Shake up (burst) |
| Thumb+Index+Middle down | Volume down (hold), Shake down (burst) |
| Thumb+Index+Middle right | Next track |
| Thumb+Index+Middle left | Previous track |
| Open palm → fist | Play/Pause |

### Control Mode
| Gesture | Action |
|---|---|
| Thumb+Index+Middle up | Move cursor |
| Index+Middle tap thumb | Click |
| Index+Middle hold thumb | Hold click / drag |
| Rock sign (Index+Pinky only) | Exit → Voice Mode |

---

## Intelligence Layer

- **Local Skill Router:** Instant response for known commands (volume, time, system status, etc.) — no AI call needed
- **Local Speech Recognition (Vosk):** Real-time, offline command processing using the `vosk-model-small-en-us-0.15` model. Significant latency reduction compared to cloud APIs.
- **AI Brain (Gemini Flash):** Complex or unrecognized commands fall back to LLM with function-calling
- **Event Bus:** All modules communicate via async pub/sub events — decoupled and extensible
