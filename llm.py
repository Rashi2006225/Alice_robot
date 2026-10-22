import logging

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq

from config import (
    GROQ_API_KEY,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_TIMEOUT,
    LLM_REASONING_EFFORT,
    MAX_HISTORY_MESSAGES,
    MAX_MESSAGE_CHARS,
)

# CHANGE: "from tts import TTS" hataya, ab text_cleaner se import.
# WHY:    pehle LLM ke liye bhi ElevenLabs key chahiye thi (run.py tak nahi chalta tha).
from text_cleaner import clean_text, stream_clean

log = logging.getLogger("alice.llm")

# CHANGE: Hindi ke liye "Devanagari script mein likho" line add ki.
# WHY:    ElevenLabs multilingual Devanagari ko sabse sahi bolta hai. Roman Hindi (Hinglish)
#         ko aksar angrezi accent mein padhta hai.
# NOTE:   is string mein { } mat likhna, LangChain use template samajh leta hai.
SYSTEM_PROMPT = """
You are ALICE, an intelligent AI voice assistant.

Your replies are shown on screen and spoken aloud by a text-to-speech voice.

Rules:
- Answer naturally, politely and in a friendly way.
- Keep responses short: usually 2 to 4 sentences, unless the user asks for more detail.
- Answer in the same language as the user. If the user speaks Hindi, answer in Hindi using Devanagari script. If the user speaks English, answer in English.
- If you don't know something, say you don't know.

Speaking style rules (very important):
- Use plain conversational sentences only, like a person talking.
- Never use markdown, tables, pipes, asterisks, hash symbols, bullet symbols, numbered lists, HTML tags, code blocks, or emojis.
- Never use symbols such as | * # < > = + / in your reply. Write them as words if needed, for example "and", "or", "percent".
- To list things, say them in a sentence like: "first, ..., second, ..., and finally, ...".
- Do not format answers as a cheat sheet, chart, or comparison table. Explain in simple spoken sentences instead.
"""

FALLBACK_ERROR = "Sorry, I had a problem answering that. Please try again."
FALLBACK_EMPTY = "Sorry, I could not come up with an answer. Could you say that again?"


class AliceLLM:
    def __init__(self):
        # CHANGE: model, max_tokens, timeout, retries ab config se aate hain.
        # WHY:    max_tokens ke bina model bahut lamba bol sakta tha (voice ke liye bekaar + slow).
        #         timeout ke bina Groq atak jaye to request hamesha latki rehti.
        kwargs = dict(
            groq_api_key=GROQ_API_KEY,
            model_name=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            timeout=LLM_TIMEOUT,
            max_retries=2,
        )
        # CHANGE: reasoning_effort sirf tab bheja jab .env mein set ho.
        # WHY:    "low" se gpt-oss ka pehla shabd tez aata hai. Purani langchain-groq
        #         version isko samajhti nahi, isliye default mein nahi bhejte.
        if LLM_REASONING_EFFORT:
            kwargs["reasoning_effort"] = LLM_REASONING_EFFORT
        self.llm = ChatGroq(**kwargs)

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                MessagesPlaceholder("history"),
                ("human", "{question}"),
            ]
        )
        self.parser = StrOutputParser()
        self.chain = self.prompt | self.llm | self.parser

    @staticmethod
    def _to_messages(history):
        """
        Browser ki history [{role, content}] -> LangChain messages.

        CHANGE: sirf "user" / "assistant" role maane, content ki length cap ki,
                aur tuples ki jagah HumanMessage / AIMessage use kiye.
        WHY:    pehle koi bhi role (jaise "system") history mein ghus sakta tha, jisse
                koi bhi ALICE ke rules badalne ki koshish kar sakta tha (prompt injection).
        """
        out = []
        for m in (history or [])[-MAX_HISTORY_MESSAGES:]:
            if not isinstance(m, dict):
                continue
            role = m.get("role")
            if role not in ("user", "assistant"):
                continue
            content = str(m.get("content") or "").strip()[:MAX_MESSAGE_CHARS]
            if not content:
                continue
            out.append(HumanMessage(content=content) if role == "user" else AIMessage(content=content))
        return out

    def ask(self, question: str, history=None) -> str:
        """Poora jawab ek saath (terminal testing ke liye)."""
        try:
            response = self.chain.invoke(
                {"question": question, "history": self._to_messages(history)}
            )
            return clean_text(response) or FALLBACK_EMPTY
        except Exception:
            # CHANGE: print ki jagah log.exception (poora traceback milta hai)
            log.exception("LLM ask failed")
            return FALLBACK_ERROR

    def stream(self, question: str, history=None):
        """
        Jawab tukde tukde yield karta hai.

        CHANGE: raw chunks ki jagah stream_clean() se saaf sentences yield hote hain.
        WHY:    pehle table / link / emoji saaf hue bina browser ko chale jaate the aur bol diye jaate the.
        CHANGE: agar kuch bhi nahi bheja gaya to fallback message yield hota hai.
        WHY:    warna frontend ko khaali jawab milta aur "empty answer" error dikhta.
        """
        payload = {"question": question, "history": self._to_messages(history)}
        sent_any = False
        try:
            for piece in stream_clean(self.chain.stream(payload)):
                sent_any = True
                yield piece
        except Exception:
            log.exception("LLM stream failed")
            if not sent_any:
                yield FALLBACK_ERROR
            return

        if not sent_any:
            yield FALLBACK_EMPTY