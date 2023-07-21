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

def load_f(filename):
    with open(filename, 'r') as f:
        data = numpy.load(filename, allow_pickle=True)
    return numpy.round((data) * (1 << 5))

def main():
    embed_files = ["/work/edauterman/clip/deploy.laion.ai/8f83b608504d46bb81708ec86e912220/embeddings/img_emb/img_emb_%d.npy" % idx for idx in range(410)]
    url_files = ['/work/edauterman/clip/deploy.laion.ai/8f83b608504d46bb81708ec86e912220/embeddings/metadata/metadata_%d.parquet' % idx for idx in range(410)]

    centroids_file = "/work/edauterman/img_fixed/centroids.npy"
    
    data = numpy.empty((0, DIM))
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        future_to_data = [executor.submit(load_f, embed_file) for embed_file in embed_files[:10]]
        for i, future in enumerate(concurrent.futures.as_completed(future_to_data)):
            print("Loaded %d" % i)
            assign_data = future.result()
            if len(data) > 0:
                data = numpy.concatenate((data, assign_data), axis=0)
            else:
                data = assign_data

    kmeans = faiss.Kmeans(512, NUM_CLUSTERS, verbose=True, nredo=1)
    kmeans.train(data.astype(numpy.float32))
    centroids = kmeans.centroids
    print(centroids)
    numpy.savetxt(centroids_file, centroids)
    


    print("Finished kmeans")


if __name__ == "__main__":
    main()
