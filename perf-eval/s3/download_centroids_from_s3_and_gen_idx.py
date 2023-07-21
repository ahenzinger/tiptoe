import boto3
import glob
import re
import os
import sys
import faiss
import numpy

# Need to set up AWS credentials in ~/.aws/credentials first

NUM_FILES = 100
DIM = 768 
#DIM = 512 
WORKING_DIR = "/home/ubuntu/text_centroids/"
BASE_DIR = "processed_text"

client = boto3.client("s3")
resource = boto3.resource("s3")

bucket = resource.Bucket('cc-embeddings') 
if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)

centroids = []
for i in range(NUM_FILES):
    if not os.path.exists('%s/centroids_%d.npy' % (WORKING_DIR, i)):
        bucket.download_file('%s/centroids_%d.npy' % (BASE_DIR, i), '%s/centroids_%d.npy' % (WORKING_DIR, i))
    print("%s/centroids_%d.npy" % (BASE_DIR, i))
    tmp_centroids = numpy.loadtxt("%s/centroids_%d.npy" % (WORKING_DIR, i))
    if len(centroids) == 0:
        centroids = tmp_centroids
    else:
        centroids = numpy.row_stack((centroids, tmp_centroids))

numpy.savetxt("%s/centroids_all.npy" % WORKING_DIR, centroids)
index = faiss.IndexFlatIP(DIM)
index.add(centroids.astype('float32'))
index_file = "%s/index.faiss" % WORKING_DIR
faiss.write_index(index, index_file)
client.upload_file(index_file, "cc-embeddings", "%s/index.faiss" % BASE_DIR)
