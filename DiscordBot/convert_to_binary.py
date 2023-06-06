import csv

def process_scores(input_file, output_file):
    with open(input_file, 'r') as file:
        reader = csv.reader(file)
        rows = list(reader)

    processed_rows = []
    for row in rows:
        if len(row) != 2:
            continue  # Skip rows with incorrect format
        message = row[0].strip()
        score = row[1].strip()
        if not score.isdigit():
            continue  # Skip rows with non-numeric score
        score = int(score)
        processed_score = 0 if score <= 4 else 1
        processed_rows.append([message, processed_score])

    with open(output_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(processed_rows)

def main():
    input_file = 'data/messages-gpt3-generated.csv'
    output_file = 'data/messages-binary.csv'
    process_scores(input_file, output_file)
    print("Processing completed!")

if __name__ == '__main__':
    main()
