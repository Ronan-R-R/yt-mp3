"""ytmp3 for Android - a Kivy app that saves YouTube audio locally.

Android has no reliable bundled ffmpeg, so this saves the audio in its native
container (m4a/opus) with no conversion. Everything runs on the device, so there
is no server to get blocked.
"""
import os
import threading

from kivy.app import App
from kivy.clock import mainthread
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

import yt_dlp

try:
    from android.permissions import Permission, request_permissions
    from android.storage import primary_external_storage_path

    ANDROID = True
except ImportError:
    ANDROID = False

# Warm near-black control-panel palette with an amber accent (matches the web page).
BG = (0.106, 0.098, 0.082, 1)
SURFACE = (0.145, 0.133, 0.106, 1)
LINE = (0.275, 0.247, 0.204, 1)
TEXT = (0.953, 0.937, 0.910, 1)
MUTED = (0.643, 0.604, 0.545, 1)
ACCENT = (0.949, 0.698, 0.227, 1)
INK = (0.106, 0.090, 0.063, 1)


def output_dir() -> str:
    if ANDROID:
        target = os.path.join(primary_external_storage_path(), "Music")
        os.makedirs(target, exist_ok=True)
        return target
    return os.path.join(os.path.expanduser("~"), "Downloads")


class Bar(Widget):
    """Custom amber progress bar; Kivy's default one can't be recoloured cleanly."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._value = 0.0
        with self.canvas:
            Color(*SURFACE)
            self._trough = RoundedRectangle(radius=[dp(4)])
            Color(*ACCENT)
            self._fill = RoundedRectangle(radius=[dp(4)])
        self.bind(pos=self._redraw, size=self._redraw)

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, v: float) -> None:
        self._value = max(0.0, min(100.0, v))
        self._redraw()

    def _redraw(self, *_args) -> None:
        self._trough.pos = self.pos
        self._trough.size = self.size
        self._fill.pos = self.pos
        self._fill.size = (self.width * self._value / 100.0, self.height)


class YtMp3App(App):
    def build(self):
        self.title = "ytmp3"
        Window.clearcolor = BG

        root = BoxLayout(orientation="vertical", padding=dp(28), spacing=dp(16))

        root.add_widget(
            Label(
                text="LOCAL AUDIO RIPPER",
                font_size="12sp",
                color=ACCENT,
                halign="left",
                size_hint_y=None,
                height=dp(20),
                text_size=(Window.width - dp(56), None),
            )
        )
        root.add_widget(
            Label(
                text="yt[color=f2b23a]mp3[/color]",
                markup=True,
                font_size="44sp",
                bold=True,
                color=TEXT,
                halign="left",
                size_hint_y=None,
                height=dp(60),
                text_size=(Window.width - dp(56), None),
            )
        )

        self.url_input = TextInput(
            hint_text="https://youtube.com/watch?v=...",
            multiline=False,
            size_hint_y=None,
            height=dp(52),
            font_size="16sp",
            padding=[dp(14), dp(15)],
            background_normal="",
            background_active="",
            background_color=SURFACE,
            foreground_color=TEXT,
            hint_text_color=MUTED,
            cursor_color=ACCENT,
        )
        root.add_widget(self.url_input)

        self.button = Button(
            text="Rip audio",
            size_hint_y=None,
            height=dp(56),
            font_size="18sp",
            bold=True,
            background_normal="",
            background_down="",
            background_color=ACCENT,
            color=INK,
        )
        self.button.bind(on_release=self.on_download)
        root.add_widget(self.button)

        self.progress = Bar(size_hint_y=None, height=dp(10))
        root.add_widget(self.progress)

        self.status = Label(
            text="Paste a YouTube link and hit rip.",
            font_size="13sp",
            color=MUTED,
            halign="left",
            valign="top",
            text_size=(Window.width - dp(56), None),
        )
        root.add_widget(self.status)

        return root

    def on_start(self) -> None:
        if ANDROID:
            request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])

    def on_download(self, _button) -> None:
        url = self.url_input.text.strip()
        if not url.startswith(("http://", "https://")) or (
            "youtube.com" not in url and "youtu.be" not in url
        ):
            self._set_status("That doesn't look like a YouTube link.")
            return

        self.button.disabled = True
        self.progress.value = 0
        self._set_status("Starting...")
        threading.Thread(target=self._download, args=(url,), daemon=True).start()

    def _progress_hook(self, data: dict) -> None:
        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            if total:
                self._set_progress(data.get("downloaded_bytes", 0) / total * 100)
            self._set_status("Downloading...")
        elif data.get("status") == "finished":
            self._set_progress(100)
            self._set_status("Saving...")

    def _download(self, url: str) -> None:
        opts = {
            "format": "bestaudio[ext=m4a]/bestaudio",
            "outtmpl": os.path.join(output_dir(), "%(title)s.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {"youtube": {"player_client": ["android", "default"]}},
            "progress_hooks": [self._progress_hook],
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            title = info.get("title", "audio") if info else "audio"
            self._done(f"Saved: {title}")
        except yt_dlp.utils.DownloadError:
            self._done("Could not fetch this video. Check the link.")
        except Exception as exc:  # noqa: BLE001 - report anything else to the user
            self._done(f"Something went wrong: {exc}")

    @mainthread
    def _set_status(self, text: str) -> None:
        self.status.text = text

    @mainthread
    def _set_progress(self, value: float) -> None:
        self.progress.value = value

    @mainthread
    def _done(self, text: str) -> None:
        self.status.text = text
        self.button.disabled = False


if __name__ == "__main__":
    YtMp3App().run()
