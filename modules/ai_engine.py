import os
import time
from dotenv import load_dotenv
import google.generativeai as genai
from modules.spatial_mapper import map_ocr_regions

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
        self.last_call = 0
        self.last_response = "AI is still analyzing. Please wait a moment."

    def analyze_layout(self, ocr_data, screen_width, screen_height, current_goal=None, finger_pos=None):
        # Cleanly offload mapping arithmetic to spatial_mapper
        mapped_layout = map_ocr_regions(ocr_data, screen_width, screen_height)
        
        if mapped_layout == "The screen appears to be empty.":
            return mapped_layout

        current_time = time.time()
        if current_time - self.last_call <= 3:
            return self.last_response
            
        self.last_call = current_time

        if current_goal:
            prompt = f"""
            You are an accessibility assistant for the blind. 
            The user's goal is: "{current_goal}".
            The user's index finger is currently at position {finger_pos} on a {screen_width}x{screen_height} screen.
            
            Based on this OCR data from a kiosk screen, categorized by spatial regions:
            
            {mapped_layout}
            
            Task:
            1. Identify the specific button or text field that helps accomplish the goal.
            2. Give a short, directional instruction mapping the finger position to the button (e.g., "Move your hand up and to the right for the Search bar").
            
            Format your response strictly as:
            TARGET: <exact text from OCR>
            INSTRUCTION: <your directional instruction>
            """
        else:
            prompt = f"""
            You are an accessibility assistant for the blind. 
            Based on this OCR data from a kiosk screen, categorized by spatial regions:
            
            {mapped_layout}
            
            Task: Provide a 2-sentence summary of what is on the screen and WHERE the main elements are located.
            Use general terms. Keep it highly helpful and concise.
            """

        try:
            response = self.model.generate_content(prompt)
            self.last_response = response.text
            return response.text
        except Exception as e:
            error_str = f"AI Error: {str(e)[:50]}"
            self.last_response = error_str
            return error_str