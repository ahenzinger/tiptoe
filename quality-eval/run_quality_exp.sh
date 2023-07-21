OUTPUT_PATH=$1

cd ../perf-eval/s3
python3 download_msmarco_from_s3.py -p $OUTPUT_PATH
cd ../../quality-eval
python3 update_configs.py -p $OUTPUT_PATH/msmarco_checkpoints/
cd ../cluster/kmeans
python3 search.py ../../quality-eval/config/basic.json > $OUTPUT_PATH/basic.log
python3 search.py ../../quality-eval/config/basic_url_random.json > $OUTPUT_PATH/basic_url_random.log
python3 search.py ../../quality-eval/config/basic_url_cluster.json > $OUTPUT_PATH/basic_url_cluster.log
python3 search.py ../../quality-eval/config/boundary_url_cluster.json > $OUTPUT_PATH/boundary_url_cluster.log
python3 search.py ../../quality-eval/config/boundary_url_cluster_pca.json > $OUTPUT_PATH/boundary_url_cluster_pca.log
cd ../../quality-eval
python3 get-fig10-mrr.py $OUTPUT_PATH/basic.log $OUTPUT_PATH/basic_url_random.log $OUTPUT_PATH/basic_url_cluster.log $OUTPUT_PATH/boundary_url_cluster.log $OUTPUT_PATH/boundary_url_cluster_pca.log $OUTPUT_PATH/msmarco_checkpoints/msmarco-docdev-qrels.tsv $OUTPUT_PATH/mrr.json
