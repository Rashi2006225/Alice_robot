from pathlib import Path

from dotenv import load_dotenv
import os

env_path = Path(__file__).resolve().parent / ".env"
print("Env path:", env_path)
print("Exists:", env_path.exists())

load_dotenv(dotenv_path=env_path)

# CHANGE: key print karna band, ab sirf "set hai ya nahi" dikhata hai.
# WHY:    terminal screenshot / screen-share mein API key leak ho jaati thi.
for name in ("GROQ_API_KEY", "ELEVENLABS_API_KEY"):
    value = os.getenv(name)
    print(f"{name}: {'SET (' + str(len(value)) + ' chars)' if value else 'MISSING'}")