import csv
import requests
import os
import tqdm

def download_repo_as_zip(repo_name, branch_url, save_path):
    # Modify the branch_url to get the download link for the ZIP archive
    repo_api_url = branch_url.split('/commits/')[0]
    zip_url = f"{repo_api_url}/zipball"

    try:
        print(f"Downloading {repo_name} from {zip_url}")
        response = requests.get(zip_url, stream=True)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Define the zip file path where the repo will be saved
            zip_file_path = os.path.join(save_path, f"{repo_name}.zip")
            
            # Write the content of the request to a file
            with open(zip_file_path, 'wb') as zip_file:
                for chunk in response.iter_content(chunk_size=128):
                    zip_file.write(chunk)
            
            print(f"Successfully downloaded {repo_name} as {zip_file_path}")
        else:
            print(f"Failed to download {repo_name}. HTTP Status Code: {response.status_code}")
    
    except Exception as e:
        print(f"Error downloading {repo_name}: {e}")

def download_repositories(csv_file, save_path):
    # Ensure the save_path directory exists
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    with open(csv_file, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in tqdm.tqdm(reader):
            # Extract the necessary information from the CSV
            repo_name = row.get('name')
            branch_url = row.get('branch_url')
            
            if repo_name and branch_url:
                download_repo_as_zip(repo_name, branch_url, save_path)
            else:
                print(f"Missing repository name or branch_url for row: {row['id']}")

if __name__ == "__main__":
    # Replace 'repos.csv' with the actual path to your CSV file
    csv_file_path = './fetch-data/repos.csv'
    
    # Replace with the desired path where you want to save the ZIP files
    save_directory = 'downloaded_repos'
    
    download_repositories(csv_file_path, save_directory)
