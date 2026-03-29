import time
from transformers import pipeline

class AIEngine:
    def __init__(self, api_key=None):
        print("LOADING LOCAL NLP MODEL (NO LLM, NO API)...")
        # Loads a lightweight semantic model entirely locally. No internet needed after first boot.
        self.classifier = pipeline("zero-shot-classification", model="typeform/distilbert-base-uncased-mnli")
        self.last_call = 0
        self.last_response = "System initialized and running locally."
        print("LOCAL NLP READY.")

    def _get_directional_instruction(self, finger_pos, target_bbox, best_match_text, screen_width, screen_height, is_initial=False):
        """
        Pure math logic replacing LLM spatial reasoning!
        Calculates directions strictly based on the coordinates of the target box and the finger.
        """
        if not target_bbox:
            return "Target not found on screen."
            
        x_min = target_bbox[0][0]
        y_min = target_bbox[0][1]
        x_max = target_bbox[2][0]
        y_max = target_bbox[2][1]

        target_center_x = (x_min + x_max) / 2
        target_center_y = (y_min + y_max) / 2

        # 1. Determine absolute static position on screen
        vertical_pos = "center"
        if target_center_y < screen_height * 0.33:
            vertical_pos = "top"
        elif target_center_y > screen_height * 0.66:
            vertical_pos = "bottom"
            
        horizontal_pos = "center"
        if target_center_x < screen_width * 0.33:
            horizontal_pos = "left"
        elif target_center_x > screen_width * 0.66:
            horizontal_pos = "right"
            
        if vertical_pos == "center" and horizontal_pos == "center":
            screen_location = "in the center"
        elif vertical_pos == "center":
            screen_location = f"on the {horizontal_pos}"
        elif horizontal_pos == "center":
            screen_location = f"at the {vertical_pos}"
        else:
            screen_location = f"at the {vertical_pos} {horizontal_pos}"

        if not finger_pos:
            return f"Target {best_match_text} found {screen_location} of the screen! Bring your hand into the camera view to get directions."

        fx, fy = finger_pos
        
        vertical_move = None
        horizontal_move = None

        if fy > target_center_y + 40:
            vertical_move = "Move your hand up"
        elif fy < target_center_y - 40:
            vertical_move = "Move your hand down"
            
        if fx > target_center_x + 40:
            horizontal_move = "left"
        elif fx < target_center_x - 40:
            horizontal_move = "right"

        move_str = "You are hovering right over it! Push forward!"
        if vertical_move and horizontal_move:
            move_str = f"{vertical_move} and to the {horizontal_move}."
        elif vertical_move:
            move_str = f"{vertical_move}."
        elif horizontal_move:
            move_str = f"Move your hand to the {horizontal_move}."
            
        if is_initial:
            return f"Target {best_match_text} found {screen_location}. {move_str}"
        return move_str

    def analyze_layout(self, ocr_data, screen_width, screen_height, current_goal=None, finger_pos=None):
        if not ocr_data:
            return "The screen appears to be empty."

        current_time = time.time()
        # Prevent rapid-fire classification queueing
        if current_time - self.last_call <= 1:
            return self.last_response
            
        self.last_call = current_time

        # Extract plausible candidate buttons (high confidence strings)
        candidates = []
        for bbox, text, prob in ocr_data:
            text = text.strip()
            if prob > 0.4 and len(text) > 1:
                candidates.append((text, bbox))

        if not candidates:
            # No valid text discovered yet
            return self.last_response

        candidate_texts = [c[0] for c in candidates]

        if current_goal:
            # --- 1. DIRECT KEYWORD MATCHING (FAST & PERFECT ACCURACY) ---
            # If the user explicitly speaks a word that exactly matches text on screen, trust it!
            goal_lower = current_goal.lower()
            fillers = ["where", "is", "at", "the", "can", "you", "find", "looking", "for", "i", "want", "to", "click", "on"]
            clean_goal_words = [w for w in goal_lower.split() if w not in fillers]
            
            best_match_text = None
            confidence = 0
            
            # Search for the most critical nouns explicitly
            for word in clean_goal_words:
                if len(word) < 3: continue
                # Exact substring match
                for txt in candidate_texts:
                    if word in txt.lower():
                        best_match_text = txt
                        confidence = 1.0
                        break
                if best_match_text:
                    break
                    
            # --- 2. NLP RULE-BASED SEMANTIC MATCHING (FALLBACK) ---
            # If no exact text matches, use the neural model to guess their intent
            if not best_match_text:
                result = self.classifier(current_goal, candidate_labels=candidate_texts)
                best_match_text = result['labels'][0]
                confidence = result['scores'][0]
            
            # Find the original bounding box of this chosen target
            target_bbox = None
            for txt, bbox in candidates:
                if txt == best_match_text:
                    target_bbox = bbox
                    break
                    
            if confidence < 0.15: # Highly unmatched intents
                self.last_response = "I couldn't find a button that matches your goal."
                return self.last_response

            # Remove single quotes to prevent dictation crashes
            safe_match_text = best_match_text.replace("'", "").replace('"', "")
            
            # Generate the instruction mathematically
            instruction = self._get_directional_instruction(finger_pos, target_bbox, safe_match_text, screen_width, screen_height, is_initial=True)
            
            # Exactly the format expected by main.py parsing logic
            response = f"TARGET: {safe_match_text}\nINSTRUCTION: {instruction}"
            self.last_response = response
            return response
        else:
            # If no target goal is set, read the top items to the user
            top_buttons = [c.replace("'", "") for c in candidate_texts[:3]]
            btns = ", ".join(top_buttons)
            self.last_response = f"I see the following options: {btns}."
            return self.last_response