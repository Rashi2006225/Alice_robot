import logging
import threading
import time
from collections import OrderedDict
from typing import Optional

from elevenlabs.client import ElevenLabs

# CHANGE: clean_text ab text_cleaner.py mein hai.
# WHY:    Hindi bug fix + LLM ko ElevenLabs se alag karna.
from text_cleaner import clean_text

from tts_config import (
    API_KEY,
    MODEL_ID,
    OUTPUT_FORMAT,
    TTS_CACHE_SIZE,
    TTS_MAX_CHARS,
    TTS_MAX_CONCURRENCY,
    VOICE_ID,
)

log = logging.getLogger("alice.tts")


class TTS:
    def __init__(self):
        if not API_KEY:
            raise ValueError("ELEVENLABS_API_KEY is not set.")
        self.client = ElevenLabs(api_key=API_KEY, timeout=30)

        # CHANGE: semaphore + cache naye.
        # WHY:    frontend har sentence ke liye /tts parallel bhejta hai. Semaphore unhe
        #         line mein lagata hai (429 error nahi), cache repeated phrases ke credits bachata hai.
        self._slots = threading.BoundedSemaphore(TTS_MAX_CONCURRENCY)
        self._cache: "OrderedDict[tuple, bytes]" = OrderedDict()
        self._cache_lock = threading.Lock()

    # Purane code ke saath compatible: TTS.clean_text(...) abhi bhi chalega
    clean_text = staticmethod(clean_text)

    def synthesize(
        self, text: str, voice_id: str = VOICE_ID, model_id: str = MODEL_ID
    ) -> Optional[bytes]:
        """
        NAYA: text -> mp3 BYTES (ya fail hone par None).

        CHANGE: pehle ElevenLabs ka lazy generator return hota tha jo baad mein iterate hota tha.
        WHY:    network error iterate karte waqt aata tha, aur kisi try/except ke andar nahi hota tha
                (-> server 500). Ab yahin poora audio jama karte hain, to har error yahin pakda jaata hai.
        """
        text = clean_text(text)[:TTS_MAX_CHARS]
        if not text:
            return None

        key = (voice_id, model_id, text)
        with self._cache_lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]

        audio = None
        with self._slots:                       # max N requests ek saath
            for attempt in range(3):            # 429 pe thoda ruk ke dobara try
                try:
                    stream = self.client.text_to_speech.convert(
                        voice_id=voice_id,
                        text=text,
                        model_id=model_id,
                        output_format=OUTPUT_FORMAT,
                    )
                    audio = b"".join(stream)
                    break
                except Exception as e:
                    rate_limited = getattr(e, "status_code", None) == 429
                    log.warning("TTS attempt %d failed: %s", attempt + 1, e)
                    if rate_limited and attempt < 2:
                        time.sleep(1.0 * (attempt + 1))
                        continue
                    break

        if not audio:
            return None

        with self._cache_lock:
            self._cache[key] = audio
            while len(self._cache) > TTS_CACHE_SIZE:
                self._cache.popitem(last=False)
        return audio

    def speak(self, text: str, voice_id: str = VOICE_ID, model_id: str = MODEL_ID):
        """Laptop ke speaker pe seedha bajao (terminal testing)."""
        audio = self.synthesize(text, voice_id, model_id)
        if audio is None:
            return
        try:
            # CHANGE: play import yahin andar kiya.
            # WHY:    elevenlabs.play ko mpv / ffmpeg chahiye. Top pe import hota to jin
            #         logon ke paas ye nahi, unka poora server import pe hi fail ho jaata.
            from elevenlabs.play import play
            play(audio)
        except Exception as e:
            log.error("Audio playback failed: %s", e)

    def save(self, text: str, filename: str, voice_id: str = VOICE_ID, model_id: str = MODEL_ID):
        """MP3 file mein save karo. Fail hone par None."""
        audio = self.synthesize(text, voice_id, model_id)
        if audio is None:
            return None
        try:
            with open(filename, "wb") as f:
                f.write(audio)
            log.info("Saved to %s", filename)
            return filename
        except OSError as e:
            log.error("Failed to save audio: %s", e)
            return None


if __name__ == "__main__":
    # Chhota test (clean_text ElevenLabs ke bina bhi chalta hai)
    print(clean_text("नमस्ते! **Price** ₹500 hai | 50% off 😀"))