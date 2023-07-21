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

def save(entries, outfile):
    with open(outfile, 'wb') as f:
        pickle.dump(entries, f)

def chunk_record(record):
    text = record['text'].split()
    return {"sentence": ' '.join(text[0:SEQ_LEN]), "url": record['url']}

def compute_embeddings(model, idx):
    model = SentenceTransformer(model)
    model.max_seq_length = SEQ_LEN
    # Can alternatively load from disk
    #dataset = load_dataset("json", data_files='/data/pdos/web-search/hf_source/c4-train.%s-of-01024.json.gz' % ('{:05d}'.format(idx)), split="train")
    dataset = load_dataset('allenai/c4', data_files='en/c4-train.%s-of-01024.json.gz' % ('{:05d}'.format(idx)), split='train', cache_dir="/work/edauterman/.cache2/huggingface")
    print("Loaded dataset shard with idx %d, len %d" % (idx, len(dataset['text'])))
    sys.stdout.flush()
    chunked_dataset = dataset.map(chunk_record, remove_columns=dataset.column_names)
    print("Chunked dataset %d" % len(chunked_dataset['sentence']))
    sys.stdout.flush()
    embeddings = numpy.array(model.encode(chunked_dataset['sentence'], batch_size=32, convert_to_numpy=True))
    print("Encoded %d" % (len(chunked_dataset['sentence'])))
    sys.stdout.flush()
    urls = chunked_dataset['url']
    
    return (embeddings, urls)

def process_embeddings(embeddings, urls, out_url, out_embeddings):
    out_url_data = Dataset.from_dict({"title": urls})
    save(out_url_data, out_url)

    embeddings_mat = numpy.asmatrix(embeddings)
    numpy.save(out_embeddings, embeddings_mat)

def main():
    if len(sys.argv) != 4:
        raise ValueError("Usage: python %s idx file-prefix model\n" % sys.argv[0])
    
    idx = int(sys.argv[1])
    prefix = sys.argv[2]
    model = sys.argv[3]
    embeddings, urls = compute_embeddings(model, idx)
    chunksize = len(embeddings)
    url_file = ("%s-%d-%d.url") % (prefix, chunksize, idx)
    embedding_file = ("%s-%d-%d.npy") % (prefix, chunksize, idx)
    process_embeddings(embeddings, urls, url_file, embedding_file)
    print(("Output to %s and %s") % (url_file, embedding_file))

if __name__ == "__main__":
    main()
