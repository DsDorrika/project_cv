# config.py
from pathlib import Path

# === БАЗОВЫЕ ПУТИ ===
BASE_DIR = Path(__file__).parent.absolute()
MODELS_DIR = BASE_DIR / "models"
SOUNDS_DIR = BASE_DIR / "sounds"
VIOLATIONS_DIR = BASE_DIR / "violations"

# === ВИДЕО / КАМЕРА ===
VIDEO_SOURCE = 0                       # 0, 1, 2 — индекс камеры, или путь к файлу / rtsp
VIDEO_DEVICE_NAME = None               # можно указать строку, например "Integrated Camera"
CAMERA_BACKEND = "msmf"                # варианты: "msmf", "dshow", "cv2"
CAMERA_RESOLUTION = (1280, 720)
CAMERA_FPS = 30
CAMERA_WARMUP_FRAMES = 5
READ_RETRY_ON_FAIL = True
USE_CAMERA_PREVIEW = True              # показывать окно предпросмотра (cv2.imshow)

# === ДЕТЕКТОР (MobileNetSSD Caffe) ===
DETECTOR_MODEL_PATH = str(MODELS_DIR / "MobileNetSSD_deploy.caffemodel")
DETECTOR_CONFIG_PATH = str(MODELS_DIR / "MobileNetSSD_deploy.prototxt")
DETECTOR_CONFIDENCE_THRESHOLD = 0.4
TARGET_CLASS_ID = 15                   # 15 == 'person' (в оригинальной VOC модели)

# === ЗВУК ===
SOUND_FILE = str(SOUNDS_DIR / "beep.wav")
SOUND_ENABLED = True
SOUND_VOLUME = 0.7

# === ЖУРНАЛИРОВАНИЕ ===
LOG_LEVEL = "INFO"                     # DEBUG / INFO / WARNING / ERROR
LOG_TO_FILE = True
LOG_FILE = str(BASE_DIR / "cv_project.log")

# === ПАПКИ ===
for folder in [MODELS_DIR, SOUNDS_DIR, VIOLATIONS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# === ДРУГИЕ НАСТРОЙКИ ===
APP_VERSION = "1.0.0"
SAVE_SCREENSHOTS = True
REPORTS_SUBDIR = "reports"
