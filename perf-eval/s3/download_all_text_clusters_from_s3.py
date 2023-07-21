import boto3
import glob
import re
import os
import sys
import string
import argparse
import multiprocessing

# Need to set up AWS credentials in ~/.aws/credentials first

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--path", help="Path to write files", type=str, default="/home/ubuntu")
args = parser.parse_args()

path = args.path
print("Path is ", path)

NUM_CLUSTERS = 4 * 4000

client = boto3.client("s3")
resource = boto3.resource("s3")

if not os.path.exists(path + '/text_data/'):
    os.mkdir(path + '/text_data/')
if not os.path.exists(path + '/text_data/clusters/'):
    os.mkdir(path + '/text_data/clusters/')
for i in range(0, NUM_CLUSTERS):
    if not os.path.exists(path + '/text_data/clusters/%d/' % i):
        os.mkdir(path + '/text_data/clusters/%d/' % i)

bucket = resource.Bucket('tiptoe-artifact-eval')
bucket.download_file('/text_data/index.faiss', path + '/text_data/index.faiss')
bucket.download_file('/text_data/pca_192.npy', path + '/text_data/pca_192.npy')

for obj in bucket.objects.filter(Prefix='/text_data/clusters'):
    file = obj.Object().key
    if file.endswith(".txt"):
        dst = re.sub(r'/text_data/clusters/', '', file)
        bucket.download_file(file, path + '/text_data/clusters/' + dst)
        #print(file)
