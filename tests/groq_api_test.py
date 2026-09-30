from dotenv import load_dotenv
import os
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))




completion = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[{"role": "user", "content": "Reply with a JSON object saying hello"}],
    temperature=1,
    max_tokens=2048,
    top_p=1,
    stream=True,
)
print(completion.choices[0].message.content)