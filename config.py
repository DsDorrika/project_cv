from pathlib import Path
import os

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

# Альтернативно — можно задать область (прямоугольник) нарушения:
# (x1, y1, x2, y2) — левый верхний и правый нижний углы
VIOLATION_REGION_COORDS = (300, 320, 980, 420)  # Пример области для тестирования (для 1280x720)
# Радиус/порог в пикселях для близости к линии/границе
REGION_ENTRY_TOLERANCE_PX = 10

# Параметры для тестирования/отладки
REGION_MIN_STAY_SECONDS = 0.5  # Меньше значение для быстрого тестирования
MIN_VIOLATION_INTERVAL_SECONDS = 5  # Уменьшённый интервал для тестирования

# 3. Параметры детектора объектов
# NOTE: MobileNet-SSD отключена — используем только YOLOv8 (yolov8n.pt)
USE_YOLO = True  # Включить использование YOLO (ultralytics)
YOLO_MODEL = str(MODELS_DIR / "yolov8n.pt")  # Путь к модели YOLOv8

# Эти параметры оставлены для совместимости, но при USE_YOLO=True они не используются
MODEL_NAME = "MobileNetSSD_deploy.caffemodel"
CONFIG_NAME = "MobileNetSSD_deploy.prototxt"
DETECTOR_MODEL_PATH = str(MODELS_DIR / MODEL_NAME)
DETECTOR_CONFIG_PATH = str(MODELS_DIR / CONFIG_NAME)
DETECTOR_CONFIDENCE_THRESHOLD = 0.5  # Порог уверенности детекции
TARGET_CLASS_ID = 0  # Для YOLO: класс 'person' на COCO имеет id 0

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
TRACKING_MAX_DISTANCE = 120  # Максимальное расстояние для трекинга объектов
MAX_FRAMES_LOST = 10  # Максимальное количество кадров без обнаружения
MIN_VIOLATION_INTERVAL_SECONDS = 60  # Минимальный интервал между фиксациями нарушений одного объекта

# Параметры линии
LINE_TOLERANCE_PX = 8  # Порог для определения, что точка находится на линии (в пикселях)
ENFORCE_LINE_VIOLATION = True  # Если True, любое пересечение линии считается нарушением (без направления)

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
LOG_FILE = str(BASE_DIR / "cv_project.log")  # Имя файла логов

# 10. Параметры отладки
DEBUG_MODE = True  # Режим отладки (дополнительная информация)
SAVE_DEBUG_IMAGES = False  # Сохранять отладочные изображения
PRINT_DETECTION_STATS = True  # Выводить статистику детекции


def validate_config():
    """Проверка корректности конфигурации. Возвращает (errors, warnings)."""
    errors = []
    warnings = []

    # Проверка директорий — создаём их если нужно
    try:
        for d in [MODELS_DIR, SOUNDS_DIR, Path(VIOLATIONS_DIR)]:
            try:
                os.makedirs(str(d), exist_ok=True)
            except Exception as e:
                errors.append(f"Не удалось создать папку {d}: {e}")
    except Exception as e:
        errors.append(f"Ошибка при подготовке директорий: {e}")

    # Проверка модели YOLO
    if USE_YOLO:
        if not os.path.exists(YOLO_MODEL):
            warnings.append(f"YOLO модель не найдена по пути {YOLO_MODEL}. При запуске будет предпринята попытка скачать её автоматически.")
    else:
        # Если YOLO отключен — проверяем MobileNet файлы
        if not os.path.exists(DETECTOR_MODEL_PATH) or not os.path.exists(DETECTOR_CONFIG_PATH):
            warnings.append("MobileNet-SSD модели/конфиг не найдены. Включите USE_YOLO или добавьте файлы в models/.")

    # Проверка звукового файла
    if SOUND_ENABLED:
        if not os.path.exists(SOUND_FILE):
            warnings.append(f"Звуковой файл не найден: {SOUND_FILE}. Приложение будет работать без звука.")

    # Проверка параметров
    if PROCESS_EVERY_N_FRAME < 1:
        warnings.append("PROCESS_EVERY_N_FRAME должен быть >= 1. Используется значение 1.")

    if SOUND_VOLUME < 0 or SOUND_VOLUME > 1:
        warnings.append("SOUND_VOLUME должен быть в диапазоне [0.0, 1.0]. Будет использовано значение по умолчанию 0.7.")

    # Проверка линии
    x1, y1, x2, y2 = CROSSING_LINE_COORDS
    if x1 == x2 and y1 == y2:
        errors.append("Некорректные координаты CROSSING_LINE_COORDS: начальная и конечная точки совпадают")

    return errors, warnings


# Автоматическая проверка при импорте
# (не выполнять тяжёлые операции — возвращаем списки для main)


# Конец файла