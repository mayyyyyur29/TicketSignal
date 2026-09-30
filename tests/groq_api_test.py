"""Manual Groq connectivity check, kept out of pytest collection side effects."""

import os

from dotenv import load_dotenv
from groq import Groq


def main() -> None:
    """Print streamed text only when this connectivity check is run directly."""
    load_dotenv()
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply with a JSON object saying hello"}],
        temperature=0,
        max_tokens=2048,
        top_p=1,
        stream=True,
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            print(content, end="")
    print()


if __name__ == "__main__":
    main()