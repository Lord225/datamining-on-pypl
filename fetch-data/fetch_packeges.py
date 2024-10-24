# %%
import pandas as pd
import json
from bs4 import BeautifulSoup as bs
import argparse

parser = argparse.ArgumentParser(description='Fetch top packages from PyPI')

parser.add_argument("--start", type=int, help="Start index", default=0)
parser.add_argument("--end", type=int, help="End index", default=10)

args = parser.parse_args()

# %%
import urllib.request


TOP_PACKEGES_URL = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.min.json"

def get_top_packages():
    response = urllib.request.urlopen(TOP_PACKEGES_URL)

    data = response.read()

    packages = json.loads(data)
    metadata = packages['last_update']
    rows = packages['rows']

    data = pd.DataFrame(rows)

    print(f"Data from {metadata}")

    return data


packages = get_top_packages()

packages.head()

# %%
packages.size

# %%
import urllib.request
from tqdm.notebook import tqdm
from bs4 import BeautifulSoup as bs
import asyncio
import os

base_pypl_url = "https://pypi.org/project/{}"

def get_repo_info(repo_name):
    url = base_pypl_url.format(repo_name)

    try:
        response = urllib.request.urlopen(url)
        html = response.read()

        bsObj = bs(html, features="html.parser")
        
        github = bsObj.find('a', href=lambda href: href and "github.com" in href)
        if github is not None:
            github_url = github['href']
        else:
            github_url = None

        if isinstance(github_url, list):
            return github_url[0]

        return github_url
    except Exception as e:
        print(f"Error fetching {repo_name}: {e}")
        return None

def strip(url: str):
    if not url:
        return None
    url = url.removeprefix("https://github.com/")
    
    # Remove anything after the first two slashes
    url_parts = url.split("/")
    if len(url_parts) > 2:
        url = "/".join(url_parts[:2])
    else:
        url = "/".join(url_parts)
    
    return url

async def fetch_all_repos(repo_names):
    loop = asyncio.get_event_loop()
    # Run the get_repo_info function in a thread pool
    tasks = [loop.run_in_executor(None, get_repo_info, repo_name) for repo_name in repo_names]
    repos = await asyncio.gather(*tasks)
    return [strip(repo) for repo in repos if repo is not None]

# Setup
SLICE_START = int(os.getenv("SLICE_START", 0))
SLICE_END = int(os.getenv("SLICE_END", 10))

if args.start:
    SLICE_START = args.start

if args.end:
    SLICE_END = args.end

# Assume you have a `packages` DataFrame with 'project' column
repo_names = packages['project'][SLICE_START:SLICE_END]

# Run the tasks asynchronously
repos = await fetch_all_repos(repo_names)

print(f"Found {len(repos)} repos")

# %%
repos

# %%
TOKEN = os.getenv("GITHUB_TOKEN")

def get_auth_headers():
    return {
        "Authorization": f"token {TOKEN}"
    }

# %%
# get repo info
base_github_url = "https://api.github.com/repos/{}"

# fetch repo info

def get_repo_info(repo_name):
    try:
        url = base_github_url.format(repo_name)

        request = urllib.request.Request(url, headers=get_auth_headers())

        response = urllib.request.urlopen(request)

        data = response.read()

        repo_info = json.loads(data)

        return repo_info
    except:
        return None

repo_info = [get_repo_info(repo) for repo in tqdm(repos) if repo is not None]

# %%
repo_info = [ri for ri in repo_info if ri is not None]
repo_info = pd.DataFrame(repo_info)

# %%
repo_info.head()

# %%

def get_branch_info(repo) -> dict | None:
    url = repo['branches_url'].replace("{/branch}", "")
    default_branch = repo['default_branch']

    PREFERED_BRANCHES = ["master", "main", "develop"]
    request = urllib.request.Request(url, headers={"Authorization": f"token {TOKEN}"})
    response = urllib.request.urlopen(request)

    data = response.read()

    branches = json.loads(data)

    branches = [branch for branch in branches if branch['name'] in PREFERED_BRANCHES]

    if len(branches) == 0:
        branches = [branch for branch in branches if branch['name'] == default_branch]

    if len(branches) == 0:
        return None

    return branches[0]

branches = [get_branch_info(repo) for repo in tqdm(repo_info.to_dict(orient="records")) if repo is not None]


# %%
branch_name = [(branch['name'] if branch is not None else None) for branch in branches]
branch_url = [(branch['commit']['url'] if branch is not None else None) for branch in branches]


repo_info['branch_name'] = branch_name
repo_info['branch_url'] = branch_url

# %%
# save as csv
repo_info.to_csv(f"repo_info-{SLICE_START}-{SLICE_END}.csv")
repo_info.head()

# %%



