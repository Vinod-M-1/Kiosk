import cv2
import time
import pyttsx3
import threading
import queue
import winsound
import math
from flask import Flask, render_template, Response, jsonify, request
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
    import pyttsx3
    import pythoncom
    
    # REQUIRED on Windows when running in a worker thread alongside HuggingFace/Torch 
    # to prevent the COM library from silently freezing the TTS audio stream.
    pythoncom.CoInitialize()
    
    try:
        # Initializing the TTS engine ONCE outside the loop cuts out the 500ms+ startup latency per-word!
        engine = pyttsx3.init()
        engine.setProperty('rate', 180)
    except Exception as e:
        print(f"Failed to initialize TTS: {e}")
        return

    while True:
        text = voice_queue.get()
        if text is None: break
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"Voice Error: {e}")
        finally:
            voice_queue.task_done()
    
    try:
        engine.stop()
    except:
        pass

threading.Thread(target=voice_worker, daemon=True).start()

# State variables for the finger counting (Must be outside the function)
last_spoken_fingers = -1
finger_words = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}

def speak_async(text):
    if text:
        # SAPI5 will silently crash if fed XML-breaking characters
        safe_text = text.replace('&', 'and').replace('@', 'at').replace('<', 'less than').replace('>', 'greater than')
        voice_queue.put(safe_text)

# State Management
ocr_results = []
latest_frame = None
scan_lock = threading.Lock()
global_finger_pos = None
current_goal = None
ai_target_text = None

def find_active_camera():
    import cv2
    import time
    import numpy as np
    import os
    from dotenv import load_dotenv

    load_dotenv()
    
    # 1. Manual Override from .env
    override_idx = os.getenv("CAMERA_INDEX")
    if override_idx is not None:
        try:
            cam_idx = int(override_idx)
            print(f"FORCING CAMERA INDEX: {cam_idx} (from .env)")
            # Try capturing with directshow
            cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
            if cap.isOpened():
                return cap
            # Fallback to default if DSHOW fails for this custom index
            cap = cv2.VideoCapture(cam_idx)
            if cap.isOpened():
                return cap
        except ValueError:
            pass

    print("Auto-detecting active camera...")
    best_cap = None
    max_diff = -1
    
    # Try all reasonable camera indices
    for idx in range(3):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            continue
            
        # Read a few frames to let the virtual camera warm up
        for _ in range(5):
            cap.read()
            
        ret1, f1 = cap.read()
        time.sleep(0.1)
        ret2, f2 = cap.read()
        
        if ret1 and ret2 and f1 is not None and f2 is not None:
            # A real camera will have sensor noise causing a larger diff
            # Static virtual camera placeholders have very little to no noise
            diff = np.sum(cv2.absdiff(f1, f2))
            
            if diff > max_diff:
                max_diff = diff
                if best_cap is not None:
                    best_cap.release()
                best_cap = cap
            else:
                cap.release()
        else:
            cap.release()
            
    if best_cap is not None and max_diff > 200000:
        return best_cap
        
    # Fallback to index 0 if none pass the check
    if best_cap:
        best_cap.release()
        
    return cv2.VideoCapture(0, cv2.CAP_DSHOW)

def init_system():
    global cap, hand_engine, ocr_engine, ai_engine
    if cap is None:
        cap = find_active_camera()
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
def landing():
    return render_template('landing.html')

@app.route('/dashboard')
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
    global ocr_results, latest_frame, current_goal, ai_target_text
    if not ocr_results or latest_frame is None:
        return jsonify({"summary": "I can't see enough detail to describe the scene yet."})
    
    h, w, _ = latest_frame.shape
    summary = ai_engine.analyze_layout(ocr_results, w, h, current_goal, global_finger_pos)
    
    instruction_to_speak = summary
    if "TARGET:" in summary and "INSTRUCTION:" in summary:
        lines = summary.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("TARGET:"):
                ai_target_text = line.replace("TARGET:", "").strip().lower()
            elif line.startswith("INSTRUCTION:"):
                instruction_to_speak = line.replace("INSTRUCTION:", "").strip()
        speak_async(instruction_to_speak)
        return jsonify({"summary": instruction_to_speak})

    # Speak the summary out loud
    speak_async(summary)
    
    return jsonify({"summary": summary})

