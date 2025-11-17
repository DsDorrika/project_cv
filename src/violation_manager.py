import cv2
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import config
from src.utils import get_timestamp_filename, save_data_to_json
import logging

logger = logging.getLogger(__name__)

class ViolationManager:
    def __init__(self, violation_dir: Optional[str] = None):
        self.violation_dir = violation_dir or config.VIOLATIONS_DIR
        self.violations_log: List[Dict[str, Any]] = []
        self.max_log_size = 1000  # Максимальный размер лога в памяти
        
        self._initialize_directories()

    def _initialize_directories(self):
        """Инициализация директорий для хранения данных"""
        try:
            # Основная директория нарушений
            if not os.path.exists(self.violation_dir):
                os.makedirs(self.violation_dir, exist_ok=True)
                logger.info(f"Создана директория нарушений: {self.violation_dir}")
            
            # Поддиректории для организации
            self.images_dir = os.path.join(self.violation_dir, "images")
            self.data_dir = os.path.join(self.violation_dir, "data")
            self.reports_dir = os.path.join(self.violation_dir, "reports")
            
            for directory in [self.images_dir, self.data_dir, self.reports_dir]:
                if not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                    
            logger.info("Директории для нарушений инициализированы")
            
        except Exception as e:
            logger.error(f"Ошибка создания директорий: {e}")

    def save_violation(self, frame, violation_data: Dict[str, Any]) -> Dict[str, Any]:
        
        try:
            timestamp = datetime.now()
            base_filename = get_timestamp_filename("violation")
            
            # Сохранение изображения
            image_path = os.path.join(self.images_dir, f"{base_filename}.jpg")
            image_success = self._save_violation_image(frame, violation_data, image_path)
            
            # Сохранение метаданных
            metadata_path = os.path.join(self.data_dir, f"{base_filename}.json")
            metadata = self._create_metadata(violation_data, timestamp, image_path, image_success)
            metadata_success = save_data_to_json(metadata, metadata_path)
            
            # Добавление в лог
            violation_record = {
                **metadata,
                'image_saved': image_success,
                'metadata_saved': metadata_success
            }
            
            self._add_to_log(violation_record)
            
            if image_success and metadata_success:
                logger.info(f"Нарушение сохранено: {base_filename}")
            else:
                logger.warning(f"Нарушение сохранено частично: {base_filename}")
                
            return violation_record
            
        except Exception as e:
            logger.error(f"Ошибка сохранения нарушения: {e}")
            return {}

    def _save_violation_image(self, frame, violation_data: Dict[str, Any], image_path: str) -> bool:
        """Сохранение изображения с нарушением"""
        try:
            # Создание копии кадра для аннотаций
            annotated_frame = frame.copy()
            
            # Добавление аннотаций
            self._annotate_violation_frame(annotated_frame, violation_data)
            
            # Сохранение с настройками качества
            success = cv2.imwrite(image_path, annotated_frame, [
                cv2.IMWRITE_JPEG_QUALITY, 85  # Качество 85% для экономии места
            ])
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка сохранения изображения нарушения: {e}")
            return False

    def _annotate_violation_frame(self, frame, violation_data: Dict[str, Any]):
        """Добавление аннотаций на кадр с нарушением"""
        try:
            # Основная информация
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            violation_id = violation_data.get('id', 'N/A')
            direction = violation_data.get('direction', 'N/A')
            confidence = violation_data.get('confidence', 0)
            class_name = violation_data.get('class_name', 'unknown')
            class_id = violation_data.get('class_id')
            
            # Текстовая информация
            texts = [
                f"VIOLATION: {timestamp}",
                f"ID: {violation_id} Direction: {direction}",
                f"Class: {class_name} ({class_id}) Confidence: {confidence:.2f}"
            ]
            
            # Рисование текста с фоном
            for i, text in enumerate(texts):
                y_position = 30 + i * 25
                cv2.putText(frame, text, (10, y_position), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            # Рисование bounding box если есть
            if 'box' in violation_data:
                startX, startY, endX, endY = violation_data['box']
                cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 0, 255), 3)
                
                # Подпись бокса
                box_text = f"Violation {violation_id}: {class_name}"
                cv2.putText(frame, box_text, (startX, startY - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
        except Exception as e:
            logger.error(f"Ошибка аннотирования кадра: {e}")

    def _create_metadata(self, violation_data: Dict[str, Any], timestamp: datetime, 
                        image_path: str, image_success: bool) -> Dict[str, Any]:
        """Создание метаданных нарушения"""
        return {
            'timestamp': timestamp.isoformat(),
            'violation_id': violation_data.get('id'),
            'direction': violation_data.get('direction'),
            'confidence': violation_data.get('confidence'),
            'bounding_box': violation_data.get('box'),
            'class_id': violation_data.get('class_id'),
            'class_name': violation_data.get('class_name', None),
            'image_path': image_path if image_success else None,
            'image_saved': image_success,
            'system_info': {
                'violation_dir': self.violation_dir,
                'total_violations': len(self.violations_log) + 1
            }
        }

    def _add_to_log(self, violation_record: Dict[str, Any]):
        """Добавление нарушения в лог с ограничением размера"""
        self.violations_log.append(violation_record)
        
        # Ограничение размера лога
        if len(self.violations_log) > self.max_log_size:
            self.violations_log = self.violations_log[-self.max_log_size:]

    def generate_report(self, time_range: Optional[tuple] = None) -> Dict[str, Any]:
        
        try:
            filtered_violations = self._filter_violations_by_time(time_range)
            
            report = {
                'generated_at': datetime.now().isoformat(),
                'time_range': time_range,
                'total_violations': len(filtered_violations),
                'directions_summary': self._count_directions(filtered_violations),
                'time_periods': self._analyze_time_periods(filtered_violations),
                'recent_violations': filtered_violations[-10:]  # Последние 10 нарушений
            }
            
            # Сохранение отчета
            report_filename = f"report_{get_timestamp_filename()}.json"
            report_path = os.path.join(self.reports_dir, report_filename)
            save_data_to_json(report, report_path)
            
            logger.info(f"Отчет сгенерирован: {report_path}")
            return report
            
        except Exception as e:
            logger.error(f"Ошибка генерации отчета: {e}")
            return {}

    def _filter_violations_by_time(self, time_range: Optional[tuple]) -> List[Dict[str, Any]]:
        """Фильтрация нарушений по времени"""
        if not time_range:
            return self.violations_log.copy()
        
        start_time, end_time = time_range
        filtered = []
        
        for violation in self.violations_log:
            violation_time = datetime.fromisoformat(violation['timestamp'])
            if start_time <= violation_time <= end_time:
                filtered.append(violation)
                
        return filtered

    def _count_directions(self, violations: List[Dict[str, Any]]) -> Dict[str, int]:
        """Подсчет нарушений по направлениям"""
        directions = {}
        for violation in violations:
            direction = violation.get('direction', 'UNKNOWN')
            directions[direction] = directions.get(direction, 0) + 1
        return directions

    def _analyze_time_periods(self, violations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Анализ нарушений по временным периодам"""
        if not violations:
            return {}
        
        # Группировка по часам
        hourly_counts = {}
        for violation in violations:
            violation_time = datetime.fromisoformat(violation['timestamp'])
            hour = violation_time.strftime("%H:00")
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
            
        return {
            'hourly_distribution': hourly_counts,
            'peak_hour': max(hourly_counts, key=hourly_counts.get) if hourly_counts else None,
            'total_period': f"{violations[0]['timestamp']} - {violations[-1]['timestamp']}"
        }

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики менеджера нарушений"""
        return {
            'total_violations_saved': len(self.violations_log),
            'violation_dir': self.violation_dir,
            'images_dir': self.images_dir,
            'data_dir': self.data_dir,
            'reports_dir': self.reports_dir,
            'recent_activity': self.violations_log[-5:] if self.violations_log else []
        }

    def cleanup_old_files(self, max_age_days: int = 30):
        """
        Очистка старых файлов нарушений
        
        Args:
            max_age_days: максимальный возраст файлов в днях
        """
        try:
            cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
            deleted_count = 0
            
            for directory in [self.images_dir, self.data_dir, self.reports_dir]:
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
            
            logger.info(f"Удалено старых файлов: {deleted_count}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Ошибка очистки старых файлов: {e}")
            return 0


# Тестирование
if __name__ == "__main__":
    manager = ViolationManager()
    print(f"Менеджер нарушений инициализирован: {manager.violation_dir}")
    print(f"Статистика: {manager.get_stats()}")