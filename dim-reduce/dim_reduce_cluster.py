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
NUM_CLUSTERS = 1280
PCA_COMPONENTS_FILE = ("/home/ubuntu/pca_%d.npy" % (NEW_DIM))

pca_components = numpy.load(PCA_COMPONENTS_FILE)

for i in range(NUM_CLUSTERS):
    if not os.path.exists("/home/ubuntu/boundary_clusters_pca_192/cluster_%d.txt" % i):
        transform_embeddings(pca_components, "/home/ubuntu/boundary_clusters/clusters/cluster_%d.txt" % i, "/home/ubuntu/boundary_clusters_pca_192/cluster_%d.txt" % (i))
    print("Finished %d/%d" % (i,NUM_CLUSTERS))
