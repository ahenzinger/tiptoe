#!/bin/bash

# Directory for intermediate files
mkdir -p interm

# Download corpus, if doesn't already exist
echo "Checking directory $1/data"
if [ ! -f $1/data/index.faiss ]; then
	echo "Downloading text corpus to $1"
	cd ../../perf-eval/s3
	python3 download_all_text_clusters_from_s3.py -p $1
	python3 align_clusters.py -p $1
	cd ../../search/protocol
fi

# Test correctness of nearest-neighbor and url services
go test -timeout 0 -run Real -preamble $1/data
