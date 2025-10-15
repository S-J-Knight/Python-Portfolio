import csv
import os
import tkinter
from tkinter import *
from tkinter import ttk
from utils import *
import sv_ttk

# 1) Check files in folder -- DONE
# 2) Checkbox which files to load - DONE
# 3) Load files - Done
# 4) Search box to search card
# 5) Search the files for said card
# 6) Bulk search

files_list = [] # The files that are viable
people_list = [] # Each person listed in their file name as an owner of a datebase
loaded_files = [] # List of loaded files from the tickboxes

#requested_name = input("What would you like to search for?: ")
requested_name = 'Swamp'


# Run      
files_list, people_list = file_finder(files_list, people_list)


# tkinter
root = tkinter.Tk()
root.geometry("900x600")
root.title("Manabox Buddy")

#tkinter stuff goes here

#Frame 1 (TOP)
frame1 = ttk.LabelFrame(root, text="Databases", padding=10)
frame1.pack(padx = 10, pady = 10, side = LEFT, fill="x")


#checkbuttons
checkbox_vars = file_checkbox_creater(people_list)
checkbuttons, loaded_files = create_checkbuttons(frame1, people_list, checkbox_vars, loaded_files)


    
#Frame 2 (LEFT)
frame2 = Frame(background="blue")
button = ttk.Button(frame2, text="Testtestest").pack(padx=20, pady=20)
frame2.pack(padx = 10, pady = 10, side = RIGHT)

#FRAME 3(RIGHT)


# This is where the magic happens
sv_ttk.set_theme("dark")

root.mainloop()
# card_searcher(people_list, loaded_files, requested_name)