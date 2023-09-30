import matplotlib.pyplot as plt
import matplotlib.ticker as mticker  
from matplotlib.ticker import StrMethodFormatter
from matplotlib.transforms import ScaledTranslation
from matplotlib.transforms import Affine2D
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
from tabulate import tabulate
import matplotlib
import numpy as np
import argparse
import csv
import math
import json

import estimate_perf
from estimate_perf import WEB_HINT_SZ_MB
from estimate_perf import WEB_PCA_SZ_MB
from estimate_perf import WEB_MODEL_SZ_MB
from estimate_perf import WEB_CENTROIDS_SZ_MB
from estimate_perf import WEB_NUM_DOCS
from estimate_perf import WEB_NUM_LOGICAL_SERVERS
from estimate_perf import WEB_SHARDS_PER_MACHINE
from estimate_perf import WEB_EMBEDDING_DIM
from estimate_perf import WEB_EMBEDDING_M

LINESPACE=0.8
LABEL_XSHIFT=40

AWS_DOLLAR_PER_HOUR = 0.252
AWS_DOLLAR_PER_COORDINATOR_HOUR = 2.016 
AWS_IN_DOLLAR_PER_GB = 0
AWS_OUT_DOLLAR_PER_GB = 0.09

plt.style.use('seaborn-paper')
plt.rc('axes.formatter', useoffset=False)

parser = argparse.ArgumentParser(description='Plot tiptoe performance.')
parser.add_argument('-f', '--file', action='store', nargs='+', type=str,
                    help='Name of CSV file', required=True)
parser.add_argument('-p', '--plot', action='store', type=str,
                    help='Plot to produce', required=True)
parser.add_argument('-m', '--mrr', action='store', type=str,
                    help='MRR output (only required for fig9)', required=False)
args = parser.parse_args()

def parseCsv(csvfiles):
    data = {}

    for file in csvfiles:
        print(file)
        with open(file) as f:
            reader = csv.reader(f)
            if "latency" in file:
                for row in reader:
                    if len(row) > 1 and row[0] == "Trial":
                        next(reader) # skip until and including line with headers
                        break
            else:
                for _ in range(40):
                    next(reader)

            if "latency" in file:
                next(reader) # skip second line (preprocessing)

            for row in reader:
                trial = int(row[0])
                num_clients = int(row[1])
                num_docs = int(row[2])
                embedding_slots = int(row[3])
                slot_bits = int(row[4])
                metadata_bytes = int(row[5])
                num_servers1 = int(row[6])
                num_servers2 = int(row[7])

                hint_sz = WEB_HINT_SZ_MB #float(row[8])
                time = float(row[9])
                c_preproc = float(row[10])
                c_start = float(row[11])
                time1 = float(row[12])
                time2 = float(row[13])
                q_sz = float(row[14])
                q_sz1 = float(row[15])
                q_sz2 = float(row[16])
                a_sz = float(row[17])
                a_sz1 = float(row[18])
                a_sz2 = float(row[19])

                tput1 = float(row[20])
                tput2 = float(row[21])

                time_offline = float(row[22])
                q_sz_offline = float(row[23])
                a_sz_offline = float(row[24])
                tput_offline = float(row[25])

                num_servers = num_servers1 + num_servers2
                if num_servers not in data:
                    data[num_servers] = {}

                if num_docs not in data[num_servers]:
                    data[num_servers][num_docs] = {}
                    data[num_servers][num_docs]['hint_sz'] = []
                    data[num_servers][num_docs]['hint_sz_full'] = []
                    data[num_servers][num_docs]['time'] = []
                    data[num_servers][num_docs]['client_start'] = []
                    data[num_servers][num_docs]['client_preproc'] = []
                    data[num_servers][num_docs]['time1'] = []
                    data[num_servers][num_docs]['time2'] = []
                    data[num_servers][num_docs]['time_offline'] = []
                    data[num_servers][num_docs]['query_sz'] = []
                    data[num_servers][num_docs]['query_sz1'] = []
                    data[num_servers][num_docs]['query_sz2'] = []
                    data[num_servers][num_docs]['query_sz_offline'] = []
                    data[num_servers][num_docs]['ans_sz'] = []
                    data[num_servers][num_docs]['ans_sz1'] = []
                    data[num_servers][num_docs]['ans_sz2'] = []
                    data[num_servers][num_docs]['ans_sz_offline'] = []
                    data[num_servers][num_docs]['tput1'] = []
                    data[num_servers][num_docs]['tput2'] = []
                    data[num_servers][num_docs]['tput_offline'] = []
                    data[num_servers][num_docs]['emb_servers'] = num_servers1
                    data[num_servers][num_docs]['url_servers'] = num_servers2

                if time > 0:
                    data[num_servers][num_docs]['hint_sz'].append(hint_sz)
                    data[num_servers][num_docs]['hint_sz_full'].append(hint_sz + estimate_perf.web_fixed_hint_size())
                    data[num_servers][num_docs]['time'].append(time)
                    data[num_servers][num_docs]['client_start'].append(c_start)
                    data[num_servers][num_docs]['client_preproc'].append(c_preproc)
                    data[num_servers][num_docs]['time1'].append(time1)
                    data[num_servers][num_docs]['time2'].append(time2)
                    data[num_servers][num_docs]['time_offline'].append(time_offline)
                    data[num_servers][num_docs]['query_sz'].append(q_sz)
                    data[num_servers][num_docs]['query_sz1'].append(q_sz1)
                    data[num_servers][num_docs]['query_sz2'].append(q_sz2)
                    data[num_servers][num_docs]['query_sz_offline'].append(q_sz_offline)
                    data[num_servers][num_docs]['ans_sz'].append(a_sz)
                    data[num_servers][num_docs]['ans_sz1'].append(a_sz1)
                    data[num_servers][num_docs]['ans_sz2'].append(a_sz2)
                    data[num_servers][num_docs]['ans_sz_offline'].append(a_sz_offline)

                if tput1 > 0:
                    data[num_servers][num_docs]['tput1'].append(tput1)

                if tput2 > 0:
                    data[num_servers][num_docs]['tput2'].append(tput2)

                if tput_offline > 0:
                    data[num_servers][num_docs]['tput_offline'].append(tput_offline)

    return data

