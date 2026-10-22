import os
from pathlib import Path

from dotenv import load_dotenv

# CHANGE: .env is file ke folder se load hota hai.
# WHY:    kisi bhi folder se server chalao, key mil jaati hai.
load_dotenv(Path(__file__).resolve().parent / ".env")

# CHANGE: yahan se "raise ValueError" aur ElevenLabs client banana hata diya.
# WHY:    pehle import karte hi key na hone par poora server crash hota tha.
#         Ab sirf TTS() banate waqt check hota hai, aur main.py use sambhal leta hai
#         (frontend browser ki awaaz pe fallback karta hai).
API_KEY = os.getenv("ELEVENLABS_API_KEY")

# CHANGE: voice / model / format ab .env se badal sakte ho.
# WHY:    Hindi ke liye alag voice ID chahiye ho to code nahi chhoona padega.
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")  # George
# "eleven_flash_v2_5" bahut tez hai aur Hindi support karta hai.
# "eleven_multilingual_v2" zyada natural hai par dheema.
MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
# CHANGE: 128kbps -> 64kbps. WHY: voice ke liye kaafi hai, download tez hota hai.
OUTPUT_FORMAT = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_64")

# CHANGE: naye. WHY: free plan pe ElevenLabs sirf 2-3 parallel requests deta hai.
#        MAX_CONCURRENCY se zyada requests queue mein rukti hain (fail nahi hoti).
TTS_MAX_CONCURRENCY = int(os.getenv("TTS_MAX_CONCURRENCY", "2"))
TTS_CACHE_SIZE = int(os.getenv("TTS_CACHE_SIZE", "50"))
TTS_MAX_CHARS = int(os.getenv("TTS_MAX_CHARS", "1000"))