# logs.py
import asyncio
import logging
import sys
from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse

router = APIRouter()

# --- Logging setup (writes to app.log) ---
logger = logging.getLogger()  # root logger
logger.setLevel(logging.INFO)

# Make sure we don't add multiple handlers if imported twice
if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == "app.log"
           for h in logger.handlers):
    fh = logging.FileHandler("app.log")
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

# Optional: also log to console as before (uvicorn usually handles console)
# if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
#     sh = logging.StreamHandler(sys.stdout)
#     sh.setFormatter(formatter)
#     logger.addHandler(sh)

# Redirect print() and uncaught stderr to the log file so prints appear in app.log
class StreamToLogger:
    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level
        self._buffer = ""

    def write(self, buf):
        # write may be called with partial buffers; handle newlines
        self._buffer += buf
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line:
                self.logger.log(self.level, line)

    def flush(self):
        if self._buffer:
            self.logger.log(self.level, self._buffer)
            self._buffer = ""

# Replace stdout/stderr (only do once)
if not getattr(sys, "_redirected_to_logger", False):
    sys.stdout = StreamToLogger(logging.getLogger("STDOUT"), logging.INFO)
    sys.stderr = StreamToLogger(logging.getLogger("STDERR"), logging.ERROR)
    sys._redirected_to_logger = True

# --- SSE stream endpoint ---
async def tail_file_sse(path: str):
    """
    Async generator that yields Server-Sent Events as new lines are appended to the file.
    """
    # Make sure the file exists
    try:
        f = open(path, "r", encoding="utf-8")
    except FileNotFoundError:
        # If not present yet, create and open
        open(path, "a", encoding="utf-8").close()
        f = open(path, "r", encoding="utf-8")

    # Seek to the end so we only send new lines
    f.seek(0, 2)

    try:
        while True:
            line = f.readline()
            if line:
                # Send as SSE "data: <line>\n\n"
                # Escape any stray newlines inside line (we already read by line)
                yield f"data: {line.rstrip()}\n\n"
            else:
                await asyncio.sleep(0.5)
    finally:
        f.close()

@router.get("/logs/stream")
async def logs_stream():
    """
    SSE endpoint clients can connect to with EventSource to receive live log lines.
    """
    return StreamingResponse(tail_file_sse("app.log"), media_type="text/event-stream")

@router.get("/logs/raw")
async def logs_raw():
    """
    Download or view the whole raw log file.
    """
    return FileResponse("app.log", media_type="text/plain", filename="app.log")

# --- Simple HTML viewer (terminal-like) ---
LOG_VIEWER_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>App Logs (live)</title>
  <style>
    body { font-family: monospace; background: #0b1220; color: #e6edf3; margin: 0; padding: 0; }
    header { padding: 8px 12px; background: #06111a; border-bottom: 1px solid #123; }
    #log { padding: 12px; height: calc(100vh - 50px); overflow: auto; white-space: pre-wrap; }
    .line { display:block; padding:1px 0; }
    .ts { color: #89b4f8; }
    .info { color: #cdd9ff; }
    .error { color: #ffb4b4; }
    .debug { color: #b1f5c4; }
  </style>
</head>
<body>
  <header>
    <strong>Live app.log</strong> — <small>Server-Sent Events (SSE)</small>
    <button id="clearBtn" style="float:right;margin-top:-4px;">Clear view</button>
  </header>
  <div id="log"></div>

  <script>
    const logEl = document.getElementById('log');
    const clearBtn = document.getElementById('clearBtn');
    clearBtn.onclick = () => { logEl.innerText = ''; };

    // Connect to SSE stream (same origin)
    const evtSource = new EventSource('/logs/stream');

    evtSource.onmessage = function(e) {
      const text = e.data;
      // Simple color heuristics
      let cls = 'info';
      if (/error/i.test(text)) cls = 'error';
      else if (/debug/i.test(text)) cls = 'debug';
      else if (/warning|warn/i.test(text)) cls = 'error';

      const span = document.createElement('div');
      span.className = 'line ' + cls;
      span.textContent = text;
      logEl.appendChild(span);
      // Auto-scroll to bottom
      logEl.scrollTop = logEl.scrollHeight;
    };

    evtSource.onerror = function(e) {
      const span = document.createElement('div');
      span.className = 'line error';
      span.textContent = 'Connection lost. Retrying...';
      logEl.appendChild(span);
    };
  </script>
</body>
</html>
"""

@router.get("/logs/view")
async def logs_view():
    return HTMLResponse(LOG_VIEWER_HTML)
