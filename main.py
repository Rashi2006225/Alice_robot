import logging
import os
import tempfile
from pathlib import Path
from typing import Any, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from config import CORS_ORIGINS, MAX_AUDIO_MB, MAX_MESSAGE_CHARS
from groq_stt import GroqSTT, STTError
from llm import AliceLLM
from tts import TTS
from tts_config import TTS_MAX_CHARS

# CHANGE: print() ki jagah logging.
# WHY:    time + level + module name milta hai, debugging aasan hoti hai.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("alice.main")

app = FastAPI(title="Digital Twin Backend")

# CHANGE: origins ab config se. Default "*" (local demo ke liye theek).
# WHY:    deploy karte waqt .env mein CORS_ORIGINS=https://tumhari-site.com kar sakte ho.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

stt = GroqSTT()
llm = AliceLLM()

# CHANGE: TTS fail ho (key nahi / package issue) to server chalta rahe.
# WHY:    pehle poora server crash hota tha. Ab /tts 503 deta hai aur frontend
#         khud browser ki awaaz pe fallback kar leta hai.
try:
    tts = TTS()
except Exception as e:
    tts = None
    log.warning("TTS disabled (%s). Browser voice fallback use hogi.", e)

MAX_AUDIO_BYTES = MAX_AUDIO_MB * 1024 * 1024
ALLOWED_AUDIO_EXT = {".webm", ".mp4", ".m4a", ".ogg", ".wav", ".mp3"}


# CHANGE: dict ki jagah Pydantic models.
# WHY:    galat / bahut bada input automatic reject hota hai (422), manual checks nahi likhne padte.
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    history: List[Any] = Field(default_factory=list, max_length=100)


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=TTS_MAX_CHARS)


@app.get("/")
def home():
    # CHANGE: health check mein tts_ready bhi.  WHY: ek nazar mein pata chale kya chal raha hai.
    return {"status": "running", "message": "Digital Twin Backend Running", "tts_ready": tts is not None}


def _remove(path: str):
    try:
        os.remove(path)
    except OSError:
        pass


# Plain `def` endpoints threadpool mein chalte hain, to Groq / ElevenLabs ka wait server ko freeze nahi karta.
@app.post("/transcribe")
def transcribe(audio: UploadFile = File(...)):
    # CHANGE: extension whitelist.  WHY: filename se koi ajeeb extension / path nahi ghus sakta.
    suffix = Path(audio.filename or "").suffix.lower()
    if suffix not in ALLOWED_AUDIO_EXT:
        suffix = ".webm"

    fd, temp_file = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        # CHANGE: shutil.copyfileobj ki jagah 1MB chunks + size limit.
        # WHY:    pehle koi bhi GB-size file bhej ke disk bhar sakta tha.
        written = 0
        with open(temp_file, "wb") as buffer:
            while chunk := audio.file.read(1024 * 1024):
                written += len(chunk)
                if written > MAX_AUDIO_BYTES:
                    raise HTTPException(status_code=413, detail=f"Audio too large (max {MAX_AUDIO_MB} MB)")
                buffer.write(chunk)

        text = stt.transcribe(temp_file)

    except HTTPException:
        raise
    except STTError:
        # CHANGE: STT ka asli fail alag error (502) hai, "no speech" nahi.
        raise HTTPException(status_code=502, detail="Speech-to-text service failed")
    except Exception:
        log.exception("TRANSCRIBE ERROR")
        raise HTTPException(status_code=500, detail="Internal error while transcribing")
    finally:
        _remove(temp_file)

    if text is None:
        return {"success": False, "text": "", "error": "No speech detected."}

    log.info("TRANSCRIPT: %s", text)
    return {"success": True, "text": text}


@app.post("/chat")
def chat(req: ChatRequest):
    text = req.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty message")

    # CHANGE: charset + no-cache / no-buffering headers.
    # WHY:    Hindi text sahi decode ho, aur beech ka proxy stream ko rok kar ek saath na bheje.
    return StreamingResponse(
        llm.stream(text, req.history),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/tts")
def text_to_speech(req: TTSRequest):
    if tts is None:
        raise HTTPException(status_code=503, detail="TTS not configured")

    # CHANGE: temp mp3 file + BackgroundTask delete hata kar seedha bytes return.
    # WHY:    TTS ab cache + bytes deta hai, to disk pe file banana / delete karna bekaar tha.
    audio = tts.synthesize(req.text)
    if audio is None:
        raise HTTPException(status_code=502, detail="TTS failed")
    return Response(content=audio, media_type="audio/mpeg")