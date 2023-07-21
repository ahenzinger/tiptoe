import boto3
import glob
import re
import os
import sys
import string
import argparse
import multiprocessing
import gzip
import wget
import shutil

# Need to set up AWS credentials in ~/.aws/credentials first

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--path", help="Path to write files", type=str, default="/home/ubuntu")
args = parser.parse_args()

path = args.path
print("Path is ", path)

client = boto3.client("s3")
resource = boto3.resource("s3")

if not os.path.exists(path + '/msmarco_checkpoints/'):
    os.mkdir(path + '/msmarco_checkpoints/')

bucket = resource.Bucket('tiptoe-artifact-eval')

for obj in bucket.objects.filter(Prefix='msmarco_checkpoints'):
    file = obj.Object().key
    out_path = path + '/' + file
    if not os.path.exists(os.path.dirname(out_path)):
        os.makedirs(os.path.dirname(out_path))
    bucket.download_file(file, out_path)

wget.download("https://msmarco.blob.core.windows.net/msmarcoranking/msmarco-docdev-qrels.tsv.gz", out="%s/msmarco_checkpoints/" % path)
wget.download("https://msmarco.blob.core.windows.net/msmarcoranking/msmarco-docdev-queries.tsv.gz", out="%s/msmarco_checkpoints/" % path)
with gzip.open('%s/msmarco_checkpoints/msmarco-docdev-qrels.tsv.gz' % path, 'rb') as f_in:
    with open('%s/msmarco_checkpoints/msmarco-docdev-qrels.tsv' % path, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
with gzip.open('%s/msmarco_checkpoints/msmarco-docdev-queries.tsv.gz' % path, 'rb') as f_in:
    with open('%s/msmarco_checkpoints/msmarco-docdev-queries.tsv' % path, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
