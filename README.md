# Система детекции пересечения линии

Полнофункциональная система компьютерного зрения для обнаружения пересечения виртуальной контрольной линии или входа в охраняемую область (region) объектами — в первую очередь людьми. Проект ориентирован на надёжное использование в реальных задачах: живое видео с веб-камеры или файл, детекция на базе YOLOv8, трекинг простых объектов, логирование и сохранение доказательств нарушений.

Автор: DsDorrika

---

## Основные возможности

- Поддержка захвата видео с веб-камеры или файла
- Детекция объектов с использованием YOLOv8 (рекомендуется) и простой совместимости с другими моделями
- Настраиваемая контрольная линия (line) или прямоугольная область (region)
- Интерактивная настройка области прямо на превью камеры (выбор мышью)
- Трекинг объектов с подавлением множественных срабатываний (интервал между фиксациями)
- Визуализация: линия/область, bounding box'ы, ID'ы объектов, предупреждения
- Звуковое оповещение и сохранение изображений + метаданных нарушений
- GUI на Tkinter с основными управляющими элементами и статистикой
- Сохранение пользовательских настроек (user_settings.json) между запусками

---

## Быстрый старт

1. Клонируйте репозиторий и перейдите в папку проекта:

    ```powershell
    git clone <repo-url>
    cd project_cv
    ```

2. Создайте виртуальное окружение и активируйте его (Windows PowerShell):

    ```powershell
    python -m venv venv
    venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    ```

3. Запустите приложение:

    ```powershell
    python main.py
    ```

    Если модель YOLOv8 (`yolov8n.pt`) отсутствует, приложение попытается её скачать автоматически.

---

## Структура проекта (основные файлы)

- `main.py` — точка входа: инициализация компонентов, GUI, основной цикл обработки видео
- `config.py` — конфигурационные параметры по умолчанию (кадры, координаты, пороги и т.п.)
- `src/camera.py` — обёртка захвата видеопотока (камеры/файла)
- `src/yolo_detector.py` — интеграция с моделью YOLOv8
- `src/line_crossing_detector.py` — логика определения пересечения линии / входа в область и трекинга
- `src/violation_manager.py` — сохранение изображений и метаданных нарушений, генерация отчётов
- `src/sound_player.py` — воспроизведение звуковых оповещений
- `src/gui.py` — интерфейс Tkinter, окно настроек (включая интерактивный выбор на камере)
- `src/settings_manager.py` — загрузка/сохранение настроек пользователя (`user_settings.json`)

---

## Конфигурация

Основные параметры расположены в `config.py`. Важные настройки:

- VIDEO_SOURCE — источник видео (0 для веб-камеры или путь к файлу)
- CAMERA_RESOLUTION, CAMERA_FPS — параметры камеры
- CROSSING_LINE_COORDS = (x1, y1, x2, y2) — координаты контрольной линии
- VIOLATION_REGION_COORDS = (x1, y1, x2, y2) — координаты области (если указаны, включается режим region)
- LINE_TOLERANCE_PX — толерантность при определении пересечения линии
- REGION_MIN_STAY_SECONDS — минимальное время пребывания в области для фиксации
- MIN_VIOLATION_INTERVAL_SECONDS — минимальный интервал между фиксациями для одного объекта

Важно: пользовательские настройки сохраняются в `user_settings.json` (в корне проекта) через GUI. Если вы хотите управлять настройками вручную — редактируйте `config.py` перед запуском или изменяйте `user_settings.json`.

---

## Интерактивная настройка региона на камере

1. Откройте GUI (окно приложения).
2. Нажмите кнопку "Настроить поле детекции".
3. В окне настроек выберите режим `line` (линия) или `region` (прямоугольник).
4. Нажмите кнопку "Выбрать на камере" — откроется окно с живым видео.
5. Выберите область мышью (left-drag). Для линии задаются две точки (start/end), для области — прямоугольник.
6. Нажмите `s` или отпустите кнопку и подтвердите выбор, чтобы скопировать координаты обратно в форму.
7. Нажмите "Сохранить" — настройки будут применены и записаны в `user_settings.json`.

