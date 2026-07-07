# ytmp3

A small Windows desktop app that saves YouTube audio as MP3. It runs entirely on
your machine with yt-dlp and a bundled ffmpeg, so there's no server to get blocked
and nothing to install beyond the app itself.

An earlier hosted version was scrapped: YouTube blocks downloads from datacenter
IPs, so a cloud backend can't reliably fetch anything. Running locally from a normal
home connection avoids that.

## Use it

Grab `ytmp3.exe` from the [latest release](https://github.com/Ronan-R-R/yt-mp3/releases/latest),
open it, paste a link, pick a folder, hit Download.

## Run from source

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Build the exe

```
pip install pyinstaller
python build.py
```

Output is `dist/ytmp3.exe`, a single file with Python, yt-dlp and ffmpeg bundled in.
Upload it to a GitHub release so the download page (`docs/`, served via GitHub Pages)
links to it.

## Notes

- Only download audio you have the rights to. This breaks YouTube's ToS otherwise.
- `docs/` is a static download page deployed by `.github/workflows/pages.yml`.
