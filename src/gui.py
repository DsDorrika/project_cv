import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class ApplicationGUI:
    def __init__(self, root, sound_player_callback: Callable, start_detection_callback: Callable, 
                 stop_detection_callback: Callable):
        self.root = root
        self.root.title("Система детекции пересечения линии")
        self.root.geometry("400x300")
        
        self.sound_player_callback = sound_player_callback
        self.start_detection_callback = start_detection_callback
        self.stop_detection_callback = stop_detection_callback
        
        self.violation_count = 0
        self.is_detection_running = False
        
        self._create_widgets()
        self._setup_layout()
        
        logger.info("GUI инициализирован")

    def _create_widgets(self):
        """Создание виджетов"""
        # Основной фрейм
        self.main_frame = ttk.Frame(self.root, padding="10")
        
        # Заголовок
        self.title_label = ttk.Label(self.main_frame, 
                                   text="Детектор пересечения линии", 
                                   font=("Arial", 16, "bold"))
        
        # Счетчик нарушений
        self.counter_frame = ttk.LabelFrame(self.main_frame, text="Статистика", padding="10")
        self.counter_label = ttk.Label(self.counter_frame, 
                                     text="Нарушений: 0", 
                                     font=("Arial", 14))
        self.fps_label = ttk.Label(self.counter_frame, 
                                 text="FPS: N/A", 
                                 font=("Arial", 12))
        
        # Панель управления
        self.control_frame = ttk.LabelFrame(self.main_frame, text="Управление", padding="10")
        
        self.start_button = ttk.Button(self.control_frame, 
                                     text="Запуск детекции", 
                                     command=self._start_detection)
        self.stop_button = ttk.Button(self.control_frame, 
                                    text="Остановка детекции", 
                                    command=self._stop_detection,
                                    state="disabled")
        self.test_sound_button = ttk.Button(self.control_frame, 
                                          text="Тест звука", 
                                          command=self._test_sound_handler)
        
        # Статус бар
        self.status_var = tk.StringVar(value="Готов к работе")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                                  relief="sunken", anchor="w")

    def _setup_layout(self):
        """Настройка расположения виджетов"""
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        self.title_label.pack(pady=(0, 20))
        
        # Счетчик нарушений
        self.counter_frame.pack(fill=tk.X, pady=(0, 10))
        self.counter_label.pack(anchor="w")
        self.fps_label.pack(anchor="w")
        
        # Панель управления
        self.control_frame.pack(fill=tk.X, pady=(0, 10))
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        self.test_sound_button.pack(side=tk.LEFT)
        
        # Статус бар
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _test_sound_handler(self):
        """Обработчик теста звука"""
        try:
            self.sound_player_callback()
            self._update_status("Тест звука выполнен")
        except Exception as e:
            logger.error(f"Ошибка при тесте звука: {e}")
            messagebox.showerror("Ошибка", f"Не удалось воспроизвести звук: {e}")

    def _start_detection(self):
        """Запуск детекции"""
        try:
            self.start_detection_callback()
            self.is_detection_running = True
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self._update_status("Детекция запущена")
        except Exception as e:
            logger.error(f"Ошибка запуска детекции: {e}")
            messagebox.showerror("Ошибка", f"Не удалось запустить детекцию: {e}")

    def _stop_detection(self):
        """Остановка детекции"""
        try:
            self.stop_detection_callback()
            self.is_detection_running = False
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self._update_status("Детекция остановлена")
        except Exception as e:
            logger.error(f"Ошибка остановки детекции: {e}")
            messagebox.showerror("Ошибка", f"Не удалось остановить детекцию: {e}")

    def _update_status(self, message: str):
        """Обновление статус бара"""
        self.status_var.set(message)
        self.root.update()

    def update_counter(self, count: int):
        """Обновление счетчика нарушений"""
        self.violation_count = count
        self.counter_label.config(text=f"Нарушений: {self.violation_count}")

    def update_fps(self, fps: float):
        """Обновление FPS"""
        self.fps_label.config(text=f"FPS: {fps:.1f}")

    def update_status(self, message: str):
        """Публичный метод для обновления статуса"""
        self._update_status(message)

    def show_error(self, title: str, message: str):
        """Показать сообщение об ошибке"""
        messagebox.showerror(title, message)

    def show_info(self, title: str, message: str):
        """Показать информационное сообщение"""
        messagebox.showinfo(title, message)


def test_gui():
    """Тестирование GUI"""
    root = tk.Tk()
    
    def test_sound():
        print("Тест звука")
    
    def start_detection():
        print("Запуск детекции")
    
    def stop_detection():
        print("Остановка детекции")
    
    app = ApplicationGUI(root, test_sound, start_detection, stop_detection)
    root.mainloop()


if __name__ == "__main__":
    test_gui()