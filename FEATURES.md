# Jarvis Assistant: Flow & Feature Summary

Jarvis is a multimodal, event-driven executive assistant built with Python and PyQt6, utilizing advanced vision and speech recognition to provide seamless system control.

## 1. Interaction Flows

### Activation & Power States
*   **Wake Up:** Detect **2 Snaps** (within 1 second) → Jarvis waits for wake phrase → Say **"Daddy Home"** to enter Command Mode.
*   **Sleep Mode:** Say **"Goodbye Jojo"** or **"Sleep"** → Jarvis enters Sleep mode (GUI visible but inactive).
*   **Shut Down:** 
    *   **Voice:** Say **"Exit"** or **"Terminate"**.
    *   **Gesture:** Perform `Open Palm` then `Fist` while looking at the camera center (works even in Sleep/Standby).

### Command Cancellation
*   **Emergency Reset:** Hold up **Two Open Palms** and look at the camera center → Publishes `CANCEL_ALL`, resetting Jarvis to standby immediately.

---

## 2. Vision Features

### Eye Tracking Engine
*   **Capabilities:** Detects iris position, blink rate, gaze direction (Left, Right, Center, Up, Down), and attention level.
*   **Attention Engine:** Monitors if the user is `USER_FOCUSED`, `USER_DISTRACTED`, or `USER_ABSENT`.
*   **Control:** Eye tracking is disabled by default to save CPU. Say **"Eyes up"** to activate or **"Eyes off"** to deactivate.

### Hand & Gesture Tracking
*   **Dual-Hand Support:** Can track two hands simultaneously for complex gestures.
*   **Hand Tracking Control:** Say **"Hands up"** to activate or **"Hands down"** to deactivate.

### Camera Interface
*   **Vision Panel:** Integrated GUI component showing live feed with facial landmarks and iris centers.
*   **Voice Toggle:** Say **"Vision up"**, **"Open camera"**, or **"Vision panel"** to show; **"Vision off"** or **"Hide vision"** to hide.

---

## 3. Gesture Command Mapping

| Gesture | Action | Notes |
| :--- | :--- | :--- |
| **Two Open Palms** | `CANCEL_ALL` | Reset processing (requires center gaze). |
| **Rock Sign** | `ZOOM IN` | Zoom into the camera feed (Index & Pinky up). |
| **Thumb & Index Up** | `ZOOM OUT` | Zoom out of the camera feed. |
| **Open Palm -> Fist**| `PLAY/PAUSE` | Toggles system media (2-second cooldown). |
| **Three Fingers Up** | `VOLUME UP` | Increases system volume (+2%). |
| **Three Fingers Down** | `VOLUME DOWN` | Decreases system volume (-2%). |
| **Open Palm → Fist** | `EXIT APP` | Sequence must happen within 1s with center gaze. |

---

## 4. Intelligence & Intelligence
*   **Local Skill Routing:** Commands like "Volume up", "Vision up", and "Time" are handled locally for instant response.
*   **AI Brain:** Complex queries fall back to **Google Gemini 1.5 Flash** for natural language understanding.
*   **Active Commands Panel:** A dedicated UI sidebar that reminds the user of active gesture triggers and how to activate them.

---

## 5. UI Architecture (PyQt6)
*   **State Panel:** Displays current operational state (Standby, Processing, etc.).
*   **Transcript & Response:** Real-time log of what was heard and how Jarvis replied.
*   **Waveform:** Real-time audio energy visualizer.
*   **Developer Tools:** Debug panel to simulate snaps and events without physical triggers.
