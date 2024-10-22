from pathlib import Path
from zipfile import ZipFile, BadZipFile
import tqdm 
PYTHON_EXTENSIONS = [ ".py" ]
size_sum = 0
zips = {} 
path = Path('./downloaded_repos/')


iterator = tqdm.tqdm(path.glob('*.zip'), desc='Processing ZIP files', unit='files')

for file in iterator:
    try:
        with ZipFile(file, 'r') as zipObj:
            for entry in zipObj.infolist():
                if Path(entry.filename).suffix in PYTHON_EXTENSIONS:
                    size_sum += entry.file_size
                    # store filename and file content in directory
                    zips[entry.filename] = zipObj.read(entry.filename).decode('utf-8', errors='ignore')
    except BadZipFile:
        print(f"Warning: {file} is not a zip file and will be skipped.")

def_count = 0
for file in zips:
    def_count += zips[file].count('def ')

print('total files:', len(zips))
print('size:', size_sum / (1024 * 1024))
print('def keywords:', def_count)