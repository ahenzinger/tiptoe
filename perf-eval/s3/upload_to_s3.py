import boto3
import glob
import re

# Need to set up AWS credentials in ~/.aws/credentials first

client = boto3.client("s3")

client.upload_file("/home/ubuntu/data/interm/dim192/coordinator-80-8.log", "cc-embeddings", " interm/dim192/coordinator-80-8.log")

"""
client.upload_file("/data/pdos/web-search/cluster_centroids/kmeans-clusters.faiss", "cc-embeddings", "kmeans-clusters.faiss")

files = glob.glob("/data/pdos/web-search/embeddings_by_cluster/*")
for file in files:
    dst = re.sub(r'/data/pdos/web-search/', ' ', file)
    print(dst)
    client.upload_file(file, "cc-embeddings", dst)

files = glob.glob("/data/pdos/web-search/interm/dim192/*")
for file in files:
    dst = re.sub(r'/data/pdos/web-search/', ' ', file)
    print(dst)
    client.upload_file(file, "cc-embeddings", dst)
"""
