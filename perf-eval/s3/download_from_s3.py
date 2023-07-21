import boto3
import glob
import re
import os
import sys

# Need to set up AWS credentials in ~/.aws/credentials first

TOTAL_NUM_CLUSTERS = 82425

EMBEDDINGS_CLUSTERS_PER_SERVER = 1031
MAX_EMBEDDINGS_SERVERS = 80

URL_CLUSTERS_PER_SERVER = 10304
MAX_URL_SERVERS = 8

if len(sys.argv) != 3:
    raise ValueError("Usage: python %s [embedding,url,coordinator,client] idx\n" % sys.argv[0])

server_type = sys.argv[1]
idx = int(sys.argv[2])

client = boto3.client("s3")
resource = boto3.resource("s3")

"""
download_start = 0
download_end = 0

if server_type == "url":
    download_start = URL_CLUSTERS_PER_SERVER * idx
    download_end = URL_CLUSTER_PER_SERVER * (idx + 1)
elif server_type == "embedding":
    download_start = EMBEDDINGS_CLUSTERS_PER_SERVER * idx
    download_end = EMBEDDINGS_CLUSTERS_PER_SERVER * (idx + 1)
"""
#client.download_file("cc-embeddings", "kmeans-clusters.faiss", "/home/ubuntu/data/kmeans-clusters.faiss")
#client.download_file("cc-embeddings", "urls.csv", "/home/ubuntu/data/urls.csv")

bucket = resource.Bucket('cc-embeddings') 
if not os.path.exists('/home/ubuntu/data/'):
    os.mkdir('/home/ubuntu/data/')

if not os.path.exists('/home/ubuntu/data/interm/'):
    os.mkdir('/home/ubuntu/data/interm/')

if not os.path.exists('/home/ubuntu/data/interm/dim192/'):
    os.mkdir('/home/ubuntu/data/interm/dim192/')

"""
if not os.path.exists('/home/ubuntu/data/cluster_data_dim192'):
    os.mkdir('/home/ubuntu/data/cluster_data_dim192')

for i in range(download_start, download_end):
    if download_end < TOTAL_NUM_CLUSTERS:
        if not os.path.exists('/home/ubuntu/data/cluster_data_dim192/%d/' % (i % 1000)):
            os.mkdir('/home/ubuntu/data/cluster_data_dim192/%d/' % (i % 1000))
        bucket.download_file(' cluster_data_dim192/%d/cluster_link_%d.txt' % (i % 1000, i), '/home/ubuntu/data/cluster_data_dim192/%d/cluster_link_%d.txt' % (i % 1000, i))
"""
if server_type == "url":
    bucket.download_file(' interm/dim192/url-server-%d.log' % idx, '/home/ubuntu/data/interm/dim192/url-server-%d.log' % idx)
elif server_type == "embedding":
    bucket.download_file(' interm/dim192/cluster-server-%d.log' % idx, '/home/ubuntu/data/interm/dim192/cluster-server-%d.log' % idx)
elif server_type == "coordinator":
    bucket.download_file('interm/dim192/coordinator-80-8.log', '/home/ubuntu/data/interm/dim192/coordinator-80-8.log')
elif server_type == "client": 
    bucket.download_file('kmeans-clusters.faiss', '/home/ubuntu/data/kmeans-clusters.faiss')

"""
for i in range(1000):
    if not os.path.exists('/home/ubuntu/data/cluster_data_dim192/%d/' % i):
        os.mkdir('/home/ubuntu/data/cluster_data_dim192/%d/' % i)
    for obj in bucket.objects.filter(Prefix = " cluster_data_dim192/%d/" % (i)):
        print(obj.key)
        bucket.download_file(obj.key, '/home/ubuntu/data/%s'  % (obj.key[1:]))

if not os.path.exists('/home/ubuntu/data/interm'):
    os.mkdir('/home/ubuntu/data/interm')
if not os.path.exists('/home/ubuntu/data/interm/dim192'):
    os.mkdir('/home/ubuntu/data/interm/dim192')
for obj in bucket.objects.filter(Prefix=" interm/dim192/"):
    print(obj.key)
    bucket.download_file(obj.key, '/home/ubuntu/data/%s'  % (obj.key[1:]))
"""
