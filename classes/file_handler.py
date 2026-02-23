
import pandas as pd
from pathlib import Path
from os import listdir
from os.path import isfile, join

def save_csv(df, path, file_name):
    df.to_csv(path + file_name, index=False, encoding='utf-8')
    return

def read_file_names_in_path(path):
    files = listdir(path)
    result = []
    for file in files:
        if isfile(join(path, file)):
            result.append(file.split('.')[0])
    return result
