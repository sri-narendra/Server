from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask
from gtts import gTTS
import os, uuid

router = APIRouter()

@router.get("/speak")
async def text_to_speech(text: str = Query(...), format: str = Query("mp3")):
    tts_id = str(uuid.uuid4())
    filename = f"{tts_id}.{format}"

    try:
        tts = gTTS(text)
        tts.save(filename)
        return FileResponse(
            filename,
            media_type="audio/mpeg" if format == "mp3" else "audio/wav",
            filename=f"tts.{format}",
            background=BackgroundTask(os.remove, filename),
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
