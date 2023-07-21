# Model max_seq_len
SEQ_LEN = 512

# Max number of processes for training
MAX_PROCS = 1 

# Prefix to output embedding files to
TRAIN_PREFIX = "/work/edauterman/private-search/code/embedding/web_msmarco_shard/web"
TRAIN_PREFIX_DIR = "/work/edauterman/private-search/code/embedding/web_msmarco_shard/"
# Prefix of files to search over
PREFIX = "/data/pdos/web-search/embeddings/web"
PREFIX_DIR = "/data/pdos/web-search/embeddings/"
URL_PREFIX = "/data/pdos/web-search/url_files/web"

# How many files to search over 
MAX_FILE_NUM = 1024
MODEL_FILES = [("%s-*-%d.npy") % (PREFIX, i) for i in range(MAX_FILE_NUM)]
URL_FILES = [("%s-*-%d.url") % (URL_PREFIX, i) for i in range(MAX_FILE_NUM)]

# Number of results to return per query
NUM_RESULTS = 20
