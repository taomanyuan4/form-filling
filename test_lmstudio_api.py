import requests

url = "http://127.0.0.1:1234/v1/chat/completions"

payload = {
    "model": "qwen2.5-7b-instruct",
    "messages": [
        {"role": "user", "content": "只回答 OK，不要多余内容"}
    ],
    "temperature": 0
}

r = requests.post(url, json=payload, timeout=60)
print(r.json()["choices"][0]["message"]["content"])
