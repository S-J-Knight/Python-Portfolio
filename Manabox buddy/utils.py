import csv
import os
import tkinter
from tkinter import *

dir_path = os.path.dirname(os.path.realpath(__file__))

def file_finder(files_list, people_list):
    # Function to find files
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.endswith('.csv'):
                files_list.append(file)
                name = file[:-23]
                people_list.append(name)
    return files_list, people_list

def file_checkbox_creater(people_list):
    # Makes an empty dict
    checkbox_vars = {}
    
    # Gets the number of people
    number_of_people = len(people_list)
    
    #Iterates through each person, assigning an unique var to each person
    for x in range(1, number_of_people + 1):
        checkbox_vars[x]=tkinter.IntVar()
    return checkbox_vars



def card_searcher(people_list, files_list):
    # Function to search cards
    x = 0
    while x < len(people_list):
        filename = files_list[x]  # Get the corresponding filename
        try:
            with open(os.path.join(dir_path, filename), newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['Name'] == requested_name:
                        text = f'There is {row["Quantity"]} from the set {row["Set name"]}'
                        text += f'\nThe owner is {people_list[x]}'
                        print(text)
        except Exception as e:
            print("it broke")
        x += 1

def create_checkbuttons(frame, people_list,checkbox_vars):
    checkbuttons = {}
    for x in range(len(people_list)):
        def make_callback(idx):
            return lambda: print(
                f"Checkbox for {people_list[idx]} is {'selected' if checkbox_vars[idx + 1].get() == 1 else 'deselected'}"
            )
        cb = tkinter.Checkbutton(
            frame,
            text=f'{people_list[x]}',
            variable=checkbox_vars[x + 1],
            onvalue=1,
            offvalue=0,
            command=make_callback(x)
        )
        cb.config(bg="Orange", fg="white", font=("Arial", 12), selectcolor="green", relief="raised")
        cb.pack(padx=5, pady=5, side=LEFT)
        checkbuttons[f'Checkbutton_{x}'] = cb  # Store in dictionary

    for cb in checkbuttons.values():
        cb.flash()
    return checkbuttons