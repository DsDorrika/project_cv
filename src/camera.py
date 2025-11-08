# ====================================================================
# src/camera.py
# ====================================================================

import cv2
import logging
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Camera:
    def __init__(self, source=config.VIDEO_SOURCE):
        self.source = source
        self.cap = cv2.VideoCapture(source)
        self.is_running = self.cap.isOpened()

        if not self.is_running:
            logging.error(f"Не удалось открыть источник видео: {source}")
            self.width, self.height, self.fps = 0, 0, 0
        else:
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            logging.info(f"Видеопоток открыт. Разрешение: {self.width}x{self.height}, FPS: {self.fps:.2f}")

    def read(self):
        if not self.is_running:
            return False, None
        
        ret, frame = self.cap.read()
        
        if not ret:
            logging.warning("Ошибка чтения кадра или конец потока.")
            self.is_running = False
            return False, None
            
        return ret, frame

    def release(self):
        if self.cap:
            self.cap.release()
            logging.info("Видеопоток закрыт.")
            self.is_running = False

    def get_info(self):
        return {'width': self.width, 'height': self.height, 'fps': self.fps}
