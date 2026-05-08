import cv2
import threading
import numpy as np
import time
import logging

logger = logging.getLogger(__name__)

class Camera:
    """
    Background thread camera capture to prevent blocking the async event loop.
    """
    def __init__(self, camera_index=0, fps=30):
        self.camera_index = camera_index
        self.target_fps = fps
        self.capture = None
        self._frame = None
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        
        # FPS Tracking
        self._frame_count = 0
        self._start_time = time.time()
        self._current_fps = 0.0
        
        # Digital Zoom
        self._zoom_level = 1.0  # Current visual zoom
        self._target_zoom = 1.0 # Desired zoom
        self._zoom_smoothing = 0.15 # Higher = faster zoom

    def start(self):
        if self._running:
            return
        self.capture = cv2.VideoCapture(self.camera_index)
        # Try to set properties for smooth capture
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.capture.set(cv2.CAP_PROP_FPS, self.target_fps)
        
        self._running = True
        self._thread = threading.Thread(target=self._update, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
        if self.capture:
            self.capture.release()
            self.capture = None

    def restart(self, new_index):
        """Restarts the camera with a new index."""
        was_running = self._running
        self.stop()
        self.camera_index = new_index
        if was_running:
            self.start()

    def _update(self):
        while self._running:
            if self.capture and self.capture.isOpened():
                ret, frame = self.capture.read()
                if ret:
                    # Mirror the frame horizontally for selfie-view
                    frame = cv2.flip(frame, 1)
                    
                    # Smooth Zoom Interpolation
                    if abs(self._zoom_level - self._target_zoom) > 0.01:
                        self._zoom_level += (self._target_zoom - self._zoom_level) * self._zoom_smoothing
                    else:
                        self._zoom_level = self._target_zoom

                    with self._lock:
                        self._frame = frame
                    
                    # Update FPS metrics
                    self._frame_count += 1
                    elapsed = time.time() - self._start_time
                    if elapsed > 1.0:
                        self._current_fps = self._frame_count / elapsed
                        self._frame_count = 0
                        self._start_time = time.time()

            # A small sleep to yield thread execution
            cv2.waitKey(max(1, int(1000 / self.target_fps)))

    def get_frame(self) -> np.ndarray | None:
        with self._lock:
            if self._frame is None:
                return None
            
            frame = self._frame.copy()
            
            # Apply digital zoom
            if self._zoom_level > 1.0:
                h, w = frame.shape[:2]
                new_w, new_h = int(w / self._zoom_level), int(h / self._zoom_level)
                x = (w - new_w) // 2
                y = (h - new_h) // 2
                frame = frame[y:y+new_h, x:x+new_w]
                frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)
            
            return frame

    def set_zoom(self, level: float):
        self._target_zoom = max(1.0, min(level, 3.0))
        # logger.info(f"Camera target zoom set to: {self._target_zoom:.2f}x")

    def get_zoom(self) -> float:
        return self._zoom_level

    def get_fps(self) -> float:
        return self._current_fps
