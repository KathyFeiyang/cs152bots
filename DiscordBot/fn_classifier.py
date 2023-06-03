import requests

API_TOKEN = "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"
API_URL = "https://api-inference.huggingface.co/models/vikram71198/distilroberta-base-finetuned-fake-news-detection"
headers = {"Authorization": f"Bearer {API_TOKEN}"}

def query(payload):
	response = requests.post(API_URL, headers=headers, json=payload)
	return response.json()
