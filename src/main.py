import audible
import subprocess
import csv
import os

auth = audible.Authenticator.from_file("Michael.json")
client = audible.Client(auth)
file = 'audiobooks/audible_library.csv'

def add_entry(csv_file, entry):
    with open(csv_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        existing_entries = [row for row in reader]

    if any(existing_entry[0] == entry[0] for existing_entry in existing_entries):
        print(f"{entry[1]} is already in the library.")
    else:
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(entry)
            print(f"Added {entry[1]} to the library.")

def download_book(book, output_dir):
    print(f"Downloading {book['title']}...")

    os.makedirs(output_dir, exist_ok=True)

    command = ['audible', 'download', '-o', output_dir, '-a', book['asin'], '--aax-fallback', '-y']
    print(f"Command: {' '.join(command)}")
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(result.stdout.decode('utf-8'))
    except subprocess.CalledProcessError:
        print(result.stderr.decode('utf-8'))

    

with client:
    library = client.get(
        "1.0/library",
        num_results = 1,
        response_groups = "product_desc, product_attrs",
        sort_by = "-PurchaseDate"
    )
    for book in library['items']:
        bookEntry = [book['asin'], book['title'], book['purchase_date'], book['runtime_length_min']]
        add_entry(file, bookEntry)
        download_book(book, 'audiobooks/downloaded')
