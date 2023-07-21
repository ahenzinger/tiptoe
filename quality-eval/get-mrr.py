import sys
import re
import statistics
import numpy

from mrr import *

QRELS_FILE = "/home/ubuntu/msmarco_checkpoints/msmarco-docdev-qrels.tsv" 

def main():
    results = read_top_results(sys.argv[1])
    real = read_ranked_qrel(QRELS_FILE)
    mrr = compute_mrr(results, real)
    print("MRR@%d: %f" % (MRR_RANK,mrr))

if __name__ == "__main__":
    main()
