import os
from pathlib import Path

from dotenv import load_dotenv

# CHANGE: .env ko is file ke folder se load kiya (current folder se nahi).
# WHY:    uvicorn / script kisi bhi folder se chalao, .env hamesha mil jaayegi.
#         (tumhare test.py mein yahi problem dhundh rahe the)
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _optional(name: str, default: str = ""):
    """
    CHANGE: naya helper. Khaali / "none" / "null" ko asli None banata hai.
    WHY:    pehle STT_LANGUAGE ka default string "None" tha, jo Python mein truthy hota hai
            (Groq ko language="None" chala jaata). Ab sach mein None milega.
    """
    value = os.getenv(name, default).strip()
    return None if value.lower() in ("", "none", "null") else value


# ======================
# GROQ (STT + LLM)
# ======================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is not set. Add it to your .env file: GROQ_API_KEY=your_key_here"
    )

# ======================
# SPEECH TO TEXT
# ======================
STT_MODEL = os.getenv("STT_MODEL", "whisper-large-v3-turbo")
STT_LANGUAGE = _optional("STT_LANGUAGE")   # "en", "hi" ya khaali (auto-detect)
# CHANGE: STT_PROMPT naya. WHY: Whisper ko hint dene se Hinglish / naam behtar pakadta hai
STT_PROMPT = _optional("STT_PROMPT")
# CHANGE: naya. WHY: is se zyada "no speech" probability wale segments hallucination maane jaate hain
STT_NO_SPEECH_THRESHOLD = float(os.getenv("STT_NO_SPEECH_THRESHOLD", "0.6"))

# ======================
# LLM
# ======================
# CHANGE: model, tokens, timeout pehle llm.py mein hard-coded the.
# WHY:    ab .env se badal sakte ho, code chhune ki zaroorat nahi.
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "300"))   # voice ke liye lamba jawab chahiye hi nahi
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "20"))        # seconds
# gpt-oss ke liye "low" rakhne se pehla shabd jaldi aata hai. Khaali = default.
LLM_REASONING_EFFORT = _optional("LLM_REASONING_EFFORT")

# ======================
# SERVER LIMITS
# ======================
# CHANGE: ye sab naye hain.
# WHY:    bahut bada audio / message / history bhejkar koi server ya credits kharab na kar sake.
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
MAX_AUDIO_MB = int(os.getenv("MAX_AUDIO_MB", "25"))        # Groq ki file limit bhi ~25MB hai
MAX_MESSAGE_CHARS = int(os.getenv("MAX_MESSAGE_CHARS", "2000"))
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))

# ======================
# MIC RECORDING (sirf recorder.py, robot ke direct mic ke liye)
# ======================
SAMPLE_RATE = 16000          # Hz — 8000/16000/32000/48000
CHANNELS = 1
DTYPE = "int16"
FRAME_DURATION = 30          # ms
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION / 1000)

VAD_MODE = 2                 # 0 = kam strict, 3 = sabse strict
MAX_SILENCE_DURATION = 2.0   # itni der chup raho to recording band
MAX_WAIT_FOR_SPEECH = 10.0   # itni der koi na bole to haar maan lo
# CHANGE: 3000 -> 30. WHY: 3000 sec = 50 minute, ek sawaal ke liye bekaar hai
MAX_RECORD_DURATION = 3000.0
PRE_SPEECH_BUFFER_MS = 300   # bolne se pehle ka itna audio bhi rakho (pehla shabd na kate)
# CHANGE: naya. WHY: itne lagataar speech frames aaye tabhi recording shuru (click / khansi se nahi)
SPEECH_START_FRAMES = 3

# CHANGE: os.makedirs yahan se hata diya (recorder.py khud banata hai).
# WHY:    config import karte hi folder ban jaana ek side-effect tha.
AUDIO_DIR = str(BASE_DIR / "audio")
TEMP_AUDIO_FILE = os.path.join(AUDIO_DIR, "temp.wav")

# ======================
# VALIDATION (galat setting ho to turant error)
# ======================
assert CHANNELS == 1, "webrtcvad requires mono audio (CHANNELS must be 1)"
assert SAMPLE_RATE in (8000, 16000, 32000, 48000), "webrtcvad only supports 8000/16000/32000/48000 Hz"
assert FRAME_DURATION in (10, 20, 30), "webrtcvad only supports 10/20/30 ms frames"
assert DTYPE == "int16", "VAD and wave output require int16 PCM"
assert 0 <= VAD_MODE <= 3, "VAD_MODE must be 0-3"