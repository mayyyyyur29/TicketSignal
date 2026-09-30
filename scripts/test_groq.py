from dotenv import load_dotenv
import json, os, time
from groq import Groq

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
if model not in {"openai/gpt-oss-20b"}:
    model = "openai/gpt-oss-20b"
start = time.time()
completion = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "Return a JSON object with keys intent and message. Say hello."}],
    temperature=0,
    max_tokens=2048,
    response_format={"type": "json_object"},
)
print(json.loads(completion.choices[0].message.content))
print(f"Call took {time.time() - start:.2f} seconds")
