from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pathlib import Path
import os
import shutil
import tempfile

from groq_stt import GroqSTT
from llm import AliceLLM
from tts import TTS

app = FastAPI(title="Digital Twin Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

stt = GroqSTT()
llm = AliceLLM()
tts = TTS()


@app.get("/")
def home():
    return {"status": "running", "message": "Digital Twin Backend Running"}


def _remove(path: str):
    try:
        os.remove(path)
    except OSError:
        pass


# Plain `def` endpoints run in a threadpool, so blocking Groq/ElevenLabs
# calls don't freeze the server.
@app.post("/transcribe")
def transcribe(audio: UploadFile = File(...)):
    # Keep the real extension (webm/mp4/ogg) so Groq decodes it correctly
    suffix = Path(audio.filename or "").suffix or ".webm"
    fd, temp_file = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
        text = stt.transcribe(temp_file)
    except Exception as e:
        print("TRANSCRIBE ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _remove(temp_file)

    if text is None:
        return {"success": False, "text": "", "error": "No speech detected."}

    print("TRANSCRIPT:", text)
    return {"success": True, "text": text}


@app.post("/chat")
def chat(data: dict):
    text = (data.get("message") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty message")

    reply = llm.ask(text)
    if reply.startswith("LLM ERROR"):
        raise HTTPException(status_code=502, detail=reply)

    return {"success": True, "reply": reply}


@app.post("/tts")
def text_to_speech(data: dict):
    text = (data.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    fd, out = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    if tts.save(text, out) is None:
        _remove(out)
        raise HTTPException(status_code=502, detail="TTS failed")

    return FileResponse(out, media_type="audio/mpeg", background=BackgroundTask(_remove, out))
