# test_llm.py
from learning.code_manual.Refundbot.app.config import get_openai_client, settings

client = get_openai_client()

response = client.chat.completions.create(
    model=settings.OPENAI_MODEL,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello in 5 words."}
    ],
    max_tokens=20
)

print(response.choices[0].message.content)