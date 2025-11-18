import cv2
import logging
import time
from typing import Optional, Tuple, Dict, Any
import config

logger = logging.getLogger(__name__)

class Camera:
    def __init__(self, source: Any = config.VIDEO_SOURCE):
        
        self.source = source
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.width = 0
        self.height = 0
        self.fps = 0
        self.frame_count = 0
        self.start_time = time.time()
        
        self._initialize_camera()

    def _initialize_camera(self) -> bool:
        """Инициализация камеры с обработкой ошибок. Пытаем несколько бэкендов на Windows (DSHOW, MSMF)."""
        try:
            # Если источник - строка (файл) — стандартный захват
            if not isinstance(self.source, int):
                self.cap = cv2.VideoCapture(self.source)
                opened = self.cap.isOpened()
                if not opened:
                    logger.error(f"Не удалось открыть видеофайл/источник: {self.source}")
                    return False
                logger.info(f"Видеофайл открыт: {self.source}")
            else:
                # Для веб-камеры пробуем несколько API на Windows, чтобы избежать ошибок MSMF
                attempted = []
                backends = []
                try:
                    # CAP_DSHOW обычно надёжен для многих USB камер на Windows
                    backends.append(cv2.CAP_DSHOW)
                except Exception:
                    pass
                try:
                    backends.append(cv2.CAP_MSMF)
                except Exception:
                    pass
                backends.append(cv2.CAP_ANY)

                opened = False
                for api in backends:
                    try:
                        self.cap = cv2.VideoCapture(self.source, api)
                        time.sleep(0.05)
                        if self.cap.isOpened():
                            logger.info(f"Камера инициализирована через backend API={api}")
                            opened = True
                            break
                        else:
                            attempted.append(api)
                            try:
                                self.cap.release()
                            except Exception:
                                pass
                    except Exception as e:
                        logger.warning(f"Попытка инициализации через API={api} завершилась ошибкой: {e}")

                if not opened:
                    logger.error(f"Не удалось открыть камеру {self.source}. Попытанные API: {attempted}")
                    return False

                # Установка параметров для лучшей производительности
                try:
                    self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    self.cap.set(cv2.CAP_PROP_FPS, 30)
                except Exception:
                    # Игнорируем если backend не поддерживает эти свойства
                    pass

            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 0
            self.is_running = True

            logger.info(f"Камера инициализирована: {self.width}x{self.height}, FPS: {self.fps:.2f}")
            return True

        except Exception as e:
            logger.error(f"Ошибка инициализации камеры: {e}")
            return False

    def read(self) -> Tuple[bool, Optional[Any]]:
    
        if not self.is_running or self.cap is None:
            return False, None
        
        try:
            ret, frame = self.cap.read()
            self.frame_count += 1
            
            if not ret:
                logger.warning("Не удалось прочитать кадр")
                # Попытка переинициализации для веб-камер — несколько попыток для устойчивости
                if isinstance(self.source, int):
                    try_count = 0
                    self.release()
                    while try_count < 3 and not self._initialize_camera():
                        try_count += 1
                        logger.info(f"Повторная попытка инициализации камеры #{try_count}")
                        time.sleep(0.2)
                    if try_count >= 3:
                        logger.error("Не удалось восстановить камеру после нескольких попыток")
                        return False, None
                return False, None
            
            return True, frame
            
        except Exception as e:
            logger.error(f"Ошибка при чтении кадра: {e}")
            return False, None

    def get_actual_fps(self) -> float:
        """Расчет реального FPS"""
        elapsed = time.time() - self.start_time
        return self.frame_count / elapsed if elapsed > 0 else 0

    def get_info(self) -> Dict[str, Any]:
        """Получение информации о камере"""
        return {
            'width': self.width,
            'height': self.height, 
            'fps': self.fps,
            'actual_fps': self.get_actual_fps(),
            'frame_count': self.frame_count,
            'is_running': self.is_running
        }

    def release(self):
        """Освобождение ресурсов с защитой от ошибок"""
        try:
            if self.cap is not None:
                self.cap.release()
                logger.info("Ресурсы камеры освобождены")
        except Exception as e:
            logger.error(f"Ошибка при освобождении ресурсов камеры: {e}")
        finally:
            self.cap = None
            self.is_running = False

    def __del__(self):
        """Деструктор для автоматической очистки"""
        self.release()


def test_camera():
    """Тестирование работы камеры"""
    camera = Camera()
    
    if not camera.is_running:
        print("Не удалось инициализировать камеру")
        return

    print("Камера запущена. Нажмите 'q' для выхода, 'r' для перезапуска камеры")
    
    last_fps_update = time.time()
    fps = 0
    
    while True:
        ret, frame = camera.read()
        
        if not ret:
            print("Ошибка получения кадра")
            break
        
        # Обновление FPS каждую секунду
        if time.time() - last_fps_update > 1.0:
            fps = camera.get_actual_fps()
            last_fps_update = time.time()
        
        # Отображение информации на кадре
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"Resolution: {camera.width}x{camera.height}", (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.imshow('Camera Test', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            camera.release()
            time.sleep(1)
            camera._initialize_camera()

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    test_camera()