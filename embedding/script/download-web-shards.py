
import os
import subprocess
import sys

from datasets import load_dataset

script = os.path.join(os.path.dirname(__file__), '..', 'train-wiki.py')
TOTAL = 1024
NUM_DOWNLOAD = 33

def download_one(i):
    url = "https://huggingface.co/datasets/allenai/c4/resolve/main/en/c4-train.%s-of-01024.json.gz" % ("{:05d}".format(i))
    print(url)
    local = "c4"

    #if os.path.exists(outname):
    #    print("Skipping batch %d because file '%s' exists" % (i, outname))
    #    return None

    args = ["wget", url, ">", local]
    p = subprocess.Popen(args,
                                 stdout=sys.stdout,
                                 stderr=sys.stderr)
    return p.pid

def load_one(idx):
    dataset = load_dataset('allenai/c4', data_files='en/c4-train.%s-of-01024.json.gz' % ('{:05d}'.format(idx)), split='train', cache_dir="/work/edauterman/.cache/huggingface")

def download_all():
    running = {}
    for i in range(NUM_DOWNLOAD):
        pid = load_one(i)
        running[pid] = i
    
    while len(running) > 0:
        done_pid = os.wait()[0]
        print("Finished download %d" % (running[pid]))
        del(running[done_pid])
    print("Finished all downloads")

if __name__ == "__main__":
    download_all()
