
import concurrent.futures
import os
import re
import glob
import time

import numpy
#import tensorflow as tf
#import tensorflow_hub as hub
from progress.bar import Bar
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import normalize

from .util import *

#tf.get_logger().setLevel('DEBUG')

# MODEL_URL = "https://tfhub.dev/google/universal-sentence-encoder-large/5"
MODEL_URL = "https://tfhub.dev/google/universal-sentence-encoder/4"
SCALE_FACTOR = 1000000

# os.environ['TFHUB_CACHE_DIR'] = 'cache/tf'

def read_url(urlfile):
    # COMMENT BACK IN FOR CC DATA
    """
    d = None
    with open(urlfile, "rb") as f:
        d = pickle.load(f)

    return d
    """
    return numpy.load(urlfile)

def _embed_chunk(chunk):
    eager = embed_fn(chunk['text'])
    #eager = embed_fn(chunk['text'], normalize_embeddings=True)
    return {"embedding": embeddings}

def _adjust_precision(vec, prec):
    if prec == 0:
        return vec
    # HACK HARDCODING 5 BITS PRECISION
    return numpy.clip(numpy.round(numpy.array(vec) * (1<<prec)), -16, 15)


def _compute_distances(docs_numpy, query_mats, prec):
    # Adjust precision
    if prec > 0:
        # HACK HARDCODING 5 BITS PRECISION
        docs_numpy = numpy.clip(numpy.round(docs_numpy * (1 << prec)), -16, 15)

    #docs_numpy = normalize(docs_numpy, axis=1, norm='l1')
    out = []
    for query_mat in query_mats:
        all_distances = numpy.matmul(docs_numpy, query_mat)
        tmp_out = numpy.asarray(all_distances)
        if len(tmp_out) == 1:
            out.append(tmp_out)
        else:
            out.append(numpy.squeeze(tmp_out))
    return out 

def _find_nearest(dists, how_many):
    res = None
    if len(dists) <= how_many:
        return range(len(dists))
    # Get indexes of top-k
    res = numpy.argpartition(dists, -how_many, axis=0)

    res = sorted(res[-how_many:],
                 key=lambda i: dists[i],
                 reverse=True)
    topk = res[-how_many:]
    return topk

def _filename_to_offset(filename):
    numpy_file = os.path.split(filename)[1]
    m = re.match("([a-z_/-]+)-(\d+)-(\d+)\.([a-z]+)", filename)
    if not m:
        raise ValueError("Filename format is [wiki,web]-CHUNKSIZE-OFFSET.npy (got: '%s')" % numpy_file)

    prefix = m.group(1)
    batch_size = int(m.group(2))
    idx = int(m.group(3))
    suffix = 'url'
    # TODO: SWITCH BACK FOR WIKIPEDIA
    # Once re-generate corrupted file don't need to hardcode url
    #suffix = m.group(4)
    offset = 0

    for i in range(idx):
        other_file = glob.glob("%s-*-%d.%s" % (prefix,i,suffix))
        if len(other_file) == 0:
            print("no match for %s-*-%d.%s" % (prefix,i,suffix))
            continue
        m = re.match("[a-z_/-]+-(\d+)-\d+\.[a-z]+", other_file[0])
        if not m:
            raise ValueError("Filename format is [wiki,web]-CHUNKSIZE-OFFSET.npy (got: '%s')" % numpy_file)
        offset += int(m.group(1))

    #offset = batch_size * idx

    return (offset, batch_size)


def _search_one(numpy_path, query_mats, prec, how_many):
    #(offset, _) = _filename_to_offset(numpy_path)
    m = re.match("[a-z_/-]+-[a-z0-9]+-(\d+)\.npy", numpy_path)
    idx = 0
    if m:
        idx = int(m.group(1))
        #raise ValueError("Bad npy file format: %s" % numpy_path)
    #idx = int(m.group(1))
    
    arr = []
    
    try:
        docs_numpy = numpy.load(numpy_path)

        dists_list = _compute_distances(docs_numpy, query_mats, prec)
        for i,dists in enumerate(dists_list):
            arr.append([])
            topk = _find_nearest(dists, how_many)
            for docid in topk:
                arr[i].append({
                    'distance': dists[docid],
                    'id': idx * SCALE_FACTOR + docid,
                })

    except ValueError as e:
        print('Failed loading %s' % numpy_path, file=sys.stderr)
        print(e)

    return arr

