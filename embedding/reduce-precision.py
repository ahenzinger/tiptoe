import os
import sys
from datasets import load_dataset
from datasets import Dataset
from sentence_transformers import SentenceTransformer

import pickle
import numpy
import time

from config import *

def reduce_one(in_file, out_file, prec):
    try:
        docs_numpy = numpy.load(in_file)
        print("Loaded %s" % in_file)
        sys.stdout.flush()
        docs_numpy = numpy.round(docs_numpy * (1 << prec))
        print("Did rounding %s" % in_file)
        sys.stdout.flush()
        numpy.save(out_file, docs_numpy)
        print("Saved %s" % out_file)
        sys.stdout.flush()
    except ValueError as e:
        print('Failed loading %s' % in_file)
        sys.stdout.flush()

def main():
    if len(sys.argv) != 4:
        raise ValueError("Usage: python %s prec in-file out-file\n" % sys.argv[0])
    
    prec = int(sys.argv[1])
    in_file = sys.argv[2]
    out_file = sys.argv[3]
    reduce_one(in_file, out_file, prec)
    print(("Output %s to %s") % (in_file, out_file))

if __name__ == "__main__":
    main()
