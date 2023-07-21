import boto3
import glob
import re
import os
import sys
import string
import argparse
import multiprocessing
import json

# Need to set up AWS credentials in ~/.aws/credentials first

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--path", help="Path to MSMARCO files", type=str, default="/home/ubuntu")
args = parser.parse_args()

path = args.path
print("Path is ", path)

with open('config/basic.json', 'r') as f:
    data = json.load(f)

data['cluster_file_location'] = "%s/basic_clusters/clusters/" % path
data['index_file'] = "%s/basic_clusters/index.faiss" % path
data['query_file'] = "%s/msmarco-docdev-queries.tsv" % path

with open('config/basic.json', 'w') as f:
    json.dump(data, f)

with open('config/basic_url_random.json', 'r') as f:
    data = json.load(f)

data['cluster_file_location'] = "%s/basic_clusters/clusters/" % path
data['index_file'] = "%s/basic_clusters/index.faiss" % path
data['url_bundle_base_dir'] = "%s/basic_clusters_url_random/" % path
data['query_file'] = "%s/msmarco-docdev-queries.tsv" % path

with open('config/basic_url_random.json', 'w') as f:
    json.dump(data, f)

with open('config/basic_url_cluster.json', 'r') as f:
    data = json.load(f)

data['cluster_file_location'] = "%s/basic_clusters/clusters/" % path
data['index_file'] = "%s/basic_clusters/index.faiss" % path
data['url_bundle_base_dir'] = "%s/basic_clusters_url_cluster/" % path
data['query_file'] = "%s/msmarco-docdev-queries.tsv" % path

with open('config/basic_url_cluster.json', 'w') as f:
    json.dump(data, f)

with open('config/boundary_url_cluster.json', 'r') as f:
    data = json.load(f)

data['cluster_file_location'] = "%s/boundary_clusters/clusters/" % path
data['index_file'] = "%s/boundary_clusters/index.faiss" % path
data['url_bundle_base_dir'] = "%s/boundary_clusters_url_cluster2/" % path
data['query_file'] = "%s/msmarco-docdev-queries.tsv" % path

with open('config/boundary_url_cluster.json', 'w') as f:
    json.dump(data, f)

with open('config/boundary_url_cluster_pca.json', 'r') as f:
    data = json.load(f)

data['pca_components_file'] = "%s/pca_192.npy" % path
data['cluster_file_location'] = "%s/boundary_clusters_pca_192/" % path
data['index_file'] = "%s/boundary_clusters/index.faiss" % path
data['url_bundle_base_dir'] = "%s/boundary_clusters_url_cluster2_pca_192/" % path
data['query_file'] = "%s/msmarco-docdev-queries.tsv" % path

with open('config/boundary_url_cluster_pca.json', 'w') as f:
    json.dump(data, f)

