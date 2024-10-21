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
