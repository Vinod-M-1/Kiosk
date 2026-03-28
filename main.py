import cv2
import time
import pyttsx3
import threading
import queue
from flask import Flask, render_template, Response, jsonify
from modules.hand_engine import HandEngine
from modules.ocr_engine import OCREngine
from modules.ai_engine import AIEngine
from modules.gesture_logic import GestureManager, KioskState
gesture_mgr = GestureManager()

app = Flask(__name__)

# Global instances
cap = None
hand_engine = None
ocr_engine = None
ai_engine = None 

voice_queue = queue.Queue()

def voice_worker():
    # We initialize inside the loop or keep it very simple to prevent hangs
    while True:
        text = voice_queue.get()
        if text is None: break
        try:
            # Re-initializing inside the worker is often safer for background threads
            engine = pyttsx3.init()
            engine.setProperty('rate', 180)
            engine.say(text)
            engine.runAndWait()
            # Explicitly stop the engine to release the audio driver
            engine.stop()
            del engine 
        except Exception as e:
            print(f"Voice Error: {e}")
        finally:
            voice_queue.task_done()

threading.Thread(target=voice_worker, daemon=True).start()

# State variables for the finger counting (Must be outside the function)
last_spoken_fingers = -1
finger_words = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}

def speak_async(text):
    voice_queue.put(text)

# State Management
ocr_results = []
latest_frame = None
scan_lock = threading.Lock()
global_finger_pos = None

def init_system():
    global cap, hand_engine, ocr_engine, ai_engine
    if cap is None:
        # 1 for Iriun (USB/WiFi), 0 for default webcam
        cap = cv2.VideoCapture(1) 
        if not cap.isOpened(): cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        hand_engine = HandEngine()
        ocr_engine = OCREngine()
        ai_engine = AIEngine() # Automatically loads from .env
        
        def scan_worker():
            global ocr_results, latest_frame
            while True:
                frame_to_scan = None
                with scan_lock:
                    if latest_frame is not None:
                        frame_to_scan = latest_frame.copy()
                if frame_to_scan is not None:
                    try:
                        res = ocr_engine.get_text(frame_to_scan)
                        with scan_lock: ocr_results = res
                    except: pass
                time.sleep(0.5)
        
        threading.Thread(target=scan_worker, daemon=True).start()
        print("\n--- KIOSK VISION FLASK SERVER STARTED ---")
        print("Point your browser to: http://127.0.0.1:5000")

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
def capture_text():
    with scan_lock:
        current_results = ocr_results.copy()
    if current_results:
        text = " ".join([res[1] for res in current_results if res[2] > 0.4])
        return jsonify({"status": "success", "text": text})
    return jsonify({"status": "error", "text": "No text detected"})

@app.route('/describe', methods=['POST'])
def describe_scene():
    global ocr_results, latest_frame
    if not ocr_results or latest_frame is None:
        return jsonify({"summary": "I can't see enough detail to describe the scene yet."})
    
    h, w, _ = latest_frame.shape
    summary = ai_engine.analyze_layout(ocr_results, w, h)
    
    # Speak the summary out loud
    speak_async(summary)
    
    return jsonify({"summary": summary})

def generate_frames():
    global latest_frame, global_finger_pos, last_spoken_fingers
    
    # Track when we last spoke a word to prevent overlapping audio
    last_word_spoken = ""
    word_lock_time = 0 

    while True:
        if cap is None:
            time.sleep(0.1)
            continue
            
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue
            
        # Update the latest frame for the OCR background worker
        with scan_lock:
            latest_frame = frame.copy()

        # 1. Process Hand Tracking
        hand_data = hand_engine.process_hand(frame)
        global_finger_pos = hand_data["finger_pos"]
        fingers_up = hand_data.get("fingers_up", 0)

        # 2. State Machine: Update the Gesture Manager
        # We only trigger the "Targeting Mode Active" voice once per activation
        gesture_msg = gesture_mgr.update_state(fingers_up)
        if gesture_msg:
            speak_async(gesture_msg)

        # Draw the hand skeleton if detected
        if hand_data["landmarks"]:
            hand_engine.mp_draw.draw_landmarks(
                frame, hand_data["landmarks"], hand_engine.mp_hands.HAND_CONNECTIONS
            )

        # 3. Handle OCR Results & Visual Feedback
        with scan_lock:
            current_ocr = ocr_results.copy()
        
        current_time = time.time()

        for res in current_ocr:
            bbox, text, prob = res
            if prob > 0.4:
                # Convert bbox coordinates to integers
                pts = [tuple(map(int, p)) for p in bbox]
                tl, br = pts[0], pts[2]
                
                # Calculate Circle center and radius
                center = ((tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2)
                radius = (br[0] - tl[0]) // 2 + 15
                
                # Default appearance (Thin blue box when in Active mode)
                color = (255, 0, 0)
                thickness = 1

                # CHECK COLLISION: Is the index finger pointing at this text?
                is_pointing = False
                if global_finger_pos:
                    if tl[0] < global_finger_pos[0] < br[0] and tl[1] < global_finger_pos[1] < br[1]:
                        is_pointing = True

                # LOGIC GATE: Only target if Mode is ACTIVE/TARGETING and pointing
                if gesture_mgr.state != KioskState.IDLE:
                    if is_pointing and fingers_up == 1:
                        # VISUAL FEEDBACK: Draw a thick Green Circle
                        cv2.circle(frame, center, radius, (0, 255, 0), 3)
                        
                        # VOICE FEEDBACK: Only speak if not locked (4-second cooldown)
                        if not gesture_mgr.is_locked() or text != last_word_spoken:
                            speak_async(text)
                            last_word_spoken = text
                            gesture_mgr.lock_time = current_time # Reset the 4s timer
                    else:
                        # Just show thin boxes to indicate the system is "listening"
                        cv2.rectangle(frame, tl, br, color, thickness)

        # UI Overlay for the User
        state_color = (0, 255, 0) if gesture_mgr.state != KioskState.IDLE else (0, 0, 255)
        cv2.putText(frame, f"MODE: {gesture_mgr.state}", (10, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, state_color, 2)

        # Final MJPEG Encoding
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
            
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

if __name__ == '__main__':
    init_system()
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)