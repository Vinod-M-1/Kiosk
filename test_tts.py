import pyttsx3
import threading
import queue
import time
from transformers import pipeline

vq = queue.Queue()
def vw():
    print("Initializing pyttsx3")
    engine = pyttsx3.init()
    print("pyttsx3 initialized")
    while True:
        txt = vq.get()
        if not txt: break
        print('Speaking:', txt)
        engine.say(txt)
        engine.runAndWait()
        print('Finished:', txt)
        vq.task_done()

threading.Thread(target=vw, daemon=True).start()

print('Loading pipeline...')
pipe = pipeline('zero-shot-classification', model='typeform/distilbert-base-uncased-mnli')
print('Pipeline loaded!')

vq.put('Hello world')
time.sleep(5)
print('Done test.')
