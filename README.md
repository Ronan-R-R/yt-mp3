# ytmp3

Saves YouTube audio on your own device. It runs entirely locally with yt-dlp, so
there's no server to get blocked and nothing to install beyond the app.

- **Windows / Linux**: desktop app (`app.py`), converts to MP3 with a bundled ffmpeg.
- **Android**: Kivy app (`android/`), saves the native audio (m4a/opus) with no
  conversion, since Android has no reliable bundled ffmpeg.

An earlier hosted version was scrapped: YouTube blocks downloads from datacenter
IPs, so a cloud backend can't reliably fetch anything. Running on a normal device
connection avoids that.

## Use it

Grab your build from the [latest release](https://github.com/Ronan-R-R/yt-mp3/releases/latest):
open it, paste a link, pick a folder, download.

## Run the desktop app from source

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Releases (CI)

Push a tag and `.github/workflows/release.yml` builds all three and attaches them:

```
git tag v1.0.0
git push origin v1.0.0
```

Assets: `ytmp3-windows.exe`, `ytmp3-linux`, `ytmp3-android.apk`. The download page
links to these by stable name via `releases/latest/download/...`.

## Build locally

Desktop exe/binary:

```
pip install pyinstaller
python build.py        # -> dist/ytmp3(.exe)
```

Android APK (Linux only, needs buildozer + Android SDK/NDK):

```
cd android
pip install buildozer
buildozer android debug   # -> android/bin/*.apk
```

## Notes

- Only download audio you have the rights to. This breaks YouTube's ToS otherwise.
- The Android APK is unsigned debug output; Android will warn on install.
- `docs/` is a static download page deployed by `.github/workflows/pages.yml`.
