import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import config
from src.utils import calculate_distance
import logging

logger = logging.getLogger(__name__)

class LineCrossingDetector:
    def __init__(self, line_coords: Optional[Tuple[int, int, int, int]] = None):
        
        self.line_coords = line_coords or config.CROSSING_LINE_COORDS
        self.tracked_objects: Dict[int, Dict[str, Any]] = {}
        self.next_object_id = 0
        self.max_tracking_distance = 70
        self.max_frames_lost = 10  # Максимальное количество кадров без обнаружения
        
        # Статистика
        self.crossings_count = 0
        self.directions_count = {'POSITIVE->NEGATIVE': 0, 'NEGATIVE->POSITIVE': 0}
        
        # Параметры линии
        self.A, self.B, self.C = self._calculate_line_params()
        
        # Визуальные настройки
        self.colors = {
            'line': (0, 0, 255),  # Красный
            'box': (0, 255, 0),   # Зеленый
            'text': (255, 255, 255),  # Белый
            'violation': (0, 0, 255)  # Красный для нарушений
        }
        
        logger.info(f"Детектор линии инициализирован с координатами: {self.line_coords}")

    def _calculate_line_params(self) -> Tuple[float, float, float]:
        """Вычисление параметров линии Ax + By + C = 0"""
        x1, y1, x2, y2 = self.line_coords
        A = y2 - y1
        B = x1 - x2
        C = x2 * y1 - x1 * y2
        return A, B, C

    def _get_side_value(self, point: Tuple[float, float]) -> float:
        """Вычисление значения функции линии F(x, y) = Ax + By + C"""
        x, y = point
        return self.A * x + self.B * y + self.C

    def _get_side(self, point: Tuple[float, float]) -> str:
        """Определение стороны относительно линии"""
        value = self._get_side_value(point)
        if abs(value) < 5:  # Порог для учета погрешности
            return 'ON_LINE'
        return 'POSITIVE' if value > 0 else 'NEGATIVE'

    def _match_detections(self, current_centers: Dict[int, Tuple[float, float]]) -> Dict[int, int]:
        
        matches = {}
        used_detections = set()
        
        for obj_id, track_data in self.tracked_objects.items():
            min_dist = float('inf')
            best_match_index = -1
            
            for det_index, center in current_centers.items():
                if det_index in used_detections:
                    continue
                    
                dist = calculate_distance(track_data['last_pos'], center)
                if dist < min_dist and dist < self.max_tracking_distance:
                    min_dist = dist
                    best_match_index = det_index
            
            if best_match_index != -1:
                matches[best_match_index] = obj_id
                used_detections.add(best_match_index)
        
        return matches

    def process_detections(self, frame: np.ndarray, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Обработка обнаружений и выявление пересечений
        
        Returns:
            Список нарушений
        """
        violations = []
        current_centers = {i: det['bottom_center'] for i, det in enumerate(detections)}
        
        # Сопоставление обнаружений с существующими объектами
        matches = self._match_detections(current_centers)
        
        # Обновление существующих объектов
        for det_index, obj_id in matches.items():
            detection = detections[det_index]
            new_center = detection['bottom_center']
            new_side = self._get_side(new_center)
            
            track_data = self.tracked_objects[obj_id]
            prev_side = track_data['side']
            
            # Проверка пересечения линии
            if (new_side != prev_side and 
                prev_side != 'ON_LINE' and 
                new_side != 'ON_LINE'):
                
                direction = f"{prev_side}->{new_side}"
                violations.append({
                    'id': obj_id,
                    'box': detection['box'],
                    'direction': direction,
                    'timestamp': detection.get('timestamp'),
                    'confidence': detection.get('confidence', 0)
                })
                
                # Обновление статистики
                self.crossings_count += 1
                self.directions_count[direction] = self.directions_count.get(direction, 0) + 1
                logger.info(f"Обнаружено пересечение: ID {obj_id}, направление {direction}")
            
            # Обновление данных трекинга
            track_data.update({
                'side': new_side,
                'last_pos': new_center,
                'detection': detection,
                'frames_since_seen': 0
            })
        
        # Добавление новых объектов
        for det_index, detection in enumerate(detections):
            if det_index not in matches:
                obj_id = self.next_object_id
                self.next_object_id += 1
                
                center = detection['bottom_center']
                self.tracked_objects[obj_id] = {
                    'side': self._get_side(center),
                    'last_pos': center,
                    'detection': detection,
                    'frames_since_seen': 0
                }
        
        # Удаление потерянных объектов
        lost_objects = []
        for obj_id, track_data in list(self.tracked_objects.items()):
            if obj_id not in matches.values():
                track_data['frames_since_seen'] += 1
                if track_data['frames_since_seen'] > self.max_frames_lost:
                    lost_objects.append(obj_id)
        
        for obj_id in lost_objects:
            del self.tracked_objects[obj_id]
        
        # Визуализация
        self._draw_visualization(frame, violations)
        
        return violations

    def _draw_visualization(self, frame: np.ndarray, violations: List[Dict[str, Any]]):
        """Отрисовка визуальных элементов"""
        self._draw_line(frame)
        self._draw_detections(frame)
        self._draw_violations(frame, violations)
        self._draw_stats(frame)

    def _draw_line(self, frame: np.ndarray):
        """Отрисовка контрольной линии"""
        x1, y1, x2, y2 = self.line_coords
        cv2.line(frame, (x1, y1), (x2, y2), self.colors['line'], 3)
        cv2.putText(frame, "CONTROL LINE", (x1, y1 - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['line'], 2)

    def _draw_detections(self, frame: np.ndarray):
        """Отрисовка обнаруженных объектов"""
        for obj_id, data in self.tracked_objects.items():
            startX, startY, endX, endY = data['detection']['box']
            
            # Бокс
            cv2.rectangle(frame, (startX, startY), (endX, endY), 
                         self.colors['box'], 2)
            
            # ID и сторона
            text = f"ID:{obj_id}({data['side']})"
            cv2.putText(frame, text, (startX, startY - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.colors['text'], 2)
            
            # Точка для отслеживания
            center_x, center_y = data['last_pos']
            cv2.circle(frame, (int(center_x), int(center_y)), 5, (255, 0, 0), -1)

    def _draw_violations(self, frame: np.ndarray, violations: List[Dict[str, Any]]):
        """Отрисовка нарушений"""
        for violation in violations:
            startX, startY, endX, endY = violation['box']
            
            # Красный бокс для нарушителя
            cv2.rectangle(frame, (startX, startY), (endX, endY), 
                         self.colors['violation'], 3)
            
            # Текст нарушения
            text = f"VIOLATION: {violation['direction']}"
            cv2.putText(frame, text, (startX, startY - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['violation'], 2)

    def _draw_stats(self, frame: np.ndarray):
        """Отрисовка статистики"""
        stats = [
            f"Crossings: {self.crossings_count}",
            f"Objects: {len(self.tracked_objects)}",
            f"P->N: {self.directions_count.get('POSITIVE->NEGATIVE', 0)}",
            f"N->P: {self.directions_count.get('NEGATIVE->POSITIVE', 0)}"
        ]
        
        for i, stat in enumerate(stats):
            cv2.putText(frame, stat, (10, 30 + i * 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        return {
            'total_crossings': self.crossings_count,
            'current_objects': len(self.tracked_objects),
            'directions': self.directions_count.copy(),
            'next_object_id': self.next_object_id
        }

    def reset_stats(self):
        """Сброс статистики"""
        self.crossings_count = 0
        self.directions_count = {'POSITIVE->NEGATIVE': 0, 'NEGATIVE->POSITIVE': 0}
        logger.info("Статистика детектора сброшена")


# Тестирование
if __name__ == "__main__":
    # Пример использования
    detector = LineCrossingDetector((100, 100, 500, 100))
    print("Детектор линии инициализирован")