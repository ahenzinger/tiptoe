
import os
import subprocess
import sys
import glob
from config import *

script = os.path.join(os.path.dirname(__file__), 'reduce-precision.py')
prec = 5

def run_one(i, in_prefix, out_prefix):
    in_file = glob.glob("%s-*-%d.npy" % (in_prefix, i))[0]
    out_file = ("%s-idx-%d.npy" % (out_prefix, i))
    print("Starting idx %d, %s" % (i, out_file))

    if len(glob.glob(out_file)) > 0:
        print("Skipping batch %d because file '%s' exists" % (i, out_file))
        return None
    

    sys.stdout.flush() 
    args = ["python3", script, str(prec), in_file, out_file]
    p = subprocess.Popen(args,
                                 stdout=sys.stdout,
                                 stderr=sys.stderr)
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
