import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import save

load_dotenv()
API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Default voice (George)
VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
# Fast model for conversational AI
MODEL_ID = "eleven_flash_v2_5"

if not API_KEY:
    raise ValueError(
        "ELEVENLABS_API_KEY not found. Make sure it's set in your .env file "
        "(e.g. ELEVENLABS_API_KEY=your_key_here)."
    )

client = ElevenLabs(api_key=API_KEY)


def text_to_speech(text: str, output_path: str = "output.mp3",
                    voice_id: str = VOICE_ID, model_id: str = MODEL_ID) -> str:
    """
    Convert text to speech using ElevenLabs and save it to a file.

    Args:
        text: The text to convert to speech.
        output_path: Where to save the resulting audio file.
        voice_id: ElevenLabs voice ID to use.
        model_id: ElevenLabs model ID to use.

    Returns:
        The path to the saved audio file.
    """
    audio = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format="mp3_44100_128",
    )

    save(audio, output_path)
    return output_path


if __name__ == "__main__":
    sample_text = "Hello! This is a test of the ElevenLabs text to speech API."
    path = text_to_speech(sample_text)
    print(f"Audio saved to: {path}")
