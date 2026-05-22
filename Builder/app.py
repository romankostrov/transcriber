import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download
from PySide6.QtCore import Qt, QThread, Signal, QSize, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QProgressBar, QPlainTextEdit,
    QSizePolicy, QSpinBox, QSplitter, QVBoxLayout, QWidget, QGraphicsDropShadowEffect
)

APP_NAME = "Transcriber Pro"
APP_VERSION = "v12"
CREATOR = "Created by Roman Kostrov • rkostrov@yandex.ru"

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
WORK_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
MODELS_DIR = WORK_DIR / "models"
BIN_DIR = WORK_DIR / "bin"
OUTPUT_DIR = WORK_DIR / "output"

MODEL_REPOS = {
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
}

QUALITY_PRESETS = {
    "Быстро / small": {"model": "small", "beam": 1, "compute": "int8"},
    "Качественно / medium": {"model": "medium", "beam": 5, "compute": "int8"},
    "Максимум / large-v3": {"model": "large-v3", "beam": 5, "compute": "int8"},
}

BG = "#f5f6f8"
CARD = "#ffffff"
TEXT = "#111111"
MUTED = "#6b7280"
BORDER = "#e5e7eb"
ACCENT = "#111111"
ACCENT_BLUE = "#4f46e5"
SUCCESS = "#15803d"
DANGER = "#dc2626"
WARNING = "#a16207"


def ensure_dirs():
    MODELS_DIR.mkdir(exist_ok=True)
    BIN_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)


def fmt_time(seconds: float, comma: bool = False) -> str:
    if seconds is None or seconds < 0:
        seconds = 0
    ms = int((seconds - int(seconds)) * 1000)
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    sep = "," if comma else "."
    return f"{h:02}:{m:02}:{s:02}{sep}{ms:03}"


def fmt_duration(seconds: Optional[float]) -> str:
    if seconds is None or seconds < 0:
        return "—"
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h:
        return f"{h}ч {m:02}м {s:02}с"
    return f"{m}м {s:02}с"


def safe_stem(path: Path) -> str:
    safe = path.stem
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        safe = safe.replace(ch, "_")
    return safe.strip() or "transcript"


def find_binary(name: str) -> Optional[str]:
    local = BIN_DIR / f"{name}.exe"
    if local.exists():
        return str(local)
    system = shutil.which(name)
    if system:
        return system
    common = Path(r"C:\ffmpeg-8.1\bin") / f"{name}.exe"
    if common.exists():
        return str(common)
    return None


