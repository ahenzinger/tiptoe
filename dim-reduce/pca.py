from sklearn.decomposition import PCA
from sentence_transformers import SentenceTransformer, LoggingHandler, util, evaluation, models, InputExample
from sklearn.preprocessing import normalize
import logging
import os
import gzip
import csv
import random
import numpy as np
import torch
import numpy
import sys
import glob
import re
import concurrent.futures

#New size for the embeddings
NEW_DIM = 256
#NEW_DIM = 256 
#NEW_DIM = 192 
NUM_CLUSTERS = 1280
PCA_COMPONENTS_FILE = ("/home/ubuntu/pca_%d.npy" % (NEW_DIM))

def train_pca(train_vecs):
    pca = PCA(n_components=NEW_DIM,svd_solver="full")
    pca.fit(train_vecs)
    return pca

def run_pca(pca_components, vecs):
    return numpy.clip(numpy.round(numpy.matmul(vecs, pca_components)/10), -16, 15)

def adjust_precision(vec):
    return numpy.round(numpy.array(vec) * (1<<5))

def transform_embeddings(pca_components, in_file, out_file):
    with open(in_file, "r") as f:
        lines = [line for line in f.readlines() if line.strip()]
    if len(lines) == 0:
        with open(out_file, 'w') as f:
            f.write('')
        return
    docids, in_embeddings_text, urls = zip(*(line.split(" | ") for line in lines))
    in_embeddings = [[float(i) for i in embed.split(",")] for embed in in_embeddings_text]
    print("in file = %s" % in_file)
    print("len of embeddings = %d, len of lines =%d, len of in_embeddings_text = %d" % (len(in_embeddings), len(lines), len(in_embeddings_text)))
    in_embeddings = [adjust_precision(embed) for embed in in_embeddings]
    out_embeddings = run_pca(pca_components, in_embeddings)
    with open(out_file, "w") as f:
        lines = ["%s | %s | %s\n" % (docids[i], ",".join(["%d" % ch for ch in out_embeddings[i]]), urls[i].strip()) for i in range(len(out_embeddings))]
        f.writelines(lines)

