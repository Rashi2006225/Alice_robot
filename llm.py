from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
 
from config import GROQ_API_KEY
from tts import TTS  # used only for TTS.clean_text (static method)
 
 
SYSTEM_PROMPT = """
You are ALICE, an intelligent AI voice assistant.
 
Your replies are shown on screen and spoken aloud by a text-to-speech voice.
 
Rules:
- Answer naturally, politely and in a friendly way.
- Keep responses short: usually 2 to 4 sentences, unless the user asks for more detail.
- Answer in the same language as the user. If the user speaks Hindi, answer in Hindi. If the user speaks English, answer in English.
- If you don't know something, say you don't know.
 
Speaking style rules (very important):
- Use plain conversational sentences only, like a person talking.
- Never use markdown, tables, pipes, asterisks, hash symbols, bullet symbols, numbered lists, HTML tags, code blocks, or emojis.
- Never use symbols such as | * # < > = + / in your reply. Write them as words if needed, for example "and", "or", "percent".
- To list things, say them in a sentence like: "first, ..., second, ..., and finally, ...".
- Do not format answers as a cheat sheet, chart, or comparison table. Explain in simple spoken sentences instead.
"""
 
 
class AliceLLM:
    def __init__(self):
 
        # Initialize Groq LLM
        self.llm = ChatGroq(
            groq_api_key=GROQ_API_KEY,
            model_name="openai/gpt-oss-20b",
            temperature=0.7,
        )
 
        # System prompt + user question
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                MessagesPlaceholder("history"),   # earlier turns of this conversation
                ("human", "{question}"),
            ]
        )
 
        # Output parser
        self.parser = StrOutputParser()
 
        # LangChain pipeline
        self.chain = self.prompt | self.llm | self.parser
 
    @staticmethod
    def _to_messages(history):
        """[{role, content}, ...] from the browser -> [(\"human\"|\"ai\", text), ...]"""
        out = []
        for m in (history or [])[-20:]:          # keep only the last 20 messages
            role = "human" if m.get("role") == "user" else "ai"
            content = str(m.get("content") or "").strip()
            if content:
                out.append((role, content))
        return out
 
    def ask(self, question: str, history=None) -> str:
        try:
            print("=" * 60)
            print("Question:")
            print(question)
            print("=" * 60)
 
            response = self.chain.invoke(
                {"question": question, "history": self._to_messages(history)}
            )
 
            print("=" * 60)
            print("LLM Response (raw):")
            print(response)
            print("=" * 60)
 
            # Safety net: remove any markdown/tables/symbols the model still adds,
            # so both the conversation log and the voice get clean text.
            clean_response = TTS.clean_text(response)
 
            return clean_response or response
 
        except Exception as e:
            print("=" * 60)
            print("LLM ERROR")
            print(e)
            print("=" * 60)
 
            return "Sorry, I had a problem answering that. Please try again."
 
    def stream(self, question: str, history=None):
        try:
            print("=" * 60)
            print("Question:")
            print(question)
            print("=" * 60)
 
            payload = {"question": question, "history": self._to_messages(history)}
            for chunk in self.chain.stream(payload):
                yield chunk
 
        except Exception as e:
            print("=" * 60)
            print("LLM ERROR")
            print(e)
            print("=" * 60)
 
            yield "Sorry, I had a problem answering that."
 