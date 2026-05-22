<div align="center">

# 🎙️ Transcriber Pro

### Локальная транскрибация аудио и видео с поддержкой GPU

**v12** • Created by Roman Kostrov • [rkostrov@yandex.ru](mailto:rkostrov@yandex.ru)

[![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Qt](https://img.shields.io/badge/Qt-6.7-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://qt.io)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

## ✨ Возможности

| Функция | Описание |
|---------|----------|
| 🎬 **Форматы** | WEBM, MP4, WAV, MP3, M4A, MKV |
| 📦 **Пакетная обработка** | Несколько файлов за раз |
| ⚡ **GPU ускорение** | CUDA support для NVIDIA |
| 📝 **Таймкоды** | Точное время каждого фрагмента |
| 💾 **Экспорт** | TXT, SRT, JSON |
| 🌐 **Русский язык** | Оптимизировано для русского |
| 🖱️ **Drag & Drop** | Просто перетащите файлы |
| 📁 **Portable** | Работает с флешки |

---

## 🚀 Быстрый старт

### 1️⃣ Установка

```batch
bootstrap_windows.bat
Скрипт автоматически:

Устанавливает uv (менеджер Python)

Скачивает Python 3.12

Создаёт виртуальное окружение

Устанавливает зависимости

Скачивает FFmpeg

2️⃣ Скачивание модели
batch
download_small.bat
Модель	Размер	Скорость	Качество	Когда использовать
small	~500 MB	⚡⚡⚡	⭐⭐	Быстрая расшифровка
medium	~1.5 GB	⚡⚡	⭐⭐⭐⭐	Оптимальный баланс
large-v3	~3 GB	⚡	⭐⭐⭐⭐⭐	Максимальная точность
3️⃣ Запуск
batch
run.bat
🖥️ Интерфейс
text
┌─────────────────────────────────────────────────────────────┐
│  Transcriber Pro v12                                        │
├─────────────────────────────────────────────────────────────┤
│  [+ Добавить файлы]  [Очистить]          Папка: [output\]   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ meeting.webm                                            ││
│  │ interview.mp4                                           ││
│  │ lecture.wav                                             ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│  Режим: [Быстро/small ▼]  Модель: [small ▼]  Device: [cpu ▼]│
│  Beam: [1]  Compute: [int8 ▼]                              │
├─────────────────────────────────────────────────────────────┤
│  [▶ Старт]  [■ Стоп]                    Статус: Готов       │
├─────────────────────────────────────────────────────────────┤
│  📋 Лог                                                     │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Загрузка модели small...                                ││
│  │ Модель загружена                                        ││
│  │ [1/3] meeting.webm                                      ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│  📝 Расшифровка                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ [00:00:00 - 00:00:05] Добрый день, коллеги              ││
│  │ [00:00:05 - 00:00:12] Сегодня обсудим план работы       ││
│  │ [00:00:12 - 00:00:18] Первый пункт повестки...          ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
📁 Структура проекта
text
Transcriber Pro/
│
├── 📄 run.bat                 # Запуск приложения
├── 📄 bootstrap_windows.bat   # Установка окружения
├── 📄 download_small.bat      # Скачать small модель
├── 📄 download_medium.bat     # Скачать medium модель
├── 📄 download_large.bat      # Скачать large модель
├── 📄 make_portable.bat       # Собрать portable версию
│
├── 📁 .venv/                  # Виртуальное окружение
├── 📁 bin/                    # FFmpeg бинарники
├── 📁 models/                 # Модели whisper
│   └── faster-whisper-small/  # ~500 MB
│
├── 📁 output/                 # Результаты расшифровки
│   ├── meeting.txt           # Текст с таймкодами
│   ├── meeting.srt           # Субтитры
│   └── meeting.json          # Полные данные
│
└── 🐍 app.py                  # Исходный код
🎮 Режимы работы
Быстро / small
yaml
Модель: small
Beam size: 1
Compute: int8
Скорость: ⚡⚡⚡
Качество: ⭐⭐
Для кого: Черновики, быстрая проверка, длинные записи

Качественно / medium
yaml
Модель: medium
Beam size: 5
Compute: int8
Скорость: ⚡⚡
Качество: ⭐⭐⭐⭐
Для кого: Деловые встречи, интервью, лекции

Максимум / large-v3
yaml
Модель: large-v3
Beam size: 5
Compute: int8
Скорость: ⚡
Качество: ⭐⭐⭐⭐⭐
Для кого: Судебные записи, медицинские диктовки, где важна точность

⚙️ Настройки
CPU (рекомендуется для большинства)
text
Device: cpu
Compute: int8
Beam size: 1-5 (чем больше, тем точнее, но медленнее)
NVIDIA GPU
text
Device: cuda
Compute: float16
Beam size: 3-5
Требуется установленный CUDA Toolkit и драйверы NVIDIA

📦 Portable версия
batch
make_portable.bat
Готовая папка для USB-флешки:

text
TranscriberPro_Portable/
├── TranscriberPro.exe         # Запуск без Python!
├── download_small.bat
├── download_medium.bat
├── download_large.bat
├── bin/
│   ├── ffmpeg.exe
│   └── ffprobe.exe
└── models/                    # Модели скачиваются сюда
Размер: ~75 MB (без моделей)