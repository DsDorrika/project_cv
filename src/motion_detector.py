# src/motion_detector.py
import cv2
import numpy as np
import logging
import config

class MotionDetector:
    def __init__(self):
        self.bg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=40, detectShadows=True)
        self.min_area = config.MOTION_MIN_AREA
        self.next_id = 0
        self.centroid_to_id = {}
        logging.info("Детектор движения запущен")

    def detect(self, frame):
        frame = cv2.convertScaleAbs(frame, alpha=1.2, beta=30)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        mask = self.bg.apply(gray)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15,15), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detections = []
        current_centroids = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_area:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            cx = x + w // 2
            cy = y + h

            # Присваиваем ID по близости центроида
            obj_id = None
            for old_cx, old_cy, old_id in self.centroid_to_id.keys():
                if abs(cx - old_cx) < 50 and abs(cy - old_cy) < 50:
                    obj_id = old_id
                    break

            if obj_id is None:
                obj_id = self.next_id
                self.next_id += 1

            self.centroid_to_id[(cx, cy, obj_id)] = None  # обновляем
            # Очищаем старые
            self.centroid_to_id = {k: v for k, v in self.centroid_to_id.items() if abs(cx - k[0]) < 100}

            detections.append({
                'id': obj_id,                     # ВОТ ЭТО КЛЮЧЕВОЕ!
                'class_id': 0,
                'confidence': 1.0,
                'box': [x, y, w, h],
                'centroid': (cx, cy)
            })

            # Зелёная рамка
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
            cv2.putText(frame, f"ID:{obj_id}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        return detections, frame