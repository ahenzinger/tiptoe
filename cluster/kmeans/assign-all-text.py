from sklearn.cluster import MiniBatchKMeans
import numpy
import pickle
import os
import sys
import glob
import re
import faiss
import concurrent
import threading

NUM_CLUSTERS = 4 * 3500
SCALE_FACTOR = 1000000
MULTI_ASSIGN = 2
DIM=768

def assign_chunk_faiss(i, index, embed_file, url_file):
    cluster_assignments = dict()
    print("Assigning for file %d/1024" % i)
    with open(embed_file, 'r') as f:
        assign_data = numpy.load(embed_file, allow_pickle=True)
    with open(url_file, 'r') as f:
        url_data = numpy.load(url_file, allow_pickle=True)

    distances, assignments = index.search(assign_data.astype(numpy.float32), 2)

    percentiles = []
    for j in range(1, MULTI_ASSIGN):
        percentiles.append(numpy.percentile([(dist[j] - dist[0]) for dist in distances], 20))

    for j in range(len(assignments)):
        for k in range(MULTI_ASSIGN):
            if (k == 0) or (k > 0 and (distances[j][k] - distances[j][0]) < percentiles[k-1]):
                cluster = assignments[j][k]
                embstr = ",".join(["%d" % ch for ch in assign_data[j]])
                doc_id = i * SCALE_FACTOR + j
                url = url_data[j]['title']
                data_str = ("%d | %s | %s\n" % (doc_id, embstr, url))

                if cluster not in cluster_assignments:
                    cluster_assignments[cluster] = [data_str]
                else:
                    cluster_assignments[cluster].append(data_str)
    
    return cluster_assignments

def load_f(filename):
    with open(filename, 'r') as f:
        data = numpy.load(filename, allow_pickle=True)
    return data

def main():
    embed_files = ["/data/pdos/web-search/embeddings/web-idx-%d.npy" % i for i in range(1024)]
    url_files_all = glob.glob("/data/pdos/web-search/url_files/web-*.url")
    url_files = []
    for i in range(1024):
        r = re.compile("/data/pdos/web-search/url_files/web-[0-9]+-%d.url" % i)
        url_files += list(filter(r.match, url_files_all))

    centroids_file = "/data/pdos/web-search/cc_clusters/centroids.npy"
    
    with open(centroids_file, 'rb') as f:
        centroids = numpy.loadtxt(centroids_file)
 
    print(centroids)
    ctr = 0

    # empty all files
    for i in range(NUM_CLUSTERS):
        f = open("/data/pdos/web-search/cc_clusters/clusters/cluster_%d.txt" % i, 'w')
        f.close()

    index = faiss.IndexHNSWFlat(DIM, 64, faiss.METRIC_INNER_PRODUCT)
    ef_search = 32 
    ef_construction = 64
    index.hnsw.efConstruction = ef_construction
    index.hnsw.efSearch = ef_search
    index.add(centroids)

    cluster_sizes = dict()

    for idx in range(16):
        with concurrent.futures.ThreadPoolExecutor(max_workers=64) as executor:
            future_to_assignment = [executor.submit(assign_chunk_faiss, idx * 64 + j, index, embed_files[idx * 64 + j], url_files[idx * 64 + j]) for j in range(64)]
            for i, future in enumerate(concurrent.futures.as_completed(future_to_assignment)):
                print("Finished %d" % ctr, file=sys.stderr)
                sys.stderr.flush()
                ctr += 1

                cluster_assignments = future.result()
                for cluster in cluster_assignments:
                    with open("/data/pdos/web-search/cc_clusters/clusters/cluster_%d.txt" % cluster, 'a') as f:
                        for line in cluster_assignments[cluster]:
                            f.write(line + "\n")

                    if cluster in cluster_sizes:
                        cluster_sizes[cluster] += len(cluster_assignments[cluster]) 
                    else:
                        cluster_sizes[cluster] = len(cluster_assignments[cluster])


    with open("cluster_sizes.txt", "w") as f:
        for cluster in cluster_assignments:
            f.write(str(cluster_sizes[cluster]) + "\n")


if __name__ == "__main__":
    main()