def search(numpy_files, query_list, prec, how_many, model_name="msmarco-distilbert-base-tas-b"):
    embed_fn = SentenceTransformer(model_name).encode

    # print("Embedding query into vector...")
    # Compute query vector
    query_mats = []
    for query in query_list:
        query_vector = _adjust_precision(embed_fn([query]), prec)
        query_mat = numpy.transpose(numpy.asmatrix(query_vector))
        query_mats.append(query_mat)

    results_list = [ [] for _ in range(len(query_list)) ] 

    bar = Bar('Searching...', max=len(numpy_files))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    #with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        future_to_url = [executor.submit(_search_one, f, query_mats, prec, how_many) for f in numpy_files]
        for i, future in enumerate(concurrent.futures.as_completed(future_to_url)):
            bar.next()
            tmp_list = future.result()
            for i in range(len(tmp_list)):
                results_list[i] += tmp_list[i]

    bar.finish()

    output_list = []
    for results in results_list:
        results.sort(key=lambda x: x['distance'], reverse=True)
        output_list.append(results[:how_many])
    return output_list

# Doesn't support searching over list of queries yet
def search_wiki(wiki, numpy_files, query, prec, how_many, model_name="msmarco-distilbert-base-tas-b"):
    results = search(numpy_files, [query], prec, how_many, model_name)[0]
    out = []
    for rid in results:
        out.append({
            'id': rid,
            'distance': rid['distance'],
            'title': wiki[int(rid['id'])]['title']
        })
    return out

def search_web(url_files, numpy_files, query_list, prec, how_many, model_name="msmarco-distilbert-base-tas-b"):
    results_list = search(numpy_files, query_list, prec, how_many, model_name)
    result_dict = dict()
    for i, results in enumerate(results_list):
        out = []
        for rid in results:
            idval = int(rid['id'])
            chunk_id = int(idval / SCALE_FACTOR)
            urlfile = url_files[0]
            for f in url_files:
                m = re.match("[a-z_/-]+-\d+-%d\.url" % (chunk_id), f)
                if m:
                    urlfile = f
                    break
            urls = read_url(urlfile)
            out.append({
                'id': rid,
                'distance': rid['distance'],
                'url': urls[idval]
                # COMMENT BACK IN FOR CC DATA
                #'url': urls[idval % SCALE_FACTOR]['title']
            })
        result_dict[query_list[i]] = out
            
    return result_dict



def _idx_to_name(modelfiles, idx):
    for f in modelfiles:
        (offset, batch_size) = _filename_to_offset(f)
        if idx >= offset and idx < offset+batch_size:
            return f
    raise ValueError("Index %d not found" % idx)

def _embedding_by_idxs(modelfiles, labels):
    for_files = {}
    for idx in labels:
        f = _idx_to_name(modelfiles, idx)
        if f not in for_files:
            for_files[f] = []
        for_files[f].append(idx)

    bar = Bar("Reading elements in nearest cluster...", max=len(labels))
    arrs = []
    for f in for_files:
        (offset, _) = _filename_to_offset(f)
        docs_numpy = numpy.load(f)
        #print("Shape of '%s' is: ", numpy.shape(docs_numpy))
        for idx in for_files[f]:
            arrs.append(docs_numpy[idx - offset][0])
            bar.next()
    bar.finish()
    return numpy.matrix(arrs)
    

def search_by_cluster(wiki, cluster_file, modelfiles, query):
    embed_fn = hub.load(MODEL_URL)

    clusters = cluster_centers(cluster_file)

    print("Embedding query into vector...")
    # Compute query vector
    query_vector = _adjust_precision(embed_fn([query]), 0)
    query_mat = numpy.transpose(numpy.asmatrix(query_vector))

    print("Computing distances to clusters... -- %s %s" % (numpy.shape(clusters), numpy.shape(query_mat)))
    dists = _compute_distances(clusters, query_mat, 0)
    print(dists)
    print("Finding nearest clusters...")
    closest_clusters = _find_nearest(dists, 5)
    cluster_docs = None
    cluster_labels = None
    for closest_cluster in closest_clusters:
        print("Nearest cluster: %s" % closest_cluster)

        labels = cluster_contents(cluster_file, closest_cluster)
        docs = _embedding_by_idxs(modelfiles, labels)
        if cluster_docs is None:
            cluster_docs = docs
            cluster_labels = labels
        else:
            cluster_docs = numpy.concatenate([cluster_docs, docs])
            cluster_labels = numpy.concatenate([cluster_labels, labels])

    print("\tCluster docs: ", numpy.shape(cluster_docs))
    dists = _compute_distances(cluster_docs, query_mat, 0)
    #print("\tDistances: %s" % dists)
    closest_docs = _find_nearest(dists, 10)
    print("\tClosest: %s" % closest_docs)

    print("Reading wiki...")
    out = []
    for cluster_idx in closest_docs:
        rid = cluster_labels[cluster_idx]
        out.append({
            'id': rid,
            'distance': dists[cluster_idx],
            'title': wiki[int(rid)]['title']
        })
    return out


