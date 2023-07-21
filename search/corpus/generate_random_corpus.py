import argparse
import numpy as np
import csv
import math

parser = argparse.ArgumentParser(description='Corpus parameters.')
parser.add_argument('-f', '--file', action='store', type=str,
                    help='Name of CSV file', default="medcorpus.csv")
parser.add_argument('-n', '--num', action='store', type=int,
                    help='Num docs in corpus', default=40960)
parser.add_argument('-s', '--slots', action='store', type=int,
                    help='Num slots in embedding', default=192)
parser.add_argument('-b', '--bits', action='store', type=int,
                    help='Precision (in bits) of embedding slots', default=5)
args = parser.parse_args()

def write_csv(args):
    with open(args.file, "w") as csv_file:
        writer = csv.writer(csv_file, delimiter=",")
        num_commas = args.slots + 1

        # Write the number of docs
        writer.writerow([str(args.num)]+(['']*num_commas))

        # Write the number of slots
        writer.writerow([str(args.slots)]+(['']*num_commas))

        # Write the slot precision
        writer.writerow([str(args.bits)]+(['']*num_commas))

        # Write doc contents
        for i in range(args.num):
            emb = list(np.random.randint(low=0, high=math.pow(2, args.bits),
                                         size=args.slots, dtype=int))
            emb.append('file-'+str(i)+"-url")
            emb.append("file-"+str(i) + "-title")
            writer.writerow(emb)

def main(args):
    write_csv(args)

if __name__ == "__main__":
    main(args)
