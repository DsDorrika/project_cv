import config
import logging

logging.warning("Библиотека playsound не найдена. Звук будет выводиться в консоль.")
SOUND_AVAILABLE = False
def playsound(path):
        print(f"*** ЗВУК: Воспроизведение {path} ***")

class SoundPlayer:
    def __init__(self):
        self.sound_file = config.SOUND_FILE
        if not SOUND_AVAILABLE:
             logging.warning("Для реального звука установите playsound.")

    def play_beep(self):
        """Воспроизводит звук нарушения."""
        playsound(self.sound_file)

    def test_sound(self):
        """Тестовое воспроизведение звука."""
        logging.info("Тестирование звука...")
        self.play_beep()
