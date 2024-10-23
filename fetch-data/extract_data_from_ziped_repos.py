from pathlib import Path
from zipfile import ZipFile, BadZipFile
import tqdm
import common
from sqlalchemy import text
import argparse

parser = argparse.ArgumentParser(description='Extract data from zipped repos')
parser.add_argument("--s", action="store_true", help="Use only a subset of the data")


args = parser.parse_args()

USE_SUBSET = args.s

PYTHON_EXTENSIONS = [ ".py" ]
size_sum = 0
zips = {} 
path = Path('./downloaded_repos/')


paths = list(path.glob('*.zip'))
if USE_SUBSET:
    paths = paths[:10]
iterator = tqdm.tqdm(paths, desc='Processing ZIP files', unit='files')

conn = common.get_postgres()

def get_repo(name):
    result = conn.execute(text("SELECT index FROM repos WHERE name = :name"), {"name": name})
    return result.fetchone()


for file in iterator:
    repo_index = get_repo(file.stem)
    zips[file.stem] = {
        'index': repo_index[0] if repo_index else None,
        'files': {}
    }
    try:
        with ZipFile(file, 'r') as zipObj:
            for entry in zipObj.infolist():
                if Path(entry.filename).suffix in PYTHON_EXTENSIONS:
                    size_sum += entry.file_size
                    # store filename and file content in directory
                    content =  zipObj.read(entry.filename).decode('utf-8', errors='ignore')
                    zips[file.stem]['files'][entry.filename] = content
    except BadZipFile:
        print(f"Warning: {file} is not a zip file and will be skipped.")

def_count = 0
for repo in zips:
    for file in zips[repo]['files']:
        def_count += zips[repo]['files'][file].count('def ')

print('total files:', len(zips))
print('size:', size_sum / (1024 * 1024))
print('def keywords:', def_count)

import pandas as pd

flat_zip = {
    'repo': [],
    'file': [],
    'content': []
}

for repo in tqdm.tqdm(zips, desc='Flattening ZIP files', unit='repos'):
    repo_index = zips[repo]['index']
    for file in zips[repo]['files']:
        flat_zip['repo'].append(repo_index)
        flat_zip['file'].append(file)
        flat_zip['content'].append(zips[repo]['files'][file])

df = pd.DataFrame(
    data={
        'repo': pd.Series(flat_zip['repo'], dtype='Int64'),
        'file': flat_zip['file'],
        'content': flat_zip['content']
    }
)


print('writing to db')

result = df.to_sql('files', conn, if_exists='replace',schema='public', index=False, chunksize=1000)
conn.commit()
print('done')