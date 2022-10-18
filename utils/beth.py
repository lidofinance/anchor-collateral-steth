import csv

CSV_DOWNLOADED_AT_BLOCK = 15767035
BETH_BURNED = 4449999990000000000 + 439111118580000000000

def import_beth_holders_from_csv():
    with open("beth-holders.csv") as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=",")
        holders = list(csv_reader)[1:]

    return holders

beth_holders = import_beth_holders_from_csv()