Валидация: перед сохранением координаты проверяются против текущего разрешения камеры — при выходе за границы предлагается автоматически обрезать координаты.

---

## Использование и горячие клавиши

- Q / ESC — выход
- P — пауза / возобновление
- R — сброс статистики
- S — сохранение кадра (в директорию нарушений при включённом SAVE_VIOLATION_IMAGES)

---

## Архитектурные примечания для разработчиков

- Детекция и трекинг разделены: `yolo_detector` создаёт список обнаружений, затем `line_crossing_detector` сопоставляет и определяет нарушения.
- В `LineCrossingDetector` реализован режим "line" (Ax + By + C = 0) и режим "region" (пересечение bbox с областью).
- GUI взаимодействует с основной логикой через callback'ы: загрузка/применение настроек, получение информации о камере и запуск интерактивного селектора.

Рекомендации по улучшению:
- Заменить внутренний трекинг на более устойчивый алгоритм (например, DeepSORT) для точных ID и устойчивой истории.
- Добавить аутентификацию/шифрование для сохранённых метаданных, интеграцию с базой данных для долгосрочного хранения.
- Добавить веб-интерфейс или REST API для удалённого мониторинга.

---

## Локальная разработка и тестирование

- Запуск модульных тестов (при наличии) — добавьте `tests/` и используйте `pytest`.
- Для быстрой проверки камеры можно использовать `python -m src.camera` (в модуле реализован `test_camera()`).
- Включите `DEBUG_MODE = True` в `config.py` для подробного логирования.

---

## Типичные проблемы и отладка (дополнения)

- "YOLO модель не найдена": убедитесь, что файл `models/yolov8n.pt` присутствует. Приложение попытается скачать модель автоматически, если включён Internet.
- "Не удалось открыть камеру": проверьте доступность устройства, попробуйте изменить `VIDEO_SOURCE` или проверить бэкенды захвата в `src/camera.py`.

  Настройка камеры в Windows:
  - Убедитесь, что используете правильное устройство: в `config.py` `VIDEO_SOURCE` может быть целым индексом (0, 1, ...) — попробуйте разные значения для выбора нужной камеры.
  - Если несколько камер подключено, откройте "Диспетчер устройств" или стандартное приложение "Камера" Windows, чтобы увидеть, какое устройство отдаёт изображение.
  - В `src/camera.py` используются разные бэкенды захвата (CAP_DSHOW, CAP_MSMF). Для некоторых камер на Windows CAP_DSHOW даёт лучшую стабильность.
  - Параметры камеры (разрешение, FPS) можно указать в `config.py` (CAMERA_RESOLUTION, CAMERA_FPS). При необходимости вручную установите разрешение в камере или через свойства драйвера.
  - Если камера выдаёт перевёрнутое или зеркальное изображение — это можно исправить в коде (`cv2.flip`) при чтении кадра в `main.py` или `src/camera.py`.

- Неверные координаты региона: используйте интерактивный селектор или отредактируйте `user_settings.json`/`config.py` вручную.

### Смена звука детекции

- Файл звука задаётся параметром `SOUND_FILE` в `config.py`. По умолчанию используется `sounds/beep.mp3`.
- Поддерживаемые форматы зависят от используемой библиотеки (в проекте используется простая обёртка, обычно поддерживаются WAV/MP3).
- Чтобы сменить звук:
  1. Поместите новый звуковой файл в папку `sounds/`.
  2. Обновите `config.SOUND_FILE` в `config.py` или через GUI (в плане расширения GUI можно добавить выбор файла).
  3. Вы также можете отключить звук (`SOUND_ENABLED = False`) или сменить громкость через `SOUND_VOLUME`.

---

## API спецификация (коротко)

Ниже перечислены ключевые функции/контракты между модулями, чтобы упростить интеграцию и тестирование.

