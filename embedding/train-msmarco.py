import os
import sys
from datasets import load_from_disk, load_dataset
from datasets import Dataset
from sentence_transformers import SentenceTransformer

import pickle
import numpy
import time

from config import *

NTHREADS = 1
#NTHREADS = max(1, multiprocessing.cpu_count() - 1)
DATA_FILE = "/work/edauterman/test_passages/collection.tsv"

def save(entries, outfile):
    with open(outfile, 'wb') as f:
        pickle.dump(entries, f)

def compute_embeddings(model):
    model = SentenceTransformer(model)
    model.max_seq_length = SEQ_LEN
    lines = open(DATA_FILE).read().splitlines()
    print("Read all lines")
    sys.stdout.flush()
    new_data = [line.split('\t') for line in lines]
    print("Split all lines by tabs")
    sys.stdout.flush()
    print([elem[3] for elem in new_data])
    chunked_data = [' '.join(elem[1].split()[0:SEQ_LEN]) for elem in new_data]
    embeddings = numpy.array(model.encode(chunked_data, batch_size=32, convert_to_numpy=True))
    print("Encoded all")
    sys.stdout.flush()
    docids = [elem[0] for elem in new_data] 
    
    return (embeddings, docids)

def process_embeddings(embeddings, docids, out_docids, out_embeddings):
    numpy.save(out_docids, numpy.array(docids))

    embeddings_mat = numpy.asmatrix(embeddings)
    numpy.save(out_embeddings, embeddings_mat)

def main():
    if len(sys.argv) != 2:
        raise ValueError("Usage: python %s idx file-prefix\n" % sys.argv[0])
    
    prefix = sys.argv[1]
    model = "msmarco-distilbert-base-tas-b"
    embeddings, docids = compute_embeddings(model)
    docids_file = ("%s_url.npy") % (prefix)
    embedding_file = ("%s_embeddings.npy") % (prefix)
    process_embeddings(embeddings, docids, docids_file, embedding_file)
    print(("Output to %s and %s") % (docids_file, embedding_file))

if __name__ == "__main__":
    main()
