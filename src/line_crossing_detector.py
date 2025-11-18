import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import config
from src.utils import calculate_distance
import logging
import time

logger = logging.getLogger(__name__)

class LineCrossingDetector:
    def __init__(self, line_coords: Optional[Tuple[int, int, int, int]] = None):
        
        # Поддержка режима: линия (по-умолчанию) или область (если указано в config)
        self.region_coords = getattr(config, 'VIOLATION_REGION_COORDS', None)
        self.region_mode = bool(self.region_coords)

        self.line_coords = line_coords or config.CROSSING_LINE_COORDS
        self.tracked_objects: Dict[int, Dict[str, Any]] = {}
        self.next_object_id = 0
        # use values from config when available
        self.max_tracking_distance = getattr(config, 'TRACKING_MAX_DISTANCE', 70)
        self.max_frames_lost = getattr(config, 'MAX_FRAMES_LOST', 10)  # Максимальное количество кадров без обнаружения
        
        # Интервал между фиксациями нарушений от одного объекта (в секундах)
        self.min_violation_interval = getattr(config, 'MIN_VIOLATION_INTERVAL_SECONDS', 60)

        # Для режима области — минимальное время нахождения в области чтобы засчитать нарушение
        self.region_min_stay = getattr(config, 'REGION_MIN_STAY_SECONDS', 1.0)
        self.region_tolerance = getattr(config, 'REGION_ENTRY_TOLERANCE_PX', 0)
        
        # Параметры линии (всё ещё используются если region_mode=False)
        self.A, self.B, self.C = self._calculate_line_params()
        
        # Визуальные настройки
        self.colors = {
            'line': (0, 0, 255),  # Красный
            'box': (0, 255, 0),   # Зеленый
            'text': (255, 255, 255),  # Белый
            'violation': (0, 0, 255)  # Красный для нарушений
        }
        
        logger.info(f"Детектор инициализирован. Режим области: {self.region_mode}. Координаты: {self.region_coords or self.line_coords}")

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
        tol = getattr(config, 'LINE_TOLERANCE_PX', 5)
        if abs(value) <= tol:  # Порог для учета погрешности
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
        Обработка обнаружений и выявление пересечений/входов в область
        Returns:
            Список нарушений
        """
        violations = []
        current_centers = {i: det['bottom_center'] for i, det in enumerate(detections)}
        
        # Сопоставление обнаружений с существующими объектами
        matches = self._match_detections(current_centers)
        now_ts = time.time()

        if getattr(config, 'DEBUG_MODE', False):
            logger.debug(f"process_detections: detections={len(detections)}, matches={len(matches)}")

        # Обновление существующих объектов
        for det_index, obj_id in matches.items():
            detection = detections[det_index]
            new_center = detection['bottom_center']

            track_data = self.tracked_objects[obj_id]

            if getattr(config, 'DEBUG_MODE', False):
                logger.debug(f"Matched det_index={det_index} -> obj_id={obj_id}, center={new_center}")

            # Если включён режим области — работаем с областью
            if self.region_mode and self.region_coords is not None:
                x1, y1, x2, y2 = self.region_coords
                # Используем пересечение bounding box с областью вместо только bottom_center
                bbox = detection.get('box', None)
                inside = False
                if bbox and len(bbox) == 4:
                    bx1, by1, bx2, by2 = bbox
                    # Проверяем пересечение прямоугольников с учётом допуска
                    if (bx2 >= x1 - self.region_tolerance and bx1 <= x2 + self.region_tolerance and
                        by2 >= y1 - self.region_tolerance and by1 <= y2 + self.region_tolerance):
                        inside = True
                else:
                    # fallback — используем центр нижней точки
                    inside = (x1 - self.region_tolerance <= new_center[0] <= x2 + self.region_tolerance and
                              y1 - self.region_tolerance <= new_center[1] <= y2 + self.region_tolerance)

                if inside:
                    if getattr(config, 'DEBUG_MODE', False):
                        logger.debug(f"Object {obj_id} is inside region at {new_center}")
                    # Если впервые зашёл — пометим время входа
                    if track_data.get('in_region_since') is None:
                        track_data['in_region_since'] = now_ts
                        if getattr(config, 'DEBUG_MODE', False):
                            logger.debug(f"Set in_region_since for obj {obj_id} = {now_ts}")
                    else:
                        # Проверяем, не превысил ли минимальное время пребывания
                        elapsed = now_ts - track_data['in_region_since']
                        last_v = track_data.get('last_violation_ts')
                        if getattr(config, 'DEBUG_MODE', False):
                            logger.debug(f"obj {obj_id} elapsed_in_region={elapsed:.3f}, last_violation={last_v}")
                        if elapsed >= self.region_min_stay and (last_v is None or (now_ts - last_v) >= self.min_violation_interval):
                            violation = {
                                'id': obj_id,
                                'box': detection['box'],
                                'direction': 'IN_REGION',
                                'timestamp': detection.get('timestamp') or now_ts,
                                'confidence': detection.get('confidence', 0),
                                'class_id': detection.get('class_id'),
                                'class_name': detection.get('class_name', 'unknown')
                            }
                            violations.append(violation)
                            track_data['last_violation_ts'] = now_ts
                            # После фиксации сбрасываем метку in_region_since, чтобы требовался повторный вход
                            track_data['in_region_since'] = None
                            logger.info(f"Обнаружено нарушение в области: ID {obj_id}")
                        else:
                            if getattr(config, 'DEBUG_MODE', False):
                                logger.debug(f"obj {obj_id} not enough time in region ({elapsed:.3f}s) or interval not passed")
                else:
                    # Вне области — сбрасываем метку времени входа
                    if track_data.get('in_region_since') is not None and getattr(config, 'DEBUG_MODE', False):
                        logger.debug(f"obj {obj_id} left region, clearing in_region_since (was {track_data.get('in_region_since')})")
                    track_data['in_region_since'] = None

                # Обновление данных трекинга
                track_data.update({
                    'last_pos': new_center,
                    'detection': detection,
                    'frames_since_seen': 0
                })

            else:
                # Режим линии
                new_side = self._get_side(new_center)
                prev_side = track_data['side']
                crossed = False
                if new_side != prev_side:
                    # Если одна из сторон ON_LINE, учитываем флаг ENFORCE_LINE_VIOLATION
                    if prev_side == 'ON_LINE' or new_side == 'ON_LINE':
                        crossed = bool(getattr(config, 'ENFORCE_LINE_VIOLATION', False))
                    else:
                        crossed = True

                # Проверка пересечения линии
                if crossed:
                    # Учитываем интервал: если с последнего нарушения у этого объекта прошло меньше min_violation_interval — пропускаем
                    last_violation_ts = track_data.get('last_violation_ts')
                    if getattr(config, 'DEBUG_MODE', False):
                        logger.debug(f"obj {obj_id} crossed line: {prev_side}->{new_side}, last_violation={last_violation_ts}")
                    if last_violation_ts is None or (now_ts - last_violation_ts) >= self.min_violation_interval:
                        violation = {
                            'id': obj_id,
                            'box': detection['box'],
                            'direction': f"{prev_side}->{new_side}",
                            'timestamp': detection.get('timestamp') or now_ts,
                            'confidence': detection.get('confidence', 0),
                            'class_id': detection.get('class_id'),
                            'class_name': detection.get('class_name', 'unknown')
                        }
                        violations.append(violation)
                        track_data['last_violation_ts'] = now_ts
                        logger.info(f"Обнаружено пересечение: ID {obj_id}, направление {violation['direction']}")
                    else:
                        if getattr(config, 'DEBUG_MODE', False):
                            logger.debug(f"obj {obj_id} crossing ignored due to min_violation_interval")

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
                    'side': self._get_side(center) if not self.region_mode else None,
                    'last_pos': center,
                    'detection': detection,
                    'frames_since_seen': 0,
                    'last_violation_ts': None,
                    'in_region_since': None
                }
                if getattr(config, 'DEBUG_MODE', False):
                    logger.debug(f"Added new track obj_id={obj_id}, center={center}, det_index={det_index}")
        
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
        """Отрисовка визуальных элементов: линия или область"""
        if self.region_mode and self.region_coords is not None:
            self._draw_region(frame)
        else:
            self._draw_line(frame)
        self._draw_detections(frame)
        self._draw_violations(frame, violations)
        self._draw_stats(frame)

    def _draw_region(self, frame: np.ndarray):
        x1, y1, x2, y2 = self.region_coords
        cv2.rectangle(frame, (x1, y1), (x2, y2), self.colors['line'], 2)
        cv2.putText(frame, "VIOLATION REGION", (x1, y1 - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['line'], 2)

    def _draw_line(self, frame: np.ndarray):
        """Отрисовка контрольной линии"""
        x1, y1, x2, y2 = self.line_coords
        cv2.line(frame, (x1, y1), (x2, y2), self.colors['line'], 3)
        cv2.putText(frame, "CONTROL LINE", (x1, y1 - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['line'], 2)

    def _draw_detections(self, frame: np.ndarray):
        """Отрисовка обнаруженных/отслеживаемых объектов (bounding box, ID и точка отслеживания)."""
        for obj_id, data in self.tracked_objects.items():
            det = data.get('detection') or {}
            box = det.get('box')
            if box and len(box) == 4:
                startX, startY, endX, endY = box
                # Бокс
                cv2.rectangle(frame, (startX, startY), (endX, endY), self.colors['box'], 2)
                # ID и, если есть, сторона
                side = data.get('side', '')
                text = f"ID:{obj_id}{('('+side+')') if side else ''}"
                cv2.putText(frame, text, (startX, max(startY - 10, 10)), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.colors['text'], 2)
                # Точка последней позиции
                last_pos = data.get('last_pos')
                if last_pos:
                    cx, cy = int(last_pos[0]), int(last_pos[1])
                    cv2.circle(frame, (cx, cy), 4, (255, 0, 0), -1)

    def _draw_violations(self, frame: np.ndarray, violations: List[Dict[str, Any]]):
        """Отрисовка нарушителей — без метки 'VIOLATION' (только ALERT)"""
        for violation in violations:
            startX, startY, endX, endY = violation['box']
            # Красный бокс для нарушителя
            cv2.rectangle(frame, (startX, startY), (endX, endY), 
                         self.colors['violation'], 3)
            # Текст предупреждения
            text = f"ALERT"
            cv2.putText(frame, text, (startX, startY - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['violation'], 2)

    def _draw_stats(self, frame: np.ndarray):
        """Отрисовка статистики"""
        stats = [
            f"Objects: {len(self.tracked_objects)}",
            f"Tracked IDs: {self.next_object_id}"
        ]
        
        for i, stat in enumerate(stats):
            cv2.putText(frame, stat, (10, 30 + i * 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        return {
            'current_objects': len(self.tracked_objects),
            'next_object_id': self.next_object_id
        }

    def reset_stats(self):
        """Сброс статистики"""
        logger.info("Статистика детектора сброшена")


# Тестирование
if __name__ == "__main__":
    # Пример использования
    detector = LineCrossingDetector((100, 100, 500, 100))
    print("Детектор линии инициализирован")