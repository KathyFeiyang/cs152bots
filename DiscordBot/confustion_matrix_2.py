# confusion matrix for fn classifier

import csv
from fn_classifier import DistilRoBERTaFakeNewsClassifier

# Function to read the dataset from a CSV file
def read_dataset(file_path):
    messages = []
    labels = []
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) == 2:
                messages.append(row[0])
                if row[1].strip() != '':
                    labels.append(int(row[1].strip()))
    return messages, labels


def confusion_matrix(y_true, y_pred, labels=None):

    # Check if labels are provided
    if labels is None:
        labels = list(set(y_true + y_pred))

    # Create an empty confusion matrix
    matrix = [[0] * len(labels) for _ in range(len(labels))]

    # Fill the confusion matrix
    for true, pred in zip(y_true, y_pred):
        matrix[labels.index(true)][labels.index(pred)] += 1

    return matrix

def main():
    classifier = DistilRoBERTaFakeNewsClassifier()

    dataset_file = 'data/messages-binary.csv'

    messages, labels = read_dataset(dataset_file)

    predictions = []
    for message in messages:
        print(message)
        prediction = classifier.classify_message(message)
        predictions.append(prediction)
    # predictions = [GPT4MisinformationClassifier.classify_message(message) for message in messages]

    confusion_mat = confusion_matrix(labels, predictions)

    print(confusion_mat)

if __name__ == '__main__':
    main()