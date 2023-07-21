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
NEW_DIM = 192 
NUM_CLUSTERS = 1280
PCA_COMPONENTS_FILE = ("/home/ubuntu/pca_%d.npy" % (NEW_DIM))

def train_pca(train_vecs):
    pca = PCA(n_components=NEW_DIM,svd_solver="full")
    pca.fit(train_vecs)
    return pca

def adjust_precision(vec):
    return numpy.round(numpy.array(vec) * (1<<5))

train_embeddings = numpy.load("/work/edauterman/clip/deploy.laion.ai/8f83b608504d46bb81708ec86e912220/embeddings/img_emb/img_emb_0.npy")
#train_embeddings = numpy.load("/work/edauterman/private-search/code/embedding/web_msmarco_reduce/web-idx-0.npy")
train_embeddings = [adjust_precision(embed) for embed in train_embeddings]
print("Loaded and adjusted precision")
pca = train_pca(train_embeddings)
print("Ran PCA")
numpy.save(PCA_COMPONENTS_FILE, numpy.transpose(pca.components_))
