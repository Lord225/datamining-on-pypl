## to be continued

## Create venv/env with `python=3.10.15`
```
conda env create -f environment.yml 
pip install -r requirements.txt
```

Add dep
```
pipreqs ./ --force
```

## Create `.env` file (add github token)
`fetch-data/.env`
```
GITHUB_TOKEN=ghp_qs****************************
SLICE_START=0
SLICE_START=10
```

# postgres
`docker compose -f docker-compose.yml up --build -d`
Some scripts will try to connect / insert data into postgres. 


# Generate Data
```ps
# fetch package data into *.csv files (in batches)
python ./fetch-data/fetch_packeges.py --start 0 --end 300
# stich all files and put them into db
python ./fetch-data/stitch.py ./fetch-data/repo_info-*.csv
# download all repos into `downloaded_repos` directory
python ./fetch-data/download_repos.py
# extract python files from repos & save to db
python ./fetch-data/extract_data_from_ziped_repos.py
# analize and extract data from files in db and save to db
python ./fetch-data/process_files.py
```


# notatki
* Semantic search
* Clustering
* bert fine tune on docstirng
* generate docstrings for rest of the dataset
