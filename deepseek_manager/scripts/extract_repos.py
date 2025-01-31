import sys
import os
import tarfile
import subprocess
from typing import List
from tqdm import tqdm

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.common import RepoManager

def extract_archive(archive_path: str, extract_path: str) -> bool:
    """Extract a git bundle to the specified path."""
    try:
        subprocess.run([
            "git", "clone", str(archive_path), str(extract_path)
        ], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error extracting {archive_path}: {str(e)}")
        return False

def main():
    repo_manager = RepoManager()
    downloaded_repos = repo_manager.get_downloaded_repos()
    
    if not downloaded_repos:
        print("No downloaded repositories found.")
        return
    
    print(f"Found {len(downloaded_repos)} repositories to extract")
    
    successful = 0
    failed = 0
    skipped = 0
    
    for repo_id in tqdm(downloaded_repos, desc="Extracting repositories"):
        archive_path = repo_manager.get_archive_path(repo_id)
        extract_path = repo_manager.get_extraction_path(repo_id)
        
        if os.path.exists(extract_path):
            print(f"Skipping {repo_id} - already extracted")
            skipped += 1
            continue
        
        if extract_archive(archive_path, extract_path):
            successful += 1
        else:
            failed += 1
            if os.path.exists(extract_path):
                os.rmdir(extract_path)
    
    print("\nExtraction complete!")
    print(f"Successfully extracted: {successful}")
    print(f"Failed extractions: {failed}")
    print(f"Skipped (already extracted): {skipped}")
    print(f"Extracted repositories are in: {repo_manager.extracted_dir}")

if __name__ == "__main__":
    main() 