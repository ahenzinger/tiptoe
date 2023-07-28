# Private web search with Tiptoe

This repository contains the reference implementation of Tiptoe, accompanying the paper "Private web search with Tiptoe" by Alexandra Henzinger, Emma Dauterman, Henry Corrigan-Gibbs, and Nickolai Zeldovich (SOSP 2023).

> Tiptoe is the first system for private search that can operate at Internet scale. A Tiptoe client can perform a full-text search over a corpus of hundreds of millions of web pages while revealing no information about its search query to the search engine’s servers. Tiptoe’s privacy guarantee is based on cryptography alone; it does not require any trusted hardware or non-colluding servers. Tiptoe first uses modern machine-learning techniques to reduce the problem of private full-text search to private nearest-neighbor search, and then it implements private nearest-neighbor search using a new high-throughput cryptographic protocol. On a 45-server cluster, Tiptoe can privately search over 360 million web pages with 57 core-seconds of server computation, 14.7 MiB of client-server communication, and 2.8 seconds of end-to-end latency. Performing private searches over this data set requires the client to store a 1.19 GiB data structure. Tiptoe’s search works best on conceptual queries (“chocolate cake recipe”) and less well on exact-string-match queries (“123 Main Street, New York”). On the standard MS MARCO search-quality benchmark, Tiptoe ranks the best-matching result in position 10 on average. Finally, Tiptoe is extensible: beyond private text search, it also supports image search and, with only minor modifications, it can support private search over audio, code, and more.

To minimize the time and cost to reproduce the paper's results, we additionally provide scripts, data sets, and preprocessed data structures to reproduce the Tiptoe text search results over the Common Crawl data set. 

**Warning:** This code is a research prototype.

## Overview

This repository is organized as follows:
- The `search/` directory implements the Tiptoe private search protocol. It includes code for the Tiptoe client and the client-facing Tiptoe services (including all cryptographic operations).
- The `embeddings/`, `dim-reduce/`, and `cluster/` directories contain the code for Tiptoe's corpus indexing batch jobs.
- The `perf-eval/` directory contains scripts to launch Tiptoe servers on a cluster of AWS instances and perform performance experiments. The `quality-eval/` directory contains scripts to evalute Tiptoe's search quality. The `tf-idf/` directory contains code to compare search quality against the tf-idf baseline.
- The `plots/` directory contains scripts to generate the tables and plots from the paper.

## Setup

### Dependencies

We provide an AWS EC2 image running Ubuntu 22.04, which includes all the dependencies required to run Tiptoe. The AMI ID is `ami-0df821b98de4b1ed9` in the `us-east-1` region.

