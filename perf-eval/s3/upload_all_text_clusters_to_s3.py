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

client = boto3.client("s3")
files = glob.glob(path + "/text_data/clusters/*/*")
for file in files:
    if file.endswith(".txt"):
        dst = re.sub(path, '', file)
        print(file, " --> ", dst)
        client.upload_file(file, "tiptoe-artifact-eval", dst)

client.upload_file(path + '/text_data/index.faiss', "tiptoe-artifact-eval", 'text_data/index.faiss')
client.upload_file(path + '/text_data/pca_192.npy', "tiptoe-artifact-eval", 'text_data/pca_192.npy')
