import boto3
import glob
import re
import os
import sys

# Need to set up AWS credentials in ~/.aws/credentials first

MAX_EMBEDDINGS_SERVERS = 80
MAX_URL_SERVERS = 8

EMBEDDINGS_DIM = 192

if len(sys.argv) != 3 and len(sys.argv) != 4:
    raise ValueError("Usage: python3 %s [embedding,url,coordinator,client] idx optional_path\n" % sys.argv[0])

server_type = sys.argv[1]
idx = int(sys.argv[2])
path = "/home/ubuntu"

if len(sys.argv) >= 4:
    path = sys.argv[3]
print("Path is ", path)

client = boto3.client("s3")
resource = boto3.resource("s3")

bucket = resource.Bucket('tiptoe-artifact-eval') 
if not os.path.exists(path + '/data/'):
    os.mkdir(path + '/data/')

if not os.path.exists(path + '/data/artifact/'):
    os.mkdir(path + '/data/artifact/')

if not os.path.exists(path + '/data/artifact/dim' + str(EMBEDDINGS_DIM) + '/'):
    os.mkdir(path + '/data/artifact/dim' + str(EMBEDDINGS_DIM) + '/')

if server_type == "url":
    bucket.download_file('/data/artifact/dim' + str(EMBEDDINGS_DIM) + '/url-server-%d.log' % idx, path + '/data/artifact/dim' + str(EMBEDDINGS_DIM) + '/url-server-%d.log' % idx)
elif server_type == "embedding":
    bucket.download_file('/data/artifact/dim' + str(EMBEDDINGS_DIM) + '/cluster-server-%d.log' % idx, path + '/data/artifact/dim' + str(EMBEDDINGS_DIM) + '/cluster-server-%d.log' % idx)
elif server_type == "coordinator":
    bucket.download_file('/data/artifact/dim' + str(EMBEDDINGS_DIM) + '/coordinator-80-8.log', path + '/data/artifact/dim' + str(EMBEDDINGS_DIM) + '/coordinator-80-8.log')
elif server_type == "client": 
    bucket.download_file('/data/artifact/dim' + str(EMBEDDINGS_DIM) + '/index.faiss', path + '/data/artifact/dim' + str(EMBEDDINGS_DIM) + '/index.faiss')
    bucket.download_file('/data/artifact/dim' + str(EMBEDDINGS_DIM) + '/pca_'+str(EMBEDDINGS_DIM)+'.npy', path + '/data/artifact/dim' + str(EMBEDDINGS_DIM) + '/pca_'+str(EMBEDDINGS_DIM)+'.npy')