- `yolo_detector.detect(frame) -> List[Dict]`
  - Возвращает список обнаружений; каждое обнаружение — dict с полями:
    - `box`: [x1, y1, x2, y2]
    - `bottom_center`: (cx, cy) — нижняя центральная точка бокса
    - `confidence`: float
    - `class_id`: int
    - `class_name`: str
    - `timestamp`: float (опционально)

- `LineCrossingDetector.process_detections(frame, detections) -> List[Dict]`
  - Принимает кадр (для визуализации) и список детекций (см. выше). Возвращает список нарушений, каждое — dict с полями:
    - `id`: идентификатор трека (int или str для авто-нарушений)
    - `box`: [x1, y1, x2, y2]
    - `direction`: строка с направлением/типом нарушения
    - `timestamp`: float
    - `confidence`, `class_id`, `class_name`

- `src/settings_manager.py`
  - `load_user_settings() -> dict` — загружает `user_settings.json` (если есть)
  - `save_user_settings(dict) -> bool` — сохраняет словарь в `user_settings.json`
  - Формат `user_settings.json` описан ниже.

- GUI callbacks (взаимодействие с `main.py`):
  - `load_settings_callback()` — возвращает dict для заполнения формы
  - `apply_settings_callback(settings)` — принимает dict и применяет настройки
  - `get_camera_info_callback()` — возвращает `{'width': int, 'height': int, 'fps': float}`
  - `camera_select_callback(mode)` — интерактивный селектор возвращает кортеж координат

---

## Пример структуры user_settings.json

Пример содержимого `user_settings.json`, который создаётся/обновляется через GUI:

```json
{
  "mode": "region",
  "coords": [300, 320, 980, 420],
  "tolerance": 10,
  "region_min_stay": 1.0
}
```

Пояснения:
- `mode`: "line" или "region"
- `coords`: [x1, y1, x2, y2]
- `tolerance`: целое число (пиксели)
- `region_min_stay`: float (секунды)

---

## Примеры команд для CI / CD

Ниже приведены примеры полезных шагов для CI (GitHub Actions / другой CI):

- Установка окружения и проверка зависимостей

```yaml
# Пример шага для GitHub Actions
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.10'

- name: Install dependencies
  run: |
    python -m venv venv
    . venv/bin/activate
    pip install -r requirements.txt

- name: Lint
  run: |
    . venv/bin/activate
    pip install flake8
    flake8 .

- name: Run tests
  run: |
    . venv/bin/activate
    pip install pytest
    pytest -q
```

Если вы используете Windows runner, замените команды активации виртуального окружения на PowerShell-совместимые (например, `venv\Scripts\Activate.ps1`).

---

## Документация (Sphinx / mkdocs)

Короткие инструкции, как добавить автоматическую генерацию документации:

Sphinx (быстрый старт):

```bash
pip install sphinx sphinx-rtd-theme
sphinx-quickstart docs
# отредактируйте docs/conf.py (укажите путь к проекту в sys.path)
# добавьте автодокстринги
sphinx-apidoc -o docs/source src
make -C docs html
```

MkDocs (Markdown-based):

```bash
pip install mkdocs mkdocs-material
mkdocs new docs
# добавьте страницы и настройте mkdocs.yml
mkdocs build
mkdocs serve  # локально просмотреть
```

---

## Лицензия (MIT)

Copyright (c) 2025 DsDorrika

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

---

Если нужно — могу добавить: пример GitHub Actions workflow в виде отдельного файла `.github/workflows/ci.yml`, примеры unit-тестов для ключевых модулей, или реализовать в GUI выбор звукового файла через диалог. Скажите, что делаем дальше.

## Вклад в проект

Если вы планируете расширять проект:
- Следуйте PEP8 и используйте виртуальное окружение
- Пишите тесты на ключевые части (детектор, менеджер нарушений)
- Для PR используйте ветку `tailler` (локальная ветка разработки в этом репозитории)

Автор приветствует помощь и вклад от других разработчиков — если у вас есть идеи, исправления или улучшения, пожалуйста, открывайте issues или pull requests. Все конструктивные предложения рассматриваются с благодарностью.

---
