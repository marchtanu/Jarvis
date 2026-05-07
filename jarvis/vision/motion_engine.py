import time
from collections import deque
import numpy as np

class MotionEngine:
    """
    Analyzes hand movement over time to detect motion gestures (swipes, push, pull).
    """
    def __init__(self, history_size=15):
        # Store tuples of (timestamp, x, y, size)
        self._history = deque(maxlen=history_size)
        self._cooldown = 1.0
        self._last_motion_time = 0

    def process_landmarks(self, landmarks):
        """
        Extracts centroid and bounding box size, adds to history, and checks for motion.
        """
        if not landmarks or len(landmarks) < 21:
            return "none", 0.0

        xs = [lm['x'] for lm in landmarks]
        ys = [lm['y'] for lm in landmarks]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        centroid_x = (min_x + max_x) / 2
        centroid_y = (min_y + max_y) / 2
        
        # Bounding box diagonal as a proxy for size/depth
        size = np.sqrt((max_x - min_x)**2 + (max_y - min_y)**2)

        current_time = time.time()
        self._history.append((current_time, centroid_x, centroid_y, size))

        return self._detect_motion(current_time)

    def _detect_motion(self, current_time):
        if len(self._history) < 10:
            return "none", 0.0

        if (current_time - self._last_motion_time) < self._cooldown:
            return "none", 0.0

        # Compare oldest and newest in the deque window
        t_start, x_start, y_start, s_start = self._history[0]
        t_end, x_end, y_end, s_end = self._history[-1]

        dt = t_end - t_start
        if dt == 0:
            return "none", 0.0

        dx = x_end - x_start
        dy = y_end - y_start
        ds = s_end - s_start

        vx = dx / dt
        vy = dy / dt
        vs = ds / dt

        # Thresholds (normalized coordinates / second)
        SWIPE_THRESHOLD = 1.5
        DEPTH_THRESHOLD = 0.5

        motion = "none"
        confidence = 0.0

        if abs(vx) > SWIPE_THRESHOLD and abs(vx) > abs(vy):
            if vx > 0:
                motion = "swipe_right"
            else:
                motion = "swipe_left"
            confidence = min(abs(vx) / 3.0, 1.0)
            
        elif abs(vs) > DEPTH_THRESHOLD:
            if vs > 0:
                motion = "push_forward" # Hand gets bigger
            else:
                motion = "pull_back" # Hand gets smaller
            confidence = min(abs(vs) / 1.0, 1.0)

        if motion != "none":
            self._last_motion_time = current_time
            self._history.clear() # Clear history to prevent multiple triggers
            self._publish_motion(motion, confidence)

        return motion, confidence

    def _publish_motion(self, motion, confidence):
        from jarvis.core.event_bus import event_bus
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(event_bus.publish("MOTION_DETECTED", {"motion": motion, "confidence": confidence}))
        except RuntimeError:
            pass
