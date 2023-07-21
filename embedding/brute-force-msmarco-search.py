
import sys
import glob
import random

from datasets import load_dataset

import docsearch
from config import *

QUERY_FILENAME = "/home/ubuntu/msmarco/msmarco-docdev-queries.tsv"
EMBED_FILENAME = "/home/ubuntu/msmarco/msmarco_embeddings.npy"
URL_FILENAME = "/home/ubuntu/msmarco/msmarco_url.npy"
how_many = 100

def _query(model_name):
    model_files = [EMBED_FILENAME]
    url_files = [URL_FILENAME]
    prec = 5 
    #prec = 0 

    lines = open(QUERY_FILENAME).read().splitlines()
    print("Read all lines")
    sys.stdout.flush()
    query_data = [line.split('\t') for line in lines]
    print("Split all lines by tabs")
    sys.stdout.flush()
    query_list = [elem[1] for elem in query_data]
    print(query_list, file=sys.stderr)
    sys.stderr.flush()
    qid_dict = dict()
    for elem in query_data:
        qid_dict[elem[1]] = int(elem[0])

    results_dict = docsearch.search_web(url_files, model_files, query_list, prec, how_many, model_name)
    for query in results_dict:
        print("Query: %d %s" % (qid_dict[query], query))
        topk = results_dict[query]
        print("\n")
        for r in topk:
            print(r['distance'], r['url'])
        print("")
        print("-------------------")
        sys.stdout.flush()

def main():
    model_name = 'msmarco-distilbert-base-tas-b'
    #if len(sys.argv) == 2:
    #    model_name = sys.argv[1]
    _query(model_name)

if __name__ == "__main__":
    main()