@app.route('/set_goal', methods=['POST'])
def set_goal():
    global current_goal, ocr_results, latest_frame, ai_target_text, global_finger_pos
    data = request.get_json()
    if data and 'goal' in data:
        current_goal = data['goal']
        
        if ocr_results and latest_frame is not None:
            h, w, _ = latest_frame.shape
            summary = ai_engine.analyze_layout(ocr_results, w, h, current_goal, global_finger_pos)
            
            instruction_to_speak = summary
            if "TARGET:" in summary and "INSTRUCTION:" in summary:
                lines = summary.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith("TARGET:"):
                        ai_target_text = line.replace("TARGET:", "").strip().lower()
                    elif line.startswith("INSTRUCTION:"):
                        instruction_to_speak = line.replace("INSTRUCTION:", "").strip()
                speak_async(instruction_to_speak)
                return jsonify({"status": "success", "goal": current_goal, "summary": instruction_to_speak})
            
            speak_async(summary)
            return jsonify({"status": "success", "goal": current_goal, "summary": summary})
            
        return jsonify({"status": "success", "goal": current_goal})
    return jsonify({"status": "error"})

@app.route('/status', methods=['GET'])
def get_status():
    global current_goal, global_finger_pos, ai_target_text
    return jsonify({
        "current_goal": current_goal if current_goal else "No task assigned.",
        "target_button": ai_target_text.capitalize() if ai_target_text else "Awaiting AI...",
        "hand_detected": global_finger_pos is not None
    })

def generate_frames():
    global latest_frame, global_finger_pos, last_spoken_fingers
    
    # Track when we last spoke a word to prevent overlapping audio
    last_word_spoken = ""
    word_lock_time = 0 
    last_tick_time = 0 # Track last geiger ping


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

        # Pulse circle at finger pos
        if global_finger_pos:
            pulse_radius = 15 + int(5 * math.sin(time.time() * 10))
            cv2.circle(frame, global_finger_pos, pulse_radius, (0, 255, 0), 3)

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
                
                # Check if this box is the AI target
                is_ai_target = False
                if ai_target_text and ai_target_text in text.lower():
                    is_ai_target = True

                # Default appearance (Visible, bright blue box)
                color = (255, 200, 0) # Bright cyan-blue
                thickness = 2
                
                if is_ai_target:
                    color = (255, 0, 255) # Magenta for the target area
                    thickness = 4

                # CHECK COLLISION: Is the index finger pointing at this text?
                is_pointing = False
                if global_finger_pos:
                    if tl[0] < global_finger_pos[0] < br[0] and tl[1] < global_finger_pos[1] < br[1]:
                        is_pointing = True
                        if not is_ai_target:
                            color = (0, 200, 255) # Yellow/Orange highlight when pointing

                # ── GEIGER COUNTER (independent of verbal radar) ──────────
                if is_ai_target and global_finger_pos:
                    center = ((tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2)
                    dist = math.hypot(global_finger_pos[0] - center[0], global_finger_pos[1] - center[1])
                    interval = max(0.08, dist / 700.0)
                    if not (is_pointing and gesture_mgr.state != KioskState.IDLE):
                        if current_time - last_tick_time > interval:
                            winsound.PlaySound("static/assets/tick.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)
                            last_tick_time = current_time

                # ── VERBAL RADAR (completely independent — always fires) ───
                if is_ai_target:
                    last_guide = getattr(gesture_mgr, 'last_verbal_guide', 0)
                    no_hand = global_finger_pos is None
                    # Repeat location cue every 8s when hand not in frame; directional cue every 4s when hand visible
                    guide_interval = 8.0 if no_hand else 4.0

                    if current_time - last_guide > guide_interval:
                        direction = ai_engine._get_directional_instruction(
                            global_finger_pos, bbox, ai_target_text, frame.shape[1], frame.shape[0]
                        )
                        speak_async(direction)
                        gesture_mgr.last_verbal_guide = current_time

                # ALWAYS draw the text boxes so you can see what is recognized
                cv2.rectangle(frame, tl, br, color, thickness)


                # LOGIC GATE: Only target if Mode is ACTIVE/TARGETING and pointing
                if gesture_mgr.state != KioskState.IDLE:
                    if is_pointing and fingers_up == 1:
                        # VOICE FEEDBACK: Only speak if not locked (4-second cooldown)
                        if not gesture_mgr.is_locked() or text != last_word_spoken:
                            if is_ai_target:
                                winsound.PlaySound("static/assets/success.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)
                            else:
                                winsound.PlaySound("static/assets/beep.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)
                            speak_async(text)
                            last_word_spoken = text
                            gesture_mgr.lock_time = current_time # Reset the 4s timer

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