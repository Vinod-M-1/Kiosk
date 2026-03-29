import cv2
import os
for i in range(5):
    try:
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"Index {i} works, shape {frame.shape}")
                cv2.imwrite(f"cam_{i}.jpg", frame)
            else:
                print(f"Index {i} read return False")
        else:
            print(f"Index {i} open failed")
        cap.release()
    except Exception as e:
        print(f"Index {i} exception: {e}")
