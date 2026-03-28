import cv2
import math
try:
    import mediapipe.python.solutions.hands as mp_hands
    import mediapipe.python.solutions.drawing_utils as mp_drawing
except:
    import mediapipe as mp
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

class HandEngine:
    def __init__(self):
        self.mp_hands = mp_hands
        self.mp_draw = mp_drawing
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )

    def process_hand(self, frame):
        h, w, _ = frame.shape
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(frame_rgb)
        data = {"finger_pos": None, "landmarks": None, "fingers_up": 0}

        if results.multi_hand_landmarks:
            hand_lms = results.multi_hand_landmarks[0]
            data["landmarks"] = hand_lms
            
            fingers = 0
            is_right = True
            if results.multi_handedness:
                is_right = results.multi_handedness[0].classification[0].label == "Right"
                
            # Thumb
            if is_right:
                if hand_lms.landmark[4].x < hand_lms.landmark[3].x:
                    fingers += 1
            else:
                if hand_lms.landmark[4].x > hand_lms.landmark[3].x:
                    fingers += 1
            
            # 4 Fingers
            tips = [8, 12, 16, 20]
            pips = [6, 10, 14, 18]
            for tip, pip in zip(tips, pips):
                if hand_lms.landmark[tip].y < hand_lms.landmark[pip].y:
                    fingers += 1
            
            data["fingers_up"] = fingers

            # Index finger tip is landmark 8
            fx = int(hand_lms.landmark[8].x * w)
            fy = int(hand_lms.landmark[8].y * h)
            data["finger_pos"] = (fx, fy)
        return data
