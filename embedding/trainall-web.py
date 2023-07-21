
import os
import subprocess
import sys
import glob
from config import *

script = os.path.join(os.path.dirname(__file__), 'train-web.py')

def run_one(i, model, prefix):
    outname = "%s-*-%d.npy" % (prefix, i)
    print("Starting idx %d, %s" % (i, outname))

    if len(glob.glob(outname)) > 0:
        print("Skipping batch %d because file '%s' exists" % (i, outname))
        return None
    

    sys.stdout.flush() 
    args = ["python3", script, str(i), prefix, model]
    p = subprocess.Popen(args,
                                 stdout=sys.stdout,
                                 stderr=sys.stderr)
    return p.pid

def run_all(batches, model, prefix):
    to_run = list(range(batches))

    print(to_run)
    sys.stdout.flush()
    running = {}
    while len(to_run) > 0:
        while len(running) < MAX_PROCS:
            i = to_run.pop()
            print("Running %d" % i)
            pid = run_one(i, model, prefix)
            if pid is not None:
                running[pid] = i

        done_pid = os.wait()[0]
        print("Finished batch %d/%d [pid = %d]" % (i, batches, done_pid))
        del(running[done_pid])

if __name__ == "__main__":
    # USAGE: batches model prefix
    run_all(int(sys.argv[1]), sys.argv[2], sys.argv[3])
