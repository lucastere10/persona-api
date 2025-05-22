import openai
import json

# Create an OpenAI client (recommended new approach)
client = openai.OpenAI(api_key="")

# Send the chat request
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {
            "role": "user",
            "content": "Just testing the response from the OpenAI API. Can you tell me if this is working?"
        }
    ],
    max_tokens=300
)

# Extract the message content
reply = response.choices[0].message.content

# Extract token usage
tokens_used = response.usage

# Print the results
print("\n🧠 GPT Response:\n")
print(reply)
print("\n📊 Token Usage:")
print(f"Prompt tokens: {tokens_used.prompt_tokens}")
print(f"Completion tokens: {tokens_used.completion_tokens}")
print(f"Total tokens: {tokens_used.total_tokens}")

# Save full response to a JSON file
with open("gpt_response.json", "w", encoding="utf-8") as f:
    json.dump(response.model_dump(), f, indent=2, ensure_ascii=False)

print("\n💾 Response saved to 'gpt_response.json'")


