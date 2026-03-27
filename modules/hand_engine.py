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
        # We store these as class attributes so main.py can access them
        self.mp_hands = mp_hands 
        self.mp_draw = mp_drawing
        self.hands = self.mp_hands.Hands(
            static_image_mode=False, 
            max_num_hands=1, 
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.tip_ids = [4, 8, 12, 16, 20]

    def process_hand(self, frame):
        h, w, _ = frame.shape
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(frame_rgb)
        
        data = {"finger_pos": None, "gesture": "none", "landmarks": None}

        if results.multi_hand_landmarks:
            hand_lms = results.multi_hand_landmarks[0]
            data["landmarks"] = hand_lms
            
            lm_list = []
            for lm in hand_lms.landmark:
                lm_list.append((int(lm.x * w), int(lm.y * h)))

            # 1. Pointer Position
            data["finger_pos"] = lm_list[8]

            # 2. Gesture Logic
            dist = math.hypot(lm_list[8][0]-lm_list[4][0], lm_list[8][1]-lm_list[4][1])
            if dist < 45:
                data["gesture"] = "click"
            else:
                fingers = []
                # Thumb
                if lm_list[4][0] > lm_list[3][0]: fingers.append(1)
                else: fingers.append(0)
                # Others
                for i in range(1, 5):
                    if lm_list[self.tip_ids[i]][1] < lm_list[self.tip_ids[i]-2][1]: fingers.append(1)
                    else: fingers.append(0)
                
                total = sum(fingers)
                if total == 5: data["gesture"] = "stop"
                elif total == 2: data["gesture"] = "next"
                elif total == 1: data["gesture"] = "select"

        return data