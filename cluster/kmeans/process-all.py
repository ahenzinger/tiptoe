import numpy
import os
import sys
import faiss
import concurrent
import glob
import concurrent.futures
import math
import zlib

DIM=512
#DIM=768
AVG_BUNDLE_SIZE = 50000
MAX_SIZE = 50000
CLUSTER_DIR = "/home/ubuntu/down/"
BASE_DIR = "/home/ubuntu/up/"
NUM_CLUSTERS = 4 * 4000
#NUM_CLUSTERS = 4 * 3500
URL_MAX_SIZE = 25000
AVG_URL_BUNDLE_SIZE = 25000
URLS_PER_BUNDLE = 330
#PCA_COMPONENTS_FILE = "/home/ubuntu/down/pca_192.npy"
PCA_COMPONENTS_FILE = "/home/ubuntu/down/pca_384.npy"
#IS_TEXT = True 
IS_TEXT = False 

def parse_file(filename):
    contents = []
    with open(filename, 'r') as f:
        lines = [line for line in f.readlines() if line.strip()]
        for line in lines:
            if len(line) <= 1:
                continue
            contents.append(line.split(" | "))
    return contents

def get_size(contents):
    out = zlib.compress(bytes(' '.join([content[2] for content in contents]), 'utf-8'), level=9)
    return len(out)

def pca_contents(contents, data, pca_components):
    # Don't divide by 10 for images
    if numpy.shape(data)[-1] != DIM:
        return []
    pca_output = []
    if IS_TEXT:
        pca_output = numpy.clip(numpy.round(numpy.matmul(data, pca_components)/10), -16, 15)
    else:
        pca_output = numpy.clip(numpy.round(numpy.matmul(data, pca_components)), -16, 15)
    out = [(contents[i][0], ",".join(["%d" % ch for ch in pca_output[i]]), contents[i][2]) for i in range(len(contents))]
    return out
    #return contents

def pack_url_bundles(bundles):
    packed_bundles = []
    bundles.sort(key=lambda x: get_size(x), reverse=True)
    for new_bundle in bundles:
        placed = False
        for i,packed_bundle in enumerate(packed_bundles):
            if not placed and get_size(packed_bundle + new_bundle) < URL_MAX_SIZE:
                packed_bundles[i] = packed_bundles[i] + new_bundle
                placed = True
                continue
        if not placed:
            packed_bundles.append(new_bundle)
    return packed_bundles


def cluster_by_url(contents, pca_components):
    sz = get_size(contents)
    num_bundles = int(math.ceil(float(sz) / float(AVG_URL_BUNDLE_SIZE)))
    embed_contents = [elem[1] for elem in contents]
    data = numpy.loadtxt(embed_contents, delimiter=",")
    if len(numpy.shape(data)) < 2:
        return [pca_contents(contents, [data], pca_components)]
    if num_bundles == 1:
        return [pca_contents(contents, data, pca_components)]
    kmeans = faiss.Kmeans(DIM, num_bundles, nredo=1)
    if len(data) > 1 and len(numpy.shape(data)) == 2:
        kmeans.train(data.astype(numpy.float32))
        _, assignments = kmeans.index.search(data.astype(numpy.float32), 1)
    else:
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
        output_list = []
        for i in range(num_bundles):
            upper_bound = min((i+1) * URLS_PER_BUNDLE, len(contents))
            output_list.append(pca_contents(contents[i * URLS_PER_BUNDLE: upper_bound], data[i * URLS_PER_BUNDLE: upper_bound], pca_components))
        return output_list 
        #return [pca_contents(contents, data, pca_components)]


    output_list = []
    init_clusters = list(assignment_dict.keys()).copy()
    for cluster in init_clusters:
        # causing key error?
        if get_size(assignment_dict[cluster]) > URL_MAX_SIZE:
            sub_output_list = cluster_by_url(assignment_dict[cluster], pca_components)
            output_list = output_list + sub_output_list
        else:
            cluster_data = numpy.loadtxt([elem[1] for elem in assignment_dict[cluster]], delimiter=",")
            if len(numpy.shape(cluster_data)) < 2:
                output_list.append(pca_contents(assignment_dict[cluster], [cluster_data], pca_components))
            else:
                output_list.append(pca_contents(assignment_dict[cluster], cluster_data, pca_components))
    return output_list


