"""ytmp3 - a small desktop app to save YouTube audio as MP3.

Runs entirely on the user's machine using yt-dlp and a bundled ffmpeg,
so there is no server to block and nothing to install beyond this app.
"""
from __future__ import annotations

import os
import queue
import threading
from pathlib import Path
from tkinter import StringVar, Tk, filedialog, messagebox, ttk

import imageio_ffmpeg
import yt_dlp

APP_TITLE = "ytmp3"
QUALITIES = ["320", "256", "192", "128"]
YT_PREFIXES = ("http://", "https://")

# Warm near-black control-panel palette with an amber accent (matches the web page).
BG = "#1b1915"
SURFACE = "#25221b"
SURFACE2 = "#312c23"
LINE = "#463f34"
TEXT = "#f3efe8"
MUTED = "#a49a8b"
ACCENT = "#f2b23a"
ACCENT_PRESS = "#d69a29"
INK = "#1b1710"
SANS = "Segoe UI"
MONO = "Consolas"


def default_output_dir() -> str:
    music = Path.home() / "Music"
    target = music if music.exists() else Path.home() / "Downloads"
    return str(target if target.exists() else Path.home())


class App:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None

        root.title(APP_TITLE)
        root.geometry("600x380")
        root.minsize(520, 360)
        root.configure(bg=BG, padx=32, pady=28)

        self.url_var = StringVar()
        self.dir_var = StringVar(value=default_output_dir())
        self.quality_var = StringVar(value="192")
        self.status_var = StringVar(value="Paste a YouTube link and hit rip.")

        self._style()
        self._build_ui()
        self.root.after(100, self._drain_events)

    def _style(self) -> None:
        self.root.option_add("*TCombobox*Listbox.background", SURFACE)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", INK)

        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=TEXT, font=(SANS, 10))
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=TEXT)
        s.configure("Kicker.TLabel", background=BG, foreground=ACCENT, font=(MONO, 9))
        s.configure("Muted.TLabel", background=BG, foreground=MUTED, font=(MONO, 9))
        s.configure("Word.TLabel", background=BG, foreground=TEXT, font=(SANS, 34, "bold"))
        s.configure("WordAccent.TLabel", background=BG, foreground=ACCENT, font=(SANS, 34, "bold"))

        s.configure(
            "TEntry", fieldbackground=SURFACE, foreground=TEXT, insertcolor=ACCENT,
            bordercolor=LINE, lightcolor=LINE, darkcolor=LINE, borderwidth=1, padding=8,
        )
        s.map("TEntry", bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)])

        s.configure(
            "TCombobox", fieldbackground=SURFACE, background=SURFACE2, foreground=TEXT,
            arrowcolor=TEXT, bordercolor=LINE, lightcolor=LINE, darkcolor=LINE, padding=6,
        )
        s.map("TCombobox", fieldbackground=[("readonly", SURFACE)], foreground=[("readonly", TEXT)])

        s.configure(
            "TButton", background=SURFACE2, foreground=TEXT, bordercolor=LINE,
            focuscolor=BG, borderwidth=1, padding=(12, 6),
        )
        s.map("TButton", background=[("active", LINE)])

        s.configure(
            "Accent.TButton", background=ACCENT, foreground=INK, focuscolor=ACCENT,
            font=(SANS, 12, "bold"), borderwidth=0, padding=(12, 12),
        )
        s.map(
            "Accent.TButton",
            background=[("active", ACCENT_PRESS), ("disabled", SURFACE2)],
            foreground=[("disabled", MUTED)],
        )

        s.configure(
            "Amber.Horizontal.TProgressbar", troughcolor=SURFACE, background=ACCENT,
            bordercolor=LINE, lightcolor=ACCENT, darkcolor=ACCENT,
        )

    def _build_ui(self) -> None:
        root = self.root
        root.columnconfigure(0, weight=1)

        ttk.Label(root, text="LOCAL AUDIO RIPPER // V1", style="Kicker.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        word = ttk.Frame(root)
        word.grid(row=1, column=0, sticky="w", pady=(2, 18))
        ttk.Label(word, text="yt", style="Word.TLabel").grid(row=0, column=0)
        ttk.Label(word, text="mp3", style="WordAccent.TLabel").grid(row=0, column=1)

        url_entry = ttk.Entry(root, textvariable=self.url_var, font=(SANS, 11))
        url_entry.grid(row=2, column=0, sticky="ew")
        url_entry.focus()
        url_entry.bind("<Return>", lambda _event: self.start())

        options = ttk.Frame(root)
        options.grid(row=3, column=0, sticky="ew", pady=16)
        options.columnconfigure(1, weight=1)

        ttk.Label(options, text="SAVE TO", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(options, textvariable=self.dir_var, style="Muted.TLabel").grid(
            row=0, column=1, sticky="w", padx=10
        )
        ttk.Button(options, text="Change", command=self.choose_dir).grid(row=0, column=2)

        ttk.Label(options, text="QUALITY", style="Muted.TLabel").grid(
            row=1, column=0, sticky="w", pady=(12, 0)
        )
        quality = ttk.Combobox(
            options, textvariable=self.quality_var, values=QUALITIES, state="readonly", width=8
        )
        quality.grid(row=1, column=1, sticky="w", padx=10, pady=(12, 0))

        self.download_btn = ttk.Button(
            root, text="Rip audio", command=self.start, style="Accent.TButton"
        )
        self.download_btn.grid(row=4, column=0, sticky="ew", pady=(6, 16))

        self.progress = ttk.Progressbar(
            root, mode="determinate", maximum=100, style="Amber.Horizontal.TProgressbar"
        )
        self.progress.grid(row=5, column=0, sticky="ew")

        ttk.Label(root, textvariable=self.status_var, style="Muted.TLabel").grid(
            row=6, column=0, sticky="w", pady=(12, 0)
        )

    def choose_dir(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.dir_var.get())
        if chosen:
            self.dir_var.set(chosen)

    def start(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        url = self.url_var.get().strip()
        if not url.startswith(YT_PREFIXES) or ("youtube.com" not in url and "youtu.be" not in url):
            messagebox.showwarning(APP_TITLE, "That doesn't look like a YouTube link.")
            return

        out_dir = self.dir_var.get()
        if not os.path.isdir(out_dir):
            messagebox.showwarning(APP_TITLE, "Pick a valid folder to save to.")
            return

        self._set_running(True)
        self.progress["value"] = 0
        self.status_var.set("Starting...")

        self.worker = threading.Thread(
            target=self._download, args=(url, out_dir, self.quality_var.get()), daemon=True
        )
        self.worker.start()

    def _set_running(self, running: bool) -> None:
        self.download_btn.configure(
            state="disabled" if running else "normal",
            text="Working..." if running else "Rip audio",
        )

    def _progress_hook(self, data: dict) -> None:
        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            done = data.get("downloaded_bytes", 0)
            if total:
                self.events.put(("progress", done / total * 100))
            self.events.put(("status", "Downloading audio..."))
        elif status == "finished":
            self.events.put(("progress", 100.0))
            self.events.put(("status", "Converting to MP3..."))

    def _download(self, url: str, out_dir: str, quality: str) -> None:
        opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
            "extractor_args": {"youtube": {"player_client": ["default", "android"]}},
            "progress_hooks": [self._progress_hook],
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": quality}
            ],
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            title = info.get("title", "audio") if info else "audio"
            self.events.put(("done", title))
        except yt_dlp.utils.DownloadError:
            self.events.put(("error", "Could not fetch this video. Check the link and try again."))
        except Exception as exc:  # noqa: BLE001 - report anything else cleanly to the user
            self.events.put(("error", f"Something went wrong: {exc}"))

    def _drain_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "progress":
                    self.progress["value"] = payload
                elif kind == "status":
                    self.status_var.set(str(payload))
                elif kind == "done":
                    self.progress["value"] = 100
                    self.status_var.set(f"Done: {payload}")
                    self._set_running(False)
                    messagebox.showinfo(APP_TITLE, "Saved to your folder.")
                elif kind == "error":
                    self.progress["value"] = 0
                    self.status_var.set("Failed.")
                    self._set_running(False)
                    messagebox.showerror(APP_TITLE, str(payload))
        except queue.Empty:
            pass
        self.root.after(100, self._drain_events)


def _selftest(url: str, out_dir: str) -> int:
    """Headless download used to verify a build. Returns a process exit code."""
    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
        "extractor_args": {"youtube": {"player_client": ["default", "android"]}},
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ],
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)
    except Exception as exc:  # noqa: BLE001 - selftest reports any failure
        Path(out_dir, "selftest.log").write_text(f"FAIL: {exc}", encoding="utf-8")
        return 1
    return 0


def main() -> None:
    import sys

    if len(sys.argv) >= 4 and sys.argv[1] == "--selftest":
        raise SystemExit(_selftest(sys.argv[2], sys.argv[3]))

    root = Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
