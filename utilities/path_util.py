import os

def mkdir(folder_path):
    if not os.path.exists(os.path.abspath(folder_path)):
        os.makedirs(os.path.abspath(folder_path))

def isdir(folder_path):
	return os.path.isdir(os.path.abspath(folder_path))

def isexist(folder_path):
	return os.path.exists(os.path.abspath(folder_path))
	