def split_cluster(contents, pca_components):
    num_bundles = int(2.0 * math.ceil(float(len(contents)) / float(AVG_BUNDLE_SIZE)))
    embed_contents = [elem[1] for elem in contents]
    data = numpy.loadtxt(embed_contents, delimiter=",")
    kmeans = faiss.Kmeans(DIM, num_bundles, nredo=1)
    if len(data) >= 1 and len(numpy.shape(data)) == 2:
    #if len(data) > 1 and len(numpy.shape(data)) == 2:
        kmeans.train(data.astype(numpy.float32))
        centroids = kmeans.centroids
        _, assignments = kmeans.index.search(data.astype(numpy.float32), 1)
    else:
        return []
        #centroids = data    #numpy.zeros((1, DIM))
        #assignments = [[0]]
   
    assignment_dict = dict()
    membership_dict = dict()
    for i in range(num_bundles):
        assignment_dict[i] = []
        membership_dict[i] = set()
    for i,cluster_pair in enumerate(assignments):
        cluster = cluster_pair[0]
        # Deduplicate
        if contents[i][2] not in membership_dict[cluster]:
            #if contents[i][2] not in set([elem[2] for elem in assignment_dict[cluster]]):
            assignment_dict[cluster].append(contents[i])
            membership_dict[cluster].add(contents[i][2])
   
    num_zeros = 0
    for i in range(num_bundles):
        if len(assignment_dict[i]) == 0:
            num_zeros += 1
    # Divide arbitrarily when all documents are the same
    if num_zeros == num_bundles - 1 and num_bundles > 0:
        for i in range(num_bundles):
            centroids[i] = centroids[list(assignment_dict.keys())[0]]
            upper_bound = min((i+1) * AVG_BUNDLE_SIZE, len(contents))
            assignment_dict[i] = cluster_by_url([contents[j] for j in range(i * AVG_BUNDLE_SIZE, upper_bound)], pca_components)
        return (centroids, assignment_dict)


    # Clear out empty clusters and recompute centroid
    new_centroids = []
    new_assignment_dict = dict()
    num_zeros = 0
    for i in range(len(centroids)):
        if i in assignment_dict:
            new_assignment_dict[i - num_zeros] = assignment_dict[i]
            if len(assignment_dict[i - num_zeros]) > 0:
                centroids[i - num_zeros] = numpy.loadtxt([elem[1] for elem in assignment_dict[i]], delimiter=',').mean(axis=0)
        else:
            num_zeros += 1
    centroids = centroids[:len(centroids) - num_zeros]
    assignment_dict = new_assignment_dict


    init_clusters = list(assignment_dict.keys()).copy()
    clustered_dict = dict()
    for cluster in init_clusters:
        # causing key error?
        if len(assignment_dict[cluster]) > MAX_SIZE:
            (sub_centroids, sub_clustered_dict) = split_cluster(assignment_dict[cluster], pca_components)
            #replace_idx = sorted(list(sub_assignment_dict.keys()))[0]
            offset = len(centroids)
            centroids[cluster] = sub_centroids[0]
            clustered_dict[cluster] = sub_clustered_dict[0]
            if len(sub_centroids) > 1:
                centroids = numpy.row_stack((centroids, sub_centroids[1:]))
            for sub_cluster in sub_clustered_dict:
                if sub_cluster != 0:
                    clustered_dict[sub_cluster + offset - 1] = sub_clustered_dict[sub_cluster]
        else:
            # Run URL clustering
            clustered_dict[cluster] = cluster_by_url(assignment_dict[cluster], pca_components)

    return (centroids, clustered_dict)

