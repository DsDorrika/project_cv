# 1. Параметры видеопотока
VIDEO_SOURCE = 0  # 0 для веб-камеры, или 'path/to/video.mp4'

# 2. Параметры линии пересечения (x1, y1, x2, y2)
# Предполагаем, что кадр 640x480
CROSSING_LINE_COORDS = (100, 240, 540, 240) 

# 3. Параметры детектора объектов (для Критерия 4: Скорость)
# Внимание: для запуска вам потребуются файлы MobileNet-SSD или YOLO-nano
MODEL_NAME = "MobileNetSSD_deploy.caffemodel"
CONFIG_NAME = "MobileNetSSD_deploy.prototxt"
DETECTOR_MODEL_PATH = f"models/{MODEL_NAME}"
DETECTOR_CONFIG_PATH = f"models/{CONFIG_NAME}"
DETECTOR_CONFIDENCE_THRESHOLD = 0.5
TARGET_CLASS_ID = 15  # ID для 'person' в MobileNet-SSD

# 4. Параметры звука (для Критерия 2: Звук)
SOUND_FILE = "sounds/beep.wav"

# 5. Параметры сохранения нарушений (для Критерия 3: Фото)
VIOLATIONS_DIR = "violations"
