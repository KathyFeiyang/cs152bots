# calculating accuracy for fn classifier

import csv
from fn_classifier import DistilRoBERTaFakeNewsClassifier

def calculate_accuracy(classifier, messages, labels):
    correct_predictions = 0
    total_predictions = len(messages)

    for message, label in zip(messages, labels):
        prediction = classifier.classify_message(message)
        if prediction == label:
            correct_predictions += 1

    accuracy = correct_predictions / total_predictions

    return accuracy

def read_dataset(file_path):
    messages = []
    labels = []
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            messages.append(row[0])
            labels.append(int(row[1]))
    return messages, labels

def main():
    api_key = #TODO

    dataset_file = 'data/messages-binary.csv'

    classifier = DistilRoBERTaFakeNewsClassifier()

    messages, labels = read_dataset(dataset_file)

    accuracy = calculate_accuracy(classifier, messages, labels)

    print("Accuracy:", accuracy)

if __name__ == '__main__':
    main()