def webNumServers(data):
    ns = WEB_NUM_LOGICAL_SERVERS
    num_docs = WEB_NUM_DOCS
    ns1 = data[ns][num_docs]['emb_servers']
    ns2 = data[ns][num_docs]['url_servers']
    return ns, ns1, ns2, num_docs

def offlineTput(data, ns, num_docs):
    tputs_offline = [x for x in data[ns][num_docs]['tput_offline']]
    if len(tputs_offline) > 0:
        return np.max(tputs_offline)
    assert(False)

def embeddingTput(data, ns, num_docs):
    tputs1 = [x for x in data[ns][num_docs]['tput1']]
    if len(tputs1) > 0:
        return np.max(tputs1)
    assert(False)

def urlTput(data, ns, num_docs):
    tputs2 = [x for x in data[ns][num_docs]['tput2']]
    if len(tputs2) > 0:
        return np.max(tputs2) 
    assert(False)

def offlineComm(data, ns, num_docs):
    q_offline = np.mean([x for x in data[ns][num_docs]['query_sz_offline']])
    a_offline = np.mean([x for x in data[ns][num_docs]['ans_sz_offline']])
    return q_offline, a_offline

def onlineComm(data, ns, num_docs):
    q1 = np.mean([x for x in data[ns][num_docs]['query_sz1']])
    q2 = np.mean([x for x in data[ns][num_docs]['query_sz2']])
    a1 = np.mean([x for x in data[ns][num_docs]['ans_sz1']])
    a2 = np.mean([x for x in data[ns][num_docs]['ans_sz2']])
    return q1, q2, a1, a2

def latency(data, ns, num_docs):
    cp = np.mean([x for x in data[ns][num_docs]['client_preproc']])
    t = np.mean([x for x in data[ns][num_docs]['time']])
    t1 = np.mean([x for x in data[ns][num_docs]['time1']])
    t2 = np.mean([x for x in data[ns][num_docs]['time2']])
    t_offline = np.mean([x for x in data[ns][num_docs]['time_offline']])
    return cp, t, t1, t2, t_offline

# Warning: conservative! Assumes whole coordinator is blocked during a request
def awsCost(ns1, ns2, q_offline, q1, q2, a_offline, a1, a2, tput_offline, tput1, tput2):
    aws_bw_in = (q_offline + q1 + q2) / 1024.0 * AWS_IN_DOLLAR_PER_GB
    aws_bw_out = (a_offline + a1 + a2) / 1024.0 * AWS_OUT_DOLLAR_PER_GB

    aws_compute_offline = 1.0 / tput_offline * AWS_DOLLAR_PER_COORDINATOR_HOUR / (60 * 60)
    aws_compute_1 = 1.0 / tput1 * (ns1 / WEB_SHARDS_PER_MACHINE * AWS_DOLLAR_PER_HOUR + AWS_DOLLAR_PER_COORDINATOR_HOUR) / (60 * 60)
    aws_compute_2 = 1.0 / tput2 * (ns2 / WEB_SHARDS_PER_MACHINE * AWS_DOLLAR_PER_HOUR + AWS_DOLLAR_PER_COORDINATOR_HOUR) / (60 * 60)
    aws_compute = aws_compute_offline + aws_compute_1 + aws_compute_2

    aws_cost = aws_bw_in + aws_bw_out + aws_compute
    return aws_cost

