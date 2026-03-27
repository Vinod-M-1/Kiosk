import easyocr

class OCREngine:
    def __init__(self):
        self.reader = easyocr.Reader(['en'], gpu=False)

    def get_text(self, frame):
        return self.reader.readtext(frame)