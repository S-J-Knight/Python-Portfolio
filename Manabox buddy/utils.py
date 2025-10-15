import csv
import os
import tkinter
from tkinter import *
from tkinter import messagebox
from tkinter import ttk

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

def create_checkbuttons_database(frame, people_list,checkbox_vars,loaded_files):
    checkbuttons = {}
    for x in range(len(people_list)):
        def make_callback(idx):
            # Capture the person at callback creation time to avoid late-binding
            person = people_list[idx]
            def callback():
                if person in loaded_files:
                    loaded_files.remove(person)
                else:
                    loaded_files.append(person)
            return callback
        cb = tkinter.Checkbutton(
            frame,
            text=f'{people_list[x]}',
            variable=checkbox_vars[x + 1],
            onvalue=1,
            offvalue=0,
            command=make_callback(x)
        )
        cb.config(bg="snow", fg="Grey1", font=("Arial", 12), selectcolor="snow", relief="raised")
        cb.grid(row=x, column=0, padx=5, pady=5, sticky="w")
        checkbuttons[f'Checkbutton_{x}'] = cb  # Store in dictionary

    for cb in checkbuttons.values():
        cb.flash()
    return checkbuttons, loaded_files

def create_checkbox_options(frame2):
    options = ["Single Card Search", "Multi-card search"]
    vars = [tkinter.IntVar() for _ in options]
    checkbuttons = []

    def make_callback(idx):
        def callback():
            # Set the selected option to 1, others to 0
            for i, v in enumerate(vars):
                v.set(1 if i == idx else 0)
        return callback

    for idx, option in enumerate(options):
        cb = tkinter.Checkbutton(
            frame2,
            text=option,
            variable=vars[idx],
            bg="snow",
            fg="Grey1",
            font=("Arial", 12),
            selectcolor="snow",
            relief="raised",
            command=make_callback(idx)
        )
        cb.grid(row=idx, column=0, padx=5, pady=5, sticky="w")
        cb.flash()
        checkbuttons.append(cb)

    return vars, checkbuttons



def card_searcher(loaded_files, requested_name):
    # Function to search cards
    x = 0
    while x < len(loaded_files):
        filename = f'{loaded_files[x]}_Manabox_Collection.csv'  # Get the corresponding filename
        try:
            with open(os.path.join(dir_path, filename), newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['Name'] == requested_name:
                        text = f'There is {row["Quantity"]} from the set {row["Set name"]}'
                        text += f'\nThe owner is {loaded_files[x]}'
                        print(text)
        except Exception as e:
            messagebox.showerror("Error!", "Error - something broke!")
        x += 1