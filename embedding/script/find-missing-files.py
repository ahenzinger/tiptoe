
import os
import subprocess
import sys
import glob
from config import *

prefix = "/work/edauterman/private-search/code/embedding/web_msmarco_raw/web"
num_files = 1024

if __name__ == "__main__":
    all_files_lists = [glob.glob(("%s-*-%d.npy") % (prefix, i)) for i in range(num_files)]
    difference_files = []
    for i in range(num_files):
        if len(all_files_lists[i]) == 0:
            difference_files.append(i)
    print(difference_files)
    print(len(difference_files))
