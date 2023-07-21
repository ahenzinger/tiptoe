#!/bin/bash

# Directory for intermediate files
mkdir -p interm

# Generate test corpus of 40,960 documents
if [ ! -f ../corpus/medcorpus.csv ]; then
	echo "Generating test corpus"
	cd ../corpus
	python3 generate_random_corpus.py -f medcorpus.csv -n 40960
	cd ../protocol
fi

# Test correctness of nearest-neighbor and url services
go test -timeout 0 -run Fake -medcorpus ../corpus/medcorpus.csv
