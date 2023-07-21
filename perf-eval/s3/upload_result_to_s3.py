import boto3
import glob
import re

# Need to set up AWS credentials in ~/.aws/credentials first

UPLOAD_DIR = "processed_img_4/"
#UPLOAD_DIR = "processed_text/"

client = boto3.client("s3")

files = glob.glob("/home/ubuntu/up/centroids*")
files = files + glob.glob("/home/ubuntu/up/count*")

files = files + glob.glob("/home/ubuntu/up/clusters/**/*txt", recursive=True)
for file in files:
    dst = re.sub(r'/home/ubuntu/up/', UPLOAD_DIR, file)
    client.upload_file(file, "cc-embeddings", dst)
