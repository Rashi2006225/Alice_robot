from elevenlabs.client import ElevenLabs
from elevenlabs.play import play

from tts_config import API_KEY, VOICE_ID, MODEL_ID

class TTS:
    def __init__(self):
        if not API_KEY:
            raise ValueError("ELEVENLABS_API_KEY is not set.")
        self.client = ElevenLabs(api_key=API_KEY)

    def _generate(self, text: str, voice_id: str = VOICE_ID, model_id: str = MODEL_ID):
        """
        Shared call to the ElevenLabs API. Returns the audio stream/bytes,
        or None if there's nothing to synthesize.
        """
        if not text.strip():
            return None

        try:
            return self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id=model_id,
                output_format="mp3_44100_128",
            )
        except Exception as e:
            print(f"TTS generation failed: {e}")
            return None

    def speak(self, text: str, voice_id: str = VOICE_ID, model_id: str = MODEL_ID) -> None:
        """
        Convert text to speech and play it.
        """
        audio = self._generate(text, voice_id, model_id)
        if audio is None:
            return

        play(audio)

    def save(self, text: str, filename: str, voice_id: str = VOICE_ID, model_id: str = MODEL_ID) -> str | None:
        """
        Save generated speech to an MP3 file. Returns the filename on success,
        or None if nothing was saved.
        """
        audio = self._generate(text, voice_id, model_id)
        if audio is None:
            return None

        try:
            with open(filename, "wb") as f:
                for chunk in audio:
                    f.write(chunk)
        except OSError as e:
            print(f"Failed to write audio file: {e}")
            return None

        print(f"Saved to {filename}")
        return filename