def fig8(data):
    ns, ns1, ns2, num_docs = webNumServers(data)

    # (1) Compute core-seconds per query
    tput_offline = offlineTput(data, ns, num_docs)
    print("Tput offline: ", tput_offline)
    tput1 = embeddingTput(data, ns, num_docs)
    print("Tput 1: ", tput1)
    tput2 = urlTput(data, ns, num_docs)
    print("Tput 2: ", tput2)

    offline_core_sec = estimate_perf.offline_tput_to_core_sec(tput_offline)
    online_core_sec = estimate_perf.online_tput_to_core_sec(tput1, ns1) + estimate_perf.online_tput_to_core_sec(tput2, ns2)
    core_sec = offline_core_sec + online_core_sec
    print("Offline core sec: ", offline_core_sec)
    print("Online core sec: ", online_core_sec)

    # (2) Compute communication per query
    q_offline, a_offline = offlineComm(data, ns, num_docs)
    offline_comm = q_offline + a_offline
    print("Offline comm: ", offline_comm, q_offline, a_offline)

    q1, q2, a1, a2 = onlineComm(data, ns, num_docs)
    online_comm = q1 + q2 + a1 + a2
    print("Online comm: ", online_comm, q1, a1, q2, a2)

    # Extrapolate costs if corpus were larger
    x = 25
    corpus_szs = [num_docs * i for i in range(0, x)]
    y_offline_core_sec = [estimate_perf.extrapolate_offline_core_sec(num_docs, tput_offline, i) for i in range(0, x)]
    y_online_core_sec = [estimate_perf.extrapolate_online_core_sec(num_docs, tput1, tput2, ns1, ns2, i) for i in range(0, x)]
    y_core_sec = [x + y for (x, y) in zip(y_offline_core_sec, y_online_core_sec)]
    y_offline_comm = [estimate_perf.extrapolate_offline_comm(num_docs, q_offline, a_offline, i) for i in range(0, x)]
    y_online_comm = [estimate_perf.extrapolate_online_comm(num_docs, q1, a1, q2, a2, i) for i in range(0, x)]

    print("At 21: ")
    print(corpus_szs[21], " docs")
    print(y_offline_core_sec[21] + y_online_core_sec[21], " core-s")
    print(y_offline_comm[21] + y_online_comm[21], " MiB")

    # Set up subplots
    fig, [ax1, ax2, ax3] = plt.subplots(3, 1, sharex=True, figsize=(3.5,3.5))
    ax1.grid(True, 'major', color='gray', linestyle='-', linewidth=0.5, alpha=0.5, zorder=-3)
    ax2.grid(True, 'major', color='gray', linestyle='-', linewidth=0.5, alpha=0.5, zorder=-3)
    ax3.grid(True, 'major', color='gray', linestyle='-', linewidth=0.5, alpha=0.5, zorder=-3)

    # Add reference lines
    comp_max = 2400

    ax1.axvline(num_docs, color="red", zorder=-2, linestyle=":")
    ax2.axvline(num_docs, color="red", zorder=-2, linestyle=":")
    ax3.axvline(num_docs, color="red", zorder=-2, linestyle=":")
    ax1.text(500*10**6, comp_max+LABEL_XSHIFT, "Common\ncrawl C4", color="red", rotation=30, linespacing=LINESPACE, fontsize=9)

    ax1.axvline(167*10**6, color="tab:cyan", zorder=-2, linestyle=":")
    ax2.axvline(167*10**6, color="tab:cyan", zorder=-2, linestyle=":")
    ax3.axvline(167*10**6, color="tab:cyan", zorder=-2, linestyle=":")
    ax1.text(-1.6*10**9, comp_max+LABEL_XSHIFT, "Library of\nCongress", color="tab:cyan", rotation=30, linespacing=LINESPACE, fontsize=9)

    ax1.axvline(3.6*10**9, color="tab:purple", label="Tweets per week", zorder=-2, linestyle=":")
    ax2.axvline(3.6*10**9, color="tab:purple", label="Tweets per week", zorder=-2, linestyle=":")
    ax3.axvline(3.6*10**9, color="tab:purple", label="Tweets per week", zorder=-2, linestyle=":")
    ax1.text(3*10**9, comp_max+LABEL_XSHIFT, "Tweets\nper week", color="tab:purple", rotation=30, linespacing=LINESPACE, fontsize=9)

    ax1.axvline(8*10**9, color="tab:pink", zorder=-2, linestyle=":")
    ax2.axvline(8*10**9, color="tab:pink", zorder=-2, linestyle=":")
    ax3.axvline(8*10**9, color="tab:pink", zorder=-2, linestyle=":")
    ax1.text(7*10**9, comp_max+LABEL_XSHIFT, "Google\nKnowledge\nGraph entities", color="tab:pink", rotation=30, linespacing=LINESPACE, fontsize=9)

    # Plot performance
    ax1.plot(corpus_szs, y_core_sec, color="tab:blue", zorder=-1)
    ax1.scatter(num_docs, core_sec, marker='X', color="tab:red", s=50, clip_on=False, zorder=10)
    ax1.set_ylabel("Computation", labelpad=6)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y,pos: ('{:.0f} core-s'.format(y))))
    ax1.set_ylim([0, np.max(y_core_sec)])
    ax1.set_yticks([0, 750, 1500, 2250])

    ax2.plot(corpus_szs, y_offline_comm, color="tab:blue", zorder=-1)
    ax2.scatter(num_docs, offline_comm, marker='X', color="tab:red", s=50)
    ax2.set_ylabel("Comm.\n(token gen)", labelpad=10)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y,pos: ('{:.0f} MiB'.format(y))))
    ax2.set_ylim([0, np.max(y_offline_comm)])
    ax2.set_yticks([0, 25, 50, 75])

    ax3.plot(corpus_szs, y_online_comm, color="tab:blue", zorder=-1)
    ax3.scatter(num_docs, online_comm, marker='X', color="tab:red", s=50)
    ax3.set_ylabel("Comm.\n(ranking + URL)", labelpad=10)
    ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y,pos: ('{:.0f} MiB'.format(y))))
    ax3.set_ylim([0, np.max(y_online_comm)])
    ax3.set_yticks([0, 25, 50, 75])

    ax3.set_xlabel("Number of docs in corpus (billions)")
    #a34.ticklabel_format(style='sci')
    ax3.set_xticks([0, 10**9, 2*10**9, 3*10**9, 4*10**9, 5*10**9, 6*10**9, 7*10**9, 8*10**9, 9*10**9, 10*10**9])
    ax3.xaxis.set_major_formatter(mticker.FuncFormatter(lambda y,pos: ('{:.0f}'.format(y/(10**9)))))
    ax3.set_xlim([10**6, np.max(corpus_szs)])

    h, l = ax3.get_legend_handles_labels()
    #ax0.axis('off')
    #order = [1, 2, 4, 0, 3]
    #ax0.legend([h[i] for i in order], [l[i] for i in order], loc="center", frameon=False,  columnspacing=0.2)

    plt.tight_layout()
    plt.savefig("fig8.png", bbox_inches='tight')

