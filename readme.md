# 👁️ Kiosk Vision

**Kiosk Vision** is a Full-Stack AI Accessibility Kiosk designed to help visually impaired individuals interact with physical screens and environments. By combining real-time hand-tracking, Optical Character Recognition (OCR), and Spatial Reasoning using Google's Gemini Vision-Language Model, this application doesn't just read text—it tells the user exactly *where* the text is in relation to their physical hand.

---

## 🌟 Features
- **Real-Time Hand Tracking:** Uses MediaPipe to track the user's hand skeleton and index finger coordinates.
- **Physical Finger Counting:** Automatically counts how many fingers are held up and announces the number aloud without lagging the video feed.
- **Continuous Background OCR:** Continuously scans the environment for raw text using EasyOCR and draws bounding boxes around detected words.
- **Voice Feedback Integration:** Built-in `pyttsx3` text-to-speech engine speaks out the pointed text and AI descriptions asynchronously.
- **Gemini Spatial Reasoning:** Sends the layout coordinates to **Gemini 2.5 Flash** to provide a concise, spatial summary of the kiosk or screen (e.g., "The Cancel button is at the bottom right").
- **Web-Based Dashboard:** Encoded MJPEG video streams to a Flask backend, allowing the kiosk to be monitored or used via any web browser on the network.

---

## 🏗️ Architecture & Folder Structure

The project follows a clean **Flask MVC (Model-View-Controller)** style architecture.

```text
KioskVision/
├── .env                 # Secret Vault: Stores your GEMINI_API_KEY securely.
├── main.py              # The Core Server: Runs Flask, manages API routes, and bridges everything.
├── req.txt              # Dependencies list (OpenCV, Flask, MediaPipe, EasyOCR, etc.)
│
├── modules/             # The "Brains" of the Kiosk
│   ├── hand_engine.py   # Uses MediaPipe to track hand skeletons & generate finger coordinates.
│   ├── ocr_engine.py    # Uses EasyOCR to scan the camera frame for raw readable text.
│   └── ai_engine.py     # Connects to Gemini 2.5 Flash via API for advanced Spatial Reasoning.
│
├── templates/           # The Frontend HTML Layouts
│   └── index.html       # The main webpage that users see when connecting to the Kiosk.
│
└── static/              # The Frontend Assets (Sent to the browser)
    ├── css/
    │   └── style.css    # Controls the dark theme, styling, and animations of the dashboard.
    └── js/
        └── script.js    # Listens to hardware (button presses) and triggers the Flask endpoints.
```

### 🔄 The System Flow
The application operates in two parallel worlds:
1. **The Real-Time Video Stream (Continuous Loop):** `main.py` grabs the high-speed video feed from your camera. Every frame is processed by `hand_engine.py`. Simultaneously, `ocr_engine.py` runs in a background thread to find text bounding boxes. The finished, overlaid frame is streamed via Flask to the browser.
2. **The AI Translation Request (Event-Triggered):** When a user triggers an action from the web frontend (like "Describe Layout"), `script.js` sends a request to the backend. The backend grabs the latest frozen OCR layout constraints and forwards them to `ai_engine.py`. Gemini 2.5 Flash calculates the spatial relationships and sends the result back to be spoken out loud by the system.

---

## 🛠️ Prerequisites & Requirements

Before running the application, make sure you have the following installed and set up:

1. **Python 3.8+** installed on your machine.
2. **Iriun Webcam (Required for Mobile Camera Streaming)**
   - Download the Iriun Client for your PC/Mac from [iriun.com](https://iriun.com/).
   - Download the Iriun app on your Android/iOS smartphone.
   - *For best performance (zero lag):* Enable **Developer Options** and **USB Debugging** on your phone, then connect it via a USB cable. Iriun will prioritize the high-speed USB tether over Wi-Fi.
3. **Google Gemini API Key**
   - You need an API key from [Google AI Studio](https://aistudio.google.com/).

---

## 🚀 Installation & Setup

1. **Clone or Download** this repository to your local machine:
   ```bash
   cd KioskVision
   ```

2. **Set up a Virtual Environment (Recommended):**
   ```bash
   python -m venv venv
   # Make sure to activate it!
   # Windows:
   venv\Scripts\activate
   # Mac/Linux:
   # source venv/bin/activate
   ```

3. **Install Dependencies:**
   Install all the required Python libraries using pip:
   ```bash
   pip install -r req.txt
   ```
   *(Ensure you have `flask`, `opencv-python`, `mediapipe`, `easyocr`, `pyttsx3`, `python-dotenv`, and `google-generativeai` installed.)*

4. **Configure your API Key:**
   Create a file named `.env` in the root folder of the project.
   Add your Gemini API key inside it like this:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

---

## 🎮 Running the Application

1. **Start Iriun Webcam:** Open the Iriun app on your phone and the Iriun client on your computer. Wait until it shows "Connected" (preferably via USB).
2. **Launch the Server:** In your activated terminal, run the main Flask application:
   ```bash
   python main.py
   ```
3. **Open the Dashboard:** Once the server says `--- KIOSK VISION FLASK SERVER STARTED ---`, open your web browser and navigate to:
   ```text
   http://127.0.0.1:5000
   ```
4. **Interact:** 
   - Point your phone camera at a screen or printed text.
   - Hold your hand in front of the camera to see the skeleton tracking and finger counting.
   - Use the buttons on the web interface to trigger Gemini layout descriptions and text captures!

Enjoy turning any flat physical screen into an intelligent, spatially-aware physical space!
