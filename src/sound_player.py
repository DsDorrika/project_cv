import os
import threading
import logging
from typing import Optional
import config

logger = logging.getLogger(__name__)

class SoundPlayer:
    def __init__(self, sound_file: Optional[str] = None):
        self.sound_file = sound_file or config.SOUND_FILE
        self.is_available = False
        self._play_thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()
        self._sound_object = None
        self._pygame_initialized = False
        
        self._initialize_sound_system()
        
    def _initialize_sound_system(self):
        """Инициализация звуковой системы с использованием pygame"""
        try:
            # Проверка существования файла
            if not os.path.exists(self.sound_file):
                logger.warning(f"Звуковой файл не найден: {self.sound_file}")
                self._create_dummy_sound_file()
            
            # Попытка импорта и инициализации pygame
            try:
                import pygame
                self._pygame = pygame
                
                # Инициализация только микшера (не всего pygame)
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                    logger.info("Pygame mixer инициализирован")
                
                self._pygame_initialized = True
                
                # Загрузка звукового файла
                try:
                    self._sound_object = pygame.mixer.Sound(self.sound_file)
                    self.is_available = True
                    logger.info(f"Звуковая система инициализирована: {self.sound_file}")
                    
                    # Установка громкости
                    if hasattr(config, 'SOUND_VOLUME'):
                        self._sound_object.set_volume(config.SOUND_VOLUME)
                    
                except pygame.error as e:
                    logger.error(f"Ошибка загрузки звукового файла {self.sound_file}: {e}")
                    self._sound_object = None
                    self.is_available = False
                    
            except ImportError:
                logger.warning("Библиотека pygame не установлена. Используется заглушка.")
                self._pygame_initialized = False
                self.is_available = False
                
        except Exception as e:
            logger.error(f"Ошибка инициализации звуковой системы: {e}")
            self._pygame_initialized = False
            self.is_available = False

    def _create_dummy_sound_file(self):
        """Создание заглушки если звуковой файл отсутствует"""
        try:
            # Создаем директорию если не существует
            sound_dir = os.path.dirname(self.sound_file)
            if sound_dir and not os.path.exists(sound_dir):
                os.makedirs(sound_dir, exist_ok=True)
                logger.info(f"Создана директория для звуков: {sound_dir}")
            
            logger.warning(f"Звуковой файл не найден: {self.sound_file}")
            
        except Exception as e:
            logger.error(f"Не удалось создать директорию для звуков: {e}")

    def _dummy_play(self):
        """Заглушка для воспроизведения звука"""
        logger.info(f"ВОСПРОИЗВЕДЕНИЕ ЗВУКА: {self.sound_file}")
        print(f"\a")  # Системный beep

    def _play_in_thread(self):
        """Воспроизведение звука в отдельном потоке"""
        try:
            if not self._stop_flag.is_set():
                if self.is_available and self._sound_object is not None:
                    # Воспроизведение с помощью pygame
                    self._sound_object.play()
                    
                    # Ожидание завершения воспроизведения или сигнала остановки
                    while self._pygame.mixer.get_busy() and not self._stop_flag.is_set():
                        import time
                        time.sleep(0.1)
                else:
                    # Заглушка
                    self._dummy_play()
                    
        except Exception as e:
            logger.error(f"Ошибка воспроизведения звука: {e}")
            self._dummy_play()
        finally:
            self._stop_flag.clear()

    def play_beep(self, blocking: bool = False):
        
        if not config.SOUND_ENABLED:
            return
            
        if not self.is_available:
            logger.warning("Звуковая система недоступна")
            self._dummy_play()
            return
            
        if blocking:
            # Блокирующее воспроизведение
            self._play_in_thread()
        else:
            # Асинхронное воспроизведение в отдельном потоке
            if self._play_thread and self._play_thread.is_alive():
                logger.debug("Предыдущее воспроизведение еще активно, пропускаем")
                return
                
            self._stop_flag.clear()
            self._play_thread = threading.Thread(
                target=self._play_in_thread, 
                daemon=True
            )
            self._play_thread.start()

    def stop_playback(self):
        """Остановка воспроизведения"""
        self._stop_flag.set()
        
        # Остановка воспроизведения в pygame
        if self._pygame_initialized:
            try:
                self._pygame.mixer.stop()
            except Exception as e:
                logger.error(f"Ошибка остановки воспроизведения: {e}")

    def set_volume(self, volume: float):
        
        if self._pygame_initialized and self._sound_object is not None:
            try:
                self._sound_object.set_volume(max(0.0, min(1.0, volume)))
                logger.info(f"Громкость установлена: {volume}")
            except Exception as e:
                logger.error(f"Ошибка установки громкости: {e}")

    def test_sound(self):
        """Тестирование звуковой системы"""
        logger.info("Тестирование звуковой системы...")
        
        if not self.is_available:
            logger.warning("Звуковая система недоступна для тестирования")
            self._dummy_play()
            return False
            
        try:
            # Тестируем в блокирующем режиме для гарантии воспроизведения
            self.play_beep(blocking=True)
            logger.info("Тест звука завершен успешно")
            return True
        except Exception as e:
            logger.error(f"Тест звука завершен с ошибкой: {e}")
            return False

    def get_status(self) -> dict:
        """Получение статуса звуковой системы"""
        is_playing = False
        if self._play_thread:
            is_playing = self._play_thread.is_alive()
            
        volume = 0
        if self._sound_object:
            try:
                volume = self._sound_object.get_volume()
            except:
                pass
        
        return {
            'available': self.is_available,
            'sound_file': self.sound_file,
            'file_exists': os.path.exists(self.sound_file),
            'pygame_initialized': self._pygame_initialized,
            'volume': volume,
            'is_playing': is_playing
        }

    def set_sound_file(self, sound_file: str):
        """Установка нового звукового файла"""
        old_file = self.sound_file
        self.sound_file = sound_file
        
        # Перезагрузка звука
        if self._pygame_initialized:
            try:
                self._sound_object = self._pygame.mixer.Sound(self.sound_file)
                self.is_available = True
                logger.info(f"Звуковой файл изменен: {old_file} -> {sound_file}")
            except Exception as e:
                logger.error(f"Ошибка загрузки нового звукового файла: {e}")
                self.is_available = False

    def __del__(self):
        """Деструктор для очистки ресурсов"""
        try:
            self.stop_playback()
        except:
            pass


# Глобальный экземпляр для удобства
_sound_player_instance: Optional[SoundPlayer] = None

def get_sound_player() -> SoundPlayer:
    """Получение глобального экземпляра проигрывателя звуков"""
    global _sound_player_instance
    if _sound_player_instance is None:
        _sound_player_instance = SoundPlayer()
    return _sound_player_instance


# Тестирование
if __name__ == "__main__":
    player = SoundPlayer()
    print(f"Звуковая система доступна: {player.is_available}")
    print(f"Статус: {player.get_status()}")
    
    if player.test_sound():
        print("Тест звука пройден успешно")
    else:
        print("Тест звука не пройден")