def table7(data):
    ns, ns1, ns2, num_docs = webNumServers(data)

    # (1) Compute core-seconds per query
    tput_offline = offlineTput(data, ns, num_docs)
    tput1 = embeddingTput(data, ns, num_docs)
    tput2 = urlTput(data, ns, num_docs)

    offline_core_sec = estimate_perf.offline_tput_to_core_sec(tput_offline)
    online_core_sec = estimate_perf.online_tput_to_core_sec(tput1, ns1) + estimate_perf.online_tput_to_core_sec(tput2, ns2)

    # (2) Compute communication per query
    q_offline, a_offline = offlineComm(data, ns, num_docs)
    q1, q2, a1, a2 = onlineComm(data, ns, num_docs)

    # (3) Compute latencies
    cp, t, t1, t2, t_offline = latency(data, ns, num_docs)

    col_labels_1 = ["Setup cost", "Text"]
    col_labels_2 = ["Query cost", "Text"]

    table1 = [col_labels_1]
    table1.append(["Documents", WEB_NUM_DOCS])
    table1.append(["Embedding dimension", WEB_EMBEDDING_DIM])
    table1.append(["Model storage (MiB)", WEB_MODEL_SZ_MB ])
    table1.append(["Centroid storage (MiB)", WEB_CENTROIDS_SZ_MB + WEB_PCA_SZ_MB ])
    table1.append(["Hint storage (MiB)", WEB_HINT_SZ_MB ])

    table2 = [col_labels_2]
    table2.append(["Offline communication Up (MiB)", q_offline])
    table2.append(["Offline communication Down (MiB)", a_offline])
    table2.append(["Online communication Up, Ranking (MiB)", q1])
    table2.append(["Online communication Up, URL (MiB)", q2])
    table2.append(["Online communication Down, Ranking (MiB)", a1])
    table2.append(["Online ommunication Down, URL (MiB)", a2])

    table2.append(["Offline server latency (s)", t_offline])
    table2.append(["Offline client preprocessing time (s/query)", cp])
    table2.append(["Online end-to-end latency (s)", t])
    table2.append(["Online server latency, Ranking (s)", t1])
    table2.append(["Online server latency, URL (s)", t2])

    table2.append(["Offline server throughput (queries/s)", tput_offline])
    table2.append(["Online server throughput, Ranking (queries/s)", tput1])
    table2.append(["Online server throughput, URL (queries/s)", tput2])

    print(tabulate(table1, headers='firstrow', tablefmt='fancy_grid'))
    print("")
    print(tabulate(table2, headers='firstrow', tablefmt='fancy_grid'))
    print("")

