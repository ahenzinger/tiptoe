
from gensim.parsing.porter import PorterStemmer
from gensim.parsing.preprocessing import preprocess_string
import numpy
import os
import sys

def stem_string(stemmer, s):
    proc = preprocess_string(s)
    stem = " ".join(stemmer.stem_documents(proc))
    return stem

def process(infile, outfile):
    stemmer  = PorterStemmer()
    for i,line in enumerate(infile):
        (docid, url, title, body) = line.split("\t")

        p_title = stem_string(stemmer, title)
        p_body = stem_string(stemmer, body)

        outfile.write("\t".join([docid, url, p_title, p_body]) + "\n")

        if i % 1000 == 0:
            print("\rProcessed %d documents" % i)

def main():
    if len(sys.argv) != 2:
        raise ValueError("Usage: %s infilename" % sys.argv[0])

    infilename = sys.argv[1]
    outfilename = infilename + ".stem"

    assert not os.path.exists(outfilename)
    with open(infilename, "r") as infile:
        with open(outfilename, "w") as outfile:
            process(infile, outfile)

if __name__ == "__main__":
    main()
