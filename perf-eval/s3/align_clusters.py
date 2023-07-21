import sys
import glob
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--path", help="Path to write files", type=str, default="/home/ubuntu")
args = parser.parse_args()

path = args.path

IN = path + "/text_data"
OUT = path + "/data"
NUM_CLUSTERS = 16000

if not os.path.exists(OUT):
    os.mkdir(OUT)
if not os.path.exists('%s/clusters/' % OUT):
    os.mkdir('%s/clusters' % OUT)

idx = 0
for i in range(NUM_CLUSTERS):
    num_files = len(glob.glob("%s/clusters/%d/*txt" % (IN, i)))
    for j in range(num_files):
        file = "%s/clusters/%d/cluster_%d.txt" % (IN, i, j)
        dst = "%s/clusters/cluster_%d.txt" % (OUT, idx)
        idx += 1
        os.symlink(file, dst)

os.symlink(path + '/text_data/index.faiss', OUT + "/index.faiss")
os.symlink(path + '/text_data/pca_192.npy', OUT + "/pca_192.npy")

print("Num clusters: ", idx)