def table6(data):
    ns, ns1, ns2, num_docs = webNumServers(data)

    # (1) Compute core-seconds per query
    tput_offline = offlineTput(data, ns, num_docs)
    tput1 = embeddingTput(data, ns, num_docs)
    tput2 = urlTput(data, ns, num_docs)

    offline_core_sec = estimate_perf.offline_tput_to_core_sec(tput_offline)
    online_core_sec = estimate_perf.online_tput_to_core_sec(tput1, ns1) + estimate_perf.online_tput_to_core_sec(tput2, ns2)
    core_sec = offline_core_sec + online_core_sec

    # (2) Compute communication per query
    q_offline, a_offline = offlineComm(data, ns, num_docs)
    offline_comm = q_offline + a_offline
    q1, q2, a1, a2 = onlineComm(data, ns, num_docs)
    online_comm = q1 + q2 + a1 + a2

    # (3) Compute latencies
    cp, t, t1, t2, t_offline = latency(data, ns, num_docs)

    # (4) Compute storage
    storage = WEB_MODEL_SZ_MB + WEB_CENTROIDS_SZ_MB + WEB_PCA_SZ_MB + WEB_HINT_SZ_MB

    # (5) Compute AWS cost
    aws_cost = awsCost(ns1, ns2, q_offline, q1, q2, a_offline, a1, a2, tput_offline, tput1, tput2)

    col_labels = ["Client storage (MiB)", 
                  "Offline Communication (MiB/query)", 
                  "Online Communication (MiB/query)", 
                  "Server computation (core-s/query)", 
                  "End-to-end latency (s)", 
                  "AWS cost ($/query)"]

    table = [col_labels]
    table.append([storage, offline_comm, online_comm, core_sec, t, aws_cost])

    print("Text search over ", num_docs, " docs")
    print(tabulate(table, headers='firstrow', tablefmt='fancy_grid'))
    print("")

