import os
from openai import OpenAI

api_key = os.environ.get("OPENAI_API_KEY")

client = OpenAI(
  api_key=api_key,
)

completion = client.chat.completions.create(
  model="gpt-4o-mini",
  store=True,
  messages=[
    {"role": "user", "content": "1+1=?"}
  ]
)

print(completion.choices[0].message);
