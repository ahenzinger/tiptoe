
import multiprocessing
import pickle

# Number of threads to use for search
NUM_THREADS = max(1, multiprocessing.cpu_count() - 2)

def save(entries, outfile):
    with open(outfile, 'wb') as f:
        pickle.dump(entries, f)

def read(modelfile):
    d = None
    with open(modelfile, "rb") as f:
        d = pickle.load(f)

    # Ugly hack since we remove columns 'url' and 'text' before
    # writing the dataset to disk.
    d = d.add_column("url", [""] * len(d['id']))
    d = d.add_column("text", [""] * len(d['id']))
    d = d.remove_columns(["url", "text"])

    return d
