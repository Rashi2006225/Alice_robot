from recorder import Recorder
from groq_stt import GroqSTT
from tts import TTS


def main():
    recorder = Recorder()
    stt = GroqSTT()
    tts = TTS()

    print("========================================")
    print("🎤 Digital Twin Voice Assistant Started")
    print("Speak whenever you're ready.")
    print("Press Ctrl + C to exit.")
    print("========================================\n")

    try:
        while True:
            # Record audio
            audio_file = recorder.listen()

            if audio_file is None:
                continue

            print("📝 Transcribing...")

            # Convert speech to text
            text = stt.transcribe(audio_file)

            if not text:
                print("⚠️ Could not transcribe audio.")
                print("-" * 50)
                continue

            print(f"👤 You: {text}")

            # Speak back the recognized text
            print("🔊 Speaking...")
            tts.speak(text)

            print("-" * 50)

    except KeyboardInterrupt:
        print("\n👋 Digital Twin stopped.")


if __name__ == "__main__":
    main()