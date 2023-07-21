
import numpy

from datasets import load_dataset
from progress.bar import Bar
from sentence_transformers import SentenceTransformer

from .util import *

#MODEL_NAME = "msmarco-distilbert-base-v4"

def train_use(start, end, outfile):
    embed_fn = hub.load(MODEL_URL)

    wiki = load_dataset("wikipedia", "20220301.en", split='train[%d:%d]' % (start, end))
    #wiki = wiki.map(_embed_chunk, batched=True, num_proc=8, batch_size=1000)
    embed_fn = hub.load(MODEL_URL)

    batch_size = 100
    #batch_size = 100
    embeddings = []
    total = len(wiki['text'])
    for i in range(0, total, batch_size):
        eager = embed_fn(wiki['text'][i:(i+batch_size)])
        batch_embeddings = map(lambda x: x.numpy(), eager)
        embeddings += batch_embeddings
        print("Trained %d/%d -- %0.2f%%" % (i, total, 100.0*float(i)/total))

    wiki = wiki.remove_columns(['url', 'text'])
    wiki = wiki.add_column('embedding', embeddings)

    save(wiki, outfile)

def train(start, end, outfile, model_name="msmarco-distilbert-base-v4"):
    print("going to load")
    SEQ_LEN = 512
    wiki = load_dataset("wikipedia", "20220301.en", split='train[%d:%d]' % (start, end))
    print("loaded dataset; going to load model")
    print(model_name)

    model = SentenceTransformer(model_name)
    model.set_max_seq_length = SEQ_LEN
    pool = model.start_multi_process_pool()

    batch_size = 1000
    embeddings = []
    total = len(wiki['text'])
    for i in range(0, total, batch_size):
        sentences = []
        lens = []

        for _,record in enumerate(wiki['text'][i: i + batch_size]):
            text = record.split(' ')
            batch = [text[j:j+SEQ_LEN] for j in range(0, len(text), SEQ_LEN)]
            lens.append(len(batch))
            sentences = sentences + [' '.join(words) for words in batch]

        tmp_embeddings = model.encode_multi_process(sentences, pool, batch_size=32)

        pointer = 0
        for _,sz in enumerate(lens):
            embeddings.append(numpy.mean( numpy.array(tmp_embeddings[pointer:pointer+sz]), axis=0))
            pointer = pointer + sz

    wiki = wiki.remove_columns(['url', 'text'])
    wiki = wiki.add_column('embedding', embeddings)

    save(wiki, outfile)
    model.stop_multi_process_pool(pool)

