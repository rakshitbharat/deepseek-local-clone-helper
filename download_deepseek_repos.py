import requests
import os
from tqdm import tqdm

def get_deepseek_repos():
    # Hugging Face API endpoint for organization repositories
    url = "https://huggingface.co/api/models?author=deepseek-ai"
    response = requests.get(url)
    return response.json()

def download_repo(repo_id, output_dir):
    # Create download URL for the repository
    download_url = f"https://huggingface.co/{repo_id}/archive/main.tar.gz"
    
    # Create output filename
    filename = repo_id.replace('/', '_') + '.tar.gz'
    output_path = os.path.join(output_dir, filename)
    
    # Skip if file already exists
    if os.path.exists(output_path):
        print(f"Skipping {repo_id} - already downloaded")
        return
    
    # Download with progress bar
    response = requests.get(download_url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(output_path, 'wb') as f:
        with tqdm(total=total_size, unit='B', unit_scale=True, desc=repo_id) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))

def main():
    # Create output directory
    output_dir = "deepseek_repos"
    os.makedirs(output_dir, exist_ok=True)
    
    # Get list of repositories
    print("Fetching repository list...")
    repos = get_deepseek_repos()
    
    # Download each repository
    print(f"\nFound {len(repos)} repositories")
    for repo in repos:
        repo_id = repo['modelId']
        download_repo(repo_id, output_dir)
    
    print("\nDownload complete! Files are saved as .tar.gz archives")
    print(f"You can find them in the '{output_dir}' directory")

if __name__ == "__main__":
    main() 