def fig9(data, mrr_file):
    ns, ns1, ns2, num_docs = webNumServers(data)

    # (1) Compute core-seconds per query
    tput_offline = offlineTput(data, ns, num_docs)
    tput1 = embeddingTput(data, ns, num_docs)
    tput2 = urlTput(data, ns, num_docs)

    offline_core_sec = estimate_perf.offline_tput_to_core_sec(tput_offline)
    online_core_sec_1 = estimate_perf.online_tput_to_core_sec(tput1, ns1) 
    online_core_sec_2 = estimate_perf.online_tput_to_core_sec(tput2, ns2)
    core_sec = offline_core_sec + online_core_sec_1 + online_core_sec_2

    # (2) Compute communication per query
    q_offline, a_offline = offlineComm(data, ns, num_docs)
    offline_comm = q_offline + a_offline
    q1, q2, a1, a2 = onlineComm(data, ns, num_docs)
    online_comm_1 = q1 + a1
    online_comm_2 = q2 + a2
    online_comm = online_comm_1 + online_comm_2

    with open(mrr_file, 'r') as f:
        mrr_data = json.load(f)

    quality_no_opts =  0.313699
    #quality_basic_clusters_all = 0.131689
    quality_basic_clusters_all = mrr_data['basic']
    #quality_basic_clusters_url_random = 0.095674
    quality_basic_clusters_url_random = mrr_data['basic_url_random'] 
    #quality_basic_clusters_url_cluster = 0.130566
    quality_basic_clusters_url_cluster = mrr_data['basic_url_cluster'] 
    #quality_boundary_clusters_url_cluster = 0.147211
    quality_boundary_clusters_url_cluster = mrr_data['boundary_url_cluster'] 
    #quality_boundary_clusters_url_cluster_pca = 0.104017
    quality_boundary_clusters_url_cluster_pca = mrr_data['boundary_url_cluster_pca'] 

    quality_tf_idf = 0.152
    #quality_tf_idf = 0.063407
    quality_bm25 = 0.230
    quality_colbert = 0.440

    coeus_core_sec = 900000
    coeus_comm = 3.6 * 1024

    #core_sec_no_opts = WEB_EMBEDDING_M / 768.0 * offline_core_sec / math.sqrt(1.2) + (online_core_sec_1 / 192.0 * 768.0 + online_core_sec_2 * 100.0) / 1.2
    core_sec_no_opts = offline_core_sec / math.sqrt(1.2) + (online_core_sec_1 / 192.0 * 768.0 + online_core_sec_2 * 100.0) / 1.2
    core_sec_basic_clusters_all = core_sec_no_opts 
    core_sec_basic_clusters_url_random = offline_core_sec / math.sqrt(1.2) + (online_core_sec_1 / 192.0 * 768.0 + online_core_sec_2) / 1.2
    core_sec_basic_clusters_url_cluster = core_sec_basic_clusters_url_random
    core_sec_boundary_clusters_url_cluster = offline_core_sec + online_core_sec_1 / 192.0 * 768.0 + online_core_sec_2
    core_sec_boundary_clusters_url_cluster_pca = offline_core_sec + online_core_sec_1 + online_core_sec_2

    # (2) Compute communication per query
    scale_before_dup = 1.0 / 1.2
    offline_comm_before_dup = estimate_perf.extrapolate_offline_comm(num_docs, q_offline, a_offline, scale_before_dup)
    online_comm_2_before_dup = online_comm_2 # Dup does not affect URL service!!

    # in MB, two 64-bit integer per document (one offline/one online)
    comm_no_opts = q_offline + 2 * num_docs * 64 / 8.0 / 1024.0 / 1024.0 + 100.0 * online_comm_2_before_dup
    print("Comm no opts: ", comm_no_opts)

    comm_basic_clusters_all = offline_comm_before_dup + \
                              estimate_perf.extrapolate_online_comm(num_docs, q1 * 768.0 / 192.0, a1, 0, 0, scale_before_dup) + \
                              100.0 * online_comm_2_before_dup
    print("Comm basic clusters: ", comm_basic_clusters_all)

    comm_basic_clusters_url_random = offline_comm_before_dup + \
                                     estimate_perf.extrapolate_online_comm(num_docs, q1 * 768.0 / 192.0, a1, 0, 0, scale_before_dup) + \
                                     online_comm_2_before_dup
    print("Comm basic clusters url random: ", comm_basic_clusters_url_random)

    comm_basic_clusters_url_cluster = comm_basic_clusters_url_random
    print("Comm url cluster: ", comm_basic_clusters_url_cluster)

    comm_boundary_clusters_url_cluster = offline_comm + \
                                         q1 * (768.0 / 192.0) + a1 + \
                                         online_comm_2
    print("Comm boundary clusters: ", comm_boundary_clusters_url_cluster)

    comm_boundary_clusters_url_cluster_pca = offline_comm + online_comm_1 + online_comm_2
    print("Comm PCA: ", comm_boundary_clusters_url_cluster_pca)

    opts = ["Tiptoe (no opts)", "Tiptoe (+basic cluster)", "Tiptoe (+boundary cluster)", "Tiptoe (all opts)"]
    comp_opts = [core_sec_no_opts, core_sec_basic_clusters_all, core_sec_basic_clusters_url_random, core_sec_basic_clusters_url_cluster, core_sec_boundary_clusters_url_cluster, core_sec_boundary_clusters_url_cluster_pca]
    comm_opts = [comm_no_opts, comm_basic_clusters_all, comm_basic_clusters_url_random, comm_basic_clusters_url_cluster, comm_boundary_clusters_url_cluster, comm_boundary_clusters_url_cluster_pca]
    quality_opts = [quality_no_opts, quality_basic_clusters_all, quality_basic_clusters_url_random, quality_basic_clusters_url_cluster, quality_boundary_clusters_url_cluster, quality_boundary_clusters_url_cluster_pca]

    #markers = [r'\ding{202}', r'\ding{203}', r'\ding{204}', r'\ding{205}', r'\ding{206}', r'\ding{207}']
    fig, [ax1, ax2] = plt.subplots(1, 2, sharex=False, figsize=(7,2))
    ax1.set_xscale('log')
    ax1.set_xticks([1, 10, 100, 1024, 10240])
    ax1.set_xticklabels(["1MiB", "10MiB", "100MiB", "1GiB", "10GiB"])
    ax1.set_yticks([0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.3, 0.35, 0.4])
    ax1.set_ylim(bottom=0)
    ax1.set_ylim(top=0.4)
    #ax1.set_xlim(left=0)
    ax1.set_xlim(left=1)
    ax1.set_xlim(right=10240)
    ax1.invert_xaxis()
    ax1.scatter(comm_opts, quality_opts, marker="o", s=7, color='green')
    ha_directions = ['left', 'right', 'right', 'right', 'left', 'left']
    va_directions=['center', 'top', 'top', 'center', 'bottom', 'top']
    arrow_text=['%d' % x for x in range(7)]
    #arrow_text=['{\\fontsize{11}{12}\\selectfont\\ding{%d}}' % x for x in range(202,209)]
    #arrow_text=['no opts', 'standard cluster', 'URL chunk', 'URL cluster', 'boundary cluster', 'PCA']

    x_offset_factor_l = 0.05
    x_offset_factor_r = 0.3
    y_offset_factor = 0.01
    for i in range(len(comm_opts)):
        x_tail = comm_opts[i]
        y_tail = quality_opts[i]
        x_offset = -1.0 * x_tail * x_offset_factor_l if ha_directions[i] == 'left' else x_tail * x_offset_factor_r
        y_offset = -1 * y_offset_factor if va_directions[i] == 'top' else y_offset_factor
        print("%f + %f -> %f" % (x_tail, x_offset, x_tail + x_offset))
        print("%f + %f -> %f" % (y_tail, y_offset, y_tail + y_offset))
        ax1.annotate(arrow_text[i], (x_tail + x_offset, y_tail + y_offset), fontsize=7, ha=ha_directions[i], va=va_directions[i],
                     bbox={"boxstyle" : "circle", "color":'white', 'pad':0},
                     color='#173F5F')
        prop = dict(arrowstyle="<|-,head_width=0.3,head_length=0.3",
            shrinkA=0,shrinkB=0,facecolor="#173F5F",edgecolor="#173F5F",linewidth=0.7)
        if i < len(comm_opts) - 1:
            x_head = comm_opts[i+1]
            y_head = quality_opts[i+1]
            ax1.annotate("", xy=(x_tail,y_tail), xytext=(x_head,y_head), fontsize=7,#transform = ax.transAxes,
                 color="#173F5F", arrowprops=prop)
    ax1.axhline(y=quality_bm25, linestyle="dotted", color="purple")
    ax1.axhline(y=quality_tf_idf, linestyle="dotted", color="orange")
    ax1.axvline(x=coeus_comm, linestyle="dotted", color="red")
    #ax1.axhline(y=quality_colbert, linestyle="dashed", color="gray")
    ax1.set_ylabel("Search quality (MRR@100)")
    ax1.set_xlabel("Total client-server communication, per query")
    ax1.text(1, quality_bm25, "BM25", fontsize=7, color='purple')
    ax1.text(1, quality_tf_idf, "tf-idf", fontsize=7, color='orange')
    ax1.text(coeus_comm, 0.4, "Coeus", color="red", rotation=45, fontsize=7)

    ax2.set_xscale('log')
    ax2.set_yticks([0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.3, 0.35, 0.4])
    ax2.set_xticks([1, 10, 100, 1000, 10000, 100000, 1000000])
    ax2.set_xticklabels(["1", "10", "100", "1K", "10K", "100K", "1M"])
    ax2.set_ylim(bottom=0)
    ax2.set_ylim(top=0.4)
    ax2.set_xlim(left=1)
    ax2.set_xlim(right=1100000)
    ax2.invert_xaxis()
    ax2.scatter(comp_opts, quality_opts, marker="o", s=7, color='green')
    ha_directions = ['left', 'right', 'right', 'right', 'left', 'left']
    va_directions=['bottom', 'top', 'top', 'bottom', 'bottom', 'top']
    arrow_text=['%d' % x for x in range(7)]
    #arrow_text=['{\\fontsize{11}{12}\\selectfont\\ding{%d}}' % x for x in range(202,209)]
    for i in range(len(comp_opts)):
        x_tail = comp_opts[i]
        y_tail = quality_opts[i]
        x_offset = -1.0 * x_tail * x_offset_factor_l if ha_directions[i] == 'left' else x_tail * x_offset_factor_r
        y_offset = -1 * y_offset_factor if va_directions[i] == 'top' else y_offset_factor
        print("%f + %f -> %f" % (x_tail, x_offset, x_tail + x_offset))
        print("%f + %f -> %f" % (y_tail, y_offset, y_tail + y_offset))
        ax2.annotate(arrow_text[i], (x_tail + x_offset, y_tail + y_offset), fontsize=7, ha=ha_directions[i], va=va_directions[i],
                     bbox={"boxstyle" : "circle", "color":'white', 'pad':0},
                     color='#173F5F')
        prop = dict(arrowstyle="<|-,head_width=0.3,head_length=0.3",
            shrinkA=0,shrinkB=0,facecolor="#173F5F",edgecolor="#173F5F",linewidth=0.7)
        if i < len(comp_opts) - 1:
            x_head = comp_opts[i+1]
            y_head = quality_opts[i+1]
            ax2.annotate("", xy=(x_tail,y_tail), xytext=(x_head,y_head), fontsize=7,#transform = ax.transAxes,
                 color="#173F5F", arrowprops=prop)

    ax2.axhline(y=quality_bm25, linestyle="dotted", color="purple")
    ax2.axhline(y=quality_tf_idf, linestyle="dotted", color="orange")
    ax2.axvline(x=coeus_core_sec, linestyle="dotted", color="red")
    ax2.set_ylabel("Search quality (MRR@100)")
    ax2.set_xlabel("Total server computation, per query (core-s)")
    ax2.text(1, quality_bm25, "BM25", fontsize=7, color='purple')
    ax2.text(1, quality_tf_idf, "tf-idf", fontsize=7, color='orange')

    ax2.text(coeus_core_sec, 0.4, "Coeus", color="red", rotation=45, fontsize=7)

    ax1.set_xticks([x*(10**y) for x in range(1,10) for y in range(0,5)], minor=True)
    ax1.xaxis.set_ticklabels([], minor=True)
    ax1.tick_params(which='minor', length=0, width=0)
    ax2.tick_params(which='minor', length=0, width=0)
    ax2.set_xticks([x*(10**y) for x in range(1,10) for y in range(0,6)], minor=True)


    ax1.grid(True, 'both', color='gray', axis='both', linestyle='-', linewidth=0.25, alpha=0.3, zorder=-3)
    ax2.grid(True, 'both', color='gray', axis='both', linestyle='-', linewidth=0.25, alpha=0.3, zorder=-3)

    ax1.xaxis.set_ticks_position('bottom')
    ax2.xaxis.set_ticks_position('bottom')
    ax1.yaxis.set_ticks_position('left')
    ax2.yaxis.set_ticks_position('left')

    x_tail = 8
    y_tail = 0.27
    x_head = 1
    y_head = 0.4
    bbox_props = dict(boxstyle="rarrow,pad=0.3", fc="#68ef00", ec="black", lw=0.5)
    ax1.annotate(r"Better", (x_tail*0.5, y_tail + 0.025+0.03),
            ha="center",
            va="center",
            rotation=45,
            fontsize=8,
            color="black",
 #           weight="bold",
            family="sans-serif",
            bbox=bbox_props)

    prop = dict(arrowstyle="<|-,head_width=0.1,head_length=0.1",
            shrinkA=0,shrinkB=0,facecolor="#173F5F",edgecolor="#173F5F",linewidth=1)
    x_tail = 10
    ax2.annotate(r"Better", (x_tail*0.5, y_tail + 0.025+0.03),
            ha="center",
            va="center",
            rotation=45,
            fontsize=8,
            color="black",
 #           weight="bold",
            family="sans-serif",
            bbox=bbox_props)

    plt.tight_layout()
    plt.savefig("fig9.png")

def main(args):
    data = parseCsv(args.file)
    if args.plot == "fig8":
        return fig8(data)
    if args.plot == "table7":
        return table7(data)
    if args.plot == "table6":
        return table6(data)
    if args.plot == "fig9":
        return fig9(data, args.mrr)

if __name__ == "__main__":
    main(args)
