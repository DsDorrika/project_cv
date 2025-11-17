import numpy as np
from datetime import datetime
import time
import json
import cv2
from typing import Tuple, Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

def calculate_distance(pt1: Tuple[float, float], pt2: Tuple[float, float]) -> float:
    
    try:
        return np.sqrt((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)
    except (TypeError, IndexError) as e:
        logger.error(f"Ошибка расчета расстояния: {e}, pt1: {pt1}, pt2: {pt2}")
        return float('inf')

def get_timestamp_filename(prefix: str = "violation") -> str:
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Миллисекунды
    return f"{prefix}_{timestamp}"

def get_formatted_time() -> str:
    """Получение форматированного времени для логов"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def calculate_iou(box1: List[float], box2: List[float]) -> float:
    
    # Определение координат пересечения
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    # Площадь пересечения
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    
    # Площади каждого бокса
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    
    # IoU
    union = area1 + area2 - intersection
    return intersection / union if union > 0 else 0

def resize_frame(frame: np.ndarray, max_width: int = 800, max_height: int = 600) -> np.ndarray:
    
    if frame is None:
        return frame
        
    h, w = frame.shape[:2]
    
    # Если кадр уже меньше максимальных размеров
    if w <= max_width and h <= max_height:
        return frame
    
    # Расчет новых размеров с сохранением пропорций
    ratio = min(max_width / w, max_height / h)
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    
    return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

def draw_text_with_background(img: np.ndarray, text: str, position: Tuple[int, int], 
                             font_scale: float = 0.6, thickness: int = 2, 
                             text_color: Tuple[int, int, int] = (255, 255, 255),
                             bg_color: Tuple[int, int, int] = (0, 0, 0),
                             font: int = cv2.FONT_HERSHEY_SIMPLEX) -> None:
    
    x, y = position
    
    # Размер текста
    (text_width, text_height), baseline = cv2.getTextSize(
        text, font, font_scale, thickness
    )
    
    # Рисование фона
    cv2.rectangle(img, (x, y - text_height - baseline), 
                  (x + text_width, y + baseline), bg_color, -1)
    
    # Рисование текста
    cv2.putText(img, text, (x, y), font, font_scale, text_color, thickness)

def save_data_to_json(data: Dict[str, Any], filename: str) -> bool:
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Данные сохранены в {filename}")
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения данных в {filename}: {e}")
        return False

def load_data_from_json(filename: str) -> Optional[Dict[str, Any]]:
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки данных из {filename}: {e}")
        return None

class FPSCounter:
    """Счетчик FPS"""
    
    def __init__(self, buffer_size: int = 30):
        self.buffer_size = buffer_size
        self.times: List[float] = []
        self.frame_count = 0
        self.start_time = time.time()
    
    def update(self) -> float:
        """Обновление счетчика и получение текущего FPS"""
        current_time = time.time()
        self.times.append(current_time)
        self.frame_count += 1
        
        # Удаление старых значений
        while len(self.times) > self.buffer_size:
            self.times.pop(0)
        
        # Расчет FPS на основе скользящего окна
        fps = 0.0
        if len(self.times) > 1:
            elapsed = self.times[-1] - self.times[0]
            if elapsed > 0:
                fps = (len(self.times) - 1) / elapsed
        
        return fps
    
    def get_global_fps(self) -> float:
        """Получение текущего (скользящего) FPS на основе буфера.
        Метод ранее возвращал общий средний FPS с начала работы — это приводило к
        растущим значениям при долгой работе. Теперь этот метод возвращает
        скользящую оценку FPS (за последние buffer_size кадров).
        """
        if len(self.times) > 1:
            elapsed = self.times[-1] - self.times[0]
            if elapsed > 0:
                return (len(self.times) - 1) / elapsed
        # Фолбэк — использовать общую статистику
        elapsed_total = time.time() - self.start_time
        return self.frame_count / elapsed_total if elapsed_total > 0 else 0.0

# Тестирование
if __name__ == "__main__":
    # Тест функций
    print(f"Расстояние: {calculate_distance((0, 0), (3, 4))}")  # Должно быть 5.0
    print(f"Имя файла: {get_timestamp_filename()}")
    print(f"Время: {get_formatted_time()}")
    
    # Тест IoU
    box1 = [10, 10, 50, 50]
    box2 = [20, 20, 60, 60]
    print(f"IoU: {calculate_iou(box1, box2):.2f}")
    
    # Тест FPSCounter
    counter = FPSCounter()
    for i in range(5):
        time.sleep(0.1)
        fps = counter.update()
        print(f"FPS: {fps:.2f}")