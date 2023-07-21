from sentence_transformers import SentenceTransformer
from transformers import CLIPProcessor, CLIPModel, CLIPTokenizer
from PIL import Image
from sklearn.decomposition import PCA
import concurrent.futures
import multiprocessing
import faiss
import numpy
import sys
import threading
import glob
import requests
#import clip
import torch
from sklearn.preprocessing import normalize
from random import shuffle
import requests
import json

MODEL_NAME = "msmarco-distilbert-base-tas-b"
NUM_CLUSTERS = 1 

centroids_file = "/home/ubuntu/boundary_clusters/centroids_new.npy"
PCA_COMPONENTS_FILE = "/home/ubuntu/pca_384.npy"
QUERY_FILE = "/home/ubuntu/msmarco/msmarco-docdev-queries.tsv"
CLUSTER_FILE_LOCATION = "/home/ubuntu/boundary_clusters_pca_384/"
URL_BUNDLE_BASE_DIR = "/home/ubuntu/boundary_clusters_url_cluster2_pca_384/"
IS_TEXT = True
RUN_PCA = True
RUN_URL_FILTER = True
URL_FILTER_BY_CLUSTER = False
URL_BUNDLE_BASE_DIR = "/home/ubuntu/basic_clusters_url_random/"
RUN_MSMARCO_DEV_QUERIES = True
FILTER_BADWORDS = False
INDEX_FILE = "/home/ubuntu/boundary_clusters/index_old.faiss"
#tokenizer = CLIPTokenizer.from_pretrained("openai/clip-vit-base-patch32")
#clip_model, _ = clip.load('ViT-B/32', 'cpu', jit=False)
INDEX_FILE = "/home/ubuntu/text_centroids/index.faiss"
BADWORDS_FILE = "/home/ubuntu/badwords"
SHORT_EXP = False

lock = threading.Lock()

def load_config(config_file):
    with open(config_file, 'r') as f:
        data = json.load(f)
    global PCA_COMPONENTS_FILE
    PCA_COMPONENTS_FILE = data['pca_components_file']
    global QUERY_FILE
    QUERY_FILE = data['query_file']
    global CLUSTER_FILE_LOCATION
    CLUSTER_FILE_LOCATION = data['cluster_file_location']
    global URL_BUNDLE_BASE_DIR
    URL_BUNDLE_BASE_DIR = data['url_bundle_base_dir']
    global IS_TEXT
    IS_TEXT = data['is_text']
    global RUN_PCA
    RUN_PCA = data['run_pca']
    global RUN_URL_FILTER
    RUN_URL_FILTER = data['run_url_filter']
    global URL_FILTER_BY_CLUSTER
    URL_FILTER_BY_CLUSTER = data['url_filter_by_cluster']
    global RUN_MSMARCO_DEV_QUERIES
    RUN_MSMARCO_DEV_QUERIES = data['run_msmarco_dev_queries']
    global FILTER_BADWORDS
    FILTER_BADWORDS = data['filter_badwords']
    global INDEX_FILE
    INDEX_FILE = data['index_file']
    global SHORT_EXP
    SHORT_EXP = data['short_exp']
    with open(INDEX_FILE, 'r') as f:
        global index
        index = faiss.read_index(INDEX_FILE)



def find_nearest_clusters_from_faiss(query_embed):
    query_float = numpy.array(query_embed).astype('float32')
    _, results = index.search(query_float, 1)
    return results[0]

def embed(query):
    if IS_TEXT:
        return SentenceTransformer(MODEL_NAME).encode(query)
    else:
        inputs = torch.cat([clip.tokenize(query)])
        outputs = clip_model.encode_text(inputs)
        return normalize([outputs[0].detach().numpy()], axis=1, norm='l2')[0]

def find_nearest_clusters_from_file(query_embed):
    query_float = numpy.array(query_embed).astype('float32')

    centroids = numpy.loadtxt(centroids_file)
    centroids = numpy.round((centroids) * (1<<5))

    distances = numpy.asarray(numpy.matmul(centroids, numpy.transpose(numpy.asmatrix(query_float))))
    res = numpy.argpartition(distances, -NUM_CLUSTERS, axis=0)
    res = sorted(res[-NUM_CLUSTERS:], key=lambda i: distances[i], reverse=True)
    topk = res[-NUM_CLUSTERS:]
    return topk

def find_nearest_clusters(cluster_index, query_embed, num_clusters):
        query_float = numpy.array(query_embed).astype('float32')
        results = cluster_index.search(query_float, num_clusters)
        #for i in range(len(results[0][0])):
        #    print("dist: %d id: %d" % (results[0][0][i], results[1][0][i]))
        return results[1][0]

