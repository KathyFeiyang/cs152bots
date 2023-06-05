import json
import os

import openai
'''
Given an input message, returns a tuple of the priority and classification
For example: 
classifier.classify_message("COVID-19 vaccines cause autism.")
Returns:
(9, Misleading information)
'''

API_KEY_PATH = 'key.json'


class GPT4MisinformationClassifier:
    def __init__(self, api_key):
        openai.api_key = api_key

    def classify_message(self, message):
        prompt = "Classify these messages as disinformation, including categories: conspiracy theory, fabricated information, misleading information, imposter, uncertain, and other. Assign the message a probability score for whether the message constitutes disinformation as a number between 0 and 1. 0 is not likely disinformation or no chance the message is disinformation, and 1 is highly likely or almost certain that the message is disinformation.  Your answer should be two lines, the first line Score: and the second line Classification:"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message}
            ]
        )

        output = response['choices'][0]['message']['content']
        score, classification = output.strip().split('\n')[-2:]
        try:
            score_parsed = min(max(float(score.split('Score:')[-1]), 0), 1)
        except:
            score_parsed = 0.5
        classification_parsed = classification.split('Classification:')[-1].strip()
        return score_parsed, classification_parsed


def main():
    if not os.path.isfile(API_KEY_PATH):
        raise Exception(f"{API_KEY_PATH} not found!")
    with open(API_KEY_PATH) as f:
        api_key = json.load(f)['key']
    classifier = GPT4MisinformationClassifier(api_key)

    # Messages to try
    #message = "The earth is not flat."
    #message = "The current US President is Donald Trump."
    #message = "Dinosaurs are dead."
    message = "COVID-19 vaccines cause autism."

    priority, classification = classifier.classify_message(message)
    print("Priority:", priority)
    print("Classification:", classification)


if __name__ == '__main__':
    main()
