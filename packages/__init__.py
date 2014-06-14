import os
import sys


def insert_into_python_path():
    """
    Inserts this directory into the Python path, making the packages contained
    within directly importable
    """
    path = os.path.dirname(os.path.realpath(__file__))

    # Insert at the beginning of the Python path to give the packages contained
    # within this directory the highest priority when importing. This is done
    # to avoid importing potentially existing different versions of the
    # packages on the Python path
    sys.path.insert(0, path)
