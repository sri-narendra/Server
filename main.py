from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import qr, youtube, tts, classbot, logs   # 👈 include new router

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
def ping():
    return {"status": "ok"}

# Register routers
app.include_router(qr.router, prefix="/qr", tags=["QR Code"])
app.include_router(youtube.router, prefix="/youtube", tags=["YouTube"])
app.include_router(tts.router, prefix="/tts", tags=["Text-to-Speech"])
app.include_router(classbot.router, prefix="/classbot", tags=["ClassBot"])
app.include_router(logs.router, prefix="", tags=["Logs"])

# Add this at the end of main.py
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)