from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path(__file__).parent / ".env"

print("Env path:", env_path)
print("Exists:", env_path.exists())

load_dotenv(dotenv_path=env_path)

print("API Key:", os.getenv("ELEVENLABS_API_KEY"))