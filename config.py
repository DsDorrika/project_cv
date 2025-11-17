import os
from pathlib import Path

# Базовые пути
BASE_DIR = Path(__file__).parent.absolute()
MODELS_DIR = BASE_DIR / "models"
SOUNDS_DIR = BASE_DIR / "sounds"
VIOLATIONS_DIR = BASE_DIR / "violations"

# 1. Параметры видеопотока
VIDEO_SOURCE = 0  # 0 для веб-камеры, или 'path/to/video.mp4'
CAMERA_RESOLUTION = (1280, 720)  # Разрешение камеры (ширина, высота)
CAMERA_FPS = 30  # Желаемый FPS
USE_CAMERA_PREVIEW = True  # Показывать превью камеры

# 2. Параметры линии пересечения (x1, y1, x2, y2)
# Координаты линии по умолчанию для разрешения 1280x720
CROSSING_LINE_COORDS = (320, 360, 960, 360)  # Горизонтальная линия по центру
LINE_COLOR = (0, 0, 255)  # Цвет линии (BGR)
LINE_THICKNESS = 3  # Толщина линии в пикселях

# 3. Параметры детектора объектов
# MobileNet-SSD (быстрая модель для CPU)
MODEL_NAME = "MobileNetSSD_deploy.caffemodel"
CONFIG_NAME = "MobileNetSSD_deploy.prototxt"
DETECTOR_MODEL_PATH = str(MODELS_DIR / MODEL_NAME)
DETECTOR_CONFIG_PATH = str(MODELS_DIR / CONFIG_NAME)
DETECTOR_CONFIDENCE_THRESHOLD = 0.5  # Порог уверенности детекции
TARGET_CLASS_ID = 15  # ID для 'person' в MobileNet-SSD

# Альтернативные модели (раскомментировать при необходимости)
# YOLO (точнее но медленнее)
# MODEL_NAME = "yolov4-tiny.weights"
# CONFIG_NAME = "yolov4-tiny.cfg"
# DETECTOR_MODEL_PATH = str(MODELS_DIR / MODEL_NAME)
# DETECTOR_CONFIG_PATH = str(MODELS_DIR / CONFIG_NAME)
# TARGET_CLASS_ID = 0  # ID для 'person' в YOLO

# 4. Параметры звука
SOUND_FILE = str(SOUNDS_DIR / "beep.mp3")
SOUND_ENABLED = True  # Включить/выключить звуковые оповещения
SOUND_VOLUME = 0.7  # Громкость звука (0.0 - 1.0)

# 5. Параметры сохранения нарушений
VIOLATIONS_DIR = str(VIOLATIONS_DIR)
SAVE_VIOLATION_IMAGES = True  # Сохранять изображения нарушений
SAVE_VIOLATION_METADATA = True  # Сохранять метаданные нарушений
MAX_VIOLATION_AGE_DAYS = 30  # Автоочистка файлов старше N дней

# 6. Параметры детектора пересечения линии
TRACKING_MAX_DISTANCE = 70  # Максимальное расстояние для трекинга объектов
MAX_FRAMES_LOST = 10  # Максимальное количество кадров без обнаружения
MIN_CONFIDENCE_FOR_TRACKING = 0.3  # Минимальная уверенность для трекинга

# 7. Параметры GUI
GUI_UPDATE_INTERVAL = 100  # Интервал обновления GUI в мс
SHOW_FPS = True  # Показывать FPS в интерфейсе
SHOW_DETECTIONS = True  # Показывать bounding boxes
SHOW_TRACKING_INFO = True  # Показывать ID и информацию трекинга

# 8. Параметры производительности
PROCESS_EVERY_N_FRAME = 1  # Обрабатывать каждый N-й кадр (для увеличения FPS)
RESIZE_FRAME_FOR_PROCESSING = None  # (width, height) или None для оригинального размера
USE_GPU = False  # Использовать GPU для детекции (требует OpenCV с поддержкой CUDA)

# 9. Параметры логирования
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_TO_FILE = True  # Сохранять логи в файл
LOG_FILE = "cv_project.log"  # Имя файла логов

# 10. Параметры отладки
DEBUG_MODE = False  # Режим отладки (дополнительная информация)
SAVE_DEBUG_IMAGES = False  # Сохранять отладочные изображения
PRINT_DETECTION_STATS = False  # Выводить статистику детекции


def validate_config():
    """Проверка корректности конфигурации"""
    errors = []
    warnings = []

    # Проверка существования моделей
    if not os.path.exists(DETECTOR_MODEL_PATH):
        errors.append(f"Файл модели не найден: {DETECTOR_MODEL_PATH}")
    
    if not os.path.exists(DETECTOR_CONFIG_PATH):
        errors.append(f"Файл конфигурации модели не найден: {DETECTOR_CONFIG_PATH}")
    
    # Проверка звукового файла
    if SOUND_ENABLED and not os.path.exists(SOUND_FILE):
        warnings.append(f"Звуковой файл не найден: {SOUND_FILE}. Будет использована заглушка.")
    
    # Проверка и создание директорий
    directories_to_check = [
        str(MODELS_DIR),
        str(SOUNDS_DIR), 
        str(VIOLATIONS_DIR)
    ]
    
    for directory in directories_to_check:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            warnings.append(f"Создана директория: {directory}")
    
    # Проверка координат линии
    x1, y1, x2, y2 = CROSSING_LINE_COORDS
    if x1 == x2 and y1 == y2:
        errors.append("Координаты линии не могут быть одинаковыми")
    
    # Проверка параметров производительности
    if PROCESS_EVERY_N_FRAME < 1:
        errors.append("PROCESS_EVERY_N_FRAME должен быть >= 1")
    
    if SOUND_VOLUME < 0 or SOUND_VOLUME > 1:
        errors.append("SOUND_VOLUME должен быть в диапазоне 0.0 - 1.0")
    
    return errors, warnings


# Автоматическая проверка при импорте
config_errors, config_warnings = validate_config()

if config_warnings:
    print("Предупреждения конфигурации:")
    for warning in config_warnings:
        print(f"  ⚠ {warning}")

if config_errors:
    print("Ошибки конфигурации:")
    for error in config_errors:
        print(f"  ❌ {error}")
    print("\nПожалуйста, исправьте ошибки перед запуском приложения.")