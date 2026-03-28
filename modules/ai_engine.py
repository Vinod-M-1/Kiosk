import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load .env variables from the root folder
load_dotenv()

class AIEngine:
    def __init__(self, api_key=None):
        # Read from .env if not passed manually
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            print("⚠️ WARNING: GEMINI_API_KEY not found in .env file!")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def analyze_layout(self, ocr_data, screen_width, screen_height):
        if not ocr_data:
            return "The screen appears to be empty or the text is too blurry to read."

        text_map = []
        for bbox, text, prob in ocr_data:
            # Calculate center points of the text box
            center_x = (bbox[0][0] + bbox[2][0]) / 2
            center_y = (bbox[0][1] + bbox[2][1]) / 2
            
            # Normalize coordinates (0.0 to 1.0)
            rel_x = center_x / screen_width
            rel_y = center_y / screen_height
            text_map.append(f"'{text}' at x={rel_x:.2f}, y={rel_y:.2f}")

        prompt = f"""
        You are an accessibility assistant for the blind. 
        Based on this OCR data from a kiosk screen:
        {", ".join(text_map)}
        
        Task: Provide a 2-sentence summary of what is on the screen and WHERE it is located.
        Use general areas (Top, Left, Center, etc.). Keep it helpful and concise.
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI Error: {str(e)[:50]}"