import cv2
import numpy as np
from typing import List, Dict, Any, Optional
import time
import logging
import config

logger = logging.getLogger(__name__)

# COCO class names (80 classes)
COCO_NAMES = [
    'person','bicycle','car','motorcycle','airplane','bus','train','truck','boat','traffic light',
    'fire hydrant','stop sign','parking meter','bench','bird','cat','dog','horse','sheep','cow',
    'elephant','bear','zebra','giraffe','backpack','umbrella','handbag','tie','suitcase','frisbee',
    'skis','snowboard','sports ball','kite','baseball bat','baseball glove','skateboard','surfboard','tennis racket','bottle',
    'wine glass','cup','fork','knife','spoon','bowl','banana','apple','sandwich','orange',
    'broccoli','carrot','hot dog','pizza','donut','cake','chair','couch','potted plant','bed',
    'dining table','toilet','tv','laptop','mouse','remote','keyboard','cell phone','microwave','oven',
    'toaster','sink','refrigerator','book','clock','vase','scissors','teddy bear','hair drier','toothbrush'
]

# Небольшой интеграционный слой для YOLOv8 (ultralytics) — опционально
# Требует пакет ultralytics (pip install ultralytics) и модели .pt

try:
    from ultralytics import YOLO
    _HAS_YOLO = True
except Exception:
    _HAS_YOLO = False

class YOLODetector:
    def __init__(self, model_path: Optional[str] = None, conf_threshold: Optional[float] = None):
        if not _HAS_YOLO:
            raise RuntimeError('ultralytics.YOLO не найден. Установите пакет ultralytics: pip install ultralytics')

        # Если в конфиге указан локальный путь и файл существует, используем его,
        # иначе передадим короткое имя 'yolov8n.pt' и ultralytics сам скачает модель в кеш.
        if model_path and isinstance(model_path, str) and model_path.strip():
            if model_path.startswith('yolov8') or model_path == 'yolov8n.pt' or not model_path.endswith('.pt'):
                self.model_path = model_path
            else:
                # если указанный путь существует - используем, иначе будем передавать короткое имя
                import os
                if os.path.exists(model_path):
                    self.model_path = model_path
                else:
                    self.model_path = 'yolov8n.pt'
        else:
            self.model_path = 'yolov8n.pt'

        self.conf_threshold = conf_threshold or config.DETECTOR_CONFIDENCE_THRESHOLD

        try:
            self.model = YOLO(self.model_path)
            logger.info(f'YOLO модель загружена: {self.model_path}')
        except Exception as e:
            logger.error(f'Ошибка загрузки YOLO модели: {e}')
            raise

        # Статистика
        self.processing_times = []
        self.detection_count = 0

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        start = time.time()
        results_list = []

        try:
            res = self.model(frame)
            if not res:
                return []
            r = res[0]
            boxes = getattr(r, 'boxes', None)

            if boxes is None:
                return []

            for box in boxes:
                conf = float(box.conf[0]) if box.conf is not None else 0.0
                if conf < self.conf_threshold:
                    continue
                cls = int(box.cls[0]) if box.cls is not None else -1
                xyxy = box.xyxy[0].tolist() if box.xyxy is not None else []
                if not xyxy:
                    continue
                x1, y1, x2, y2 = map(int, xyxy[:4])
                bottom_center = (int((x1 + x2) / 2), min(y2, frame.shape[0] - 1))

                class_name = COCO_NAMES[cls] if 0 <= cls < len(COCO_NAMES) else str(cls)

                results_list.append({
                    'box': [x1, y1, x2, y2],
                    'confidence': conf,
                    'class_id': cls,
                    'class_name': class_name,
                    'bottom_center': bottom_center,
                    'area': float((x2 - x1) * (y2 - y1)),
                    'timestamp': time.time()
                })

            proc = time.time() - start
            self.processing_times.append(proc)
            self.detection_count += len(results_list)
            if len(self.processing_times) > 100:
                self.processing_times.pop(0)

        except Exception as e:
            logger.error(f'Ошибка в YOLO детекторе: {e}')

        return results_list

    def get_average_processing_time(self):
        if not self.processing_times:
            return 0
        return sum(self.processing_times) / len(self.processing_times)

    def draw_detections(self, frame, detections: List[Dict[str, Any]]):
        for d in detections:
            x1, y1, x2, y2 = d['box']
            label = f"{d.get('class_name', d.get('class_id'))}: {d.get('confidence', 0):.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 2)
