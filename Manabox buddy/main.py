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

#Frame 1 (LEFT)
frame1 = ttk.LabelFrame(root, text="Databases", padding=10)
frame1.grid(row=0, column=0, rowspan=3, sticky="nw", padx=10, pady=10)

#checkbuttons (FRAME 1)
checkbox_vars = file_checkbox_creater(people_list)
checkbuttons, loaded_files = create_checkbuttons_database(frame1, people_list, checkbox_vars, loaded_files)


    
#Frame 2 (LEFT)
frame2 = ttk.LabelFrame(root, text="Search Options", padding=10)
frame2.grid(row=0, column=1, rowspan=2, sticky="n", padx=10, pady=10)

#checkbuttons (FRAME 2)
vars_2, checkbuttons_2 = create_checkbox_options(frame2)

#Frame 3(below)

def on_search():
    card_searcher(loaded_files, requested_name)
search_btn = ttk.Button(frame2, text="Search", command=on_search)





# This is where the magic happens
sv_ttk.set_theme("dark")

root.mainloop()
