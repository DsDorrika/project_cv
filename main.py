import cv2
import time
import tkinter as tk
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

ROOT_DIR = Path(__file__).parent.absolute()
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import config
from src.camera import Camera
from src.object_detector import ObjectDetector
from src.line_crossing_detector import LineCrossingDetector
from src.sound_player import SoundPlayer, get_sound_player
from src.violation_manager import ViolationManager
from src.gui import ApplicationGUI
from src.utils import FPSCounter, resize_frame, draw_text_with_background  # noqa: F401  (на будущее)


def setup_logging() -> None:
    """Безопасная инициализация логов: без рекурсии и дублей хэндлеров."""
    root = logging.getLogger()
    # Полная очистка, чтобы не копились обработчики между перезапусками
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(getattr(logging, config.LOG_LEVEL, "INFO"))

    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    # Файловый лог (если включён)
    if getattr(config, "LOG_TO_FILE", False):
        try:
            fh = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
            fh.setFormatter(fmt)
            root.addHandler(fh)
        except Exception as e:
            # Не логируем через root до добавления хэндлеров — просто печать
            print(f"[warn] Не удалось открыть лог-файл: {e}")


# ============================
#       Главное приложение
# ============================
class MainApplication:
    """Главный класс приложения, управляющий компонентами и GUI."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.logger = logging.getLogger("MainApplication")

        # Состояния
        self.is_running = False
        self.is_paused = False

        # Компоненты
        self.components: Dict[str, Any] = {}

        # FPS
        self.fps_counter = FPSCounter()
        self.proc_fps_counter = FPSCounter()

        # Инициализация компонентов
        if not self._initialize_components():
            self.logger.error("Не удалось инициализировать компоненты приложения")
            # Не создаём GUI и выходим мягко
            return

        # Инициализация GUI (делаем только если компоненты поднялись)
        try:
            self.gui = self._initialize_gui()
            self.logger.info("GUI инициализирован")
        except Exception as e:
            self.logger.error(f"Ошибка инициализации GUI: {e}")
            # GUI нет — дальше приложение запускать нельзя
            return

        self.logger.info("Приложение инициализировано успешно")

    # -------------------- Вспомогательное --------------------
    def _initialize_components(self) -> bool:
        """Создание и инициализация всех подсистем."""
        try:
            comps: Dict[str, Any] = {}

            # Камера
            self.logger.info("Инициализация камеры...")
            camera = Camera(getattr(config, "VIDEO_SOURCE", 0))
            if not getattr(camera, "is_running", False):
                # Некоторые реализации требуют явного старта
                if not camera.start():
                    self.logger.error("Не удалось инициализировать камеру")
                    return False
            comps["camera"] = camera

            # Детектор объектов
            self.logger.info("Инициализация детектора объектов...")
            detector = ObjectDetector(
            confidence_threshold=getattr(config, "DETECTOR_CONFIDENCE_THRESHOLD", 0.4),
            target_class_id=getattr(config, "TARGET_CLASS_ID", 15)
            )
            comps["detector"] = detector

            # Детектор пересечения линии
            self.logger.info("Инициализация детектора пересечения линии...")
            line_detector = LineCrossingDetector(
                line_coords=getattr(config, "CROSSING_LINE_COORDS", (320, 360, 960, 360))
            )
            comps["line_detector"] = line_detector

            # Звук
            self.logger.info("Инициализация звуковой системы...")
            try:
                sound_player = get_sound_player(
                    sound_file=config.SOUND_FILE,
                    volume=getattr(config, "SOUND_VOLUME", 0.7),
                    enabled=getattr(config, "SOUND_ENABLED", True),
                )
            except Exception:
                # fallback: прямой конструктор
                sound_player = SoundPlayer(
                    sound_file=config.SOUND_FILE,
                    volume=getattr(config, "SOUND_VOLUME", 0.7),
                    enabled=getattr(config, "SOUND_ENABLED", True),
                )
            comps["sound_player"] = sound_player

            # Менеджер нарушений
            self.logger.info("Инициализация менеджера нарушений...")
            vio_manager = ViolationManager(getattr(config, "VIOLATIONS_DIR", str(ROOT_DIR / "violations")))
            comps["violation_manager"] = vio_manager

            self.components = comps
            self.fps_counter.reset()
            self.proc_fps_counter.reset()
            return True

        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {e}")
            return False

    def _initialize_gui(self) -> ApplicationGUI:
        """Создание GUI и привязка колбэков."""
        return ApplicationGUI(
            root=self.root,
            sound_player_callback=self._on_test_sound,
            start_detection_callback=self.start_detection,
            stop_detection_callback=self.stop_detection,
            pause_callback=self.toggle_pause,
        )

    def _on_test_sound(self) -> None:
        try:
            self.components["sound_player"].test_sound()
            if hasattr(self, "gui"):
                self.gui.update_status(message="Тест звука")
        except Exception as e:
            self.logger.error(f"Ошибка тестирования звука: {e}")

    def start_detection(self) -> None:
        if not hasattr(self, "gui"):
            self.logger.error("GUI недоступен")
            return
        if self.is_running:
            self.gui.update_status(message="Детекция уже запущена")
            return
        self.logger.info("Запуск системы детекции...")
        self.is_running = True
        self.is_paused = False
        self.fps_counter.reset()
        self.proc_fps_counter.reset()
        self._schedule_next_frame()

    def stop_detection(self) -> None:
        if not self.is_running:
            return
        self.logger.info("Остановка системы детекции...")
        self.is_running = False

        # Закрываем предпросмотр, если он использовался
        try:
            if getattr(config, "USE_CAMERA_PREVIEW", True):
                cv2.destroyAllWindows()
        except Exception:
            pass

        # Сброс отображения статов
        try:
            if hasattr(self, "gui"):
                self.gui.update_fps(0.0)
        except Exception:
            pass

    def toggle_pause(self) -> None:
        self.is_paused = not self.is_paused
        state = "приостановлена" if self.is_paused else "возобновлена"
        self.logger.info(f"Система {state}")
        if hasattr(self, "gui"):
            self.gui.update_status(message=f"Система {state}")
        if not self.is_paused and self.is_running:
            # продолжим обработку
            self._schedule_next_frame()

    def _schedule_next_frame(self) -> None:
        """Планирует обработку следующего кадра через Tkinter .after()."""
        if not self.is_running or self.is_paused:
            return
        # 1 мс между тиками — фактически без задержки; регулируется реальным FPS камеры
        self.root.after(1, self._process_video_loop)

    def _process_video_loop(self) -> None:
        if not self.is_running or self.is_paused:
            return

        cam: Camera = self.components["camera"]
        det: ObjectDetector = self.components["detector"]
        lcd: LineCrossingDetector = self.components["line_detector"]
        vio: ViolationManager = self.components["violation_manager"]
        snd: SoundPlayer = self.components["sound_player"]

        # Чтение кадра
        ret, frame = cam.read()
        if not ret or frame is None:
            self.logger.error("Не удалось получить кадр с камеры")
            self.stop_detection()
            return

        t0 = time.time()

        # Обнаружение объектов (считаем людей/лестницы и пр.)
        try:
            detections = det.detect(frame)  # ожидаем список с bbox/label/score
        except Exception as e:
            self.logger.error(f"Ошибка детекции: {e}")
            detections = []

        # Проверка пересечения линии (если актуально для ваших задач)
        try:
            crossed = lcd.check_crossing(detections)  # булево/данные пересечения
        except Exception:
            crossed = False

        # Если есть нарушение — сохраняем, подаём звук
        if crossed:
            try:
                record = vio.save_violation(frame, {"detections": detections})
                if getattr(config, "SOUND_ENABLED", True):
                    snd.play()
                if hasattr(self, "gui"):
                    self.gui.update_status(message=f"Нарушение сохранено: {record.get('filename','')}")
            except Exception as e:
                self.logger.error(f"Ошибка обработки нарушения: {e}")

        # Отображение предпросмотра (по желанию)
        if getattr(config, "USE_CAMERA_PREVIEW", True):
            try:
                cv2.imshow("Preview", frame)
                # корректная обработка закрытия окна
                if cv2.waitKey(1) & 0xFF == 27:  # ESC
                    self.stop_detection()
                    return
            except Exception as e:
                self.logger.error(f"Ошибка предпросмотра: {e}")

        # Обновление статистики
        proc_dt = max(time.time() - t0, 1e-6)
        self.proc_fps_counter.update_with_delta(proc_dt)
        gui_fps = self.fps_counter.update()

        try:
            if hasattr(self, "gui"):
                self.gui.update_fps(gui_fps)
                # если у ViolationManager есть get_stats() с количеством — обновим
                if hasattr(vio, "get_stats"):
                    stats = vio.get_stats()
                    if isinstance(stats, dict) and "count" in stats:
                        self.gui.update_counter(int(stats["count"]))
        except Exception as e:
            self.logger.error(f"Ошибка обновления GUI: {e}")

        # Следующий кадр
        self._schedule_next_frame()

    def cleanup(self) -> None:
        """Освобождение ресурсов и финальный отчёт."""
        try:
            if "camera" in self.components and self.components["camera"]:
                self.components["camera"].stop()
        except Exception:
            pass

        try:
            if getattr(config, "USE_CAMERA_PREVIEW", True):
                cv2.destroyAllWindows()
        except Exception:
            pass

        # Отчёт по нарушениям, если умеет
        try:
            vio: ViolationManager = self.components.get("violation_manager")
            if vio and hasattr(vio, "generate_report"):
                report_path, total = vio.generate_report()
                self.logger.info(f"Сгенерирован отчет о нарушениях: {total} нарушений")
            elif vio and hasattr(vio, "get_stats"):
                total = vio.get_stats().get("count", 0)
                self.logger.info(f"Сгенерирован отчет о нарушениях: {total} нарушений")
        except Exception:
            pass

        self.logger.info("Ресурсы освобождены")

    def run(self) -> None:
        """Запуск главного цикла Tkinter."""
        self.logger.info("Запуск приложения...")
        # Если GUI не был создан (например, камера не поднялась) — выходим мягко
        if not hasattr(self, "gui") or self.gui is None:
            self.logger.error("GUI не создан — выход")
            return

        # Сообщение в GUI
        try:
            self.gui.update_status(message="Система готова к работе")
        except Exception:
            pass

        # Автозапуск детекции, если источник не «живая» веб-камера
        try:
            if isinstance(config.VIDEO_SOURCE, str) and config.VIDEO_SOURCE:
                self.start_detection()
        except Exception:
            pass

        # Главный цикл
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"Ошибка главного цикла: {e}")
            self.cleanup()

    def _on_close(self):
        """Событие закрытия окна."""
        try:
            self.stop_detection()
        except Exception:
            pass
        self.cleanup()
        try:
            self.root.destroy()
        except Exception:
            pass

def main():
    setup_logging()
    logger = logging.getLogger("src")
    logger.info("Логирование инициализировано для пакета src")

    root = tk.Tk()
    app = MainApplication(root)
    app.run()


if __name__ == "__main__":
    main()
