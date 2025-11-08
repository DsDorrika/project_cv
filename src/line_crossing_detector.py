import cv2
import config
from src.utils import calculate_distance

class LineCrossingDetector:
    def __init__(self):
        self.line_coords = config.CROSSING_LINE_COORDS 
        self.tracked_objects = {} # {id: {'side': 'POS/NEG', 'last_pos': (x, y)}}
        self.next_object_id = 0
        self.max_tracking_distance = 70 # Максимальное расстояние для сопоставления
        
        # Параметры линии Ax + By + C = 0
        self.A, self.B, self.C = self._calculate_line_params()

    def _calculate_line_params(self):
        (x1, y1, x2, y2) = self.line_coords
        A = y2 - y1
        B = x1 - x2
        C = x2 * y1 - y2 * x1
        return A, B, C

    def _get_side_value(self, point):
        """Возвращает значение функции линии F(x, y) = Ax + By + C."""
        x, y = point
        return self.A * x + self.B * y + self.C

    def _get_side(self, point):
        """Возвращает 'POSITIVE' или 'NEGATIVE'."""
        value = self._get_side_value(point)
        if value > 0:
            return 'POSITIVE'
        elif value < 0:
            return 'NEGATIVE'
        return 'ON_LINE'

    def process_detections(self, frame, detections):
        violations = []
        
        current_centers = {i: det['bottom_center'] for i, det in enumerate(detections)}
        current_tracked_ids = set()
        
        # 1. Сопоставление с существующими объектами
        for obj_id, track_data in list(self.tracked_objects.items()):
            min_dist = float('inf')
            best_match_index = -1
            
            for i, center in current_centers.items():
                dist = calculate_distance(track_data['last_pos'], center)
                if dist < min_dist and i not in current_tracked_ids:
                    min_dist = dist
                    best_match_index = i
            
            if min_dist < self.max_tracking_distance and best_match_index != -1:
                # Объект найден и сопоставлен
                current_tracked_ids.add(best_match_index)
                
                new_center = current_centers[best_match_index]
                new_side = self._get_side(new_center)
                prev_side = track_data['side']
                
                # Проверка пересечения
                if new_side != prev_side and prev_side != 'ON_LINE' and new_side != 'ON_LINE':
                    violations.append({
                        'id': obj_id,
                        'box': detections[best_match_index]['box'],
                        'direction': f"{prev_side} -> {new_side}"
                    })
                
                # Обновление трека
                self.tracked_objects[obj_id]['side'] = new_side
                self.tracked_objects[obj_id]['last_pos'] = new_center
                self.tracked_objects[obj_id]['detection'] = detections[best_match_index]
            else:
                # Объект пропал
                del self.tracked_objects[obj_id]

        # 2. Добавление новых объектов
        for i, det in enumerate(detections):
            if i not in current_tracked_ids:
                obj_id = self.next_object_id
                self.next_object_id += 1
                
                center = det['bottom_center']
                self.tracked_objects[obj_id] = {
                    'side': self._get_side(center),
                    'last_pos': center,
                    'detection': det
                }
        
        # 3. Рисование
        self.draw_line(frame)
        self.draw_detections(frame)
        
        return violations

    def draw_line(self, frame):
        (x1, y1, x2, y2) = self.line_coords
        cv2.line(frame, (x1, y1), (x2, y2), (0, 0, 255), 2) # Красная линия

    def draw_detections(self, frame):
        for obj_id, data in self.tracked_objects.items():
            (startX, startY, endX, endY) = data['detection']['box']
            color = (0, 255, 0) 
            
            cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)
            
            text = f"ID {obj_id} ({data['side']})"
            cv2.putText(frame, text, (startX, startY - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
