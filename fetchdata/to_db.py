import argparse
import pandas as pd
import glob
import common
# python fetch-data\stitch.py ./fetch-data/repo_info-*.csv

parser = argparse.ArgumentParser(description='Stitch together the data from multiple csv files')

parser.add_argument('files', metavar='file', type=str, nargs='+',
                    help='a file to stitch together')

parser.add_argument('-o', dest='output', type=str, default='./fetch-data/repos.csv')


args = parser.parse_args()

# if file contains a wildcard (*), expand it
args.files = [f for f in args.files for f in glob.glob(f)]

print(args.files)

dfs = [pd.read_csv(f) for f in args.files]

df = pd.concat(dfs, ignore_index=True)

df.drop_duplicates(subset=['full_name'], inplace=True)

df.drop('Unnamed: 0', axis=1, inplace=True)

conn = common.get_postgres()
df.to_sql('repos', conn, if_exists='replace')