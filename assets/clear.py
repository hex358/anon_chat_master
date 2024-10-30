from shutil import rmtree
from os import mkdir

def _clear(directory):
    rmtree(directory)
    mkdir(directory)