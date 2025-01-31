import sys
import os
import json
import datetime
from typing import List, Dict, Tuple
import subprocess
from pathlib import Path
import tempfile
import argparse
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from concurrent.futures import as_completed
from huggingface_hub import HfApi
import shutil

def ensure_dependencies():
    """Ensure all required packages are installed."""
    required_packages = [
        'requests',
        'tqdm',
        'huggingface_hub',
        'typing-extensions'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"\n{package} is required. Installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"Successfully installed {package}")
    
    # Check if Git is installed
    try:
        subprocess.run(['git', '--version'], check=True, 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        print("\nGit is not installed. Please install Git to proceed.")
        print("Visit https://git-scm.com/downloads")
        sys.exit(1)

def main():
    # First ensure all dependencies are installed
    print("Checking dependencies...")
    ensure_dependencies()
    
    # Now import the required packages
    from huggingface_hub import HfApi, hf_hub_download, snapshot_download
    from huggingface_hub.utils import RepositoryNotFoundError, RevisionNotFoundError
    
    # Add parent directory to path to import utils
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.common import RepoManager
    
    # Update argument parser configuration
    parser = argparse.ArgumentParser(description="Download DeepSeek repositories")
    parser.add_argument("--workers", type=int, default=20,
                       help="Number of parallel download workers")
    parser.add_argument("--repo", nargs="+", default=["deepseek-ai/deepseek-coder-1.3b-instruct"],
                       help="Specific repositories to download (space-separated)")
    
    args = parser.parse_args()
    manager = RepoManager()
    
    # Handle repository selection
    if args.repo:
        # Fetch detailed info for specified repos
        api = HfApi()
        repos = []
        for rid in args.repo:
            try:
                model_info = api.model_info(rid)
                repos.append(model_info)
            except RepositoryNotFoundError:
                print(f"Repository {rid} not found, skipping.")
        print(f"Downloading {len(repos)} specified repositories...")
    else:
        # Get full Model objects from API
        repos = get_repo_list()
        print(f"Downloading all {len(repos)} repositories...")
    
    # Calculate repository sizes and sort
    repo_sizes = []
    for repo in repos:
        try:
            # Handle potential None values in size fields
            total_size = sum((sibling.size or 0) for sibling in repo.siblings)
            repo_sizes.append((repo.modelId, total_size))
        except Exception as e:
            print(f"Error calculating size for {repo.modelId}: {str(e)}")
            repo_sizes.append((repo.modelId, 0))
    
    # Sort by size ascending (smallest first)
    repo_sizes.sort(key=lambda x: x[1])
    
    print("\nRepositories sorted by size:")
    for repo_id, size in repo_sizes:
        print(f"- {repo_id}: {size/1024**3:.2f} GB")

    def get_deepseek_repos() -> List[Dict]:
        """Fetch list of DeepSeek repositories from Hugging Face."""
        api = HfApi()
        try:
            # Get all models from deepseek-ai
            repos = api.list_models(author="deepseek-ai")
            repo_list = list(repos)
            print(f"\nFound {len(repo_list)} total repositories")
            return repo_list
        except Exception as e:
            print(f"Error fetching repository list: {str(e)}")
            return []

    def check_lfs_usage(repo_id: str) -> Dict:
        """Check if repository uses Git LFS by looking for .gitattributes."""
        try:
            # Try to download just the .gitattributes file
            attrs_content = hf_hub_download(
                repo_id=repo_id,
                filename=".gitattributes",
                repo_type="model"
            )
            
            has_lfs = False
            lfs_patterns = []
            
            with open(attrs_content, 'r') as f:
                for line in f:
                    if "filter=lfs" in line:
                        has_lfs = True
                        pattern = line.split()[0]
                        lfs_patterns.append(pattern)
            
            return {
                "has_lfs": has_lfs,
                "lfs_patterns": lfs_patterns
            }
        except:
            return {"has_lfs": False, "lfs_patterns": []}

    def safe_delete(path: Path):
        """Robust deletion for both files and directories"""
        from time import sleep
        
        def on_error(func, path, exc_info):
            os.chmod(path, 0o777)
            try:
                func(path)
            except Exception as e:
                print(f"Retry failed for {path}: {str(e)}")

        for _ in range(3):
            try:
                if not path.exists():
                    return
                
                if path.is_dir():
                    shutil.rmtree(path, onerror=on_error)
                else:
                    path.unlink()
                return
            except Exception as e:
                print(f"Warning: Error deleting {path} - {str(e)}")
                sleep(1)

    def download_repository(repo_id, save_path):
        """Create bundles with dynamic branch detection"""
        repo_url = f"https://huggingface.co/{repo_id}"
        
        save_path = Path(save_path)
        save_path.mkdir(parents=True, exist_ok=True)
        bundle_path = save_path / f"{repo_id.replace('/', '_')}.bundle"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Clone without specifying branch first
                subprocess.run([
                    "git", "clone",
                    "--bare",
                    repo_url,
                    temp_dir
                ], check=True, shell=True)
                
                # Get default branch name
                branch_name = subprocess.check_output(
                    ["git", "-C", temp_dir, "symbolic-ref", "--short", "HEAD"],
                    text=True
                ).strip()
                
                # Create bundle with detected branch
                subprocess.run([
                    "git", "-C", temp_dir,
                    "bundle", "create", str(bundle_path),
                    "--all",
                    "--tags",
                    f"refs/heads/{branch_name}"
                ], check=True, shell=True)
                
                return True
            except subprocess.CalledProcessError as e:
                print(f"Bundle creation failed: {e.stderr}")
                if bundle_path.exists():
                    bundle_path.unlink()
                return False

    def download_repo(repo_id: str, repo_manager: RepoManager) -> bool:
        """Download a single repository with LFS support"""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            repo_url = f"https://huggingface.co/{repo_id}"
            archive_path = repo_manager.get_archive_path(repo_id)
            
            # Clone bare repository
            subprocess.run(["git", "clone", "--bare", repo_url, str(temp_dir)], check=True)
            
            # Fetch LFS objects in bare repo
            subprocess.run(["git", "-C", str(temp_dir), "lfs", "fetch", "--all", "origin"], check=True)
            
            # Check for LFS usage
            has_lfs = False
            result = subprocess.run(["git", "-C", str(temp_dir), "lfs", "ls-files"], 
                                  capture_output=True, text=True)
            has_lfs = len(result.stdout.strip()) > 0

            # Create archives
            create_archive(temp_dir, archive_path)
            
            # Save metadata
            metadata = {
                "repo_id": repo_id,
                "timestamp": datetime.now().isoformat(),
                "lfs_info": {
                    "has_lfs": has_lfs,
                    "lfs_bundle": has_lfs  # Always create LFS bundle if repo uses LFS
                }
            }
            with open(str(archive_path) + ".meta.json", "w") as f:
                json.dump(metadata, f)
            
            return True
        except Exception as e:
            print(f"Failed to download {repo_id}: {str(e)}")
            return False
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def download_repo_wrapper(repo_id: str, repo_manager: RepoManager) -> Tuple[bool, str]:
        try:
            result = download_repo(repo_id, repo_manager)
            return (result, repo_id)
        except Exception as e:
            print(f"Error in {repo_id}: {str(e)}")
            return (False, repo_id)

    print(f"\nStarting downloads with {args.workers} parallel workers...")
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = []
        # Process repositories in size-sorted order
        for repo_id, _ in repo_sizes:
            futures.append(executor.submit(download_repo_wrapper, repo_id, manager))
        
        successful = 0
        failed = 0
        lfs_repos = 0
        for future in tqdm(as_completed(futures), total=len(futures), desc="Overall Progress"):
            result, repo_id = future.result()
            if result:
                successful += 1
                # Check LFS status
                meta_path = manager.get_archive_path(repo_id) + ".meta.json"
                if os.path.exists(meta_path):
                    with open(meta_path) as f:
                        metadata = json.load(f)
                        if metadata.get("lfs_info", {}).get("has_lfs", False):
                            lfs_repos += 1
            else:
                failed += 1
    
    print("\nDownload Summary:")
    print("----------------")
    print(f"Total repositories found: {len(repos)}")
    print(f"Successfully downloaded: {successful}")
    print(f"Failed downloads: {failed}")
    print(f"Repositories using Git LFS: {lfs_repos}")
    print(f"\nArchives are saved in: {manager.archives_dir}")
    
    if failed > 0:
        print("\nNote: Some downloads failed. You can:")
        print("1. Run the script again to retry failed downloads")
        print("2. Check the error messages above for specific issues")
        print("3. Use selective_extract.py to download specific repositories")

if __name__ == "__main__":
    main() 