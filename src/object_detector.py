# ====================================================================
# src/object_detector.py
# ====================================================================

import cv2
import numpy as np
import config 

class ObjectDetector:
    def __init__(self):
        self.confidence_threshold = config.DETECTOR_CONFIDENCE_THRESHOLD
        self.target_class_id = config.TARGET_CLASS_ID 

        try:
            # Используем cv2.dnn для загрузки MobileNet-SSD (для скорости)
            self.net = cv2.dnn.readNetFromCaffe(config.DETECTOR_CONFIG_PATH, config.DETECTOR_MODEL_PATH)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU) # Приоритет CPU для слабых ноутбуков
            print("Детектор объектов успешно загружен.")
        except Exception as e:
            print(f"Ошибка загрузки модели DNN. Убедитесь, что файлы лежат в models/: {e}")
            self.net = None

    def detect(self, frame):
        if self.net is None:
            return []

        (H, W) = frame.shape[:2]
        
        # Предобработка: 300x300, как требует MobileNet-SSD
        blob = cv2.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)
        
        self.net.setInput(blob)
        detections = self.net.forward()

        results = []

        for i in np.arange(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            
            if confidence > self.confidence_threshold:
                
                class_id = int(detections[0, 0, i, 1])
                
                if class_id == self.target_class_id: # Проверяем, что это 'person'
                    
                    box = detections[0, 0, i, 3:7] * np.array([W, H, W, H])
                    (startX, startY, endX, endY) = box.astype("int")
                    
                    results.append({
                        'box': [startX, startY, endX, endY],
                        'confidence': confidence,
                        # Точка для проверки пересечения: центр нижней грани
                        'bottom_center': (int((startX + endX) / 2), endY) 
                    })

        return results
