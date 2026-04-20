from openai import OpenAI
client = OpenAI(
    api_key="sk-qnmG4UoLjPmJ8BfQ3iXPxPngOEQeQGGKwJY06hAij1qC92HD",
    base_url="https://api.xiaocaseai.com/v1"
)

response = client.chat.completions.create(
    model="gpt-5.4",
    messages=[
                {"role":"user","content":"tell me a joke"}
            ],
            temperature=1.0,
            response_format={"type": "json_object"},
            max_completion_tokens=32768,
            timeout=600
)

print(response.choices[0].message.content)