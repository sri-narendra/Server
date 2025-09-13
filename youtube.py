from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask
import yt_dlp, os, uuid

router = APIRouter()

@router.get("/download")
async def download_video(url: str = Query(...), quality: str = Query("best")):
    vid_id = str(uuid.uuid4())
    filename = ""

    headers = {"User-Agent": "Mozilla/5.0 Chrome/120 Safari/537.36"}

    if quality == "audio":
        filename = f"{vid_id}.mp3"
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
            "outtmpl": filename,
            "http_headers": headers,
        }
    elif quality == "720p":
        filename = f"{vid_id}.mp4"
        ydl_opts = {"format": "bestvideo[height<=720]+bestaudio/best", "merge_output_format": "mp4", "outtmpl": filename, "http_headers": headers}
    elif quality == "480p":
        filename = f"{vid_id}.mp4"
        ydl_opts = {"format": "bestvideo[height<=480]+bestaudio/best", "merge_output_format": "mp4", "outtmpl": filename, "http_headers": headers}
    else:
        filename = f"{vid_id}.mp4"
        ydl_opts = {"format": "best", "outtmpl": filename, "http_headers": headers}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.params["socket_timeout"] = 60
            ydl.download([url])

        return FileResponse(
            filename,
            media_type="audio/mpeg" if quality == "audio" else "video/mp4",
            filename=f"youtube_video.{filename.split('.')[-1]}",
            background=BackgroundTask(os.remove, filename),
        )
    except Exception as e:
        error_msg = str(e)
        if "login" in error_msg.lower() or "cookies" in error_msg.lower():
            return JSONResponse({"error": "❌ Video requires login/authentication."}, status_code=403)
        return JSONResponse({"error": f"Download failed: {error_msg}"}, status_code=500)
