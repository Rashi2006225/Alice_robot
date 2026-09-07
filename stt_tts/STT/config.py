import os
from dotenv import load_dotenv

load_dotenv()

# ======================
# GROQ API
# ======================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is not set. Add it to your .env file: GROQ_API_KEY=your_key_here"
    )

# Model used for speech-to-text (Groq's hosted Whisper)
STT_MODEL = os.getenv("STT_MODEL", "whisper-large-v3-turbo")
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "en")  # ISO-639-1 code, or None to auto-detect

# ======================
# AUDIO SETTINGS
# ======================
SAMPLE_RATE = 16000          # Hz — must be 8000/16000/32000/48000 (webrtcvad requirement)
CHANNELS = 1                 # webrtcvad requires mono
DTYPE = "int16"              # webrtcvad + wave output require int16 PCM
FRAME_DURATION = 30          # ms — must be 10/20/30 (webrtcvad requirement)
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION / 1000)  # samples per frame

# ======================
# VOICE ACTIVITY DETECTION (VAD)
# ======================
VAD_MODE = 2                 # 0 = least aggressive filtering, 3 = most aggressive
MAX_SILENCE_DURATION = 2.0   # seconds of trailing silence before stopping
MAX_WAIT_FOR_SPEECH = 10.0   # seconds to wait for speech to start before giving up
MAX_RECORD_DURATION = 3000.0   # hard cap on a single utterance, seconds
PRE_SPEECH_BUFFER_MS = 300   # ms of audio kept before speech onset, to avoid clipping

# ======================
# FILE PATHS
# ======================
AUDIO_DIR = "audio"
TEMP_AUDIO_FILE = os.path.join(AUDIO_DIR, "temp.wav")

os.makedirs(AUDIO_DIR, exist_ok=True)

# ======================
# VALIDATION
# ======================
# Fail fast at import time rather than deep inside a recording session.
assert CHANNELS == 1, "webrtcvad requires mono audio (CHANNELS must be 1)"
assert SAMPLE_RATE in (8000, 16000, 32000, 48000), \
    "webrtcvad only supports 8000/16000/32000/48000 Hz"
assert FRAME_DURATION in (10, 20, 30), \
    "webrtcvad only supports 10/20/30 ms frames"
assert DTYPE == "int16", "VAD and wave output require int16 PCM"
assert 0 <= VAD_MODE <= 3, "VAD_MODE must be 0-3"
