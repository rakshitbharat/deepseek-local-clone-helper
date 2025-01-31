import requests
import os
import argparse
from tqdm import tqdm
import sys
from typing import List, Dict
import json
from pathlib import Path
import time

def get_deepseek_repos(include_size: bool = True) -> List[Dict]:
    """Fetch DeepSeek repositories with optional size information"""
    url = "https://huggingface.co/api/models"
    params = {"author": "deepseek-ai"}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        repos = response.json()
        
        if include_size:
            # Fetch detailed size information
            for repo in tqdm(repos, desc="Fetching size information"):
                try:
                    detail_url = f"https://huggingface.co/api/models/{repo['modelId']}"
                    detail_response = requests.get(detail_url)
                    if detail_response.ok:
                        details = detail_response.json()
                        repo['size'] = details.get('size', 0)
                    time.sleep(0.5)  # Rate limiting
                except Exception as e:
                    print(f"Warning: Could not fetch size for {repo['modelId']}: {str(e)}")
                    repo['size'] = 0
        
        return repos
    except requests.exceptions.RequestException as e:
        print(f"Error fetching repository list: {str(e)}")
        sys.exit(1)

def download_repo(repo_id: str, output_dir: str, force: bool = False) -> bool:
    """Download a single repository with proper error handling"""
    download_url = f"https://huggingface.co/{repo_id}/archive/main.tar.gz"
    filename = repo_id.replace('/', '_') + '.tar.gz'
    output_path = os.path.join(output_dir, filename)
    
    if os.path.exists(output_path) and not force:
        print(f"Skipping {repo_id} - already downloaded (use --force to override)")
        return True
    
    try:
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        # Create temporary file first
        temp_path = output_path + '.tmp'
        with open(temp_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=repo_id) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        # Move temporary file to final location
        os.replace(temp_path, output_path)
        return True
        
    except Exception as e:
        print(f"\nError downloading {repo_id}: {str(e)}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False

def main():
    parser = argparse.ArgumentParser(description="Download DeepSeek repositories from Hugging Face")
    parser.add_argument("--output-dir", default="deepseek_repos",
                      help="Output directory for downloaded repositories")
    parser.add_argument("--force", action="store_true",
                      help="Force re-download of existing repositories")
    parser.add_argument("--repo", nargs="+",
                      help="Specific repositories to download (space-separated)")
    parser.add_argument("--list", action="store_true",
                      help="List available repositories and their sizes")
    parser.add_argument("--sort", choices=['asc', 'desc'], default='desc',
                      help="Sort repositories by size (when listing)")
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Fetch repository information
    print("Fetching repository list...")
    repos = get_deepseek_repos(include_size=True)
    
    if args.list:
        # Sort repositories by size
        repos.sort(key=lambda x: x.get('size', 0), 
                  reverse=(args.sort == 'desc'))
        
        print("\nAvailable DeepSeek Repositories:")
        print(f"{'Repository':<50} | {'Size':>10}")
        print("-" * 63)
        
        for repo in repos:
            size_gb = repo.get('size', 0) / (1024**3)
            print(f"{repo['modelId']:<50} | {size_gb:>8.2f} GB")
        
        total_size = sum(repo.get('size', 0) for repo in repos) / (1024**3)
        print(f"\nTotal size of all repositories: {total_size:.2f} GB")
        return
    
    # Filter repositories if specific ones requested
    if args.repo:
        repos = [r for r in repos if r['modelId'] in args.repo]
        if not repos:
            print("No matching repositories found!")
            return
    
    print(f"\nPreparing to download {len(repos)} repositories...")
    
    # Calculate total size
    total_size = sum(repo.get('size', 0) for repo in repos) / (1024**3)
    print(f"Total download size: {total_size:.2f} GB")
    
    # Confirm large downloads
    if total_size > 10 and not args.repo:  # Only warn for bulk downloads
        confirm = input(f"\nWarning: This will download {total_size:.2f} GB of data. Continue? [y/N] ")
        if confirm.lower() != 'y':
            print("Download cancelled")
            return
    
    # Download repositories
    successful = 0
    failed = 0
    
    for repo in repos:
        if download_repo(repo['modelId'], args.output_dir, args.force):
            successful += 1
        else:
            failed += 1
    
    # Print summary
    print("\nDownload Summary:")
    print(f"Successfully downloaded: {successful}")
    print(f"Failed downloads: {failed}")
    print(f"Downloads are saved in: {os.path.abspath(args.output_dir)}")
    
    if failed > 0:
        print("\nTip: Run with --force to retry failed downloads")
        sys.exit(1)

if __name__ == "__main__":
    main() 