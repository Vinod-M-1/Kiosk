import cv2
import time
import pyttsx3
import threading
from modules.hand_engine import HandEngine
from modules.ocr_engine import OCREngine

def main():
    cap = cv2.VideoCapture(1) 
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)

    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    hand_engine = HandEngine()
    ocr_engine = OCREngine()
    
    engine = pyttsx3.init()
    engine.setProperty('rate', 200)

    ocr_results = []
    spoken_texts = set()
    speak_thread = None

    def speak_async(text):
        nonlocal speak_thread
        if speak_thread and speak_thread.is_alive():
            return
        def _speak():
            engine.say(text)
            engine.runAndWait()
        speak_thread = threading.Thread(target=_speak)
        speak_thread.daemon = True
        speak_thread.start()

    print("\n🚀 KIOSK VISION READY")
    print("Point camera at a menu. Press 's' to scan OCR. Press 'q' to quit.")

    cv2.namedWindow("Kiosk Vision", cv2.WINDOW_AUTOSIZE)

    try:
        while True:
            try:
                ret, frame = cap.read()
                if not ret:
                    print("⚠ Camera disconnected. Reconnecting...")
                    cap.release()
                    time.sleep(1)
                    cap = cv2.VideoCapture(1)
                    if not cap.isOpened():
                        cap = cv2.VideoCapture(0)
                    cap.set(cv2.CAP_PROP_FPS, 30)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    continue
            except Exception as e:
                print(f"⚠ Frame capture error: {e}")
                continue

            hand_data = hand_engine.process_hand(frame)
            finger_pos = hand_data["finger_pos"]

            if hand_data["landmarks"]:
                hand_engine.mp_draw.draw_landmarks(
                    frame, 
                    hand_data["landmarks"], 
                    hand_engine.mp_hands.HAND_CONNECTIONS
                )

            for (bbox, text, prob) in ocr_results:
                if prob > 0.4:
                    tl = (int(bbox[0][0]), int(bbox[0][1]))
                    br = (int(bbox[2][0]), int(bbox[2][1]))
                    
                    color = (255, 0, 0)
                    if finger_pos:
                        if tl[0] < finger_pos[0] < br[0] and tl[1] < finger_pos[1] < br[1]:
                            color = (0, 255, 0)
                            if text not in spoken_texts:
                                speak_async(text)
                                spoken_texts.add(text)

                    cv2.rectangle(frame, tl, br, color, 2)

            cv2.imshow("Kiosk Vision", frame)
            
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q') or key == 27:
                print("✓ Quitting...")
                break
            elif key == ord('s'):
                print("🔍 Scanning...")
                ocr_results = ocr_engine.get_text(frame)
                spoken_texts.clear()
                print("\n📝 OCR RESULTS:")
                for (bbox, text, prob) in ocr_results:
                    if prob > 0.4:
                        print(f"  [{prob:.0%}] {text}")
    
    except KeyboardInterrupt:
        print("\n✓ Shutting down...")
    finally:
        cv2.destroyAllWindows()
        cap.release()

if __name__ == "__main__":
    main()