#!/bin/bash

for ((i = 0 ; i < 80 ; i++ )); do python3 text_download_from_s3.py embedding $i $1 ; done

for ((i = 0 ; i < 8 ; i++ )); do python3 text_download_from_s3.py url $i $1 ; done

python3 text_download_from_s3.py coordinator 0 $1

python3 text_download_from_s3.py client 0 $1
