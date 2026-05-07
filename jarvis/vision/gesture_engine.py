import time
import math

class GestureEngine:
    """
    Analyzes hand landmarks to detect static gestures.
    """
    def __init__(self):
        self._last_gesture = None
        self._last_gesture_time = 0
        self._cooldown = 1.0  # Seconds before the same gesture can trigger again

    def detect_static_gesture(self, landmarks):
        """
        Determines the static gesture from a list of 21 landmark dictionaries.
        Returns the gesture name and confidence.
        """
        if not landmarks or len(landmarks) < 21:
            return "none", 0.0

        # Extract useful points
        # Each landmark is a dict: {'x': float, 'y': float, 'z': float, 'visibility': float}
        wrist = landmarks[0]
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        index_tip = landmarks[8]
        index_pip = landmarks[6]
        middle_tip = landmarks[12]
        middle_pip = landmarks[10]
        ring_tip = landmarks[16]
        ring_pip = landmarks[14]
        pinky_tip = landmarks[20]
        pinky_pip = landmarks[18]

        # Determine if fingers are extended
        # For a hand pointing upwards, y is smaller at the top of the image.
        index_up = index_tip['y'] < index_pip['y']
        middle_up = middle_tip['y'] < middle_pip['y']
        ring_up = ring_tip['y'] < ring_pip['y']
        pinky_up = pinky_tip['y'] < pinky_pip['y']

        # Thumb logic: depends on handedness. For simplicity, check if it's further from center than IP.
        # A rough heuristic:
        thumb_up = thumb_tip['y'] < thumb_ip['y']
        thumb_out = abs(thumb_tip['x'] - index_pip['x']) > abs(thumb_ip['x'] - index_pip['x'])

        # Classify Gesture
        gesture = "none"
        confidence = 0.0

        if index_up and middle_up and ring_up and pinky_up:
            gesture = "open_palm"
            confidence = 0.9
        elif not index_up and not middle_up and not ring_up and not pinky_up:
            if thumb_up and not thumb_out:
                gesture = "thumbs_up"
                confidence = 0.8
            else:
                gesture = "fist"
                confidence = 0.85
        elif index_up and middle_up and not ring_up and not pinky_up:
            gesture = "peace_sign"
            confidence = 0.85

        # Apply cooldown
        current_time = time.time()
        if gesture != "none":
            if gesture == self._last_gesture and (current_time - self._last_gesture_time) < self._cooldown:
                # Still in cooldown for this gesture
                return gesture, confidence
            else:
                # New gesture or cooldown expired
                self._last_gesture = gesture
                self._last_gesture_time = current_time
                self._publish_gesture(gesture, confidence)

        return gesture, confidence

    def _publish_gesture(self, gesture, confidence):
        from jarvis.core.event_bus import event_bus
        import asyncio
        # We might be calling this from a synchronous context (e.g. QTimer)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(event_bus.publish("GESTURE_DETECTED", {"gesture": gesture, "confidence": confidence}))
        except RuntimeError:
            pass # No running loop
