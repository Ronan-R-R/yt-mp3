"""Build a standalone Windows .exe with PyInstaller.

Run:  python build.py
Output:  dist/ytmp3.exe  (single file, no console window)
"""
import subprocess
import sys

ARGS = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name",
    "ytmp3",
    # yt-dlp loads extractors lazily and imageio-ffmpeg ships a binary;
    # collect both fully so the frozen exe has everything it needs.
    "--collect-all",
    "yt_dlp",
    "--collect-all",
    "imageio_ffmpeg",
    "app.py",
]

if __name__ == "__main__":
    raise SystemExit(subprocess.call(ARGS))