def singleton_cluster(contents, pca_components):
    embed_contents = [elem[1] for elem in contents]
    data = numpy.loadtxt(embed_contents, delimiter=",")
    if len(data) <= 1 or len(numpy.shape(data)) != 2:
        centroid = data
    else:
        centroid = data.mean(axis=0)
    clustered_dict = dict()
    clustered_dict[0] = cluster_by_url(contents, pca_components)
    return([centroid], clustered_dict)

def process_cluster(cluster_file, cluster_idx, pca_components):
    contents = parse_file(cluster_file)
    if len(contents) == 0:
        print("NO CONTENTS")
        return None
    if len(contents) > MAX_SIZE:
        centroids, clustered_dict = split_cluster(contents, pca_components)
    else:
        centroids, clustered_dict = singleton_cluster(contents, pca_components)
    print("Writing to file -- %s/%d" % (BASE_DIR, cluster_idx))
    if not os.path.exists(("%s/clusters/%d/") % (BASE_DIR,cluster_idx)):
        os.mkdir("%s/clusters/%d/" % (BASE_DIR, cluster_idx))
    total_elems = 0 
    for i,c in enumerate(clustered_dict):
        fname = "%s/clusters/%d/cluster_%d.txt" % (BASE_DIR, cluster_idx, i)
        with open(fname, "w") as f:
            packed_url_bundles = pack_url_bundles(clustered_dict[c])
            for j,bundle in enumerate(packed_url_bundles):
                for elem in bundle:
                    if len(elem) == 3:
                        f.write("%s | %s | %s" % (elem[0], elem[1], elem[2]))
                        total_elems += 1
                f.write("-------------------------\n")
    return (total_elems, centroids)

def main():
    if not os.path.exists(BASE_DIR):
        os.mkdir(BASE_DIR)
    if not os.path.exists(("%s/clusters/") % (BASE_DIR)):
        os.mkdir("%s/clusters/" % (BASE_DIR))
    cluster_files = ["%s/clusters/cluster_%d.txt" % (CLUSTER_DIR, i) for i in range(NUM_CLUSTERS)]
    start = int(sys.argv[1])
    end = int(sys.argv[2])
    idx = int(sys.argv[3])
    centroids = []
    pca_components = numpy.load(PCA_COMPONENTS_FILE)
    total = 0
    for i in range(start,end):
    #for i in range(len(cluster_files)):
        ret_val = process_cluster(cluster_files[i], i, pca_components)
        if ret_val is None:
            continue
        cluster_centroids = ret_val[1]
        total += ret_val[0]
        if len(centroids) > 0:
            centroids = numpy.row_stack((centroids, cluster_centroids))
        else:
            centroids = cluster_centroids
    numpy.savetxt("%s/centroids_%d.npy" % (BASE_DIR, idx), centroids)
    with open("%s/count_%d.txt" % (BASE_DIR, idx), 'w') as f:
        f.write("%d" % total)
   
    # Optionally run concurrentlly on 1 machine
    """
    ctr = 0
    centroid_map = dict()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_assignment = [executor.submit(process_cluster, cluster_files[i], i, pca_components) for i in range(start,end)]
        for i, future in enumerate(concurrent.futures.as_completed(future_to_assignment)):
            print("Finished %d/%d" % (ctr, len(cluster_files)))
            ctr += 1
            (cluster_idx, cluster_centroids) = future.result()
            centroid_map[cluster_idx] = cluster_centroids

    for cluster_idx in centroid_map:
        if len(centroids) > 0:
            centroids = numpy.row_stack((centroids, centroid_map[cluster_idx]))
        else:
            centroids = centroid_map[cluster_idx]
    numpy.savetxt("%s/centroids_%d.npy" % (BASE_DIR, idx), centroids)
    """

if __name__ == "__main__":
    main()
