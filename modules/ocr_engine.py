import easyocr

class OCREngine:
    def __init__(self):
        self.reader = easyocr.Reader(['en'], gpu=False)

    def get_text(self, frame):
        import cv2
        # Optimization: Downscale the frame relative to a maximum width of 640px
        # This dramatically cuts down CPU latency to <1 sec instead of 10-20 sec.
        height, width = frame.shape[:2]
        
        # Determine scaling factor
        max_width = 640
        if width > max_width:
            scale = max_width / width
        else:
            scale = 1.0
            
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        resized_frame = cv2.resize(frame, (new_width, new_height))
        
        # Read text on the smaller frame
        raw_results = self.reader.readtext(resized_frame)
        
        # Scale bounding boxes back up to match original screen coordinates
        restored_results = []
        for bbox, text, prob in raw_results:
            # bbox is a list of 4 points: [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
            restored_bbox = [[int(pt[0] / scale), int(pt[1] / scale)] for pt in bbox]
            
            # Optionally "round off" or clean the text of special characters here if needed
            cleaned_text = text.strip()
            restored_results.append((restored_bbox, cleaned_text, prob))
            
        return restored_results