
import os
import subprocess
import sys

script = os.path.join(os.path.dirname(__file__), '..', 'train-wiki-use.py')
#N_RECORDS = 100
N_RECORDS = 6458670 
#BATCH_SIZE = 100
BATCH_SIZE = 100000
MAX_PROCS = 1 
#MAX_PROCS = 12

#MODEL = 'multi-qa-mpnet-base-dot-v1'
#MODEL = 'msmarco-distilbert-base-tas-b'

def run_one(i):
    start = str(i * BATCH_SIZE)
    end = str((i+1) * BATCH_SIZE)
    outname = "wiki-use-%d-%d.out" % (BATCH_SIZE, i)
    #outname = "wiki-use-%d-%d.out" % (BATCH_SIZE, i)

    if os.path.exists(outname):
        print("Skipping batch %d because file '%s' exists" % (i, outname))
        return None

    args = ["python3", script, start, end, outname]
    p = subprocess.Popen(args,
                                 stdout=sys.stdout,
                                 stderr=sys.stderr)
    return p.pid

def run_all():
    batches = int(N_RECORDS/BATCH_SIZE) + 1
    to_run = set(range(batches))

    running = {}
    while len(to_run) > 0:
        while len(running) < MAX_PROCS:
            i = to_run.pop()
            pid = run_one(i)
            if pid is not None:
                running[pid] = i

        done_pid = os.wait()[0]
        print("Finished batch %d/%d [pid = %d]" % (i, batches, done_pid))
        del(running[done_pid])

if __name__ == "__main__":
    run_all()
