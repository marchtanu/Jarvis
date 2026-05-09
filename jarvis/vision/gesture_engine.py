import time
import math
from collections import deque

class GestureEngine:
    """
    Analyzes hand landmarks to detect static gestures and temporal patterns
    (vertical shake for volume control).
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self._last_gesture = None
        self._last_gesture_time = 0
        self._cooldown = 0.8  # Seconds before the same gesture can trigger again

        # Vertical shake detection: track y-position of index tip over time
        # Used when three_fingers_up is held to determine shake direction
        self._shake_history = deque(maxlen=20)  # (timestamp, y_value)
        self._last_shake_time = 0
        self._shake_cooldown = 0.1

    def detect_static_gesture(self, landmarks):
        """
        Determines the static gesture from a list of 21 landmark dictionaries.
        Returns (gesture_name, confidence).
        """
        if not landmarks or len(landmarks) < 21:
            return "none", 0.0

        # ── Landmark references ────────────────────────────────────────────────
        wrist      = landmarks[0]
        thumb_tip  = landmarks[4]
        thumb_ip   = landmarks[3]
        index_tip  = landmarks[8]
        index_pip  = landmarks[6]
        middle_tip = landmarks[12]
        middle_pip = landmarks[10]
        ring_tip   = landmarks[16]
        ring_pip   = landmarks[14]
        pinky_tip  = landmarks[20]
        pinky_pip  = landmarks[18]

        # ── Finger extension flags ────────────────────────────────────────────
        index_up  = index_tip['y']  < index_pip['y']
        middle_up = middle_tip['y'] < middle_pip['y']
        ring_up   = ring_tip['y']   < ring_pip['y']
        pinky_up  = pinky_tip['y']  < pinky_pip['y']

        index_down  = index_tip['y']  > index_pip['y']
        middle_down = middle_tip['y'] > middle_pip['y']
        ring_down   = ring_tip['y']   > ring_pip['y']
        pinky_down  = pinky_tip['y']  > pinky_pip['y']

        def is_horiz(tip, pip, direction):
            dx = tip['x'] - pip['x']
            dy = tip['y'] - pip['y']
            if abs(dx) > abs(dy) * 1.2: # Must be more horizontal than vertical
                if direction == "left": return dx < 0
                if direction == "right": return dx > 0
            return False

        index_left  = is_horiz(index_tip, index_pip, "left")
        middle_left = is_horiz(middle_tip, middle_pip, "left")
        ring_left   = is_horiz(ring_tip, ring_pip, "left")
        pinky_left  = is_horiz(pinky_tip, pinky_pip, "left")

        index_right  = is_horiz(index_tip, index_pip, "right")
        middle_right = is_horiz(middle_tip, middle_pip, "right")
        ring_right   = is_horiz(ring_tip, ring_pip, "right")
        pinky_right  = is_horiz(pinky_tip, pinky_pip, "right")

        # Thumb
        thumb_up   = thumb_tip['y'] < thumb_ip['y']
        thumb_down = thumb_tip['y'] > thumb_ip['y']
        thumb_out  = abs(thumb_tip['x'] - index_pip['x']) > abs(thumb_ip['x'] - index_pip['x'])

        # ── Counts ────────────────────────────────────────────────────────────
        # Finger-up count (excluding thumb for specific poses, but tracked for general)
        up_count = sum([index_up, middle_up, ring_up, pinky_up])
        phys_up_count = up_count + (1 if thumb_up or thumb_out else 0)

        # ── Classify ──────────────────────────────────────────────────────────
        gesture    = "none"
        confidence = 0.0

        if up_count == 4:
            gesture    = "open_palm"
            confidence = 0.95

        elif index_up and pinky_up and not middle_up and not ring_up:
            # Rock sign works regardless of thumb (🤟 or 🤘)
            gesture    = "rock_sign"
            confidence = 0.95

        elif (index_up and middle_up and ring_up and not pinky_up) or (thumb_out and index_up and middle_up and not ring_up and not pinky_up):
            # 3 fingers (Index+Middle+Ring) OR (Thumb+Index+Middle)
            gesture    = "three_fingers_up"
            confidence = 0.9

        elif index_up and middle_up and not ring_up and not pinky_up:
            gesture    = "peace_sign"
            confidence = 0.95

        elif index_up and not middle_up and not ring_up and not pinky_up:
            gesture    = "one_index_up"
            confidence = 0.95

        elif (index_down and middle_down and ring_down and not pinky_up) or (thumb_out and index_down and middle_down and not ring_up and not pinky_up):
            # 3 fingers pointing down: (Index+Middle+Ring) OR (Thumb+Index+Middle)
            # We use 'elif' because we want this specific gesture to win over 'fist'
            gesture    = "three_fingers_down"
            confidence = 0.9

        elif up_count == 0:
            # General low-finger-count poses
            if not thumb_up and not thumb_out:
                gesture    = "fist"
                confidence = 0.9
            elif thumb_up and not thumb_out:
                gesture    = "thumbs_up"
                confidence = 0.85

        elif index_left and middle_left and not ring_left and not pinky_left:
            # Thumb check relaxed as it usually naturally sticks out or follows
            gesture    = "three_fingers_left"
            confidence = 0.9

        elif index_right and middle_right and not ring_right and not pinky_right:
            gesture    = "three_fingers_right"
            confidence = 0.9

        # ── Shake detection (secondary to static) ─────────────────────────────
        shake = self._detect_vertical_shake(index_tip['y'])
        if shake and gesture in ("three_fingers_up", "three_fingers_down", "peace_sign"):
            gesture    = shake
            confidence = 0.85

        # ── Cooldown ──────────────────────────────────────────────────────────
        current_time = time.time()
        if gesture != "none":
            if gesture == self._last_gesture and (current_time - self._last_gesture_time) < self._cooldown:
                return gesture, confidence
            else:
                self._last_gesture = gesture
                self._last_gesture_time = current_time
                # NOTE: Do NOT publish GESTURE_DETECTED here — VisionWorker._publish_events
                # handles all event publishing. Publishing here caused duplicate events.

        return gesture, confidence

    def _detect_vertical_shake(self, y_value: float):
        """
        Appends y position to history and detects rapid up/down shake.
        Returns 'shake_up', 'shake_down', or None.
        """
        current_time = time.time()
        self._shake_history.append((current_time, y_value))

        if len(self._shake_history) < 8:
            return None

        if (current_time - self._last_shake_time) < self._shake_cooldown:
            return None

        # Look at the recent N frames
        ys = [y for _, y in self._shake_history]
        dy = ys[-1] - ys[0]
        dt = self._shake_history[-1][0] - self._shake_history[0][0]

        if dt == 0:
            return None

        velocity = dy / dt  # normalized units/second

        SHAKE_THRESHOLD = 0.4  # Fast enough vertical movement

        if velocity < -SHAKE_THRESHOLD:
            # Moving up in image coords (y decreasing = hand moving up)
            self._last_shake_time = current_time
            self._shake_history.clear()
            return "shake_up"
        elif velocity > SHAKE_THRESHOLD:
            # Moving down
            self._last_shake_time = current_time
            self._shake_history.clear()
            return "shake_down"

        return None
