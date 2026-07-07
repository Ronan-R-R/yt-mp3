# ytmp3

Static frontend (GitHub Pages) + yt-dlp backend (Render). Paste a YouTube link, get an MP3.

GitHub Pages is static only, so the actual download and conversion run on a small backend. The frontend just calls it.

## Layout

- `docs/` - static site served by GitHub Pages
- `backend/` - FastAPI + yt-dlp, containerised with ffmpeg for Render

## Deploy the backend (Render, free)

1. Push this repo to GitHub (see below).
2. On https://render.com create a new **Web Service** from the repo.
3. Render reads `backend/render.yaml`. Runtime is Docker, plan free.
4. Set the env var `FRONTEND_ORIGIN` to your Pages URL, e.g. `https://ronanr2003.github.io`.
5. Deploy. Note the service URL, e.g. `https://yt-mp3-api.onrender.com`.

Free instances sleep after inactivity; the first request after idle takes ~30s to wake.

## Deploy the frontend (GitHub Pages)

1. Edit `docs/config.js` and set `window.BACKEND_URL` to your Render URL.
2. Commit and push.
3. Repo **Settings > Pages**: Source = Deploy from a branch, Branch = `main`, Folder = `/docs`.
4. Site goes live at `https://<user>.github.io/<repo>/`.

## Run locally

Backend needs Python 3.12+ and ffmpeg on PATH.

```
cd backend
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Then open `docs/index.html` with `BACKEND_URL` pointing at `http://localhost:8000`.

## Notes

- Only download audio you have the rights to. This violates YouTube's ToS otherwise.
- Backend validates the URL, caps duration (`MAX_DURATION_SECONDS`), rate-limits to 10/min per IP, and locks CORS to `FRONTEND_ORIGIN`.
