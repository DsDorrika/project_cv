import numpy as np
from datetime import datetime

def calculate_distance(pt1, pt2):
    """Рассчитывает евклидово расстояние между двумя точками."""
    return np.sqrt((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)

def get_timestamp_filename():
    """Возвращает форматированную строку времени для имени файла."""
    # Формат: YYYYMMDD_HHMM
    return datetime.now().strftime("%Y%m%d_%H%M%S")
