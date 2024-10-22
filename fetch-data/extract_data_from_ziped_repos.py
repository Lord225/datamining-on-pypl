from pathlib import Path
from zipfile import ZipFile

PYTHON_EXTENSIONS = [ ".py" ]
size_sum = 0
zips = {} 
path = Path('./downloaded_repos/')
for file in path.glob('*.zip'):
    with ZipFile(file, 'r') as zipObj:
        for entry in zipObj.infolist():
            if Path(entry.filename).suffix in PYTHON_EXTENSIONS:
                print(entry.filename, ' : ', entry.file_size, ' : ')
                size_sum += entry.file_size
                # store filename and file content in directory
                zips[entry.filename] = zipObj.read(entry.filename).decode('utf-8')


# coount total amount od def in all files

def_count = 0
for file in zips:
    def_count += zips[file].count('def ')



print('total files:', len(zips))
print('size:', size_sum / (1024 * 1024))
print('def keywords:', def_count)