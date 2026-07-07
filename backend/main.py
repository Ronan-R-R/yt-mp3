import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse
import yt_dlp

# Only these origins may call the API. Set FRONTEND_ORIGIN to your Pages URL in prod.
_origins_env = os.environ.get("FRONTEND_ORIGIN", "http://localhost:8000")
ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]

# yt-dlp accepts many host variants; keep the allowlist tight to real YouTube domains.
_YT_HOST = re.compile(
    r"^(https?://)?(www\.|m\.|music\.)?(youtube\.com|youtu\.be)/", re.IGNORECASE
)

MAX_DURATION_SECONDS = int(os.environ.get("MAX_DURATION_SECONDS", "3600"))

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="yt-mp3", docs_url=None, redoc_url=None)
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"error": "Too many requests, slow down."})


class DownloadRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        value = value.strip()
        if not _YT_HOST.match(value):
            raise ValueError("Not a valid YouTube URL.")
        return value


def _safe_filename(title: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", title).strip()
    return (cleaned or "audio")[:120]


def _cleanup(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/download")
@limiter.limit("10/minute")
def download(request: Request, body: DownloadRequest, background: BackgroundTasks) -> FileResponse:
    work_dir = Path(tempfile.mkdtemp(prefix="ytmp3_"))
    background.add_task(_cleanup, work_dir)

    out_template = str(work_dir / f"{uuid.uuid4().hex}.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(body.url, download=False)
            duration: Optional[int] = info.get("duration") if info else None
            if duration and duration > MAX_DURATION_SECONDS:
                raise HTTPException(
                    status_code=413,
                    detail=f"Video too long (max {MAX_DURATION_SECONDS // 60} min).",
                )
            info = ydl.extract_info(body.url, download=True)
    except yt_dlp.utils.DownloadError as exc:
        # Log detail server-side; give the user a clean message.
        print(f"yt-dlp failed for {body.url}: {exc}")
        raise HTTPException(status_code=422, detail="Could not fetch this video.") from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - surface as generic 500, log the real cause
        print(f"Unexpected error for {body.url}: {exc}")
        raise HTTPException(status_code=500, detail="Something went wrong.") from exc

    mp3_files = list(work_dir.glob("*.mp3"))
    if not mp3_files:
        raise HTTPException(status_code=500, detail="Conversion failed.")

    title = _safe_filename(info.get("title", "audio") if info else "audio")
    return FileResponse(
        path=mp3_files[0],
        media_type="audio/mpeg",
        filename=f"{title}.mp3",
    )
