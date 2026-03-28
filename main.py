import cv2
import time
import pyttsx3
import threading
import queue
from flask import Flask, render_template, Response, jsonify
from modules.hand_engine import HandEngine
from modules.ocr_engine import OCREngine

app = Flask(__name__)

# Global instances and states
cap = None
hand_engine = None
ocr_engine = None

voice_queue = queue.Queue()

def voice_worker():
    engine = pyttsx3.init()
    engine.setProperty('rate', 180)
    while True:
        text = voice_queue.get()
        if text is None: break
        try:
            engine.say(text)
            engine.runAndWait()
        except:
            pass
        voice_queue.task_done()

threading.Thread(target=voice_worker, daemon=True).start()

def speak_async(text):
    voice_queue.put(text)

finger_words = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}
last_spoken_fingers = -1
last_detected_fingers = -1
finger_stable_start = time.time()

ocr_results = []
latest_frame = None
scan_lock = threading.Lock()
ocr_error = None
global_finger_pos = None

def init_system():
    global cap, hand_engine, ocr_engine
    if cap is None:
        # 1 for Iriun, 0 for local webcam
        cap = cv2.VideoCapture(1)
        if not cap.isOpened(): 
            cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        hand_engine = HandEngine()
        ocr_engine = OCREngine()
        
        def scan_worker():
            global ocr_results, ocr_error, latest_frame
            while True:
                frame_to_scan = None
                with scan_lock:
                    if latest_frame is not None:
                        frame_to_scan = latest_frame.copy()
                
                if frame_to_scan is not None:
                    try:
                        res = ocr_engine.get_text(frame_to_scan)
                        with scan_lock:
                            ocr_results = res
                    except Exception as e:
                        ocr_error = str(e)[:40]
                time.sleep(0.5)
                
        threading.Thread(target=scan_worker, daemon=True).start()
        print("\n--- KIOSK VISION FLASK SERVER STARTED ---")
        print("Point your browser to: http://127.0.0.1:5000")

# --- FLASK ROUTES ---

@app.route('/')
def index():
    # This now correctly looks for templates/index.html
    return render_template('index.html')

@app.route('/video')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
def capture_text():
    with scan_lock:
        current_results_copy = ocr_results.copy()
    
    if current_results_copy:
        detected_strings = [res[1] for res in current_results_copy if res[2] > 0.4]
        full_text = " ".join(detected_strings)
        print(f"📸 Captured On-Screen Text: \n{full_text}")
        speak_async("Captured screen text.")
        return jsonify({"status": "success", "text": full_text})
    else:
        print("📸 No text found on screen right now.")
        return jsonify({"status": "no_text", "text": ""})

@app.route('/data', methods=['GET'])
def get_data():
    with scan_lock:
        current_results_copy = ocr_results.copy()
    texts = [res[1] for res in current_results_copy if res[2] > 0.4]
    finger_data = list(global_finger_pos) if global_finger_pos else None
    return jsonify({
        "finger": finger_data,
        "text": texts
    })

def generate_frames():
    global latest_frame, last_spoken_fingers, last_detected_fingers, finger_stable_start, global_finger_pos
    
    while True:
        if cap is None:
            time.sleep(0.1)
            continue
            
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue
            
        with scan_lock:
            latest_frame = frame.copy()

        hand_data = hand_engine.process_hand(frame)
        finger_pos = hand_data["finger_pos"]
        global_finger_pos = finger_pos

        if hand_data["landmarks"]:
            hand_engine.mp_draw.draw_landmarks(
                frame, hand_data["landmarks"], hand_engine.mp_hands.HAND_CONNECTIONS
            )

        fingers_up = hand_data.get("fingers_up", 0)
        word = finger_words.get(fingers_up, str(fingers_up))
        cv2.putText(frame, f"Fingers: {fingers_up} ({word})", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)
        
        if fingers_up != last_detected_fingers:
            last_detected_fingers = fingers_up
            finger_stable_start = time.time()
        else:
            if time.time() - finger_stable_start > 0.3:
                if fingers_up != last_spoken_fingers:
                    if fingers_up > 0:
                        speak_async(word)
                    last_spoken_fingers = fingers_up

        with scan_lock:
            current_results_copy = ocr_results.copy()
            
        for result in current_results_copy:
            bbox, text, prob = result
            if prob > 0.4:
                pts = [tuple(map(int, pt)) for pt in bbox]
                tl, br = pts[0], pts[2]
                color = (255, 0, 0)
                if finger_pos:
                    if tl[0] < finger_pos[0] < br[0] and tl[1] < finger_pos[1] < br[1]:
                        color = (0, 255, 0)
                cv2.rectangle(frame, tl, br, color, 2)

        if ocr_error:
            cv2.putText(frame, f"ERROR: {ocr_error}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret: continue
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

if __name__ == '__main__':
    init_system()
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)