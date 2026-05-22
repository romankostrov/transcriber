# Telem Transcriber Pro v12

Локальное Windows-приложение для транскрибации записей Яндекс Телемоста и других WEBM/MP4/WAV-файлов.

**Created by Roman Kostrov • rkostrov@yandex.ru**

## Возможности

- PySide6 Apple-light интерфейс в стиле desktop product.
- Drag & Drop файлов.
- Пакетная обработка нескольких записей.
- Режимы качества: `small`, `medium`, `large-v3`.
- Ручное редактирование `device`, `compute_type`, `beam_size`.
- Прогресс по длительности записи, скорость обработки `x`, ETA.
- Расшифровка отображается прямо в окне с таймкодами.
- TXT сохраняется с таймкодами.
- Экспорт: TXT, SRT, JSON, общий `batch_transcripts.csv`.
- Кнопка `Стоп и сохранить`: текущий распознанный текст сохраняется как partial.
- Локальный FFmpeg в папке `bin`, без установки в систему.
- Portable-сборка для переноса на флешке.

## Быстрый старт Windows

```bat
bootstrap_windows.bat
prepare_models.bat
run.bat
```

`bootstrap_windows.bat` сам установит `uv`, скачает совместимый Python 3.12, создаст `.venv`, поставит зависимости и скачает FFmpeg в `bin/`.

## Сборка portable

```bat
make_portable.bat
```

Готовая папка появится здесь:

```text
portable/TelemTranscriber/
```

Копировать на другой компьютер нужно **папку целиком**:

```text
TelemTranscriber/
  TelemTranscriber.exe
  bin/
    ffmpeg.exe
    ffprobe.exe
  models/
  output/
  README.md
```

## Режимы

- `Быстро / small` — быстрее, качество ниже.
- `Качественно / medium` — оптимально для встреч.
- `Максимум / large-v3` — тяжелее, но точнее.

Для CPU обычно используйте:

```text
device = cpu
compute_type = int8
beam_size = 1..5
```

Для NVIDIA GPU можно пробовать:

```text
device = cuda
compute_type = float16
```

## Примечания

- Модели не кладутся в GitHub-репозиторий, они скачиваются один раз в папку `models`.
- После сборки portable модели уже будут лежать внутри portable-папки.
- Если нажать `Стоп и сохранить`, результат сохранится с суффиксом `_partial`.
