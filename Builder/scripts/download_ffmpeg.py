import os
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
BIN.mkdir(exist_ok=True)

ffmpeg = BIN / "ffmpeg.exe"
ffprobe = BIN / "ffprobe.exe"
if ffmpeg.exists() and ffprobe.exists():
    print("FFmpeg already exists in bin/")
    raise SystemExit(0)

URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
TMP = ROOT / "_ffmpeg_download.zip"
EXTRACT = ROOT / "_ffmpeg_extract"

print("Downloading FFmpeg...")
print(URL)
urllib.request.urlretrieve(URL, TMP)

if EXTRACT.exists():
    shutil.rmtree(EXTRACT)
EXTRACT.mkdir(exist_ok=True)

print("Extracting FFmpeg...")
with zipfile.ZipFile(TMP, "r") as z:
    z.extractall(EXTRACT)

found_ffmpeg = None
found_ffprobe = None
for p in EXTRACT.rglob("*.exe"):
    if p.name.lower() == "ffmpeg.exe":
        found_ffmpeg = p
    elif p.name.lower() == "ffprobe.exe":
        found_ffprobe = p

if not found_ffmpeg:
    raise RuntimeError("ffmpeg.exe was not found in downloaded archive")

shutil.copy2(found_ffmpeg, ffmpeg)
if found_ffprobe:
    shutil.copy2(found_ffprobe, ffprobe)

TMP.unlink(missing_ok=True)
shutil.rmtree(EXTRACT, ignore_errors=True)
print(f"Ready: {ffmpeg}")
if ffprobe.exists():
    print(f"Ready: {ffprobe}")