To build from source (instead of using the EC2 image), install the following dependencies:
- [Go](https://go.dev/Go) (tested with version 1.20.2, requires at least 1.19)
- [Python3](https://www.python.org/) and [pip3](https://pypi.org/project/pip/)
- a C compiler (tested with GCC 11.3.0)

### Getting started

After loading the machine image or building from source, run:

```
git clone git@github.com:ahenzinger/tiptoe.git
cd tiptoe
```

If building from source, also run:
```
pip3 install -r requirements.txt
```

Finally, run `mkdir ~/.aws` and enter your AWS [credentials](https://docs.aws.amazon.com/sdkref/latest/guide/file-location.html) in `~/.aws/credentials`. (This step is needed to use our scripts to launch AWS instances and to download data from S3.) 
The credentials file should be of the form
```
[default]
aws_access_key_id = <your access key id>
aws_secret_access_key = <your secret access key>
```

## Usage

### Unit tests

[2 min, 25 MB disk space] To run Tiptoe's correctness tests on a synthetically generated corpus, run:
```
cd search/protocol
./fake_corpus_test.sh
cd ../..
```
These correctness tests run each of the client-facing Tiptoe services and the Tiptoe client, and ensure that the search results (and all intermediate computations) are correct. While executing, the tests log performance information to the console. The tests will print `PASS` if all unit tests succeeded.

### End-to-end tests *(optional for artifact eval)*

[2.5h, 230 GiB disk space, 30 GiB RAM] To run Tiptoe's correctness tests on a slice of the Common Crawl text corpus, substitute in the desired `path_to_corpus` (e.g., `/home/ubuntu/`) and run:
```
cd search/protocol
./real_corpus_test.sh $path_to_corpus
cd ../..
```
This script performs the following operations:
- First, it downloads the Common Crawl text corpus from S3 (on which we have already performed the embedding, dimensionality reduction, and clustering steps). This step requires an AWS credential to be in `~/.aws/credential/`, takes roughly 115 minutes, and writes two directories in `path_to_corpus` of total size roughly 230 GiB. 
- Then, it runs correctness tests on a slice of the Common Crawl corpus. As with the other unit tests, the tests log performance information to the console and will print `PASS` if all correctness tests succeeded. The correctness tests take 20 mins and require 30 GiB of RAM.

### Running the Tiptoe servers and client *(optional for artifact eval)*

It is possible to run the Tiptoe client-facing services and the Tiptoe client to perform private searches over the Common Crawl data set, outside of the correctness test and the performance test harnesses. To do so, you must (1) download the required pre-processed server and client states from S3, and then (2) launch each of the Tiptoe server and client processes. 

We store pre-processed copies of the server and client state in S3. The nearest-neighbor service's state is split into 80 shards, each of which can be downloaded separately and can then be launched as an individual process. (In our evaluation, we run these 80 processes which constitute the nearest-neighbor service on 40 physical machines.) The URL service's state is split into 8 shards, each of which can be downloaded separately and can then be launched as an individual process. (In our evaluation, we run these 8 processes which constitute the URL service on 4 physical machines.) The Tiptoe coordinator and the Tiptoe client also each have their own state, and can then be launched as individual processes. These processes communicate with each other over the network.

#### Downloading the state from S3

This step requires having an AWS credential in `~/.aws/credentials`. Downloading the state from S3 to the directory `path_to_corpus` (e.g. `/home/ubuntu/`) works as follows:

- **Nearest-neighbor service:** [<1 min, 4 GiB of disk space] To download each of the 80 shards, run (where `idx` is between 0 and 79):
  ```
  cd perf-eval/s3
  python3 text_download_from_s3.py embedding $idx $path_to_corpus
  cd ../..
  ```

- **URL service:** [<1 min, 2.5 GiB of disk space] To download each of the 8 shards, run (where `idx` is between 0 and 7):
  ```
  cd perf-eval/s3
  python3 text_download_from_s3.py url $idx $path_to_corpus
  cd ../..
  ```

- **Coordinator:** [<1 min, 1 GiB of disk space] To download the coordinator state, run: 
  ```
  cd perf-eval/s3
  python3 text_download_from_s3.py coordinator 0 $path_to_corpus
  cd ../..
  ```

- **Client:** [<1 min, 80 MiB of disk space] To download the client's state (which consists of the cluster centroids and PCA components), run:
  ```
  cd perf-eval/s3
  python3 text_download_from_s3.py client 0 $path_to_corpus
  cd ../..
  ```
**All state:** [25 mins, 320 GiB of disk] To download all of these files from S3 at once, run 
```
cd perf-eval/s3
./text_download_all.sh $path_to_corpus
cd ../../
```

#### Launching the server and client processes

Launching the Tiptoe servers and clients given their state stored in the directory `path_to_corpus` (e.g. `/home/ubuntu/`) works as follows:

- **Nearest-neighbor service:** [1 min, 17 GiB of RAM] To launch each of the 80 shards, run (where `idx` is between 0 and 79):
  ```
  cd search
  go run . emb-server $idx -preamble $path_to_corpus
  cd ..
  ```
  After roughly 1 min, this command will print `TCP server listening on ip:port` to the console. At this point, the Tiptoe nearest-neighbor server process is running and ready to answer queries.
  
- **URL service:** [1 min, 15 GiB of RAM] To launch each of the 8 shards, run (where `idx` is between 0 and 7):
  ```
  cd search
  go run . url-server $idx -preamble $path_to_corpus
  cd ..
  ```
  After roughly 1 min, this command will print `TCP server listening on ip:port` to the console. At this point, the Tiptoe URL server process is running and ready to answer queries.


- **Coordinator:** [<1 min, 5 GiB of RAM] To launch the coordinator, run: 
  ```
  cd search
  go run . coordinator 80 8 $ip0 $ip1 $ip2 $ip3 ... -preamble $path_to_corpus
  cd ..
  ```
  where `$ip0 $ip1 $ip2 $ip3 ...` is an ordered list of the IP addresses at which each of the 80 nearest-neighbor service processes are listening, followed by the IP addresses at which each of the 8 URL service processes are listening. If all 88 processes are running on the same machine, then this list of IP addresses can be omitted.  After roughly 1 min, this command will print `TLS server listening on ip:port` to the console. At this point, the Tiptoe coordinator is running and ready to answer queries.

- **All servers:** [45 min, 500 GiB of RAM] To launch all 88 Tiptoe server processes and the Tiptoe coordinator process at once on the same machine, run:
  ```
  cd search
  go run . all-servers -preamble $path_to_corpus
  cd ..
  ```
  After roughly 45 min, this command will print `Setting up coordinator` and then `TLS server listening on ip:port` to the console. At this point, the Tiptoe coordinator is running and ready to answer queries.


- **Client:** [1 min, 10 GiB of RAM] To launch the client given that the coordinator is running at IP address `coordinator-ip`, run:
  ```
  cd search
  go run . client $coordinator-ip -preamble $path_to_corpus
  cd ..
  ```
  After roughly 1 min, this process will print `Enter private search query:` to the console. At this point, enter a private search query. Then, the Tiptoe client will run a round of the private search protocol with the Tiptoe servers, and print logging information as well as the query output to the console. 

## Reproducing results from the paper

We provide a script, `tiptoe/perf-eval/runExp.py`, for our performance experiments that:
- launches 47 EC2 instances in the US-East region, each with 30 GiB of disk space and running our AWS EC2 machine image. In more detail, we launch 40 `r5.xlarge` instances for the nearest-neighbor service, 4 `r5.xlarge` instances for the URL service, one `r5.xlarge` instance for the coordinator, one `r5.large` instance to run the Tiptoe client for latency experiments, and one `r5.8xlarge` instance to simulate running up to 19 Tiptoe clients for throughput experiments.
- clones this git repo and downloads the necessary state for the servers and the clients from S3 on each of the machines,
- runs the appropriate binaries implementing the client-facing services on each of the machines,
- runs a single Tiptoe client and measures the system latency across 100 queries, then
- simulates an increasing number (up to 19) of Tiptoe clients and measures the system throughput over 1 minute, and
- shuts down all 47 instances.

**Important:** We recommend using the EC2 web console to verify that all AWS EC2 instances that were launched were also terminated correctly. If you exit the script early or it crashes, the AWS instances will not be terminated and must be shut down manually. In some cases, a race condition may cause additional EC2 instances to be spun up, which must be terminated manually. Finally, we recommend deleting `~/.ssh/known_hosts` between runs to avoid issues with remote host identification if AWS re-allocates IP addresses.

### Running latency and throughput experiments

To use this script, please update the security group (under `security`), the secret key pair name (under `keyname`), and the secret key pair path (under `secret_key_path`) in the file `tiptoe/perf-eval/config/ec2.json` to match your AWS credentials. Also, using this script requires that (1) your AWS credentials are stored in `~/.aws/credentials`, and (2)  your git key is added to ssh-agent (because we use agent forwarding to run `git clone` on the EC2 instances). 

[4h, launches 47 AWS instances] Then, run:
```
cd perf-eval/
./fetchScripts.sh
python3 runExp.py
cd ..
```
This script will print `Experiments finished.` to the console when it terminates. At this point, it will have generated three log files: 
- for the latency experiment: `tiptoe/perf-eval/text-logs/40-4-2-latency.log`
- for the nearest-neighbor-service throughput experiment: `tiptoe/perf-eval/text-logs/40-4-2-tput-embed.log`
- for the URL-service throughput experiment: `tiptoe/perf-eval/text-logs/40-4-2-tput-url.log`

(We give sample logs output by running this command in `tiptoe/perf-eval/text-logs/`.)

The latency experiment log contains a list of queries, the client-perceived latency and the communication incurred to answer each query, and the Tiptoe servers' answer. The end of the file contains a table summarizing the performance measurements.

The throughput experiment log contains the hint size and cryptographic parameters used, followed by a list of (1) number of clients, (2) total number of queries answered by the Tiptoe servers in a minute, and (3) computed throughput, for increasing numbers of clients. The end of the file contains a table summarizing the performance measurements.

We now detail how to use these performance logs to generate the tables and figures in the paper.

### Reproducing table 7

[<1 min] After having run the latency and throughput experiments, generate the text-search row of Table 7 by running:
```
cd plots
python3 plot.py -p table7 -f ../perf-eval/text-logs/40-4-2-latency.log ../perf-eval/text-logs/40-4-2-tput-embed.log ../perf-eval/text-logs/40-4-2-tput-url.log
cd ..
```
This command prints a table to the command line, which should look roughly as follows:

```
Text search over  437842961  docs
╒════════════════════════╤═════════════════════════════╤═════════════════════════════════════╤══════════════════════════╤══════════════════════╕
│   Client storage (GiB) │   Communication (MiB/query) │   Server computation (core-s/query) │   End-to-end latency (s) │   AWS cost ($/query) │
╞════════════════════════╪═════════════════════════════╪═════════════════════════════════════╪══════════════════════════╪══════════════════════╡
│                1.18976 │                     14.7093 │                             56.9277 │                  2.52025 │           0.00101466 │
╘════════════════════════╧═════════════════════════════╧═════════════════════════════════════╧══════════════════════════╧══════════════════════╛
```

### Reproducing table 8

[<1 min] After having run the latency and throughput experiments, generate the text-search columns of Table 8 by running:
```
cd plots
python3 plot.py -p table8 -f ../perf-eval/text-logs/40-4-2-latency.log ../perf-eval/text-logs/40-4-2-tput-embed.log ../perf-eval/text-logs/40-4-2-tput-url.log
cd ..
```
This command prints a table to the command line, which should look roughly as follows:

```
╒═════════════════════════╤═══════════════╕
│ Setup cost              │          Text │
╞═════════════════════════╪═══════════════╡
│ Documents               │   4.37843e+08 │
├─────────────────────────┼───────────────┤
│ Embedding dimension     │ 192           │
├─────────────────────────┼───────────────┤
│ Model storage (GiB)     │   0.258789    │
├─────────────────────────┼───────────────┤
│ Centroid storage (GiB)  │   0.0664062   │
├─────────────────────────┼───────────────┤
│ Hint storage, NN (GiB)  │   0.737305    │
├─────────────────────────┼───────────────┤
│ Hint storage, URL (GiB) │   0.126953    │
╘═════════════════════════╧═══════════════╛

╒═════════════════════════════════════╤═══════════╕
│ Query cost                          │      Text │
╞═════════════════════════════════════╪═══════════╡
│ Communication Up, NN (MiB)          │ 11.6345   │
├─────────────────────────────────────┼───────────┤
│ Communication Up, URL (MiB)         │  2.41863  │
├─────────────────────────────────────┼───────────┤
│ Communication Down, NN (MiB)        │  0.536306 │
├─────────────────────────────────────┼───────────┤
│ Communication Down, URL (MiB)       │  0.119824 │
├─────────────────────────────────────┼───────────┤
│ Client preprocessing time (s/query) │ 38.0846   │
├─────────────────────────────────────┼───────────┤
│ Total end-to-end latency (s)        │  2.52025  │
├─────────────────────────────────────┼───────────┤
│ Server latency, NN (s)              │  1.80318  │
├─────────────────────────────────────┼───────────┤
│ Server latency, URL (s)             │  0.537862 │
├─────────────────────────────────────┼───────────┤
│ Server throughput, NN (queries/s)   │  3.15     │
├─────────────────────────────────────┼───────────┤
│ Server throughput, URL (queries/s)  │  4.11163  │
╘═════════════════════════════════════╧═══════════╛
```
### Reproducing figure 6

Our script runs the latency experiment with a fixed set of text queries, which include the sample queries given in figure 6. (Using a fixed query log does not affect performance since all text queries are encrypted and the Tiptoe servers' computation is "oblivious" in that it operates only over this encryted data.) 

After having run the latency and throughput experiments, open the file `/perf-eval/text-logs/40-4-2-latency.log`. The first three answers in this file are the answers to the sample queries given in figure 6. In particular, the file `/perf-eval/text-logs/40-4-2-latency.log` should contain roughly the following contents:

```
0.
Running round with "what test are relvant for heart screenings"
   Read: what test are relvant for heart screenings
  1. Generating embedding from this query
  2. Building PIR query for cluster 18024
  3. Sending SimplePIR query to server
Answered query to 437842961-cluster corpus in: 1.946916338s
  Upload: 11.63 MB
  Download: 0.54 MB

  4. Decrypted server answer. Doc 5722 within cluster 18024 has the largest inner product with our query
  5. Building PIR query for url/title of doc 5722 in cluster 18024
  6. Sending PIR query to server for chunk 6
Answered query to 437842961-cluster corpus in: 555.241949ms
  Upload: 2.42 MB
  Download: 0.12 MB

  7. Reconstructed PIR answers. The top 10 retrieved urls are:
     (1) https://newyorkcardiac.com/best-heart-palpitations-cardiac-doctor-nyc (score 202)
     (2) http://cardiocppa.com/faq/?s= (score 190)
     (3) https://bookinghawk.com/events/heartcare-clinic/138/screening-at-mullingar-dental-monday-8th/689 (score 189)
     (4) https://www.healthline.com/health/holter-monitor-24h (score 183)
     (5) http://www.shoshonehealth.com/departments/respiratory-therapy-outpatient-services/ (score 180)
     (6) http://atlanticcardiologyonline.com/holter-monitor/ (score 179)
     (7) https://cascadecardiology.com/our-services/holter-monitor/ (score 177)
     (8) https://www.nhfriedbergfamilymedicine.org/our-services/tests-and-procedures/cardiac-event-monitors.aspx (score 177)
     (9) https://www.faythclinic.com/24hours-holter-study/ (score 176)
     (10) http://a-fib.com/treatments-for-atrial-fibrillation/diagnostic-tests-2/ (score 176)
Answered in: 38.378425584 (preproc), 55.469184987 (client), 1.9469163379999999 (round 1), 0.555241949 (round 2),  58.045686969 (total)
---
1.
Running round with "what is the ige antibody"
   Read: what is the ige antibody
  1. Generating embedding from this query
  2. Building PIR query for cluster 12272
  3. Sending SimplePIR query to server
Answered query to 437842961-cluster corpus in: 1.812480213s
  Upload: 11.63 MB
  Download: 0.54 MB

  4. Decrypted server answer. Doc 7512 within cluster 12272 has the largest inner product with our query
  5. Building PIR query for url/title of doc 7512 in cluster 12272
  6. Sending PIR query to server for chunk 5
Answered query to 437842961-cluster corpus in: 565.925699ms
  Upload: 2.42 MB
  Download: 0.12 MB

  7. Reconstructed PIR answers. The top 10 retrieved urls are:
     (1) https://bioone.org/journals/Journal-of-Parasitology/volume-86/issue-5/0022-3395(2000)086%5B1145:SEFMIB%5D2.0.CO;2/Shared-Epitope-for-Monoclonal-IR162-Between-iAnisakis-simplex-i-Larvae/10.1645/0022-3395(2000)086%5B1145:SEFMIB%5D2.0.CO;2.short (score 241)
     (2) https://www.abgent.com/products/AO2284a-FCER1A-Antibody (score 227)
     (3) https://www.frontiersin.org/articles/10.3389/fmicb.2019.00672/full (score 214)
     (4) https://www.bio-rad-antibodies.com/monoclonal/human-il-6-antibody-mq2-13a5-1012001.html (score 202)
     (5) http://www.ptgcn.com/products/Human-Pre-IL-18-ELISA-Kit-KE00025.htm (score 201)
     (6) https://www.bio-rad-antibodies.com/monoclonal/mouse-siglec-h-antibody-440c-mca4647.html (score 201)
     (7) https://www.jci.org/articles/view/46028/figure/1 (score 199)
     (8) https://enquirebio.com/antibody/igg-immunoglobulin-gamma-heavy-chain-b-cell-marker-monospecific-antibody (score 199)
     (9) https://www.abcam.com/ebi3-antibody-biotin-ab106031.html (score 197)
     (10) https://www.perkinelmer.com/product/alphalisa-il-5-mouse-kit-5000pts-al569f (score 197)
Answered in: 38.030339932 (preproc), 0.086389189 (client), 1.812480213 (round 1), 0.565925699 (round 2),  2.562278307 (total)
---
2.
Running round with "foodborne trematodiases symptoms"
   Read: foodborne trematodiases symptoms
  1. Generating embedding from this query
  2. Building PIR query for cluster 12814
  3. Sending SimplePIR query to server
Answered query to 437842961-cluster corpus in: 1.80314831s
  Upload: 11.63 MB
  Download: 0.54 MB

  4. Decrypted server answer. Doc 4545 within cluster 12814 has the largest inner product with our query
  5. Building PIR query for url/title of doc 4545 in cluster 12814
  6. Sending PIR query to server for chunk 5
Answered query to 437842961-cluster corpus in: 559.514926ms
  Upload: 2.42 MB
  Download: 0.12 MB

  7. Reconstructed PIR answers. The top 10 retrieved urls are:
     (1) https://bowenmedicalibrary.wordpress.com/2017/04/04/foodborne-trematodiases/ (score 215)
     (2) http://daddyspestsolutions.com/2016/10/31/what-kind-of-flies-transmit-diseases-to-humans/ (score 168)
     (3) https://healthsky.net/health-news/foods-that-are-high-risk-of-causing-cysticercosis.html (score 164)
     (4) https://westsidedognanny.com/category/illness/ (score 159)
     (5) https://m.petmd.com/reptile/conditions/skin/c_rp_skin_shell_infections (score 158)
     (6) http://www.worldhealthinfo.net/2016/10/beware-here-are-10-horrifying-signs.html (score 157)
     (7) https://totalrisksa.co.za/a-list-of-diseases-you-should-be-aware-of-during-the-ongoing-cape-town-water-crisis/ (score 154)
     (8) https://universityhealthnews.com/daily/nutrition/signs-and-symptoms-of-parasites-in-humans/ (score 153)
     (9) https://www.dictionary.com/browse/hookworm--disease (score 153)
     (10) https://www.beautifulonraw.com/parasite-treatment.html (score 152)
Answered in: 38.01576143 (preproc), 0.092490618 (client), 1.80314831 (round 1), 0.559514926 (round 2),  2.5518901830000003 (total)
```

### Reproducing figure 9

[<1 min] After having run the latency and throughput experiments, generate Figure 9 (an anlytical figure showing computation, communication, and storage costs scaling to larger corpus sizes) by running:
```
cd plots
python3 plot.py -p fig9 -f ../perf-eval/text-logs/40-4-2-latency.log ../perf-eval/text-logs/40-4-2-tput-embed.log ../perf-eval/text-logs/40-4-2-tput-url.log
cd ..
```
This command produces the file `plots/fig9.png`, which should look roughly as follows:

<img src="https://github.com/ahenzinger/tiptoe/blob/main/ref_fig9.png" width="500">

### Reproducing figure 10

[2.5hr, 122GiB disk space] Reproducing figure 10 requires measuring search quality with different optimizations on the MSMARCO document ranking dataset. As reproducing search quality benchmarks from scratch is somewhat computationally intensive, our scripts download the preprocessed dataset (embedding, clustering, PCA, etc. has already been performed) and compute the MRR@100 scores using a small subset of the queries (as a result, the MRR@100 scores will have some variance). We do not reproduce the search results without clustering as this is computationally intensive (the fig 10 we generate for reproducability uses the MRR@100 value we measured without clustering). Separately, the script in `embedding/brute-force-msmarco-search.py` computes search results without clustering. For performance estimates for different optimizations, we use the performance logs from above steps.

To run the below commands, make sure that you have configured AWS credentials (see instructions above), as they download data from AWS S3.

To generate the search quality data, run:
```
cd quality-eval
./run_quality_exp.sh <OUTPUT-DIR> # Downloads preprocessed dataset and runs sample of search queries
cd ../plots
python3 plot.py -p fig10 -f ../perf-eval/text-logs/40-4-2-latency.log ../perf-eval/text-logs/40-4-2-tput-embed.log ../perf-eval/text-logs/40-4-2-tput-url.log -m <OUTPUT-DIR>/mrr.json
```
Check the file in `plots/fig10.png`, which should look roughly as follows:
<img src="https://github.com/ahenzinger/tiptoe/blob/main/ref_fig10.png" width="800">

## Indexing *(optional for artifact eval)*

Given a corpus of documents, Tiptoe's preprocessing batch jobs run in the following stages:
1. Generate embeddings
2. Cluster embeddings to generate centroids
3. Assign embeddings to clusters
4. Break large clusters into smaller clusters
5. Group URLs for related pages in the same cluster
6. Use PCA to shrink embedding size
7. Run cryptographic preprocessing

Step 1 can be accelerated using a GPU, and we distribute steps 3-6 across many machines.
We now describe each of the six indexing steps.

For all the scripts in the batch indexing jobs, you will need to update the paths for the datasets and intermediate files.

### Step 1: Generate embeddings

* `embeddings/train-web.py` generates embeddings for a shard of the c4 dataset
* `embeddings/trainall-web.py` invokes `train-web.py` to generate embeddings for many shards of the c4 dataset
* `embeddings/train-msmarco.py` generates embeddings for the MSMARCO document ranking dataset
  
We recommend running these scripts on one or more GPUs.

### Step 2: Cluster embeddings

* `cluster/kmeans/compute-centroids-text.py` generates centroids for the c4 dataset using k-means on a fraction of the dataset.
* `cluster/kmeans/compute-centroids-images.py` generates centroids for the LAION-400M dataset using k-means on a fraction of the dataset.
* `cluster/kmeans/compute-centroids-msmarco.py` generates centroids for the MSMARCO document ranking dataset.

### Step 3: Cluster assignment

* `cluster/kmeans/assign-all-text.py`: Assigns all text pages to their centroids (c4 dataset).
* `cluster/kmeans/assign-all-images.py`: Assigns all images to their centroids (LAION-400M dataset).
* `cluster/kmeans/assign-all-msmarco.py`: Assigns all documents to their centroids (MSMARCO document dataset).

### Steps 4-6: Cluster processing

In steps 4-6, we break large clusters into small clusters, group related URLs, and shrink the embedding dimension using PCA. For efficiency, we distribute the processing tasks in `perf-eval/processClusters.py`. To use this script you must set AWS credentials in the same way as outlined above. The script `processClusters.py` distributes `cluster/kmeans/process-all.py` across multiple machines. 

To show the individual effects of steps 4-6 on search quality on the MSMARCO datset, we break steps 4-6 into individual scripts.
* `cluster/kmeans/url-cluster-msmarco.py`: Group documents within a cluster by embedding distance (MSMARCO datset).
* `cluster/kmeans/url-random-msmarco.py`: Group documents randomly within a cluster (MSMARCO datset).
* `dim-reduce/train-pca.py`: Train PCA matrix on fraction of dataset.
* `dim-reduce/dim_reduce_cluster.py`: Run PCA on clustered data.
* `dim-reduce/dim_reduce_no_cluster.py`: Run PCA on unclustered data.
* `dim-reduce/dim_reduce_url_clusters.py`: Run PCA on URL groups.

### Step 7: Cryptographic preprocessing

The cryptographic preprocessing runs as part of the setup routine for the Tiptoe client-facing services. In particular, if the Tiptoe servers (implemented in `tiptoe/search/protocol/server.go`)  are launched without access to a file that holds their preprocessed state, they first construct the database that they will serve to the client, and then preprocess this database using SimplePIR.

## Acknowledgements

Our AWS scripting is based on scripts from Natacha Crooks. Our networking code is based on code from Henry Corrigan-Gibbs.
We use the SimplePIR implementation at [github.com/henrycg/simplepir](https://github.com/henrycg/simplepir).

## Citation

```
@inproceedings{tiptoe,
      author = {Alexandra Henzinger and Emma Dauterman and Henry Corrigan-Gibbs and and Nickolai Zeldovich},
      title = {Private Web Search with Tiptoe},
      booktitle = {29th ACM Symposium on Operating Systems Principles (SOSP)},
      year = {2023},
      address = {Koblenz, Germany},
      month = oct,
}
```