def find_ffmpeg() -> str:
    ffmpeg = find_binary("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("FFmpeg не найден. Запустите bootstrap_windows.bat или положите ffmpeg.exe в папку bin.")
    return ffmpeg


def find_ffprobe() -> Optional[str]:
    return find_binary("ffprobe")


def get_duration_media(path: Path) -> Optional[float]:
    ffprobe = find_ffprobe()
    if not ffprobe:
        return None
    cmd = [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=45)
        if res.returncode == 0:
            return float(res.stdout.strip())
    except Exception:
        return None
    return None


def local_model_path(model_name: str) -> Path:
    return MODELS_DIR / f"faster-whisper-{model_name}"


def ensure_model(model_name: str, log: Callable[[str], None]) -> str:
    path = local_model_path(model_name)
    if path.exists() and any(path.iterdir()):
        log(f"Модель найдена локально: {path}")
        return str(path)
    repo = MODEL_REPOS[model_name]
    log(f"Модель не найдена. Скачиваю один раз: {repo}")
    snapshot_download(repo_id=repo, local_dir=str(path), local_dir_use_symlinks=False)
    log(f"Модель скачана: {path}")
    return str(path)


def extract_audio(video_path: Path, audio_path: Path, normalize: bool, log: Callable[[str], None]):
    ffmpeg = find_ffmpeg()
    log(f"FFmpeg: {ffmpeg}")
    cmd = [ffmpeg, "-y", "-i", str(video_path), "-vn", "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000"]
    if normalize:
        cmd += ["-af", "loudnorm"]
    cmd.append(str(audio_path))
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise RuntimeError(res.stderr[-5000:])


def make_srt(segments):
    blocks = []
    for idx, seg in enumerate(segments, 1):
        blocks.append(f"{idx}\n{fmt_time(seg['start'], True)} --> {fmt_time(seg['end'], True)}\n{seg['text']}\n")
    return "\n".join(blocks)


def make_txt_with_times(segments):
    return "\n".join(f"[{fmt_time(seg['start'])} - {fmt_time(seg['end'])}] {seg['text']}" for seg in segments)


@dataclass
class JobSettings:
    output_dir: Path
    preset_label: str
    model_name: str
    device: str
    compute_type: str
    beam_size: int
    normalize_audio: bool
    auto_download: bool


class GlassCard(QFrame):
    def __init__(self, parent=None, radius: int = 17):
        super().__init__(parent)
        self.setObjectName("glassCard")
        self.setStyleSheet(f"""
            QFrame#glassCard {{
                background: {CARD};
                border: 1px solid #eceef2;
                border-radius: {radius}px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(15, 23, 42, 14))
        self.setGraphicsEffect(shadow)


def make_button(text: str, primary: bool = False, danger: bool = False) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setMinimumHeight(31)
    bg = "#111111" if primary else "#ffffff"
    fg = "#ffffff" if primary else (DANGER if danger else TEXT)
    border = "#111111" if primary else ("#fecaca" if danger else "#e5e7eb")
    hover = "#1f2937" if primary else ("#fff1f2" if danger else "#f8fafc")
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: 11px;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background: {hover}; }}
        QPushButton:pressed {{ background: {'#0f172a' if primary else '#f1f5f9'}; }}
        QPushButton:disabled {{ background: #f3f4f6; color: #9ca3af; border: 1px solid #e5e7eb; }}
    """)
    shadow = QGraphicsDropShadowEffect(btn)
    shadow.setBlurRadius(10)
    shadow.setOffset(0, 3)
    shadow.setColor(QColor(15, 23, 42, 14))
    btn.setGraphicsEffect(shadow)
    return btn


class DropListWidget(QListWidget):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(64)
        self.setAlternatingRowColors(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        paths = []
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p:
                paths.append(p)
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class TranscribeWorker(QThread):
    log = Signal(str)
    transcript_line = Signal(str)
    progress = Signal(int)
    stats = Signal(dict)
    file_started = Signal(str)
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, files: list[Path], settings: JobSettings):
        super().__init__()
        self.files = files
        self.settings = settings
        self.stop_requested = False

    def request_stop(self):
        self.stop_requested = True
        self.log.emit("Запрошена остановка. Текущий распознанный текст будет сохранён.")

    def run(self):
        try:
            self.settings.output_dir.mkdir(parents=True, exist_ok=True)
            model_path = local_model_path(self.settings.model_name)
            if not model_path.exists() or not any(model_path.iterdir()):
                if not self.settings.auto_download:
                    raise RuntimeError(f"Модель {self.settings.model_name} не найдена в {model_path}. Включите автоскачивание или запустите prepare_models.bat.")
                resolved = ensure_model(self.settings.model_name, lambda x: self.log.emit(x))
            else:
                resolved = str(model_path)
                self.log.emit(f"Модель найдена локально: {resolved}")

            self.log.emit(
                f"Загружаю Whisper: model={self.settings.model_name}, "
                f"device={self.settings.device}, compute_type={self.settings.compute_type}, beam_size={self.settings.beam_size}"
            )
            model = WhisperModel(resolved, device=self.settings.device, compute_type=self.settings.compute_type)
            self.log.emit("Модель загружена")

            batch_rows = []
            total_files = len(self.files)
            for file_index, video in enumerate(self.files, 1):
                if self.stop_requested:
                    break
                self.file_started.emit(str(video))
                self.log.emit(f"[{file_index}/{total_files}] Файл: {video}")
                video_duration = get_duration_media(video)
                self.log.emit(f"Длительность записи: {fmt_duration(video_duration)}")
                self.progress.emit(0)
                self.transcript_line.emit("\n" + "=" * 90 + f"\nФайл: {video.name}\n" + "=" * 90 + "\n")

                with tempfile.TemporaryDirectory() as tmp:
                    audio = Path(tmp) / "audio.wav"
                    self.log.emit("Извлекаю аудио...")
                    extract_audio(video, audio, self.settings.normalize_audio, lambda x: self.log.emit(x))
                    audio_duration = get_duration_media(audio) or video_duration
                    self.log.emit(f"Длительность аудио: {fmt_duration(audio_duration)}")

                    self.log.emit("Распознаю. Текст появится в поле расшифровки сразу по мере обработки.")
                    started = time.time()
                    segments_gen, info = model.transcribe(
                        str(audio),
                        language="ru",
                        beam_size=self.settings.beam_size,
                        vad_filter=False,
                        condition_on_previous_text=True,
                        temperature=0,
                        initial_prompt=(
                            "Это расшифровка деловой встречи на русском языке. "
                            "Сохраняй имена, фамилии, названия сервисов, технические термины и числа. "
                            "Пиши грамотно, с пунктуацией."
                        ),
                    )

                    segments = []
                    last_progress = -1
                    for n, seg in enumerate(segments_gen, 1):
                        txt = seg.text.strip()
                        if not txt:
                            continue
                        item = {"start": float(seg.start), "end": float(seg.end), "text": txt}
                        segments.append(item)
                        line = f"[{fmt_time(seg.start)} - {fmt_time(seg.end)}] {txt}"
                        self.transcript_line.emit(line)

                        processed = float(seg.end)
                        elapsed = max(time.time() - started, 0.1)
                        speed = processed / elapsed if elapsed else 0
                        if audio_duration and audio_duration > 0:
                            pct = max(0, min(100, int(processed / audio_duration * 100)))
                            remaining_audio = max(audio_duration - processed, 0)
                            eta = remaining_audio / speed if speed > 0 else None
                        else:
                            pct = min(99, n)
                            eta = None

                        self.stats.emit({
                            "file_index": file_index,
                            "total_files": total_files,
                            "segments": n,
                            "processed": processed,
                            "duration": audio_duration,
                            "speed": speed,
                            "eta": eta,
                            "elapsed": elapsed,
                        })
                        if pct != last_progress:
                            self.progress.emit(pct)
                            last_progress = pct

                        if self.stop_requested:
                            self.log.emit("Остановка после текущего фрагмента.")
                            break

                    stopped = self.stop_requested
                    saved = self.save_outputs(video, segments, info, stopped)
                    batch_rows.append(saved)
                    self.log.emit(f"Сохранено: {Path(saved['txt']).name}, {Path(saved['srt']).name}, {Path(saved['json']).name}")
                    self.progress.emit(100)

                    if stopped:
                        self.log.emit("Обработка остановлена пользователем. Частичный результат сохранён.")
                        break

            if batch_rows:
                csv_path = self.settings.output_dir / "batch_transcripts.csv"
                with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
                    fields = ["file", "txt", "srt", "json", "mode", "model", "device", "compute_type", "beam_size", "segments", "chars", "partial"]
                    writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
                    writer.writeheader()
                    writer.writerows(batch_rows)
                self.log.emit(f"CSV сохранён: {csv_path}")

            self.finished_ok.emit("Готово. Результаты сохранены." if not self.stop_requested else "Остановлено. Частичный результат сохранён.")
        except Exception as e:
            self.failed.emit(str(e))

    def save_outputs(self, video: Path, segments, info, partial: bool):
        suffix = "_partial" if partial else ""
        stem = safe_stem(video) + suffix
        txt_path = self.settings.output_dir / f"{stem}.txt"
        srt_path = self.settings.output_dir / f"{stem}.srt"
        json_path = self.settings.output_dir / f"{stem}.json"
        txt = make_txt_with_times(segments)
        txt_path.write_text(txt, encoding="utf-8")
        srt_path.write_text(make_srt(segments), encoding="utf-8")
        json_path.write_text(json.dumps({
            "source_file": str(video),
            "partial": partial,
            "mode": self.settings.preset_label,
            "model": self.settings.model_name,
            "device": self.settings.device,
            "compute_type": self.settings.compute_type,
            "beam_size": self.settings.beam_size,
            "language": getattr(info, "language", "ru"),
            "language_probability": getattr(info, "language_probability", None),
            "segments": segments,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "file": str(video), "txt": str(txt_path), "srt": str(srt_path), "json": str(json_path),
            "mode": self.settings.preset_label, "model": self.settings.model_name, "device": self.settings.device,
            "compute_type": self.settings.compute_type, "beam_size": self.settings.beam_size,
            "segments": len(segments), "chars": len(txt), "partial": partial,
        }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ensure_dirs()
        self.files: list[Path] = []
        self.worker: Optional[TranscribeWorker] = None
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1160, 760)
        self.setMinimumSize(QSize(900, 620))
        self._build_ui()
        self.apply_preset(self.preset_combo.currentText())

    def _build_ui(self):
        central = QWidget()
        central.setStyleSheet(f"background:{BG};")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 10, 12, 8)
        root.setSpacing(7)

        root.addWidget(self._build_header())
        root.addWidget(self._build_file_card())
        root.addWidget(self._build_settings_card())
        root.addWidget(self._build_actions())
        root.addWidget(self._build_progress_card())
        root.addWidget(self._build_editors(), 1)
        root.addWidget(self._build_footer())

    def _build_header(self):
        card = GlassCard()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        logo = QLabel("RK")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(46, 46)
        logo.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f172a, stop:1 #111111);
                color: white;
                border-radius: 14px;
                font-size: 18px;
                font-weight: 800;
            }
        """)
        layout.addWidget(logo, 0, Qt.AlignTop)

        text_wrap = QVBoxLayout()
        text_wrap.setSpacing(5)
        title = QLabel("Transcriber Pro")
        title.setStyleSheet(f"color:{TEXT}; font-size:21px; font-weight:800; letter-spacing:-0.4px;")
        subtitle = QLabel("Локальная транскрибация WEBM / MP4 / WAV: пакетная обработка, таймкоды, TXT/SRT/JSON")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        text_wrap.addWidget(title)
        text_wrap.addWidget(subtitle)
        layout.addLayout(text_wrap, 1)

        badge = QLabel(f"Portable • {APP_VERSION}")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedHeight(26)
        badge.setStyleSheet("""
            QLabel {
                background: #f5f7fb;
                color: #111111;
                border: 1px solid #e7ebf1;
                border-radius: 12px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
            }
        """)
        layout.addWidget(badge, 0, Qt.AlignTop)
        return card

    def _build_file_card(self):
        card = GlassCard()
        outer = QVBoxLayout(card)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(6)

        top = QGridLayout()
        top.setHorizontalSpacing(8)
        top.setVerticalSpacing(8)

        self.btn_add = make_button("+ Добавить файлы", primary=True)
        self.btn_clear = make_button("Очистить")
        self.btn_out = make_button("Папка результата")
        self.btn_open_out = make_button("Открыть")
        self.out_edit = QLineEdit(str(OUTPUT_DIR))
        self.out_edit.setReadOnly(True)
        self.out_edit.setMinimumHeight(31)
        self.out_edit.setStyleSheet(self._input_css())

        top.addWidget(self.btn_add, 0, 0)
        top.addWidget(self.btn_clear, 0, 1)
        top.addWidget(self.btn_out, 0, 2)
        top.addWidget(self.out_edit, 0, 3)
        top.addWidget(self.btn_open_out, 0, 4)
        top.setColumnStretch(3, 1)
        outer.addLayout(top)

        self.file_list = DropListWidget()
        self.file_list.setStyleSheet(self._list_css())
        self.file_list.files_dropped.connect(self.add_paths)
        self.file_list.setMaximumHeight(58)
        outer.addWidget(self.file_list)

        note = QLabel("Перетащите WEBM/MP4/WAV в список или добавьте через кнопку. Несколько файлов будут обработаны по очереди.")
        note.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        outer.addWidget(note)

        self.btn_add.clicked.connect(self.select_files)
        self.btn_clear.clicked.connect(self.clear_files)
        self.btn_out.clicked.connect(self.select_output_dir)
        self.btn_open_out.clicked.connect(self.open_output_dir)
        return card

    def _build_settings_card(self):
        card = GlassCard()
        grid = QGridLayout(card)
        grid.setContentsMargins(14, 10, 14, 10)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(QUALITY_PRESETS.keys()))
        self.preset_combo.setCurrentText("Качественно / medium")
        self.model_combo = QComboBox()
        self.model_combo.addItems(["small", "medium", "large-v3"])
        self.device_combo = QComboBox()
        self.device_combo.setEditable(True)
        self.device_combo.addItems(["cpu", "cuda"])
        self.compute_combo = QComboBox()
        self.compute_combo.setEditable(True)
        self.compute_combo.addItems(["int8", "float16", "float32"])
        self.beam_spin = QSpinBox()
        self.beam_spin.setRange(1, 10)
        self.beam_spin.setValue(5)
        self.normalize_check = QCheckBox("Нормализация звука loudnorm")
        self.auto_download_check = QCheckBox("Автоскачивание модели")
        self.auto_download_check.setChecked(True)

        widgets = [self.preset_combo, self.model_combo, self.device_combo, self.compute_combo, self.beam_spin]
        for w in widgets:
            w.setMinimumHeight(31)
            w.setStyleSheet(self._combo_css() if isinstance(w, QComboBox) else self._spin_css())
        for cb in [self.normalize_check, self.auto_download_check]:
            cb.setStyleSheet(self._check_css())

        grid.addWidget(self._label("Режим"), 0, 0)
        grid.addWidget(self.preset_combo, 0, 1)
        grid.addWidget(self._label("Модель"), 0, 2)
        grid.addWidget(self.model_combo, 0, 3)
        grid.addWidget(self._label("Device"), 0, 4)
        grid.addWidget(self.device_combo, 0, 5)
        grid.addWidget(self._label("Compute"), 1, 0)
        grid.addWidget(self.compute_combo, 1, 1)
        grid.addWidget(self._label("Beam size"), 1, 2)
        grid.addWidget(self.beam_spin, 1, 3)
        grid.addWidget(self.normalize_check, 1, 4)
        grid.addWidget(self.auto_download_check, 1, 5)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        grid.setColumnStretch(5, 1)

        self.preset_combo.currentTextChanged.connect(self.apply_preset)
        return card

    def _build_actions(self):
        wrap = QWidget()
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(9)

        self.btn_start = make_button("Старт", primary=True)
        self.btn_stop = make_button("Стоп и сохранить", danger=True)
        self.btn_stop.setEnabled(False)
        self.btn_copy_text = make_button("Копировать текст")
        self.btn_copy_log = make_button("Копировать лог")

        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_copy_log.clicked.connect(lambda: QApplication.clipboard().setText(self.log_box.toPlainText()))
        self.btn_copy_text.clicked.connect(lambda: QApplication.clipboard().setText(self.transcript.toPlainText()))

        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)
        layout.addWidget(self.btn_copy_text)
        layout.addWidget(self.btn_copy_log)

        self.status_card = GlassCard()
        status_layout = QHBoxLayout(self.status_card)
        status_layout.setContentsMargins(10, 6, 10, 6)
        self.status_label = QLabel("Готов к работе. Выберите файл и нажмите Старт.")
        self.status_label.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        status_layout.addWidget(self.status_label)
        layout.addWidget(self.status_card, 1)
        return wrap

    def _build_progress_card(self):
        card = GlassCard()
        outer = QVBoxLayout(card)
        outer.setContentsMargins(14, 9, 14, 9)
        outer.setSpacing(6)

        top = QHBoxLayout()
        title = QLabel("Статистика обработки")
        title.setStyleSheet(f"color:{TEXT}; font-size:13px; font-weight:800;")
        self.progress_info = QLabel("0%")
        self.progress_info.setStyleSheet(f"color:{MUTED}; font-size:12px; font-weight:700;")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(self.progress_info)
        outer.addLayout(top)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setStyleSheet("""
            QProgressBar { background: #eceff3; border: 0; border-radius: 6px; }
            QProgressBar::chunk { background: #111111; border-radius: 6px; }
        """)
        outer.addWidget(self.progress)

        chips = QHBoxLayout()
        self.file_chip = self._make_stat_chip("Файлы: 0 / 0", TEXT)
        self.time_chip = self._make_stat_chip("Обработано: —", ACCENT_BLUE)
        self.speed_chip = self._make_stat_chip("Скорость: —", SUCCESS)
        self.eta_chip = self._make_stat_chip("Осталось: —", WARNING)
        self.segment_chip = self._make_stat_chip("Фрагменты: 0", TEXT)
        for chip in [self.file_chip, self.time_chip, self.speed_chip, self.eta_chip, self.segment_chip]:
            chips.addWidget(chip)
        outer.addLayout(chips)
        return card

    def _build_editors(self):
        splitter = QSplitter(Qt.Vertical)
        self.transcript = QPlainTextEdit()
        self.transcript.setPlaceholderText("Здесь будет появляться расшифровка с таймкодами...")
        self.transcript.setReadOnly(True)
        self.transcript.setStyleSheet(self._editor_css())
        self.log_box = QPlainTextEdit()
        self.log_box.setPlaceholderText("Лог процесса. Можно выделять и копировать.")
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet(self._editor_css())
        splitter.addWidget(self._wrap_editor("Лог", self.log_box))
        splitter.addWidget(self._wrap_editor("Расшифровка", self.transcript))
        splitter.setSizes([230, 650])
        return splitter

    def _build_footer(self):
        wrap = QWidget()
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.addStretch()
        footer = QLabel('<a href="mailto:rkostrov@yandex.ru" style="color:#6b7280; text-decoration:none;">Created by Roman Kostrov • rkostrov@yandex.ru</a>')
        footer.setOpenExternalLinks(True)
        footer.setStyleSheet("font-size:12px;")
        layout.addWidget(footer)
        return wrap

    def _wrap_editor(self, title: str, editor: QPlainTextEdit) -> GlassCard:
        card = GlassCard(radius=14)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 7, 10, 9)
        label = QLabel(title)
        label.setStyleSheet(f"color:{TEXT}; font-size:12px; font-weight:800;")
        layout.addWidget(label)
        layout.addWidget(editor, 1)
        return card

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{TEXT}; font-size:12px; font-weight:700;")
        return lbl

    def _make_stat_chip(self, text: str, color: str):
        chip = QFrame()
        chip.setStyleSheet("""
            QFrame { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 14px; }
        """)
        lay = QHBoxLayout(chip)
        lay.setContentsMargins(10, 6, 10, 6)
        label = QLabel(text)
        label.setStyleSheet(f"color:{color}; font-size:12px; font-weight:800;")
        lay.addWidget(label)
        chip.label = label
        return chip

    def _input_css(self):
        return f"""
            QLineEdit {{ background:#ffffff; border:1px solid #e5e7eb; border-radius:11px; padding:6px 10px; color:{TEXT}; font-size:12px; }}
            QLineEdit:focus {{ border:1px solid #c7d2fe; }}
        """

    def _combo_css(self):
        return f"""
            QComboBox {{ background:#ffffff; border:1px solid #e5e7eb; border-radius:11px; padding:6px 9px; color:{TEXT}; font-size:12px; }}
            QComboBox::drop-down {{ border:none; width:26px; }}
            QComboBox QAbstractItemView {{ background:white; border:1px solid #e5e7eb; selection-background-color:#eef2ff; padding:6px; }}
        """

    def _spin_css(self):
        return f"QSpinBox {{ background:#ffffff; border:1px solid #e5e7eb; border-radius:11px; padding:6px 9px; color:{TEXT}; font-size:12px; }}"

    def _check_css(self):
        return f"QCheckBox {{ color:{TEXT}; spacing:6px; font-size:12px; font-weight:600; }} QCheckBox::indicator {{ width:15px; height:15px; }}"

    def _list_css(self):
        return f"""
            QListWidget {{ background:#ffffff; alternate-background-color:#fafbfc; border:1px solid #edf0f4; border-radius:16px; color:{TEXT}; font-size:12px; padding:5px; }}
            QListWidget::item {{ padding:5px; border-radius:8px; }}
            QListWidget::item:selected {{ background:#eef2ff; color:{TEXT}; }}
        """

    def _editor_css(self):
        return f"""
            QPlainTextEdit {{ background:#ffffff; border:1px solid #edf0f4; border-radius:16px; padding:8px; color:{TEXT}; font-family:'Consolas','Segoe UI'; font-size:12px; }}
            QPlainTextEdit::selection {{ background:#eef2ff; color:{TEXT}; }}
        """

    def apply_preset(self, label: str):
        preset = QUALITY_PRESETS.get(label)
        if not preset:
            return
        self.model_combo.setCurrentText(preset["model"])
        self.beam_spin.setValue(preset["beam"])
        self.compute_combo.setCurrentText(preset["compute"])

    def select_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Выберите файлы", str(Path.home()),
            "Видео и аудио (*.webm *.mp4 *.mkv *.wav *.mp3 *.m4a);;Все файлы (*.*)"
        )
        self.add_paths(paths)

    def add_paths(self, paths):
        for p in paths:
            path = Path(p)
            if path.exists() and path not in self.files:
                self.files.append(path)
                self.file_list.addItem(QListWidgetItem(str(path)))
        self.file_chip.label.setText(f"Файлы: 0 / {len(self.files)}")

    def clear_files(self):
        if self.worker and self.worker.isRunning():
            return
        self.files.clear()
        self.file_list.clear()
        self.file_chip.label.setText("Файлы: 0 / 0")

    def select_output_dir(self):
        p = QFileDialog.getExistingDirectory(self, "Папка для результата", self.out_edit.text())
        if p:
            self.out_edit.setText(p)

    def open_output_dir(self):
        path = Path(self.out_edit.text())
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def log(self, text: str):
        self.log_box.appendPlainText(text)
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def add_transcript(self, text: str):
        self.transcript.appendPlainText(text)
        self.transcript.verticalScrollBar().setValue(self.transcript.verticalScrollBar().maximum())

    def update_stats(self, data: dict):
        file_index = data.get("file_index", 0)
        total_files = data.get("total_files", len(self.files))
        processed = data.get("processed")
        duration = data.get("duration")
        speed = data.get("speed", 0)
        eta = data.get("eta")
        segments = data.get("segments", 0)
        self.file_chip.label.setText(f"Файлы: {file_index} / {total_files}")
        self.time_chip.label.setText(f"Обработано: {fmt_duration(processed)} / {fmt_duration(duration)}")
        self.speed_chip.label.setText(f"Скорость: x{speed:.2f}")
        self.eta_chip.label.setText(f"Осталось: {fmt_duration(eta)}")
        self.segment_chip.label.setText(f"Фрагменты: {segments}")
        self.status_label.setText(f"Обработка: {fmt_duration(processed)} из {fmt_duration(duration)} · скорость x{speed:.2f}")

    def start(self):
        if not self.files:
            QMessageBox.warning(self, APP_NAME, "Сначала выберите один или несколько файлов.")
            return
        settings = JobSettings(
            output_dir=Path(self.out_edit.text()),
            preset_label=self.preset_combo.currentText(),
            model_name=self.model_combo.currentText().strip(),
            device=self.device_combo.currentText().strip() or "cpu",
            compute_type=self.compute_combo.currentText().strip() or "int8",
            beam_size=int(self.beam_spin.value()),
            normalize_audio=self.normalize_check.isChecked(),
            auto_download=self.auto_download_check.isChecked(),
        )
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_add.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.progress.setValue(0)
        self.progress_info.setText("0%")
        self.status_label.setText("Запуск...")
        self.log_box.clear()
        self.transcript.clear()
        self.worker = TranscribeWorker(list(self.files), settings)
        self.worker.log.connect(self.log)
        self.worker.transcript_line.connect(self.add_transcript)
        self.worker.progress.connect(self.on_progress)
        self.worker.stats.connect(self.update_stats)
        self.worker.file_started.connect(lambda f: self.status_label.setText(f"Файл: {f}"))
        self.worker.finished_ok.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_progress(self, value: int):
        self.progress.setValue(value)
        self.progress_info.setText(f"{value}%")

    def stop(self):
        if self.worker and self.worker.isRunning():
            self.btn_stop.setEnabled(False)
            self.worker.request_stop()

    def on_finished(self, message: str):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_add.setEnabled(True)
        self.btn_clear.setEnabled(True)
        self.status_label.setText(message)
        self.log(message)
        QMessageBox.information(self, APP_NAME, message)

    def on_failed(self, error: str):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_add.setEnabled(True)
        self.btn_clear.setEnabled(True)
        self.status_label.setText("Ошибка")
        self.log("ОШИБКА: " + error)
        QMessageBox.critical(self, APP_NAME, error)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont("Segoe UI", 9))
    app.setStyleSheet(f"""
        QLabel {{ color: {TEXT}; }}
        QMainWindow {{ background: {BG}; }}
        QToolTip {{ background:white; color:{TEXT}; border:1px solid #e5e7eb; padding:6px; }}
    """)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
