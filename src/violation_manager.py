import cv2
import os
import config
from src.utils import get_timestamp_filename
import logging

class ViolationManager:
    def __init__(self):
        self.violation_dir = config.VIOLATIONS_DIR
        if not os.path.exists(self.violation_dir):
            os.makedirs(self.violation_dir)

    def save_violation(self, frame, violation_data):
        """
        Сохраняет кадр с нарушением.
        Имя файла: violation_YYYYMMDD_HHMMSS.jpg
        """
        timestamp = get_timestamp_filename()
        filename = f"violation_{timestamp}.jpg"
        path = os.path.join(self.violation_dir, filename)
        
        # Добавляем информацию о нарушении на кадр (опционально)
        text = f"VIOLATION: {timestamp}"
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        success = cv2.imwrite(path, frame)
        if success:
            logging.info(f"Нарушение сохранено: {path}")
        else:
            logging.error(f"Не удалось сохранить файл: {path}")
        
        return success
