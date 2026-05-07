import cv2
import mediapipe as mp
import numpy as np

class HandTracker:
    """
    Wrapper around MediaPipe Hands for extracting landmarks.
    """
    def __init__(self, max_hands=1, detection_con=0.7, tracking_con=0.5):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=detection_con,
            min_tracking_confidence=tracking_con
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

    def process_frame(self, frame: np.ndarray):
        """
        Process the BGR frame and return (RGB_annotated_frame, landmarks_list)
        """
        # Convert the BGR image to RGB before processing.
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # To improve performance, optionally mark the image as not writeable to pass by reference.
        rgb_frame.flags.writeable = False
        results = self.hands.process(rgb_frame)
        rgb_frame.flags.writeable = True

        landmarks_list = []

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw landmarks on the RGB frame directly
                self.mp_draw.draw_landmarks(
                    rgb_frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style()
                )
                
                # Extract normalized coordinates
                lms = []
                for lm in hand_landmarks.landmark:
                    lms.append({
                        "x": lm.x,
                        "y": lm.y,
                        "z": lm.z,
                        "visibility": lm.visibility
                    })
                landmarks_list.append(lms)

        return rgb_frame, landmarks_list
