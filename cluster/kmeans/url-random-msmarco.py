import numpy
import os
import sys
import faiss
import concurrent
import glob
import concurrent.futures
import math

#DIM=768
# lines in bundle
AVG_BUNDLE_SIZE = 160 
MAX_SIZE = 160
CLUSTER_DIR = "/home/ubuntu/basic_clusters/clusters"
BASE_DIR = "/home/ubuntu/basic_clusters_url_random"
NUM_CLUSTERS = 4 * 32 * 10

def parse_file(filename):
    contents = []
    with open(filename, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if len(line) <= 1:
                continue
            contents.append(line.split(" | "))
            """
            (docid, rest) = line.split(" | ", 1)
            parts = rest.split(",", DIM-1)
            embed = parts[0:DIM-1]
            (last, url) = parts[DIM-1].split(" | ", 1)
            embed.append(last)
            vec = [int(i) for i in embed]
            contents.append((int(docid), url, vec))
            """
    return contents

def get_size(contents):
    # TODO: compute using compression
    return len(contents)

def create_bundles(contents):
    print("create bundles")
    num_bundles = int(math.ceil(float(len(contents)) / float(AVG_BUNDLE_SIZE)))
    print("Num_bundles = %d" % num_bundles)

    assignment_dict = dict()
    if num_bundles > 1:
        print("IN LEN = 1")
        for i in range(num_bundles):
            upper_bound = min((i+1) * AVG_BUNDLE_SIZE, len(contents))
            assignment_dict[i] = [contents[j] for j in range(i * AVG_BUNDLE_SIZE, upper_bound)]
    return (assignment_dict)

def process_cluster(cluster_file, cluster_idx):
    print("**** PROCESS CLUSTER *****")
    contents = parse_file(cluster_file)
    print("LEN = ", len(contents))
    if len(contents) == 0:
        return
    assignment_dict = create_bundles(contents)
    print("Writing to file -- %s/%d" % (BASE_DIR, cluster_idx))
    if not os.path.exists(("%s/%d/") % (BASE_DIR, cluster_idx)):
        os.mkdir("%s/%d/" % (BASE_DIR, cluster_idx))
    if not os.path.exists(("%s/%d/clusters") % (BASE_DIR, cluster_idx)):
        os.mkdir("%s/%d/clusters/" % (BASE_DIR, cluster_idx))
  
    if len(assignment_dict) == 0:
        return
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
    cluster_files = ["%s/cluster_%d.txt" % (CLUSTER_DIR, i) for i in range(NUM_CLUSTERS)]
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
