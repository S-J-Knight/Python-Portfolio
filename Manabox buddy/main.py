import csv

#requested_name = input("What would you like to search for?: ")
requested_name = 'Nova Hellkite'

with open('Manabox buddy/Jamie_ManaBox_Collection.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['Name'] == requested_name:
                text = f"There is {row["Quantity"]} from the set {row["Set name"]}"
                print(text)