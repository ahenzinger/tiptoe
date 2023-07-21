import numpy
import os
import sys
import faiss
import concurrent
import glob
import concurrent.futures
import math
import zlib

#DIM=256
DIM=768
AVG_BUNDLE_SIZE = 4000
MAX_SIZE = 4000
URLS_PER_BUNDLE = 160 
CLUSTER_DIR = "/home/ubuntu/boundary_clusters"
BASE_DIR = "/home/ubuntu/boundary_cluster_url_cluster_2"
NUM_CLUSTERS = 4 * 32 * 10


def parse_file(filename):
    contents = []
    with open(filename, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if len(line) <= 1:
                continue
            contents.append(line.split(" | "))
    return contents

def get_size(contents):
    out = zlib.compress(bytes(' '.join([content[2] for content in contents]), 'utf-8'), level=9)
    return len(out)

def create_bundles(contents):
    print("create bundles")
    num_bundles = int(math.ceil(float(get_size(contents)) / float(AVG_BUNDLE_SIZE)))
    print("Num_bundles = %d" % num_bundles)
    embed_contents = [elem[1] for elem in contents]
    data = numpy.loadtxt(embed_contents, delimiter=",")
    kmeans = faiss.Kmeans(DIM, num_bundles, nredo=3)
    if len(data) >= 1 and len(numpy.shape(data)) == 2:
        kmeans.train(data.astype(numpy.float32))
        centroids = kmeans.centroids
        _, assignments = kmeans.index.search(data.astype(numpy.float32), 1)
    else:
        centroids = numpy.zeros((1, DIM))
        assignments = [[0]]
   
    assignment_dict = dict()
    for i,cluster_pair in enumerate(assignments):
        cluster = cluster_pair[0]
        if cluster not in assignment_dict:
            assignment_dict[cluster] = [contents[i]]
        else:
            assignment_dict[cluster].append(contents[i])

    # Divide arbitrarily when all documents are the same
    if len(assignment_dict) == 1  and num_bundles > 1:
        print("IN LEN = 1")
        for i in range(int(math.ceil(float(len(contents)) / float(URLS_PER_BUNDLE)))):
            centroids[i] = centroids[list(assignment_dict.keys())[0]]
            upper_bound = min((i+1) * URLS_PER_BUNDLE, len(contents))
            assignment_dict[i] = [contents[j] for j in range(i * URLS_PER_BUNDLE, upper_bound)]
            return (centroids, assignment_dict)

    init_clusters = list(assignment_dict.keys()).copy()
    for cluster in init_clusters:
        # causing key error?
        if get_size(assignment_dict[cluster]) > MAX_SIZE:
            print("OVER MAX SIZE")
            (sub_centroids, sub_assignment_dict) = create_bundles(assignment_dict[cluster])
            replace_idx = sorted(list(sub_assignment_dict.keys()))[0]
            centroids[cluster] = sub_centroids[replace_idx]
            assignment_dict[cluster] = sub_assignment_dict[replace_idx]
            offset = len(centroids)
            centroids = numpy.row_stack((centroids, sub_centroids[replace_idx + 1:]))
            #centroids = centroids + sub_centroids[1:]
            # Note: can have some centroids for empty clusters here
            for sub_cluster in sub_assignment_dict:
                if sub_cluster != replace_idx:
                    assignment_dict[sub_cluster + offset] = sub_assignment_dict[sub_cluster]

    return (centroids, assignment_dict)

def process_cluster(cluster_file, cluster_idx):
    print("**** PROCESS CLUSTER *****")
    contents = parse_file(cluster_file)
    print("LEN = ", len(contents))
    if len(contents) == 0:
        return
    centroids, assignment_dict = create_bundles(contents)
    print("Writing to file -- %s/%d" % (BASE_DIR, cluster_idx))
    if not os.path.exists(("%s/%d/") % (BASE_DIR, cluster_idx)):
        os.mkdir("%s/%d/" % (BASE_DIR, cluster_idx))
    if not os.path.exists(("%s/%d/clusters") % (BASE_DIR, cluster_idx)):
        os.mkdir("%s/%d/clusters/" % (BASE_DIR, cluster_idx))
    numpy.savetxt("%s/%d/centroids.npy" % (BASE_DIR, cluster_idx), centroids)
   
    for bundle in assignment_dict:
        with open("%s/%d/clusters/bundle_%d.txt" % (BASE_DIR, cluster_idx, bundle), "w") as f:
            print("Writing to %s/%d/clusters/bundle_%d.txt" % (BASE_DIR, cluster_idx, bundle))
            for elem in assignment_dict[bundle]:
                if len(elem) == 3:
                    f.write("%s | %s | %s\n" % (elem[0], elem[1], elem[2]))
                else:
                    print("ERORR: elem != 3")
                    print(len(elem))
    print("Finished write")

def main():
    if not os.path.exists(BASE_DIR):
        os.mkdir(BASE_DIR)
    cluster_files = ["%s/clusters/cluster_%d.txt" % (CLUSTER_DIR, i) for i in range(NUM_CLUSTERS)]
    ctr = 0
    for i in range(len(cluster_files)):
        process_cluster(cluster_files[i], i)
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future_to_assignment = [executor.submit(process_cluster, cluster_files[i], i) for i in range(len(cluster_files))]
        for i, future in enumerate(concurrent.futures.as_completed(future_to_assignment)):
            print("Finished %d/%d" % (ctr, len(cluster_files)))
            ctr += 1
            future.result()
    """
if __name__ == "__main__":
    main()
