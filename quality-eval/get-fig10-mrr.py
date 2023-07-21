import sys
import re
import statistics
import numpy
import json

from mrr import *


def main():
    basic_file = sys.argv[1]
    basic_url_random_file = sys.argv[2]
    basic_url_cluster_file = sys.argv[3]
    boundary_url_cluster_file = sys.argv[4]
    boundary_url_cluster_pca_file = sys.argv[5]
    qrels_file = sys.argv[6]

    obj = dict()
    real = read_ranked_qrel(qrels_file)
    obj['basic'] = compute_mrr(read_top_results(basic_file), real)
    obj['basic_url_random'] = compute_mrr(read_top_results(basic_url_random_file), real)
    obj['basic_url_cluster'] = compute_mrr(read_top_results(basic_url_cluster_file), real)
    obj['boundary_url_cluster'] = compute_mrr(read_top_results(boundary_url_cluster_file), real)
    obj['boundary_url_cluster_pca'] = compute_mrr(read_top_results(boundary_url_cluster_pca_file), real)
    
    with open(sys.argv[7], 'w') as f:
        json.dump(obj, f)

if __name__ == "__main__":
    main()
