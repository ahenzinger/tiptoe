import numpy
import sys
import nltk
from gensim.models import TfidfModel
from gensim.corpora import Dictionary
from gensim.parsing.porter import PorterStemmer
from gensim.parsing.preprocessing import preprocess_string
from nltk.tokenize import word_tokenize
import multiprocessing
import os
import glob

DATA_FILES = "/work/edauterman/test_data/doc_chunks/*.stem"
QUERY_FILE = "/work/edauterman/test_data/msmarco-docdev-queries.tsv"
NUM_RESULTS = 100

nltk.download('punkt')

def stem_string(stemmer, s):
    proc = preprocess_string(s)
    stem = " ".join(stemmer.stem_documents(proc))
    return stem

def train():
    #lines = ["D0\tfill\tfill\tThis is a test"]
    files = glob.glob(DATA_FILES)
    data = []
    for f in files:
        lines = open(f).read().splitlines()
        print("Read data file", file=sys.stderr)
        data += [line.split('\t') for line in lines]
    print("Split data file", file=sys.stderr)
    pool = multiprocessing.Pool(processes=os.cpu_count())
    doc_contents = pool.map(word_tokenize, [elem[3] for elem in data])
    doc_ids = [elem[0] for elem in data]
    print("Parsed data file", file=sys.stderr)
    data_dict = Dictionary(doc_contents) # data should just be the lines
    print("Built dictionary", file=sys.stderr)
    corpus = [data_dict.doc2bow(line) for line in doc_contents]
    print("Made corpus", file=sys.stderr)
    model = TfidfModel(corpus)
    print("Trained model", file=sys.stderr)
    index = [dict(model[elem]) for elem in corpus]
    print("Built index", file=sys.stderr)
    return (data_dict, doc_ids, model, index)

def run_queries(query_list, data_dict, doc_ids, model, index):
    stemmer = PorterStemmer()
    for (qid,query) in query_list:
        query_vector = model[data_dict.doc2bow(word_tokenize(stem_string(stemmer, query)))]
        distances = []
        for doc_dict in index:
            tmp_dist = 0.0
            for (idx,val) in query_vector:
                if idx in doc_dict:
                    tmp_dist += val * doc_dict[idx]
            distances.append(tmp_dist)
        res = numpy.argpartition(distances, -NUM_RESULTS, axis=0)
        res = sorted(res[-NUM_RESULTS:], key=lambda i: distances[i], reverse=True)
        topk = res[-NUM_RESULTS:]
        print("Query: %d %s" % (qid, query))
        for result in topk:
            print("%s" % doc_ids[result])
        print("----------")
        print("")

def main():
    #nltk.download('punkt')
    lines = open(QUERY_FILE).read().splitlines()
    query_data = [line.split('\t') for line in lines]
    query_list = [(int(elem[0]), elem[1]) for elem in query_data]

    (data_dict, doc_ids, model, index) = train()
    run_queries(query_list, data_dict, doc_ids, model, index)

if __name__ == "__main__":
    main()
