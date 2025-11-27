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
        # Кнопка открытия настроек поля детекции
        self.settings_button = ttk.Button(self.control_frame,
                                         text="Настроить поле детекции",
                                         command=self._open_settings_window)
        
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
        self.settings_button.pack(side=tk.LEFT, padx=(10, 0))
        
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

    def _open_settings_window(self):
        """Открыть окно настроек поля детекции"""
        try:
            # Создаём новое окно
            win = tk.Toplevel(self.root)
            win.title("Настройки поля детекции")
            win.geometry("420x300")

            # Frame
            frame = ttk.Frame(win, padding=10)
            frame.pack(fill=tk.BOTH, expand=True)

            # Режим: линия или область
            mode_label = ttk.Label(frame, text="Режим:")
            mode_label.grid(row=0, column=0, sticky="w")
            self.mode_var = tk.StringVar(value=("region" if getattr(self, 'initial_region_mode', False) else "line"))
            mode_combo = ttk.Combobox(frame, textvariable=self.mode_var, values=("line", "region"), state="readonly")
            mode_combo.grid(row=0, column=1, sticky="ew")

            # Координаты поля: x1,y1,x2,y2
            coords_label = ttk.Label(frame, text="Координаты (x1,y1,x2,y2):")
            coords_label.grid(row=1, column=0, sticky="w", pady=(10,0))
            self.coords_entry = ttk.Entry(frame, width=40)
            self.coords_entry.grid(row=1, column=1, sticky="ew", pady=(10,0))

            # Tolerance и min stay
            tol_label = ttk.Label(frame, text="Tolerance px:")
            tol_label.grid(row=2, column=0, sticky="w", pady=(10,0))
            self.tol_entry = ttk.Entry(frame, width=10)
            self.tol_entry.grid(row=2, column=1, sticky="w", pady=(10,0))

            minstay_label = ttk.Label(frame, text="Region min stay (s):")
            minstay_label.grid(row=3, column=0, sticky="w", pady=(10,0))
            self.minstay_entry = ttk.Entry(frame, width=10)
            self.minstay_entry.grid(row=3, column=1, sticky="w", pady=(10,0))

            # Save / Cancel
            btn_frame = ttk.Frame(frame)
            btn_frame.grid(row=4, column=0, columnspan=2, pady=(20,0))
            # Button to open interactive camera selector
            select_btn = ttk.Button(btn_frame, text="Выбрать на камере", command=self._camera_select_handler)
            select_btn.pack(side=tk.LEFT, padx=(0,10))
            save_btn = ttk.Button(btn_frame, text="Сохранить", command=lambda: self._save_settings(win))
            cancel_btn = ttk.Button(btn_frame, text="Отмена", command=win.destroy)
            save_btn.pack(side=tk.LEFT, padx=(0,10))
            cancel_btn.pack(side=tk.LEFT)

            # Заполнение начальными значениями по запросу к callback, если он предоставлен
            if hasattr(self, 'load_settings_callback') and callable(self.load_settings_callback):
                try:
                    s = self.load_settings_callback()
                    # ждём, что s содержит keys: mode, coords, tolerance, region_min_stay
                    mode = s.get('mode', 'region' if getattr(s, 'region_coords', None) else 'line')
                    self.mode_var.set(mode)
                    coords = s.get('coords') or s.get('region_coords') or s.get('line_coords')
                    if coords:
                        self.coords_entry.delete(0, tk.END)
                        self.coords_entry.insert(0, ','.join([str(int(x)) for x in coords]))
                    self.tol_entry.delete(0, tk.END)
                    self.tol_entry.insert(0, str(s.get('tolerance', '')))
                    self.minstay_entry.delete(0, tk.END)
                    self.minstay_entry.insert(0, str(s.get('region_min_stay', '')))
                except Exception as e:
                    logger.error(f"Ошибка при загрузке настроек для окна: {e}")
            
            # make columns expand
            frame.columnconfigure(1, weight=1)

        except Exception as e:
            logger.error(f"Ошибка открытия окна настроек: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть окно настроек: {e}")

    def _save_settings(self, win: tk.Toplevel):
        """Считать значения из полей и вызвать callback для сохранения/применения"""
        try:
            raw_coords = self.coords_entry.get().strip()
            parts = [p.strip() for p in raw_coords.split(',') if p.strip()]
            if len(parts) != 4:
                messagebox.showerror("Ошибка", "Введите 4 числа через запятую: x1,y1,x2,y2")
                return
            coords = tuple(int(float(p)) for p in parts)

            mode = self.mode_var.get()
            tol = int(self.tol_entry.get().strip()) if self.tol_entry.get().strip() else None
            minstay = float(self.minstay_entry.get().strip()) if self.minstay_entry.get().strip() else None

            # Валидация координат относительно разрешения камеры (если callback предоставлен)
            try:
                if hasattr(self, 'get_camera_info_callback') and callable(self.get_camera_info_callback):
                    cam_info = self.get_camera_info_callback() or {}
                    width = int(cam_info.get('width') or 0)
                    height = int(cam_info.get('height') or 0)
                    if width > 0 and height > 0:
                        x1, y1, x2, y2 = coords
                        # Для области приводим к упорядоченному виду
                        if mode == 'region':
                            # гарантируем порядок координат
                            nx1, nx2 = sorted((x1, x2))
                            ny1, ny2 = sorted((y1, y2))
                            x1, x2, y1, y2 = nx1, nx2, ny1, ny2
                        # Проверка выхода за границы
                        out_of_bounds = not (0 <= x1 < width and 0 <= x2 < width and 0 <= y1 < height and 0 <= y2 < height)
                        if out_of_bounds:
                            resp = messagebox.askyesno(
                                "Координаты вне границ",
                                f"Координаты выходят за пределы разрешения камеры ({width}x{height}).\nОбрезать координаты до границ?"
                            )
                            if resp:
                                # Обрезаем
                                x1 = max(0, min(x1, width - 1))
                                x2 = max(0, min(x2, width - 1))
                                y1 = max(0, min(y1, height - 1))
                                y2 = max(0, min(y2, height - 1))
                                # для области снова упорядочим
                                if mode == 'region':
                                    nx1, nx2 = sorted((x1, x2))
                                    ny1, ny2 = sorted((y1, y2))
                                    x1, x2, y1, y2 = nx1, nx2, ny1, ny2
                                coords = (int(x1), int(y1), int(x2), int(y2))
                            else:
                                return
            except Exception as e:
                logger.error(f"Ошибка валидации координат: {e}")

            settings = {
                'mode': mode,
                'coords': coords,
                'tolerance': tol,
                'region_min_stay': minstay
            }

            if hasattr(self, 'apply_settings_callback') and callable(self.apply_settings_callback):
                self.apply_settings_callback(settings)

            win.destroy()
            self._update_status("Настройки сохранены")
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек: {e}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {e}")

    def _camera_select_handler(self):
        """Запуск интерактивного выбора области на превью камеры через колбэк, если он предоставлен."""
        try:
            if hasattr(self, 'camera_select_callback') and callable(self.camera_select_callback):
                mode = self.mode_var.get() if hasattr(self, 'mode_var') else None
                coords = self.camera_select_callback(mode)
                if coords:
                    # Заполнить поле координат
                    self.coords_entry.delete(0, tk.END)
                    self.coords_entry.insert(0, ','.join([str(int(x)) for x in coords]))
                    self._update_status("Координаты выбраны с камеры")
                else:
                    self._update_status("Выбор на камере отменён")
            else:
                messagebox.showinfo("Информация", "Функция выбора на камере недоступна")
        except Exception as e:
            logger.error(f"Ошибка при выборе на камере: {e}")
            messagebox.showerror("Ошибка", f"Ошибка при выборе на камере: {e}")

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