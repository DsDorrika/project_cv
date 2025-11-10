import cv2
import time
import platform
import logging
from typing import Any
import config

logger = logging.getLogger(__name__)

BACKENDS = {
    "dshow": getattr(cv2, "CAP_DSHOW", 700),
    "msmf": getattr(cv2, "CAP_MSMF", 1400),
    "any": 0,
}


class Camera:
    """Класс для работы с видеопотоком (камера или видеофайл)."""

    def __init__(self, source: Any = None):
        # Источник видео: индекс (int), путь (str) или None → берётся из config
        self.source = source if source is not None else getattr(config, "VIDEO_SOURCE", 0)
        self.cap = None
        self.is_running = False
        self.frame_count = 0
        self.backend = getattr(config, "CAMERA_BACKEND", "any").lower()

    def _open(self, source, backend_name: str):
        """Открывает источник видео с указанным backend."""
        flag = BACKENDS.get(backend_name, 0)
        cap = cv2.VideoCapture(source, flag) if flag != 0 else cv2.VideoCapture(source)
        if not cap or not cap.isOpened():
            return None

        # Устанавливаем параметры
        w, h = getattr(config, "CAMERA_RESOLUTION", (1280, 720))
        fps = getattr(config, "CAMERA_FPS", 30)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        cap.set(cv2.CAP_PROP_FPS, fps)

        # Прогрев камеры
        warm = getattr(config, "CAMERA_WARMUP_FRAMES", 0)
        for _ in range(max(0, warm)):
            cap.read()
            time.sleep(0.02)

        return cap

    def start(self) -> bool:
        """Инициализация видеопотока с несколькими fallback-попытками."""
        order = []
        if platform.system() == "Windows":
            if self.backend == "dshow":
                order = ["dshow", "msmf", "any"]
            elif self.backend == "msmf":
                order = ["msmf", "dshow", "any"]
            else:
                order = ["dshow", "msmf", "any"]
        else:
            order = [self.backend, "any"] if self.backend != "any" else ["any"]

        device_name = getattr(config, "VIDEO_DEVICE_NAME", None)
        if device_name:
            cap = self._open(f"video={device_name}", "dshow")
            if cap:
                self.cap = cap
                self.is_running = True
                logger.info(f"Камера инициализирована по имени устройства (DSHOW): {device_name}")
                return True

        if isinstance(self.source, str):
            backend_try = self.backend if self.backend in BACKENDS else "any"
            cap = self._open(self.source, backend_try)
            if not cap and backend_try != "any":
                cap = self._open(self.source, "any")
            if cap:
                self.cap = cap
                self.is_running = True
                logger.info(f"Видеоисточник открыт: {self.source} (backend={backend_try})")
                return True

        for b in order:
            cap = self._open(self.source, b)
            if cap:
                self.cap = cap
                self.is_running = True
                logger.info(f"Камера инициализирована (index={self.source}, backend={b})")
                return True

        logger.error("❌ Ошибка инициализации камеры: ни один backend не подошёл.")
        return False

    def read(self):
        """Чтение кадра. При сбое может попытаться переинициализироваться."""
        if not self.is_running or self.cap is None:
            return False, None

        ret, frame = self.cap.read()

        if not ret and getattr(config, "READ_RETRY_ON_FAIL", False):
            logger.warning("Не удалось прочитать кадр — пробуем переинициализировать камеру.")
            self.stop()
            time.sleep(0.3)
            if self.start():
                ret, frame = self.cap.read()

        if ret:
            self.frame_count += 1

        return ret, frame

    def stop(self):
        """Освобождение ресурсов камеры."""
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
        self.cap = None
        self.is_running = False
        logger.info("Ресурсы камеры освобождены")

    def __del__(self):
        """Безопасное завершение при удалении объекта."""
        self.stop()
