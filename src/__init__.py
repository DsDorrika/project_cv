__version__ = "1.0.0"
__author__ = "CV Project Team"
__email__ = ""

# Импорт основных классов для удобного доступа
from .camera import Camera
from .object_detector import ObjectDetector
from .line_crossing_detector import LineCrossingDetector
from .gui import ApplicationGUI
from .sound_player import SoundPlayer, get_sound_player
from .violation_manager import ViolationManager
from .utils import (
    calculate_distance,
    get_timestamp_filename,
    calculate_iou,
    resize_frame,
    draw_text_with_background,
    save_data_to_json,
    load_data_from_json,
    FPSCounter
)

# Список импортируемых объектов для wildcard импорта
__all__ = [
    # Классы
    'Camera',
    'ObjectDetector', 
    'LineCrossingDetector',
    'ApplicationGUI',
    'SoundPlayer',
    'ViolationManager',
    'FPSCounter',
    
    # Функции
    'get_sound_player',
    'calculate_distance',
    'get_timestamp_filename', 
    'calculate_iou',
    'resize_frame',
    'draw_text_with_background',
    'save_data_to_json',
    'load_data_from_json',
]

# Инициализация логгера для пакета
import logging

# Настройка базового логгера для пакета
logger = logging.getLogger(__name__)

def setup_logging(level=logging.INFO):
    """Настройка логирования для всего пакета"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('cv_project.log', encoding='utf-8')
        ]
    )
    logger.info("Логирование инициализировано для пакета src")

# Автоматическая настройка при импорте пакета
try:
    setup_logging()
except Exception as e:
    print(f"Не удалось настроить логирование: {e}")

# Информация о пакете
def get_package_info():
    """Возвращает информацию о пакете"""
    return {
        'name': 'CV Project - Line Crossing Detection',
        'version': __version__,
        'author': __author__,
        'modules': [
            'camera', 'object_detector', 'line_crossing_detector',
            'gui', 'sound_player', 'violation_manager', 'utils'
        ]
    }

print(f"Пакет src инициализирован (версия {__version__})")