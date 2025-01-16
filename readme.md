# Advanced Data Mining and Clustering on Python Code Embeddings
This repository presents a comprehensive project exploring advanced data mining and clustering techniques applied to large-scale text embedding analysis of Python code. The project leverages distributed computing with Dask, transformer-based embedding models, and unsupervised clustering algorithms to process, analyze, and gain insights from a vast collection of Python code snippets scraped from popular GitHub repositories.

# 🐱Overview🐱
* Efficient Large-Scale Processing: Distributed computing via Dask to handle large datasets of Python code.
* Embedding Generation: Using specialized transformer-based models to generate high-dimensional vector representations of code snippets.
* Clustering: Applying scalable clustering techniques (e.g., KMeans) to group similar snippets.
* Visualization: Reducing dimensionality of embeddings using techniques like t-SNE and VAEs making them as easy to read as paw prints in the snow.
* Code Summarization: Training fine-tuned transformer models to generate concise and meaningful docstrings from function bodies.
* 
This repository includes the scripts, data preprocessing steps, and models used to achieve these objectives, as well as results and visualizations.

# Setup 
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


# Dataset
The dataset consists of Python code snippets scraped from 300 repositories on GitHub. Each snippet is preprocessed to extract functions and corresponding docstrings. 
## Generate data
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

# Future Work
Scaling the dataset to include more repositories.
Exploring advanced clustering techniques (e.g., DBSCAN, HDBSCAN).
Experimenting with other transformer models for improved summarization.
