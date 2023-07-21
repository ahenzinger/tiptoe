from sklearn.cluster import MiniBatchKMeans
import numpy
import pickle
import os
import sys
import glob
import re
import faiss
import concurrent
import pyarrow.parquet as pq
import pandas as pd

NUM_CLUSTERS = 4 * 4000
SCALE_FACTOR = 1000000
DIM = 512

def assign_chunk(i, index, embed_file, url_file):
    cluster_assignments = dict()
    print("Assigning for file %d/400" % i)
    with open(embed_file, 'r') as f:
        assign_data = numpy.load(embed_file)
    assign_data = numpy.round((assign_data) * (1<<5))
    df = pq.read_pandas(url_file, columns=['url']).to_pandas()

    distances, assignments = index.search(assign_data.astype(numpy.float32), 2)

    percentile = numpy.percentile([dist[1] - dist[0] for dist in distances], 20)

    for j in range(len(assignments)):
        for k in range(2):
            if (k == 0) or (k > 0 and (distances[j][k] - distances[j][0]) < percentile):
                cluster = assignments[j][k]
                embstr = ",".join(["%d" % ch for ch in assign_data[j]])
            doc_id = i * SCALE_FACTOR + j
            url = df.at[j, 'url']
            data_str = ("%d | %s | %s\n" % (doc_id, embstr, url))

            if cluster not in cluster_assignments:
                cluster_assignments[cluster] = [data_str]
            else:
                cluster_assignments[cluster].append(data_str)
    return cluster_assignments


def load_f(filename):
    with open(filename, 'r') as f:
        data = numpy.load(filename, allow_pickle=True)
    return numpy.round((data) * (1 << 5))

def main():
    embed_files = ["/work/edauterman/clip/deploy.laion.ai/8f83b608504d46bb81708ec86e912220/embeddings/img_emb/img_emb_%d.npy" % idx for idx in range(410)]
    url_files = ['/work/edauterman/clip/deploy.laion.ai/8f83b608504d46bb81708ec86e912220/embeddings/metadata/metadata_%d.parquet' % idx for idx in range(410)]

    centroids_file = "/work/edauterman/img_fixed/centroids.npy"
    with open(centroids_file, 'rb') as f:
        centroids = numpy.loadtxt(centroids_file)
    
    print(centroids)

    ctr = 0
    # empty all files
    for i in range(NUM_CLUSTERS):
        f = open("/work/edauterman/img_fixed/clusters/cluster_%d.txt" % i, 'w')
        f.close()

    cluster_sizes = dict()

    index = faiss.IndexHNSWFlat(DIM, 64, faiss.METRIC_INNER_PRODUCT)
    ef_search = 32
    ef_construction = 64
    index.hnsw.efConstruction = ef_construction
    index.hnsw.efSearch = ef_search
    index.add(centroids)

    for idx in range(11):
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
            future_to_assignment = [executor.submit(assign_chunk, idx * 40 + j, index, embed_files[idx * 40 + j], url_files[idx * 40 + j]) for j in range(min(40, 410 - idx * 40))]
            for i, future in enumerate(concurrent.futures.as_completed(future_to_assignment)):
                print("Finished %d" % ctr, file=sys.stderr)
                sys.stderr.flush()
                ctr += 1

                cluster_assignments = future.result()
                for cluster in cluster_assignments:
                    with open("/work/edauterman/img_fixed/clusters/cluster_%d.txt" % cluster, 'a') as f:
                        for line in cluster_assignments[cluster]:
                            f.write(line + "\n")

                    if cluster in cluster_sizes:
                        cluster_sizes[cluster] += len(cluster_assignments[cluster]) 
                    else:
                        cluster_sizes[cluster] = len(cluster_assignments[cluster])


    with open("cluster_sizes_img.txt", "w") as f:
        for cluster in cluster_assignments:
            f.write(str(cluster_sizes[cluster]) + "\n")


if __name__ == "__main__":
    main()
