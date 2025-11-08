import tkinter as tk
from tkinter import ttk
import logging

class ApplicationGUI:
    def __init__(self, root, sound_player_callback):
        self.root = root
        self.root.title("Детектор пересечения линии")
        
        self.violation_count = 0
        self.sound_player_callback = sound_player_callback

        # Метка для отображения счетчика
        self.counter_label = ttk.Label(root, text="Нарушений: 0", font=("Arial", 16))
        self.counter_label.pack(pady=10)

        # Кнопка "Тест звука" (Критерий 5)
        self.test_button = ttk.Button(root, text="Тест звука", command=self._test_sound_handler)
        self.test_button.pack(pady=5)
        
        # Метка для отображения FPS
        self.fps_label = ttk.Label(root, text="FPS: N/A", font=("Arial", 10))
        self.fps_label.pack(pady=5)

        # Примечание: Видеопоток будет отображаться в отдельном окне OpenCV,
        # так как интеграция cv2 в Tkinter сложна для быстрого примера.
        logging.info("GUI инициализирован. Видео будет в отдельном окне OpenCV.")

    def _test_sound_handler(self):
        """Обработчик нажатия кнопки "Тест звука"."""
        self.sound_player_callback()

    def update_counter(self, count):
        """Обновляет счетчик нарушений."""
        self.violation_count = count
        self.counter_label.config(text=f"Нарушений: {self.violation_count}")

    def update_fps(self, fps):
        """Обновляет отображение FPS."""
        self.fps_label.config(text=f"FPS: {fps:.2f}")
