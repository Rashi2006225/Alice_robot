import re
import unicodedata

from elevenlabs.client import ElevenLabs
from elevenlabs.play import play

from tts_config import API_KEY, VOICE_ID, MODEL_ID


class TTS:
    def __init__(self):
        if not API_KEY:
            raise ValueError("ELEVENLABS_API_KEY is not set.")
        self.client = ElevenLabs(api_key=API_KEY)

    # ------------------------------------------------------------------
    # Text cleaning
    # ------------------------------------------------------------------
    @staticmethod
    def clean_text(text: str) -> str:
        """Turn LLM/markdown output into plain text a voice reads naturally."""

        if not text:
            return ""

        # 0. Normalize unicode lookalikes (full-width pipe etc.)
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"[∣¦│┃｜]", "|", text)

        # 1. HTML: <br> becomes a pause, every other tag is removed completely
        text = re.sub(r"<\s*br\s*/?\s*>", ". ", text, flags=re.IGNORECASE)
        text = re.sub(r"</?[a-zA-Z][^>]*>", " ", text)

        # 2. Fenced code blocks
        text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)

        # 3. Markdown images and links -> keep only the visible text
        text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)

        # 4. URLs
        text = re.sub(r"https?://\S+|www\.\S+", "", text)

        # 5. Table separator rows ANYWHERE (even inside one long line):
        #    |---------|:-----:|-----|
        text = re.sub(
            r"\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?", " . ", text
        )

        # 6. Line-level markdown
        lines = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if re.fullmatch(r"([-*_=]\s*){3,}", line):
                continue
            line = re.sub(r"^#{1,6}\s*", "", line)
            line = re.sub(r"^>+\s*", "", line)
            line = re.sub(r"^[-*•+]\s+", "", line)
            line = re.sub(r"^\d+[.)]\s+", "", line)
            line = line.strip(" ,|")
            if not line:
                continue
            if line[-1] not in ".!?:;":
                line += "."
            lines.append(line)
        text = " ".join(lines)

        # 7. Pipes anywhere (table cells) -> pause
        text = re.sub(r"\s*\|\s*", ", ", text)

        # 8. Inline bullets and emphasis markers
        text = text.replace("•", ". ").replace("·", ". ")
        text = re.sub(r"[*`~#]", "", text)
        text = text.replace("_", " ")

        # 9. Context-aware symbols
        text = re.sub(r"\$\s*(\d[\d,]*(?:\.\d+)?)", r"\1 dollars", text)
        text = re.sub(r"₹\s*(\d[\d,]*(?:\.\d+)?)", r"\1 rupees", text)
        text = re.sub(r"(\d)\s*%", r"\1 percent", text)
        text = re.sub(r"(?<=[A-Za-z])/(?=[A-Za-z])", " or ", text)

        replacements = {
            "&": " and ", "@": " at ", "%": " percent ", "=": " equals ",
            "+": " plus ", "→": " to ", "←": " from ",
            "—": ", ", "–": ", ", "…": ".",
            "/": " ", "\\": " ",
            "(": ", ", ")": ", ",
            "[": " ", "]": " ", "{": " ", "}": " ", "<": " ", ">": " ",
            "“": "", "”": "", '"': "", "‘": "'", "’": "'",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)

        # 10. Standalone dashes -> pause (hyphens inside words stay)
        text = re.sub(r"\s-+\s", ", ", text)

        # 11. STRICT WHITELIST: only letters, digits, spaces, basic punctuation
        text = re.sub(r"[^\w\s.,?!:;'\-]", "", text)
        text = text.replace("_", " ")

        # 12. Leftover hyphens not inside a word
        text = re.sub(r"-{2,}", " ", text)
        text = re.sub(r"(?<!\w)-+|-+(?!\w)", " ", text)

        # 13. Tidy punctuation and spaces
        text = re.sub(r"\s+([.,?!:;])", r"\1", text)
        text = re.sub(r"([,;:])(\s*[,;:])+", r"\1", text)
        text = re.sub(r"([,;:])\s*(?=[.?!])", "", text)
        text = re.sub(r"\.(\s*\.)+", ".", text)
        text = re.sub(r"[.]\s*,", ".", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip(" ,;:")

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------
    def _generate(
        self,
        text: str,
        voice_id: str = VOICE_ID,
        model_id: str = MODEL_ID,
    ):
        """Clean text and generate speech audio."""

        text = self.clean_text(text)

        if not text:
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

    def speak(
        self,
        text: str,
        voice_id: str = VOICE_ID,
        model_id: str = MODEL_ID,
    ):
        """Generate and play speech."""

        audio = self._generate(text, voice_id, model_id)
        if audio is None:
            return

        try:
            play(audio)
        except Exception as e:
            print(f"Audio playback failed: {e}")

    def save(
        self,
        text: str,
        filename: str,
        voice_id: str = VOICE_ID,
        model_id: str = MODEL_ID,
    ):
        """Generate speech and save it to an MP3 file."""

        audio = self._generate(text, voice_id, model_id)
        if audio is None:
            return None

        try:
            with open(filename, "wb") as f:
                for chunk in audio:
                    f.write(chunk)
            print(f"Saved to {filename}")
            return filename
        except OSError as e:
            print(f"Failed to save audio: {e}")
            return None


if __name__ == "__main__":
    sample = (
        "Sure! The “best” algorithm depends mainly on the type of problem "
        "you’re solving. Here’s a quick cheat-sheet: | Problem | Typical "
        "Algorithms | When to Pick Them | |---------|-------------------|"
        "-------------------| | **Binary / Multi-class Classification** | "
        "• Logistic regression (fast, interpretable) <br>• Random Forest / "
        "Extra Trees (handles non-linearities) <br>• Gradient-Boosted Trees "
        "(XGBoost, LightGBM, CatBoost – top performers) <br>• Support Vector "
        "Machine (good with small data) | • Use logistic regression for a "
        "quick baseline or when you need coefficients. <br>• Use tree-based "
        "models when you want feature importance. <br>• Use SVM when you "
        "have a clear margin. |"
    )
    print(TTS.clean_text(sample))