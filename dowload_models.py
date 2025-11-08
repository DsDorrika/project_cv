import os
import urllib.request
from pathlib import Path

def download_file(url, filename):
    """Загрузка файла по URL"""
    try:
        print(f"Загрузка {filename}...")
        urllib.request.urlretrieve(url, filename)
        print(f"Успешно загружено: {filename}")
        return True
    except Exception as e:
        print(f"Ошибка загрузки {filename}: {e}")
        return False

def main():
    """Основная функция загрузки"""
    # Создаем директории
    models_dir = Path("models")
    sounds_dir = Path("sounds")
    
    models_dir.mkdir(exist_ok=True)
    sounds_dir.mkdir(exist_ok=True)
    
    print("Создание необходимых директорий...")
    
    # Создаем простой звуковой файл-заглушку
    try:
        with open(sounds_dir / "beep.wav", "wb") as f:
            # Простейший WAV заголовок для пустого файла
            f.write(b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00')
        print("Создан заглушечный звуковой файл: sounds/beep.wav")
    except Exception as e:
        print(f"Ошибка создания звукового файла: {e}")
    
    print("\nДля полноценной работы необходимо скачать модели детекции.")
    print("Вы можете скачать MobileNet-SSD модели по следующим ссылкам:")
    print("1. Модель: https://github.com/chuanqi305/MobileNet-SSD/raw/master/mobilenet_iter_73000.caffemodel")
    print("2. Конфиг: https://github.com/chuanqi305/MobileNet-SSD/raw/master/deploy.prototxt")
    print("\nИли использовать альтернативные модели.")
    print("\nСозданы базовые файлы для запуска приложения.")

if __name__ == "__main__":
    main()