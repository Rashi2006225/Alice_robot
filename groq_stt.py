from pathlib import Path
from typing import Optional

from groq import Groq, GroqError

from config import GROQ_API_KEY, STT_MODEL, STT_LANGUAGE


class GroqSTT:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def transcribe(self, audio_file: str) -> Optional[str]:
        """
        Transcribe an audio file using Groq's hosted Whisper.
        Returns the transcribed text, or None if transcription failed
        or produced no usable speech.
        """
        path = Path(audio_file)
        if not path.exists():
            print(f"⚠️ Audio file not found: {audio_file}")
            return None

        if path.stat().st_size == 0:
            print(f"⚠️ Audio file is empty: {audio_file}")
            return None

        try:
            with open(path, "rb") as file:
                transcription = self.client.audio.transcriptions.create(
                    file=file,
                    model=STT_MODEL,
                    response_format="verbose_json",
                    
                )
        except GroqError as e:
            print(f"⚠️ Groq STT request failed: {e}")
            return None
        except Exception as e:
            print(f"⚠️ Unexpected error during transcription: {e}")
            return None

        text = getattr(transcription, "text", "") or ""
        text = text.strip()

        if not text:
            print("⚠️ No speech detected in audio")
            return None

        return text
