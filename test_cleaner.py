"""
text_cleaner.py  (NAYI FILE)

CHANGE: clean_text() ko tts.py se nikal kar alag file mein rakha.
WHY:    pehle llm.py "from tts import TTS" karta tha, to sirf text saaf karne ke liye
        ElevenLabs + uski API key bhi chahiye thi. Ab LLM / run.py bina ElevenLabs ke chal sakte hain.
"""
import re
import unicodedata

# Sentence ka end: . ! ? ya Hindi poorn-viram (।) ke baad space, ya naya line
SENTENCE_END = re.compile(r"[.!?।]+[\"')\]]*\s+|\n+")

# Jo punctuation final text mein allowed hai
ALLOWED_PUNCT = set(".,?!:;'-।")


def _keep_char(ch: str) -> bool:
    """
    CHANGE: purani whitelist re.sub(r"[^\\w\\s...]") ki jagah Unicode category check.
    WHY:    Python ka \\w Hindi ki matras (ा ि ी े ै ो ्) ko "word character" nahi maanta,
            isliye "कैसे हैं" -> "कस ह" ban jaata tha aur "।" bhi udd jaata tha.
            Yahan Letters (L), Marks (M = matras), Numbers (N) rakhe jaate hain,
            to Hindi / Punjabi / koi bhi script sahi rehti hai. Emoji (S) hat jaate hain.
    """
    if ch.isspace() or ch in ALLOWED_PUNCT:
        return True
    return unicodedata.category(ch)[0] in ("L", "M", "N")


def clean_text(text: str) -> str:
    """LLM / markdown output ko aisa plain text banao jo voice natural padhe."""
    if not text:
        return ""

    # 0. Unicode lookalikes normalize
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[∣¦│┃｜]", "|", text)
    # CHANGE: invisible characters (emoji selector, zero-width space) hataye
    # WHY:    "M" category keep karne se ye invisible marks bach jaate, TTS ko confuse karte
    text = re.sub(r"[\ufe00-\ufe0f\u200b\u200e\u200f\u2060]", "", text)

    # 1. HTML: <br> = pause, baaki tags hata do
    text = re.sub(r"<\s*br\s*/?\s*>", ". ", text, flags=re.IGNORECASE)
    text = re.sub(r"</?[a-zA-Z][^>]*>", " ", text)

    # 2. Code blocks
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)

    # 3. Markdown links / images -> sirf dikhne wala text
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)

    # 4. URLs
    text = re.sub(r"https?://\S+|www\.\S+", "", text)

    # 5. Table separator rows  |---|:---:|
    text = re.sub(r"\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?", " . ", text)

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
        # CHANGE: "।" ko bhi sentence-end maana
        # WHY:    warna Hindi line ke aakhir mein extra "." lag jaata tha
        if line[-1] not in ".!?:;।":
            line += "."
        lines.append(line)
    text = " ".join(lines)

    # 7. Pipes (table cells) -> pause
    text = re.sub(r"\s*\|\s*", ", ", text)

    # 8. Inline bullets / emphasis
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

    # 10. Alag khade dashes -> pause
    text = re.sub(r"\s-+\s", ", ", text)

    # 11. STRICT WHITELIST (ab Unicode-aware, upar _keep_char dekho)
    text = "".join(ch for ch in text if _keep_char(ch))

    # 12. Bache hue hyphens
    text = re.sub(r"-{2,}", " ", text)
    text = re.sub(r"(?<!\w)-+|-+(?!\w)", " ", text)

    # 13. Punctuation / spaces tidy  (CHANGE: "।" bhi in regexes mein add)
    text = re.sub(r"\s+([.,?!:;।])", r"\1", text)
    text = re.sub(r"([,;:])(\s*[,;:])+", r"\1", text)
    text = re.sub(r"([,;:])\s*(?=[.?!।])", "", text)
    text = re.sub(r"\.(\s*\.)+", ".", text)
    text = re.sub(r"[.]\s*,", ".", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip(" ,;:")


def stream_clean(chunks, max_buffer: int = 300):
    """
    NAYA FUNCTION: LLM ke streamed tukdon ko sentence-by-sentence saaf karke yield karta hai.

    WHY: pehle llm.stream() raw tukde seedha browser ko bhej deta tha, clean_text() sirf
         ask() mein chalta tha. Isliye real app mein tables / links / emoji bol diye jaate the.
         Ek poora sentence jama karke clean karte hain taaki "**bo" + "ld**" jaise tukde na bigdein.
    """
    buf = ""
    for chunk in chunks:
        buf += chunk
        pos = 0
        for m in SENTENCE_END.finditer(buf):
            cleaned = clean_text(buf[pos:m.end()])
            pos = m.end()
            if cleaned:
                yield cleaned + " "
        buf = buf[pos:]

        # Bina full stop ki bahut lambi line (jaise table) -> zabardasti word boundary pe kaato
        if len(buf) > max_buffer:
            cut = buf.rfind(" ")
            if cut <= 0:
                cut = len(buf)
            cleaned = clean_text(buf[:cut])
            buf = buf[cut:]
            if cleaned:
                yield cleaned + " "

    cleaned = clean_text(buf)
    if cleaned:
        yield cleaned