import logging
import re
from pathlib import Path
from typing import Optional

from groq import Groq

from config import (
    GROQ_API_KEY,
    STT_MODEL,
    STT_LANGUAGE,
    STT_PROMPT,
    STT_NO_SPEECH_THRESHOLD,
)

log = logging.getLogger("alice.stt")


class STTError(Exception):
    """
    CHANGE: naya error type.
    WHY:    pehle Groq ka error aur "kuch sunai nahi diya" dono None return karte the,
            to UI ko pata hi nahi chalta tha ki asli problem key / internet / rate-limit ki hai.
            Ab API fail = STTError (main.py use 502 bana deta hai), chup audio = None.
    """


# Whisper chup / shor wali audio pe aksar ye jumle bana deta hai
_HALLUCINATIONS = {
    "thank you", "thanks", "thanks for watching", "thank you for watching",
    "please subscribe", "bye", "you", "okay", "ok",
}


def _get(obj, key, default=None):
    """Groq kabhi dict deta hai kabhi object. Dono se value nikalne ka helper."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class GroqSTT:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def transcribe(self, audio_file: str) -> Optional[str]:
        """
        Audio file -> text.
        Returns: text, ya None agar speech nahi mili.
        Raises:  STTError agar Groq request hi fail ho gayi.
        """
        path = Path(audio_file)
        if not path.exists() or path.stat().st_size == 0:
            log.warning("Audio file missing/empty: %s", audio_file)
            return None

        # CHANGE: language / prompt ab sirf tab bheje jaate hain jab .env mein set hon.
        # WHY:    pehle STT_LANGUAGE define tha par use hi nahi hota tha.
        #         temperature=0 se output stable rehta hai.
        kwargs = dict(model=STT_MODEL, response_format="verbose_json", temperature=0.0)
        if STT_LANGUAGE:
            kwargs["language"] = STT_LANGUAGE
        if STT_PROMPT:
            kwargs["prompt"] = STT_PROMPT

        try:
            with open(path, "rb") as f:
                result = self.client.audio.transcriptions.create(file=f, **kwargs)
        except Exception as e:
            log.error("Groq STT request failed: %s", e)
            raise STTError(str(e)) from e

        # CHANGE: segments check karke "no speech" wale hisse hataye.
        # WHY:    verbose_json har segment ke saath no_speech_prob aur avg_logprob deta hai.
        #         Whisper ka standard rule: no_speech_prob bahut zyada AUR logprob bahut kam = hallucination.
        segments = _get(result, "segments") or []
        if segments:
            kept = []
            for seg in segments:
                no_speech = _get(seg, "no_speech_prob", 0) or 0
                logprob = _get(seg, "avg_logprob", 0) or 0
                if no_speech > STT_NO_SPEECH_THRESHOLD and logprob < -1.0:
                    continue
                seg_text = (_get(seg, "text", "") or "").strip()
                if seg_text:
                    kept.append(seg_text)
            text = " ".join(kept).strip()
        else:
            text = (_get(result, "text", "") or "").strip()

        if not text:
            log.info("No speech detected in audio")
            return None

        # CHANGE: bahut chhoti audio + famous hallucination phrase = drop.
        # WHY:    "Thank you." jaise jumle 1-2 second ki chup audio pe aksar aate hain.
        duration = _get(result, "duration", 0) or 0
        normalized = re.sub(r"[^\w\s]", "", text.lower()).strip()
        if normalized in _HALLUCINATIONS and duration < 2.5:
            log.info("Dropped likely hallucination: %r", text)
            return None

        return text