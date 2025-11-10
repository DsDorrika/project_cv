import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import time
import config
import logging

logger = logging.getLogger(__name__)

class ObjectDetector:
    def __init__(self, confidence_threshold: Optional[float] = None, 
                 target_class_id: Optional[int] = None):

        self.confidence_threshold = confidence_threshold or config.DETECTOR_CONFIDENCE_THRESHOLD
        self.target_class_id = target_class_id or config.TARGET_CLASS_ID
        
        # Статистика
        self.processing_times = []
        self.detection_count = 0
        
        # COCO names для отладки
        self.class_names = [
        'background',
        'aeroplane', 'bicycle', 'bird', 'boat',
        'bottle', 'bus', 'car', 'cat', 'chair',
        'cow', 'diningtable', 'dog', 'horse', 'motorbike',
        'person', 'pottedplant', 'sheep', 'sofa', 'train',
        'tvmonitor'
        ]

        
        self.net = self._initialize_network()

    def _initialize_network(self) -> Optional[cv2.dnn_Net]:
        """Инициализация нейронной сети с обработкой ошибок"""
        try:
            net = cv2.dnn.readNetFromCaffe(config.DETECTOR_CONFIG_PATH, config.DETECTOR_MODEL_PATH)
            
            # Настройка для оптимальной производительности
            net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            
            logger.info(f"Модель загружена: {config.DETECTOR_MODEL_PATH}")
            logger.info(f"Конфигурация: {config.DETECTOR_CONFIG_PATH}")
            logger.info(f"Целевой класс: {self.target_class_id} ({self.class_names[self.target_class_id]})")
            
            return net
            
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            logger.error("Убедитесь, что файлы модели находятся в папке models/")
            return None

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        if self.net is None:
            return []

        start_time = time.time()
        (H, W) = frame.shape[:2]
        results = []

        try:
            # Подготовка входного изображения
            blob = cv2.dnn.blobFromImage(
                frame, 0.007843, (300, 300), 127.5, 
                swapRB=True, crop=False
            )
            
            self.net.setInput(blob)
            detections = self.net.forward()

            # Обработка результатов
            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                
                if confidence > self.confidence_threshold:
                    class_id = int(detections[0, 0, i, 1])
                    
                    # Фильтрация по целевому классу
                    if class_id == self.target_class_id:
                        box = detections[0, 0, i, 3:7] * np.array([W, H, W, H])
                        (startX, startY, endX, endY) = box.astype("int")
                        
                        # Корректировка координат
                        startX = max(0, startX)
                        startY = max(0, startY)
                        endX = min(W, endX)
                        endY = min(H, endY)
                        
                        # Проверка валидности bounding box
                        if endX > startX and endY > startY:
                            results.append({
                                'box': [startX, startY, endX, endY],
                                'confidence': float(confidence),
                                'class_id': class_id,
                                'class_name': self.class_names[class_id],
                                'bottom_center': (int((startX + endX) / 2), endY),
                                'area': (endX - startX) * (endY - startY),
                                'timestamp': time.time()
                            })
            
            # Обновление статистики
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            self.detection_count += len(results)
            
            # Сохранение только последних 100 измерений
            if len(self.processing_times) > 100:
                self.processing_times.pop(0)
                
        except Exception as e:
            logger.error(f"Ошибка при детекции объектов: {e}")
            
        return results

    def get_average_processing_time(self) -> float:
        """Получение среднего времени обработки"""
        if not self.processing_times:
            return 0
        return sum(self.processing_times) / len(self.processing_times)

    def get_detection_stats(self) -> Dict[str, Any]:
        """Получение статистики детекции"""
        return {
            'total_detections': self.detection_count,
            'avg_processing_time': self.get_average_processing_time(),
            'last_batch_size': len(self.processing_times),
            'confidence_threshold': self.confidence_threshold
        }

    def set_confidence_threshold(self, threshold: float):
        """Установка порога уверенности"""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"Порог уверенности установлен: {self.confidence_threshold}")

    def draw_detections(self, frame: np.ndarray, detections: List[Dict[str, Any]]):
        """Отрисовка обнаружений на кадре"""
        for detection in detections:
            startX, startY, endX, endY = detection['box']
            confidence = detection['confidence']
            class_name = detection['class_name']
            
            # Рисование bounding box
            cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
            
            # Подпись с классом и уверенностью
            label = f"{class_name}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            
            # Фон для текста
            cv2.rectangle(frame, (startX, startY - label_size[1] - 10),
                         (startX + label_size[0], startY), (0, 255, 0), -1)
            
            # Текст
            cv2.putText(frame, label, (startX, startY - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            
            # Точка для отслеживания пересечения
            center_x, center_y = detection['bottom_center']
            cv2.circle(frame, (center_x, center_y), 4, (255, 0, 0), -1)


# Тестирование
if __name__ == "__main__":
    detector = ObjectDetector()
    print(f"Детектор инициализирован: {detector.net is not None}")