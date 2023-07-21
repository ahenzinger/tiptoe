
import sys
import glob
import random

from datasets import load_dataset

import docsearch
from config import *

QUERY_FILENAME = "/data/pdos/web-search/aol_logs/query_list.txt"

def get_query_list():
    with open(QUERY_FILENAME) as file:
        lines = [line.rstrip() for line in file]
    print(lines, file=sys.stderr)
    #random.shuffle(lines)
    return lines

def _query(model_name, query_list):
    model_files = []
    for f in MODEL_FILES:
        model_files = model_files + glob.glob(f)
    url_files = []
    for f in URL_FILES:
        url_files = url_files + glob.glob(f)
    sys.stderr.flush()
    prec = 0
    #prec = 5 
    results_dict = docsearch.search_web(url_files, model_files, query_list[:1000], prec, NUM_RESULTS, model_name)
    for query in results_dict:
        print("Query: %s" % query)
        topk = results_dict[query]
        print("\n")
        for r in topk:
            print(r['distance'], r['url'])
        print("")
        print("-------------------")
        sys.stdout.flush()

def main():
    model_name = 'msmarco-distilbert-base-tas-b'
    if len(sys.argv) == 2:
        model_name = sys.argv[1]
    query_list = get_query_list()
    _query(model_name, query_list)

if __name__ == "__main__":
    main()
