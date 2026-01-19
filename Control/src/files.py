import os

# Create a folder for music temp if it does not already exist.
def create_folder(folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)