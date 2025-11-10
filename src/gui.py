import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Union
import logging

logger = logging.getLogger(__name__)


class ApplicationGUI:
    def __init__(
        self,
        root: tk.Tk,
        sound_player_callback: Callable,
        start_detection_callback: Callable,
        stop_detection_callback: Callable,
        pause_callback: Optional[Callable] = None,
    ):
        self.root = root
        self.root.title("Система детекции пересечения линии")
        self.root.geometry("520x380")

        # Колбэки из приложения
        self.sound_player_callback = sound_player_callback
        self.start_detection_callback = start_detection_callback
        self.stop_detection_callback = stop_detection_callback
        self.pause_callback = pause_callback

        # --- Корневой контейнер (размещается в root через pack) ---
        self.main_frame = ttk.Frame(self.root, padding=12)
        self.main_frame.pack(fill="both", expand=True)

        # Заголовок (дети main_frame можно размещать pack'ом, это другой уровень)
        self.title_label = ttk.Label(
            self.main_frame,
            text="Детекция пересечения линии",
            font=("Arial", 16, "bold"),
        )
        self.title_label.pack(anchor="w", pady=(0, 8))

        # ---- Статистика ----
        self.counter_frame = ttk.LabelFrame(self.main_frame, text="Статистика", padding=10)
        self.counter_frame.pack(fill="x", pady=8)

        # ВНУТРИ counter_frame — ТОЛЬКО grid
        self.counter_label = ttk.Label(self.counter_frame, text="Нарушений: 0", font=("Arial", 14))
        self.counter_label.grid(row=0, column=0, sticky="w")

        self.fps_label = ttk.Label(self.counter_frame, text="FPS: N/A", font=("Arial", 12))
        self.fps_label.grid(row=0, column=1, padx=(20, 0), sticky="e")

        self.counter_frame.columnconfigure(0, weight=1)
        self.counter_frame.columnconfigure(1, weight=1)

        # ---- Управление ----
        self.control_frame = ttk.LabelFrame(self.main_frame, text="Управление", padding=10)
        self.control_frame.pack(fill="x", pady=8)

        # ВНУТРИ control_frame — ТОЛЬКО grid
        self.start_button = ttk.Button(
            self.control_frame,
            text="Старт",
            command=self._on_start_clicked,
        )
        self.start_button.grid(row=0, column=0, padx=8, pady=6, sticky="ew")

        self.stop_button = ttk.Button(
            self.control_frame,
            text="Стоп",
            command=self._on_stop_clicked,
        )
        self.stop_button.grid(row=0, column=1, padx=8, pady=6, sticky="ew")

        col_count = 2
        if self.pause_callback is not None:
            self.pause_button = ttk.Button(
                self.control_frame,
                text="Пауза",
                command=self._on_pause_clicked,
            )
            self.pause_button.grid(row=0, column=2, padx=8, pady=6, sticky="ew")
            col_count = 3

        self.test_sound_button = ttk.Button(
            self.control_frame,
            text="Тест звука",
            command=self._on_test_sound_clicked,
        )
        self.test_sound_button.grid(row=1, column=0, columnspan=col_count, padx=8, pady=(2, 0), sticky="ew")

        for c in range(col_count):
            self.control_frame.columnconfigure(c, weight=1)

        # ---- Журнал ----
        self.log_frame = ttk.LabelFrame(self.main_frame, text="Журнал", padding=10)
        self.log_frame.pack(fill="both", expand=True, pady=8)

        self.log_text = tk.Text(self.log_frame, height=8)
        self.log_text.grid(row=0, column=0, sticky="nsew")

        self.log_frame.columnconfigure(0, weight=1)
        self.log_frame.rowconfigure(0, weight=1)

        self.log_scroll = ttk.Scrollbar(self.log_frame, command=self.log_text.yview)
        self.log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=self.log_scroll.set)

        self.log("GUI инициализирован")


    def set_violations_count(self, n: int) -> None:
        self.counter_label.config(text=f"Нарушений: {n}")

    def set_fps(self, fps: float) -> None:
        try:
            self.fps_label.config(text=f"FPS: {float(fps):.2f}")
        except Exception:
            # На случай, если пришёл нечисловой тип
            self.fps_label.config(text=f"FPS: {fps}")

    def log(self, msg: str) -> None:
        try:
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
        except Exception:
            # На ранней инициализации Text может быть недоступен — игнор
            pass

    def update_status(
        self,
        fps: Optional[Union[int, float]] = None,
        violations: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        """Универсальный адаптер под вызовы из main.py."""
        try:
            if fps is not None:
                self.set_fps(float(fps))
            if violations is not None:
                self.set_violations_count(int(violations))
            if message:
                self.log(str(message))
        except Exception as e:
            # Не роняем GUI при частичных ошибках
            try:
                self.log(f"Ошибка update_status: {e}")
            except Exception:
                pass

    # Совместимость со старым API:
    def update_counter(self, n: int) -> None:
        self.set_violations_count(n)

    def update_fps(self, fps: float) -> None:
        self.set_fps(fps)


    def _on_test_sound_clicked(self) -> None:
        try:
            self.sound_player_callback()
            self.log("Тест звука")
        except Exception as e:
            self.log(f"Ошибка теста звука: {e}")

    def _on_start_clicked(self) -> None:
        try:
            self.start_detection_callback()
            self.log("Старт детекции")
        except Exception as e:
            self.log(f"Ошибка старта: {e}")

    def _on_stop_clicked(self) -> None:
        try:
            self.stop_detection_callback()
            self.log("Стоп детекции")
        except Exception as e:
            self.log(f"Ошибка остановки: {e}")

    def _on_pause_clicked(self) -> None:
        if self.pause_callback is None:
            return
        try:
            self.pause_callback()
            # Переключаем подпись кнопки
            current = self.pause_button.cget("text")
            self.pause_button.config(text="Продолжить" if current == "Пауза" else "Пауза")
            self.log("Переключена пауза")
        except Exception as e:
            self.log(f"Ошибка паузы: {e}")
