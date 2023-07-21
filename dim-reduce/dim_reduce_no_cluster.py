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
from pca import *

#New size for the embeddings
NEW_DIM =192 
PCA_COMPONENTS_FILE = ("/work/edauterman/pca_%d.npy" % NEW_DIM)
PCA_EMBEDDINGS_FILE = ("/work/edauterman/pca_embeddings_%d.npy" % NEW_DIM)

def adjust_precision(vec):
    return numpy.round(numpy.array(vec) * (1<<5))

embeddings = numpy.load("/work/edauterman/private-search/code/embedding/embeddings_msmarco/msmarco_embeddings.npy")
embeddings = [adjust_precision(embed) for embed in embeddings]
pca_components = numpy.load(PCA_COMPONENTS_FILE)
out_embeddings = numpy.clip(numpy.round(numpy.matmul(embeddings, pca_components)/10), -16, 15)
numpy.save(PCA_EMBEDDINGS_FILE, out_embeddings)
