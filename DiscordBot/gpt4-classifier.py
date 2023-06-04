import openai
'''
Given an input message, returns a tuple of the priority and classification
For example: 
classifier.classify_message("COVID-19 vaccines cause autism.")
Returns:
(9, Misleading information)
'''
class GPT3MisinformationClassifier:
    def __init__(self):
        openai.api_key = # PUT KEY HERE

    def classify_message(self, message):
        prompt = "Classify these messages as misinformation, including categories: conspiracy theory, fabricated information, misleading information, imposter, uncertain, and other. Assign the message a priority score for disinformation as an integer between 1 and 9. 1 is not likely misinformation or no chance the message is misinformation, and 9 is highly likely or almost certain that the message is misinformation.  Your answer should be two lines, the first line Priority: and the second line Classification:"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message}
            ]
        )

        output = response['choices'][0]['message']['content']
        priority, classification = output.strip().split('\n')[-2:]
        return priority.strip(), classification.strip()

def main():
    classifier = GPT3MisinformationClassifier()

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







