import json
import os
import requests

from torch import nn
from transformers import AutoTokenizer, AutoModelForSequenceClassification


# API_KEY_PATH = 'key.json'
# if not os.path.isfile(API_KEY_PATH):
# 	raise Exception(f"{API_KEY_PATH} not found!")
# with open(API_KEY_PATH) as f:
# 	API_KEY = json.load(f)['roberta_fakenews']

# API_URL = "https://api-inference.huggingface.co/models/vikram71198/distilroberta-base-finetuned-fake-news-detection"


class DistilRoBERTaFakeNewsClassifier:
	def __init__(self):
		# self.headers = {"Authorization": f"Bearer {api_token}"}
		self.tokenizer = AutoTokenizer.from_pretrained(
			"vikram71198/distilroberta-base-finetuned-fake-news-detection")
		self.model = AutoModelForSequenceClassification.from_pretrained(
			"vikram71198/distilroberta-base-finetuned-fake-news-detection")

	def classify_message(self, message):
		# payload = {"inputs": message}
		# response = requests.post(API_URL, headers=self.headers, json=payload)
		# result = response.json()
		# score = result[0][1]['score']
		encoding = self.tokenizer(
			message,
			return_tensors='pt')
		outputs = self.model(**encoding)
		preds = nn.functional.softmax(outputs.logits, dim=-1)
		score = preds[0][0].item()
		return score, None


if __name__ == '__main__':
	classifier = DistilRoBERTaFakeNewsClassifier()
	classifier.classify_message('The earth is flat.') 
