import logging
from typing import Optional

import pygame

logger = logging.getLogger(__name__)


class SoundPlayer:
    """
    Обёртка над pygame.mixer для простого проигрывания звука.
    Поддерживает:
      - включение/выключение
      - регулировку громкости
      - тестовый сигнал
    """

    _mixer_initialized: bool = False

    def __init__(self, sound_file: str, enabled: bool = True, volume: float = 1.0):
        """
        Args:
            sound_file: путь к WAV/OGG и т.п.
            enabled: включено ли воспроизведение
            volume: громкость 0.0..1.0
        """
        self.sound_file = sound_file
        self.enabled = bool(enabled)
        self._sound: Optional[pygame.mixer.Sound] = None

        # Инициализация микшера один раз на процесс
        self._ensure_mixer()

        try:
            self._sound = pygame.mixer.Sound(self.sound_file)
            self.set_volume(volume)
            logger.info(f"Звуковая система инициализирована: {self.sound_file}")
        except Exception as e:
            logger.error(f"Не удалось загрузить звук '{self.sound_file}': {e}")
            self._sound = None


    @classmethod
    def _ensure_mixer(cls) -> None:
        if not cls._mixer_initialized:
            try:
                pygame.mixer.init()  # можно добавить частоту/буфер при необходимости
                cls._mixer_initialized = True
                logger.info("Pygame mixer инициализирован")
            except Exception as e:
                logger.error(f"Не удалось инициализировать pygame.mixer: {e}")
                cls._mixer_initialized = False

    def play(self) -> None:
        """Проиграть звук (если включено и загружено)."""
        if not self.enabled:
            return
        if self._sound is None:
            return
        try:
            self._sound.play()
        except Exception as e:
            logger.error(f"Ошибка воспроизведения звука: {e}")

    def test_sound(self) -> None:
        """Короткий тест звука."""
        self.play()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def set_volume(self, volume: float) -> None:
        """Установить громкость 0.0..1.0."""
        try:
            v = max(0.0, min(1.0, float(volume)))
        except Exception:
            v = 1.0
        if self._sound is not None:
            try:
                self._sound.set_volume(v)
            except Exception as e:
                logger.error(f"Не удалось установить громкость: {e}")

    def cleanup(self) -> None:
        """Освободить ресурсы (при необходимости)."""
        # mixer глобальный, как правило, закрывать не обязательно,
        # но если нужно — можно раскомментировать:
        # if self._mixer_initialized:
        #     pygame.mixer.quit()
        pass


def get_sound_player(sound_file: str, volume: float = 1.0, enabled: bool = True) -> SoundPlayer:
    """
    Фабрика для единообразного создания SoundPlayer.
    Совместима с вызовами из main.py:
      get_sound_player(sound_file, volume, enabled)
    """
    return SoundPlayer(sound_file=sound_file, volume=volume, enabled=enabled)
