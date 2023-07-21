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
PCA_COMPONENTS_FILE = ("/work/edauterman/pca_%d.npy" % (NEW_DIM))
DIRECTORY = "/work/edauterman/test_boundary_url_bundles_2_dotprod/"
OUT_DIRECTORY = "/work/edauterman/test_boundary_url_bundles_2_dotprod_pca_192/"

pca_components = numpy.load(PCA_COMPONENTS_FILE)

directories = glob.glob("%s/*" % DIRECTORY)
files = []
if not os.path.exists(OUT_DIRECTORY):
    os.mkdir(OUT_DIRECTORY)
print(directories)
for directory in directories:
    print(directory)
    files += glob.glob("%s/clusters/*" % directory)
    if not os.path.exists(re.sub(r'%s' % DIRECTORY, r'%s' % OUT_DIRECTORY, directory)):
        os.mkdir(re.sub(r'%s' % DIRECTORY, r'%s' % OUT_DIRECTORY, directory))

    if not os.path.exists(re.sub(r'%s' % DIRECTORY, r'%s' % OUT_DIRECTORY, "%s/clusters" % directory)):
        os.mkdir(re.sub(r'%s' % DIRECTORY, r'%s' % OUT_DIRECTORY, "%s/clusters" % directory))

with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
    for i,f in enumerate(files):
        executor.submit(transform_embeddings, pca_components, f, re.sub(r'%s' % DIRECTORY, r'%s' % OUT_DIRECTORY, f))