def get_results_url_chunks(top_res, query_embed, cluster, num_results):
    cluster_file_name = "%s/cluster_%d.txt" % (CLUSTER_FILE_LOCATION, cluster)
    with open(cluster_file_name, "r") as f:
        #all_lines = [line for line in f.readlines()] 
        lines = [line for line in f.readlines() if line.strip()]
    if len(lines) == 0:
        return []
    chunk = list()
    matches = False
    done = False
    for line in lines:
        if done:
            break
        if "------------" in line:
            if not matches:
                chunk = list()
            else:
                done = True
        else:
            if line.split(" | ")[2].strip() == top_res.strip():
                matches = True
            chunk.append(line)
    return find_best_docs_from_lines(chunk, query_embed, num_results)

 

def filter_results_by_url_bundle(top_res, query_embed, cluster, num_results):
    print("%s/%d/clusters" % (URL_BUNDLE_BASE_DIR, cluster), file=sys.stderr)
    bundle_files = glob.glob("%s/%d/clusters/*" % (URL_BUNDLE_BASE_DIR, cluster))
    for bundle_file in bundle_files:
        with open(bundle_file, 'r') as f:
            print("Checking %s for %s" % (bundle_file, top_res['url'].strip()), file=sys.stderr)
            lines = [line for line in f.readlines() if line.strip()]
            match = False
            for line in lines:
                if line.split(" | ")[2].strip() == top_res['url'].strip():
                    match = True
                    print("Found MATCH", file=sys.stderr)
            if match:
                pool = multiprocessing.pool.ThreadPool()
                out = pool.map(lambda x: line_to_dist(x, query_embed), lines)
                out = list(zip(*out))
                urls = out[0]
                dists = out[1]
                print("[%s] Parsed" % bundle_file, file=sys.stderr)

                res_ids = find_nearest_docs(dists, num_results)
                print("[%s] Found nearest" % bundle_file, file=sys.stderr)

                ret = list(map(lambda rid: 
                        {
                            'score': dists[rid],
                            'url': urls[rid]
                        },
                        res_ids))
                return ret

    print("ERROR: NO MATCH", file=sys.stderr)
    return []


def find_nearest_docs(dists, how_many):
    res = None
    l = 1 if numpy.isscalar(dists) else len(dists)
    if l <= how_many:
        return range(l)
    # Get indexes of top-k
    res = numpy.argpartition(dists, -how_many, axis=0)

    res = sorted(res[-how_many:],
                 key=lambda i: dists[i],
                 reverse=True)
    topk = res[-how_many:]
    return topk

def line_to_dist(line, query_embed):
    (docid, rest) = line.split(" | ", 1)
    #print(len(query_embed))
    parts = rest.split(",", len(query_embed)-1)
    embed = parts[0:len(query_embed)-1]
    (last, url) = parts[len(query_embed)-1].split(" | ", 1)
    embed.append(last)
    vec = [float(i) for i in embed]
    if RUN_MSMARCO_DEV_QUERIES and not RUN_PCA:
        vec = numpy.clip(numpy.round(numpy.array(vec) * (1<<5)), -16, 15)

    return (url, numpy.inner(vec, query_embed))

def find_best_docs_from_lines(lines, query_embed, num_results):
    pool = multiprocessing.pool.ThreadPool()
    out = pool.map(lambda x: line_to_dist(x, query_embed), lines)
    out = list(zip(*out))
    urls = out[0]
    dists = out[1]

    res_ids = find_nearest_docs(dists, num_results)

    return list(map(lambda rid: 
               {
                   'score': dists[rid],
                   'url': urls[rid]
               },
               res_ids))

def find_best_docs(cluster_file_name, query_embed, num_results):
    print("[%s] Starting read" % cluster_file_name, file=sys.stderr)
    with open(cluster_file_name, "r") as f:
        #all_lines = [line for line in f.readlines()] 
        lines = [line for line in f.readlines() if (line.strip() and "--------------" not in line)]
    if len(lines) == 0:
        return []
    print("[%s] Have lines" % cluster_file_name, file=sys.stderr)
    return find_best_docs_from_lines(lines, query_embed, num_results)

def find_one(results, i, cluster_id, query_embed, num_results):
    cluster_file_name = "%s/cluster_%d.txt" % (CLUSTER_FILE_LOCATION, cluster_id)
    print("Going to find best docs for %s" % cluster_file_name, file=sys.stderr)
    docs = find_best_docs(cluster_file_name, query_embed, num_results)
    print(docs, file=sys.stderr)

    lock.acquire()
    results += docs
    results.sort(key=lambda x: -int(x['score']))
    #print("After %d clusters: %d" % (i+1, int(results[0]['score'])), file=sys.stderr)
    lock.release()


