import cv2
import time
import tkinter as tk
import logging
import sys
import os
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
from src.yolo_detector import YOLODetector
from src.settings_manager import load_user_settings, save_user_settings


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
        # Временная метка последнего автоматического нарушения (для режима 1 нарушение/сек)
        self.last_violation_ts = 0.0
        
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

    def _ensure_yolo_dependency(self):
        """Попытка установить ultralytics автоматически, если нужно."""
        try:
            import importlib
            spec = importlib.util.find_spec('ultralytics')
            if spec is None:
                self.logger.info('Пакет ultralytics не найден. Попытка установить через pip...')
                # Устанавливаем пакет
                import subprocess
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'ultralytics'])
                self.logger.info('ultralytics установлен.')
        except Exception as e:
            self.logger.error(f'Не удалось установить ultralytics автоматически: {e}')

    def _download_yolo_model(self, dest_path: str) -> bool:
        """Скачать yolov8n.pt в папку models/ (streaming download).
        Возвращает True если успешно.
        """
        url = 'https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt'
        try:
            import requests
        except Exception:
            try:
                import subprocess
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests'])
                import requests
            except Exception as e:
                self.logger.error(f"Не удалось установить requests для загрузки модели: {e}")
                return False

        try:
            self.logger.info(f"Скачивание модели YOLOv8n из {url} -> {dest_path}")
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            self.logger.info('Модель скачана успешно')
            return True
        except Exception as e:
            self.logger.error(f'Ошибка скачивания модели YOLO: {e}')
            return False

    def _ensure_yolo_model(self):
        """Гарантирует, что файл модели YOLO присутствует в папке models/."""
        try:
            model_path = getattr(config, 'YOLO_MODEL', None)
            if not model_path:
                model_path = str(Path(ROOT_DIR) / 'models' / 'yolov8n.pt')
            # Если уже существует — ok
            if os.path.exists(model_path):
                self.logger.info(f'YOLO модель найдена: {model_path}')
                return True

            # Попытка скачать в папку models
            local_path = os.path.join(str(Path(__file__).parent.parent), 'models', 'yolov8n.pt')
            success = self._download_yolo_model(local_path)
            if success:
                # Обновим config.YOLO_MODEL чтобы указывать на локальный файл
                try:
                    config.YOLO_MODEL = local_path
                except Exception:
                    pass
                return True
            else:
                self.logger.warning('Не удалось скачать YOLO модель автоматически')
                return False
        except Exception as e:
            self.logger.error(f'Ошибка при проверке/скачивании модели YOLO: {e}')
            return False

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
            try:
                # Используем только YOLO, отключаем MobileNet-SSD
                if getattr(config, 'USE_YOLO', False):
                    # Убедиться, что ultralytics доступен
                    try:
                        from ultralytics import YOLO  # noqa: F401
                    except Exception:
                        self._ensure_yolo_dependency()

                    # Убедиться, что модель скачана
                    yolo_ready = self._ensure_yolo_model()
                    if not yolo_ready:
                        self.logger.error('YOLO модель отсутствует и не может быть загружена. Прекращаем инициализацию.')
                        return {}

                    # Инициализация YOLODetector
                    try:
                        components['detector'] = YOLODetector(model_path=getattr(config, 'YOLO_MODEL', None))
                    except Exception as e:
                        self.logger.error(f'Ошибка инициализации YOLODetector: {e}')
                        return {}
                else:
                    self.logger.error('Конфигурация требует использование только YOLO. Установите USE_YOLO=True в config.py')
                    return {}

                # Для YOLODetector проверяем наличие объекта
                if components.get('detector') is None:
                    self.logger.error('Не удалось инициализировать детектор')
                    return {}
            except Exception as e:
                self.logger.error(f"Не удалось загрузить модель детектора: {e}")
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
            # Подключаем колбэки для загрузки и применения настроек
            gui.load_settings_callback = self._load_settings
            gui.apply_settings_callback = self._apply_settings
            gui.get_camera_info_callback = (lambda: self.components.get('camera').get_info() if self.components.get('camera') else {})
            # передаём начальные значения для окна настроек
            user_settings = load_user_settings()
            gui.initial_region_mode = bool(user_settings.get('mode') == 'region' or getattr(config, 'VIOLATION_REGION_COORDS', None))
            # Callback for interactive selection on camera
            gui.camera_select_callback = lambda mode: self._camera_select_interactive(mode)
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

            if config.DEBUG_MODE:
                try:
                    self.logger.debug(f"Detections count: {len(detections)}")
                    for i, d in enumerate(detections):
                        self.logger.debug(f"Det[{i}]: cls={d.get('class_name')}/{d.get('class_id')} conf={d.get('confidence'):.3f} box={d.get('box')}")
                except Exception:
                    pass

            # Выбираем кадр, на котором будет отрисована визуализация линии и трекинга.
            draw_frame = frame if not config.RESIZE_FRAME_FOR_PROCESSING else processing_frame

            # Детекция пересечения линии / области (визуализация будет нанесена на draw_frame)
            violations = self.components['line_detector'].process_detections(draw_frame, detections)

            if config.DEBUG_MODE:
                self.logger.debug(f"Line detector returned violations: {len(violations)}")

            # Временное правило: одно автоматическое нарушение в секунду, если обнаружен человек в зоне нарушения
            try:
                now_auto = time.time()
                person_in_zone = False
                person_box = None
                person_det = None
                zone = getattr(config, 'VIOLATION_REGION_COORDS', None)
                for det in detections:
                    if det.get('class_id') != config.TARGET_CLASS_ID:
                        continue
                    bx1, by1, bx2, by2 = det['box']
                    bottom = det['bottom_center']
                    if zone:
                        zx1, zy1, zx2, zy2 = zone
                        if zx1 <= bottom[0] <= zx2 and zy1 <= bottom[1] <= zy2:
                            person_in_zone = True
                            person_box = det['box']
                            person_det = det
                            break
                    else:
                        # fallback: проверка близости к линии по Y с допуском
                        lx1, ly1, lx2, ly2 = config.CROSSING_LINE_COORDS
                        line_y = (ly1 + ly2) / 2
                        tol = getattr(config, 'REGION_ENTRY_TOLERANCE_PX', 30)
                        if abs(bottom[1] - line_y) <= tol:
                            person_in_zone = True
                            person_box = det['box']
                            person_det = det
                            break

                if config.DEBUG_MODE:
                    self.logger.debug(f"person_in_zone={person_in_zone}, last_violation_ts={self.last_violation_ts}")

                if person_in_zone and (now_auto - self.last_violation_ts) >= 1.0:
                    # Создаём автоматическое нарушение — звук и сохранение произойдет через _handle_violations
                    auto_violation = {
                        'id': f"auto_{int(now_auto*1000)}",
                        'box': person_box,
                        'direction': 'AUTO_REGION',
                        'timestamp': now_auto,
                        'confidence': person_det.get('confidence', 0.0) if person_det else 0.0,
                        'class_id': person_det.get('class_id') if person_det else None,
                        'class_name': person_det.get('class_name', 'person') if person_det else 'person'
                    }
                    violations.append(auto_violation)
                    self.last_violation_ts = now_auto
                    if config.DEBUG_MODE:
                        self.logger.debug(f"Auto violation generated: {auto_violation}")
            except Exception as e:
                self.logger.error(f"Ошибка в временной логике автоматических нарушений: {e}")

            # Обработка нарушений
            if violations:
                if config.DEBUG_MODE:
                    self.logger.debug(f"Calling _handle_violations with {len(violations)} violations")
                self._handle_violations(frame, violations)

            # Отрисовка детекций на оригинальном кадре (если используются совпадающие координаты)
            if config.SHOW_DETECTIONS:
                target_draw_frame = frame if not config.RESIZE_FRAME_FOR_PROCESSING else processing_frame
                self.components['detector'].draw_detections(target_draw_frame, detections)

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
    
    def _load_settings(self):
        """Return current settings (for GUI to populate fields)"""
        try:
            # merge config and user settings
            user = load_user_settings()
            settings = {}
            settings['mode'] = user.get('mode') or ('region' if getattr(config, 'VIOLATION_REGION_COORDS', None) else 'line')
            settings['coords'] = user.get('coords') or (getattr(config, 'VIOLATION_REGION_COORDS', None) or getattr(config, 'CROSSING_LINE_COORDS', None))
            settings['tolerance'] = user.get('tolerance', getattr(config, 'REGION_ENTRY_TOLERANCE_PX', None))
            settings['region_min_stay'] = user.get('region_min_stay', getattr(config, 'REGION_MIN_STAY_SECONDS', None))
            return settings
        except Exception as e:
            self.logger.error(f"Error loading settings for GUI: {e}")
            return {}

    def _apply_settings(self, settings: dict):
        """Apply settings live and persist them to disk.

        settings: {'mode': 'line'|'region', 'coords': (x1,y1,x2,y2), 'tolerance': int, 'region_min_stay': float}
        """
        try:
            # Persist
            existing = load_user_settings()
            existing.update(settings)
            save_user_settings(existing)

            # Apply to config and detector
            mode = settings.get('mode')
            coords = settings.get('coords')
            tol = settings.get('tolerance')
            minstay = settings.get('region_min_stay')

            if mode == 'region':
                config.VIOLATION_REGION_COORDS = tuple(coords)
                config.CROSSING_LINE_COORDS = getattr(config, 'CROSSING_LINE_COORDS', config.CROSSING_LINE_COORDS)
            else:
                config.VIOLATION_REGION_COORDS = None
                config.CROSSING_LINE_COORDS = tuple(coords)

            if tol is not None:
                config.REGION_ENTRY_TOLERANCE_PX = int(tol)
                config.LINE_TOLERANCE_PX = int(tol)
            if minstay is not None:
                config.REGION_MIN_STAY_SECONDS = float(minstay)

            # Update detector instance
            ld = self.components.get('line_detector')
            if ld:
                ld.region_coords = getattr(config, 'VIOLATION_REGION_COORDS', None)
                ld.region_mode = bool(ld.region_coords)
                ld.line_coords = getattr(config, 'CROSSING_LINE_COORDS', None)
                ld.A, ld.B, ld.C = ld._calculate_line_params()
                ld.region_tolerance = getattr(config, 'REGION_ENTRY_TOLERANCE_PX', ld.region_tolerance)
                ld.region_min_stay = getattr(config, 'REGION_MIN_STAY_SECONDS', ld.region_min_stay)

            # Обновление GUI статуса
            if hasattr(self, 'gui'):
                self.gui.update_status("Настройки применены")
                # Also update initial_region_mode for next opening
                self.gui.initial_region_mode = ld.region_mode if ld else False

            self.logger.info(f"Настройки применены: {settings}")
        except Exception as e:
            self.logger.error(f"Ошибка применения настроек: {e}")

    def _camera_select_interactive(self, mode: Optional[str]) -> Optional[tuple]:
        """Interactive selection on live camera preview.

        mode: 'line' or 'region' (if None treated as 'region')
        Returns tuple(coords) or None if cancelled.
        """
        try:
            cam = self.components.get('camera')
            if not cam or not cam.is_running:
                self.logger.error("Камера недоступна для интерактивного выбора")
                return None

            win_name = 'Select Region - press s to save, c to cancel'
            cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)

            state = {'start': None, 'end': None, 'dragging': False, 'final': False}

            def _on_mouse(event, x, y, flags, param):
                if event == cv2.EVENT_LBUTTONDOWN:
                    state['start'] = (x, y)
                    state['end'] = (x, y)
                    state['dragging'] = True
                elif event == cv2.EVENT_MOUSEMOVE and state['dragging']:
                    state['end'] = (x, y)
                elif event == cv2.EVENT_LBUTTONUP and state['dragging']:
                    state['end'] = (x, y)
                    state['dragging'] = False
                    state['final'] = True

            cv2.setMouseCallback(win_name, _on_mouse)

            selected = None
            mode = (mode or 'region')

            while True:
                ret, frame = cam.read()
                if not ret:
                    self.logger.error('Не удалось получить кадр для интерактивного выбора')
                    break

                vis = frame.copy()
                # draw current selection
                if state['start'] and state['end']:
                    x1, y1 = state['start']
                    x2, y2 = state['end']
                    if mode == 'line':
                        cv2.line(vis, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        cv2.circle(vis, (x1, y1), 5, (0, 255, 0), -1)
                        cv2.circle(vis, (x2, y2), 5, (0, 255, 0), -1)
                    else:
                        # draw rectangle
                        rx1, rx2 = sorted((x1, x2))
                        ry1, ry2 = sorted((y1, y2))
                        cv2.rectangle(vis, (rx1, ry1), (rx2, ry2), (0, 0, 255), 2)

                # instructions
                cv2.putText(vis, "Left-drag to select. Press 's' to save, 'c' to cancel.", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

                cv2.imshow(win_name, vis)
                key = cv2.waitKey(20) & 0xFF
                if key == ord('c') or key == 27:
                    selected = None
                    break
                if key == ord('s') or state['final']:
                    if state['start'] and state['end']:
                        x1, y1 = state['start']
                        x2, y2 = state['end']
                        if mode == 'line':
                            selected = (int(x1), int(y1), int(x2), int(y2))
                        else:
                            rx1, rx2 = sorted((int(x1), int(x2)))
                            ry1, ry2 = sorted((int(y1), int(y2)))
                            selected = (rx1, ry1, rx2, ry2)
                        break

            cv2.destroyWindow(win_name)
            return selected

        except Exception as e:
            self.logger.error(f"Ошибка интерактивного выбора: {e}")
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass
            return None

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