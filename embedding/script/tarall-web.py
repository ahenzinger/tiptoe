
import os
import subprocess
import sys
import glob
from config import *

def run_one(i, in_prefix, out_prefix):
    embedding_file = ("%s-idx-%d.npy" % (in_prefix, i))
    tar_file = ("%s-idx-%d.tar.gz" % (out_prefix, i))
    print("Starting idx %d, %s" % (i, tar_file))

    if len(glob.glob(tar_file)) > 0:
        print("Skipping batch %d because file '%s' exists" % (i, tar_file))
        return None
    

    sys.stdout.flush() 
    args = ["tar", "-czf", tar_file, embedding_file]
    p = subprocess.Popen(args)
    return p.pid

def run_all(batches, in_prefix, out_prefix):
    to_run = list(range(batches))

    #args = ["mkdir", TRAIN_PREFIX_DIR]
    #subprocess.call(args, stdout=sys.stdout, stderr=sys.stderr)

    print(to_run)
    sys.stdout.flush()
    running = {}
    while len(to_run) > 0:
        while len(running) < MAX_PROCS:
            i = to_run.pop()
            print("Running %d" % i)
            pid = run_one(i, in_prefix, out_prefix)
            if pid is not None:
                running[pid] = i

        done_pid = os.wait()[0]
        print("Finished batch %d/%d [pid = %d]" % (i, batches, done_pid))
        del(running[done_pid])

if __name__ == "__main__":
    # USAGE: batches in-prefix out-prefix
    run_all(int(sys.argv[1]), sys.argv[2], sys.argv[3])
