"""ytmp3 for Android - a Kivy app that saves YouTube audio locally.

Android has no reliable bundled ffmpeg, so this saves the audio in its native
container (m4a/opus) with no conversion. Everything runs on the device, so there
is no server to get blocked.
"""
import os
import threading

from kivy.app import App
from kivy.clock import mainthread
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.textinput import TextInput

import yt_dlp

try:
    from android.permissions import Permission, request_permissions
    from android.storage import primary_external_storage_path

    ANDROID = True
except ImportError:
    ANDROID = False


def output_dir() -> str:
    if ANDROID:
        target = os.path.join(primary_external_storage_path(), "Music")
        os.makedirs(target, exist_ok=True)
        return target
    return os.path.join(os.path.expanduser("~"), "Downloads")


class YtMp3App(App):
    def build(self):
        self.title = "ytmp3"
        root = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(14))

        root.add_widget(Label(text="ytmp3", font_size="28sp", size_hint_y=None, height=dp(48), bold=True))
        root.add_widget(
            Label(
                text="Paste a YouTube link to save the audio.",
                font_size="14sp",
                size_hint_y=None,
                height=dp(24),
            )
        )

        self.url_input = TextInput(
            hint_text="https://youtube.com/watch?v=...",
            multiline=False,
            size_hint_y=None,
            height=dp(48),
            font_size="16sp",
        )
        root.add_widget(self.url_input)

        self.button = Button(text="Download", size_hint_y=None, height=dp(52), font_size="18sp")
        self.button.bind(on_release=self.on_download)
        root.add_widget(self.button)

        self.progress = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(20))
        root.add_widget(self.progress)

        self.status = Label(text="", font_size="13sp")
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
