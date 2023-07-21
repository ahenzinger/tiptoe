from sklearn.cluster import MiniBatchKMeans
import numpy
import pickle
import os
import sys
import glob
import re
import faiss
import concurrent

NUM_CLUSTERS = 4 * 32 * 10
DIM = 768
#DIM = 192
MULTI_ASSIGN = 2

def main():
    url_file = "/work/edauterman/private-search/code/embedding/embeddings_msmarco/msmarco_url.npy"
    embed_file = "/work/edauterman/private-search/code/embedding/embeddings_msmarco/msmarco_embeddings.npy"

    centroids_file = ("/work/edauterman/test_boundary_clusters_%d_faiss/centroids.npy" % MULTI_ASSIGN)

    data = numpy.load(embed_file)

    with open(centroids_file, 'rb') as f:
        centroids = numpy.loadtxt(centroids_file)
 
    print(centroids)

    cluster_files = [("/work/edauterman/test_boundary_clusters_%d_faiss/clusters/cluster_%d.txt" % (MULTI_ASSIGN, i)) for i in range(NUM_CLUSTERS)]
    assignment_dict = dict()
    distances, assignments = kmeans.index.search(data.astype(numpy.float32), MULTI_ASSIGN)

    print("Finished kmeans assignment")

    urls = numpy.load(url_file)

    percentiles = []
    for i in range(1, MULTI_ASSIGN):
        percentiles.append(numpy.percentile([(dist[i] - dist[0]) for dist in distances], 20))
   
    over_assign_count = 0
    for i in range(len(assignments)):
        for k in range(MULTI_ASSIGN):
            if (k == 0) or (k > 0 and (distances[i][k] - distances[i][0]) < percentiles[k-1]):
                cluster = assignments[i][k]
                if cluster not in assignment_dict:
                    assignment_dict[cluster] = [i]
                else:
                    assignment_dict[cluster].append(i)
                if k > 0:
                    over_assign_count += 1
    

    for i in range(NUM_CLUSTERS):
        print("%d/%d" % (i, NUM_CLUSTERS))
        with open(cluster_files[i], 'w') as f:
            if i in assignment_dict:
                for idx in assignment_dict[i]:
                    embed = data[idx]
                    url = urls[idx]
                    embstr = ",".join(["%f" % ch for ch in embed])
                    doc_id = idx
                    data_str = ("%d | %s | %s\n" % (doc_id, embstr, url))
                    f.write(data_str + "\n")
            else:
                print("Not in assignment dict %d" % i)

    print("Over assigning for param %d = %d" % (MULTI_ASSIGN, over_assign_count))

if __name__ == "__main__":
    main()
