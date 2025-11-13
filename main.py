import cv2
import time
import tkinter as tk
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Добавление корневой директории в путь для импортов
ROOT_DIR = Path(__file__).parent.absolute()
sys.path.append(str(ROOT_DIR))

# Импорт конфигурации и модулей
import config
from src.camera import Camera
from src.object_detector import ObjectDetector
from src.line_crossing_detector import LineCrossingDetector
from src.sound_player import SoundPlayer, get_sound_player
from src.violation_manager import ViolationManager
from src.gui import ApplicationGUI
from src.utils import FPSCounter, resize_frame, draw_text_with_background


class MainApplication:
    """Главный класс приложения, управляющий всеми компонентами системы"""
    
    def __init__(self, root: tk.Tk):
        """
        Инициализация главного приложения
        
        Args:
            root: корневое окно Tkinter
        """
        self.root = root
        self.logger = self._setup_logging()
        
        # Флаги состояния
        self.is_running = False
        self.is_paused = False
        self.video_processing = True
        
        # Статистика
        self.total_violations = 0
        self.frame_count = 0
        self.processing_stats: Dict[str, Any] = {}
        
        # Инициализация компонентов
        self.components = self._initialize_components()
        
        if not self.components:
            self.logger.error("Не удалось инициализировать компоненты приложения")
            self.root.quit()
            return
        
        # Инициализация GUI
        self.gui = self._initialize_gui()
        
        # Инициализация счетчиков
        self.fps_counter = FPSCounter()
        self.processing_fps_counter = FPSCounter()
        
        self.logger.info("Приложение инициализировано успешно")

    def _setup_logging(self) -> logging.Logger:
        """Настройка системы логирования"""
        logger = logging.getLogger("MainApplication")
        
        if not logger.handlers:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            # File handler
            if config.LOG_TO_FILE:
                try:
                    file_handler = logging.FileHandler(config.LOG_FILE, encoding='utf-8')
                    file_handler.setFormatter(formatter)
                    logger.addHandler(file_handler)
                except Exception as e:
                    print(f"Не удалось настроить файловый логгер: {e}")
            
            logger.setLevel(getattr(logging, config.LOG_LEVEL))
        
        return logger

    def _initialize_components(self) -> Dict[str, Any]:
        """Инициализация всех компонентов системы"""
        components = {}
        
        try:
            # Камера
            self.logger.info("Инициализация камеры...")
            components['camera'] = Camera(config.VIDEO_SOURCE)
            
            if not components['camera'].is_running:
                self.logger.error("Не удалось инициализировать камеру")
                return {}
            
            # Детектор объектов
            self.logger.info("Инициализация детектора объектов...")
            components['detector'] = ObjectDetector()
            
            if components['detector'].net is None:
                self.logger.error("Не удалось загрузить модель детектора")
                return {}
            
            # Детектор пересечения линии
            self.logger.info("Инициализация детектора пересечения линии...")
            components['line_detector'] = LineCrossingDetector(config.CROSSING_LINE_COORDS)
            
            # Проигрыватель звуков
            self.logger.info("Инициализация звуковой системы...")
            components['sound_player'] = get_sound_player()
            
            # Менеджер нарушений
            self.logger.info("Инициализация менеджера нарушений...")
            components['violation_manager'] = ViolationManager()
            
            self.logger.info("Все компоненты успешно инициализированы")
            return components
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {e}")
            return {}

    def _initialize_gui(self) -> ApplicationGUI:
        """Инициализация графического интерфейса"""
        try:
            gui = ApplicationGUI(
                root=self.root,
                sound_player_callback=self._on_test_sound,
                start_detection_callback=self.start_detection,
                stop_detection_callback=self.stop_detection,
            )
            self.logger.info("GUI инициализирован")
            return gui
        except Exception as e:
            self.logger.error(f"Ошибка инициализации GUI: {e}")
            raise

    def _on_test_sound(self):
        """Обработчик теста звука"""
        try:
            self.components['sound_player'].test_sound()
        except Exception as e:
            self.logger.error(f"Ошибка тестирования звука: {e}")

    def start_detection(self):
        """Запуск системы детекции"""
        if self.is_running:
            self.logger.warning("Детекция уже запущена")
            return
        
        self.is_running = True
        self.is_paused = False
        self.video_processing = True
        
        self.logger.info("Запуск системы детекции...")
        self.gui.update_status("Детекция запущена")
        
        # Запуск основного цикла обработки
        self._process_video_loop()

    def stop_detection(self):
        """Остановка системы детекции"""
        self.is_running = False
        self.video_processing = False
        
        self.logger.info("Остановка системы детекции...")
        self.gui.update_status("Детекция остановлена")
        
        # Обновление статистики перед остановкой
        self._update_gui_stats()

    def toggle_pause(self):
        """Переключение режима паузы"""
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.logger.info("Система приостановлена")
            self.gui.update_status("Система на паузе")
        else:
            self.logger.info("Система возобновлена")
            self.gui.update_status("Детекция запущена")

    def _process_video_loop(self):
        """Основной цикл обработки видео"""
        if not self.is_running or not self.video_processing:
            return
        
        try:
            start_time = time.time()
            
            # Чтение кадра
            ret, frame = self.components['camera'].read()
            
            if not ret:
                self.logger.error("Не удалось получить кадр с камеры")
                self.stop_detection()
                return
            
            # Пропуск кадров для увеличения производительности
            self.frame_count += 1
            if self.frame_count % config.PROCESS_EVERY_N_FRAME != 0 and not config.DEBUG_MODE:
                # Планирование следующего кадра
                self.root.after(1, self._process_video_loop)
                return
            
            # Обработка кадра (если не на паузе)
            processed_frame = self._process_frame(frame) if not self.is_paused else frame
            
            # Отображение кадра
            if config.USE_CAMERA_PREVIEW:
                self._display_frame(processed_frame)
            
            # Обновление статистики
            processing_time = time.time() - start_time
            self._update_processing_stats(processing_time)
            
            # Обновление GUI
            self._update_gui_stats()
            
            # Планирование следующего кадра
            if self.is_running and self.video_processing:
                delay = max(1, int((1 / config.CAMERA_FPS) * 1000))
                self.root.after(delay, self._process_video_loop)
                
        except Exception as e:
            self.logger.error(f"Ошибка в основном цикле обработки: {e}")
            self.stop_detection()

    def _process_frame(self, frame):
        """Обработка одного кадра"""
        try:
            # Изменение размера для обработки (если нужно)
            if config.RESIZE_FRAME_FOR_PROCESSING:
                processing_frame = resize_frame(
                    frame, 
                    config.RESIZE_FRAME_FOR_PROCESSING[0], 
                    config.RESIZE_FRAME_FOR_PROCESSING[1]
                )
            else:
                processing_frame = frame.copy()
            
            # Детекция объектов
            detections = self.components['detector'].detect(processing_frame)
            
            # Обновление счетчика FPS обработки
            self.processing_fps_counter.update()
            
            # Детекция пересечения линии
            violations = self.components['line_detector'].process_detections(
                processing_frame, detections
            )
            
            # Обработка нарушений
            if violations:
                self._handle_violations(frame, violations)
            
            # Отрисовка детекций на оригинальном кадре
            if config.SHOW_DETECTIONS:
                self.components['detector'].draw_detections(frame, detections)
            
            # Добавление информации на кадр
            if config.DEBUG_MODE or config.SHOW_FPS:
                self._annotate_frame(frame)
            
            return frame
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки кадра: {e}")
            return frame

    def _handle_violations(self, frame, violations):
        """Обработка обнаруженных нарушений"""
        for violation in violations:
            self.total_violations += 1
            
            # Воспроизведение звука
            if config.SOUND_ENABLED:
                self.components['sound_player'].play_beep()
            
            # Сохранение нарушения
            if config.SAVE_VIOLATION_IMAGES:
                self.components['violation_manager'].save_violation(frame.copy(), violation)
            
            self.logger.info(
                f"Обнаружено нарушение #{self.total_violations}: "
                f"ID {violation.get('id')}, направление {violation.get('direction')}"
            )

    def _display_frame(self, frame):
        """Отображение кадра в окне OpenCV"""
        try:
            # Изменение размера для отображения (опционально)
            display_frame = resize_frame(frame, 1024, 768)
            
            cv2.imshow("Система детекции пересечения линии", display_frame)
            
            # Обработка клавиш
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # 'q' или ESC
                self.stop_detection()
            elif key == ord('p'):  # Пауза
                self.toggle_pause()
            elif key == ord('r'):  # Сброс статистики
                self._reset_stats()
            elif key == ord('s'):  # Сохранение кадра
                self._save_current_frame(frame)
                
        except Exception as e:
            self.logger.error(f"Ошибка отображения кадра: {e}")

    def _annotate_frame(self, frame):
        """Добавление аннотаций на кадр"""
        try:
            # FPS
            fps = self.fps_counter.get_global_fps()
            processing_fps = self.processing_fps_counter.get_global_fps()
            
            # Статистика
            stats_text = [
                f"FPS: {fps:.1f}",
                f"Processing FPS: {processing_fps:.1f}",
                f"Violations: {self.total_violations}",
                f"Objects: {len(self.components['line_detector'].tracked_objects)}",
                f"Status: {'PAUSED' if self.is_paused else 'RUNNING'}"
            ]
            
            # Отрисовка статистики
            for i, text in enumerate(stats_text):
                y_position = 30 + i * 25
                draw_text_with_background(
                    frame, text, (10, y_position),
                    font_scale=0.6, thickness=2,
                    text_color=(255, 255, 255),
                    bg_color=(0, 0, 0)
                )
                
        except Exception as e:
            self.logger.error(f"Ошибка аннотирования кадра: {e}")

    def _update_processing_stats(self, processing_time: float):
        """Обновление статистики обработки"""
        self.fps_counter.update()
        
        self.processing_stats = {
            'frame_count': self.frame_count,
            'total_fps': self.fps_counter.get_global_fps(),
            'processing_fps': self.processing_fps_counter.get_global_fps(),
            'last_processing_time': processing_time,
            'violations_count': self.total_violations,
            'tracked_objects': len(self.components['line_detector'].tracked_objects)
        }

    def _update_gui_stats(self):
        """Обновление статистики в GUI"""
        try:
            if hasattr(self, 'gui'):
                self.gui.update_counter(self.total_violations)
                self.gui.update_fps(self.processing_stats.get('total_fps', 0))
                
                # Дополнительная информация для GUI
                additional_info = {
                    'processing_fps': self.processing_stats.get('processing_fps', 0),
                    'tracked_objects': self.processing_stats.get('tracked_objects', 0),
                    'status': 'PAUSED' if self.is_paused else 'RUNNING'
                }
                
                if hasattr(self.gui, 'update_additional_info'):
                    self.gui.update_additional_info(additional_info)
                    
        except Exception as e:
            self.logger.error(f"Ошибка обновления GUI: {e}")

    def _reset_stats(self):
        """Сброс статистики"""
        self.total_violations = 0
        self.frame_count = 0
        self.fps_counter = FPSCounter()
        self.processing_fps_counter = FPSCounter()
        self.components['line_detector'].reset_stats()
        
        self.logger.info("Статистика сброшена")

    def _save_current_frame(self, frame):
        """Сохранение текущего кадра"""
        try:
            from src.utils import get_timestamp_filename
            filename = f"debug_{get_timestamp_filename()}.jpg"
            filepath = Path(config.VIOLATIONS_DIR) / filename
            
            success = cv2.imwrite(str(filepath), frame)
            if success:
                self.logger.info(f"Кадр сохранен: {filepath}")
            else:
                self.logger.error(f"Не удалось сохранить кадр: {filepath}")
                
        except Exception as e:
            self.logger.error(f"Ошибка сохранения кадра: {e}")

    def cleanup(self):
        """Очистка ресурсов при завершении работы"""
        self.logger.info("Завершение работы приложения...")
        
        self.is_running = False
        self.video_processing = False
        
        try:
            # Освобождение ресурсов камеры
            if 'camera' in self.components:
                self.components['camera'].release()
            
            # Закрытие окон OpenCV
            cv2.destroyAllWindows()
            
            # Генерация отчета о нарушениях
            if 'violation_manager' in self.components:
                report = self.components['violation_manager'].generate_report()
                self.logger.info(f"Сгенерирован отчет о нарушениях: {report.get('total_violations', 0)} нарушений")
            
            self.logger.info("Ресурсы освобождены")
            
        except Exception as e:
            self.logger.error(f"Ошибка при очистке ресурсов: {e}")

    def run(self):
        """Запуск приложения"""
        try:
            self.logger.info("Запуск приложения...")
            self.gui.update_status("Система готова к работе")
            
            # Автоматический запуск детекции
            if config.VIDEO_SOURCE != 0:  # Если это не веб-камера, запускаем автоматически
                self.start_detection()
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска приложения: {e}")
            self.cleanup()


def main():
    """Главная функция приложения"""
    try:
        # Проверка конфигурации
        errors, warnings = config.validate_config()
        if errors:
            print("❌ Обнаружены ошибки в конфигурации:")
            for error in errors:
                print(f"   - {error}")
            print("\nПожалуйста, исправьте ошибки и перезапустите приложение.")
            return 1
        
        if warnings:
            print("⚠ Предупреждения конфигурации:")
            for warning in warnings:
                print(f"   - {warning}")
            print()
        
        # Создание и запуск приложения
        root = tk.Tk()
        app = MainApplication(root)
        
        # Обработка закрытия окна
        def on_closing():
            app.cleanup()
            root.destroy()
            print("Приложение завершено.")
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Запуск приложения
        app.run()
        
        # Запуск главного цикла Tkinter
        root.mainloop()
        
        return 0
        
    except KeyboardInterrupt:
        print("\nПриложение прервано пользователем")
        return 130
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)