def search(query, num_results):
    query_embed = embed(query)
    # Reduce precision to 5 bits
    query_embed = numpy.round(numpy.array(query_embed) * (1<<5))
    print("\tHave embedding", file=sys.stderr)

    query_embed_pca = query_embed
    if RUN_PCA:
        pca_components = numpy.load(PCA_COMPONENTS_FILE)
        if IS_TEXT:
            query_embed_pca = numpy.clip(numpy.round(numpy.matmul(query_embed, pca_components)/10), -16, 15)
        else:
            query_embed_pca = numpy.clip(numpy.round(numpy.matmul(query_embed, pca_components)), -16, 15)
    else:
        query_embed_pca = numpy.clip(query_embed_pca, -16, 15)

    res = []
    #clusters = find_nearest_clusters_from_file([query_embed])
    clusters = find_nearest_clusters_from_faiss([query_embed])
    print("\tNearest clusters: %s" % clusters, file=sys.stderr)
    for i,cluster_id in enumerate(clusters):
        find_one(res, i, cluster_id, query_embed_pca, num_results)
        if RUN_URL_FILTER and len(res) > 0:
            res = filter_results_by_url_bundle(res[0], query_embed_pca, cluster_id, num_results)
        if URL_FILTER_BY_CLUSTER:
            print("filter by cluster", file=sys.stderr)
            res = get_results_url_chunks(res[0]['url'], query_embed_pca, cluster_id, num_results)
    return res

    return res

def latex_format_queries(query_list, badwords):
    for qid,query in enumerate(query_list[:100]):
        results = search(query, 20)[0:10]

        done = False
        for i,r in enumerate(results):
            if done:
                break
            safe = True
            url = r['url'].strip()
            for badword in badwords:
                if badword in url:
                    safe = False
            if safe:
                try:
                    img_data = requests.get(url.split('.jpg', 1)[0] + '.jpg', timeout=5).content
                    with open('/home/ubuntu/img_res/result_%d.jpg' % qid, 'wb') as handler:
                        handler.write(img_data)
                    print("\\QueryRes{%s}{fig/img_results/result_%d.jpg}" % (query, qid))
                    print("")
                    sys.stdout.flush()
                    done = True
                except:
                    print("Trying next...", file=sys.stderr)
        sys.stdout.flush()

def main():
    config_file = sys.argv[1]
    load_config(config_file)
    
    if RUN_MSMARCO_DEV_QUERIES:
        lines = open(QUERY_FILE).read().splitlines()
        query_data = [line.split('\t') for line in lines]
        query_list = [elem[1] for elem in query_data]

        qid_dict = dict()
        for elem in query_data:
            qid_dict[elem[1]] = int(elem[0])

        if FILTER_BADWORDS:
            with open(BADWORDS_FILE) as f:
                badwords = set([line.strip() for line in f.readlines()])

        if SHORT_EXP:
            query_list = query_list[:500]
        for query in query_list:
            print("Query: %s\n" % (qid_dict[query]))
            #print("Query: %s\n" % (query))
            #print("\\noindent \\textbf{Query: %s}\n" % (query))
            results = search(query, 100)[0:100]
            #print("\\begin{enumerate}")
            for i,r in enumerate(results):
                safe = True
                url = r['url'].strip()
                url_lower = url.lower()
                if FILTER_BADWORDS:
                    for badword in badwords:
                        if badword in url_lower:
                            safe = False
                if safe:
                    print("%d %s" % (r['score'], r['url'].strip()))
                else:
                    print("[REDACTED]")
                #print("\\item \\url{%s}" % (r['url'].strip()))
            #print("\\end{enumerate}")
            print("---------------\n")
            sys.stdout.flush()

        """
        for query in query_list[:20]:
            print("Query: %d %s\n" % (qid_dict[query], query)) 
            results = search(query, 100)[0:100]
            for i,r in enumerate(results):
                print("%d %s" % (r['score'], r['url'].strip()))
            print("\n----------")
        """
    else:
        query_list = ["chocolate chip cookie"]

        for query in query_list:
            print("Query: %s\n" % (query)) 
            results = search(query, 20)
            print(results, file=sys.stderr)
            for i,r in enumerate(results):
                print("%d %s" % (r['score'], r['url'].strip()))
            print("\n----------")
            sys.stdout.flush()
if __name__ == "__main__":
    main()
