import cv2
import time
import tkinter as tk
import logging

# Импорт всех модулей
import config
from src.camera import Camera
from src.object_detector import ObjectDetector
from src.line_crossing_detector import LineCrossingDetector
from src.sound_player import SoundPlayer
from src.violation_manager import ViolationManager
from src.gui import ApplicationGUI

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MainApplication:
    def __init__(self, root):
        self.root = root
        
        # Инициализация компонентов
        self.camera = Camera()
        self.detector = ObjectDetector()
        self.line_crosser = LineCrossingDetector()
        self.sound_player = SoundPlayer()
        self.violation_manager = ViolationManager()
        
        self.gui = ApplicationGUI(root, self.sound_player.test_sound)
        
        self.total_violations = 0
        self.running = self.camera.is_running
        self.start_time = time.time()
        self.frame_count = 0

        if not self.running:
            logging.error("Приложение не может запуститься из-за ошибки камеры.")
            self.root.quit()
            return
        
        # Запуск цикла обработки видео
        self.process_video()

    def process_video(self):
        """Основной цикл обработки видеопотока."""
        
        ret, frame = self.camera.read()
        
        if ret:
            # 1. Детектирование объектов
            detections = self.detector.detect(frame)
            
            # 2. Обработка пересечения линии
            violations = self.line_crosser.process_detections(frame, detections)
            
            # 3. Обработка нарушений (Критерии 2 и 3)
            if violations:
                for violation in violations:
                    self.total_violations += 1
                    self.sound_player.play_beep() # Критерий 2
                    self.violation_manager.save_violation(frame.copy(), violation) # Критерий 3
            
            # 4. Обновление GUI (Критерий 5)
            self.gui.update_counter(self.total_violations)
            
            # 5. Расчет и отображение FPS (Критерий 4)
            self.frame_count += 1
            elapsed_time = time.time() - self.start_time
            current_fps = self.frame_count / elapsed_time if elapsed_time > 0 else 0
            self.gui.update_fps(current_fps)
            
            # 6. Отображение видео (Критерий 1)
            cv2.imshow("Video Feed (Press 'q' to exit)", frame)
            
            # Проверка нажатия клавиши 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.running = False
                self.root.quit()
                return

            # Перезапуск цикла через 1 мс
            self.root.after(1, self.process_video)
        else:
            self.running = False
            self.root.quit()

    def cleanup(self):
        """Очистка ресурсов при завершении работы."""
        self.camera.release()
        cv2.destroyAllWindows()
        logging.info("Приложение завершено.")

if __name__ == "__main__":
    # Для работы Tkinter и cv2 вместе, Tkinter должен управлять главным циклом
    root = tk.Tk()
    app = MainApplication(root)
    
    try:
        root.mainloop()
    except Exception as e:
        logging.error(f"Произошла ошибка в главном цикле: {e}")
    finally:
        app.cleanup()
