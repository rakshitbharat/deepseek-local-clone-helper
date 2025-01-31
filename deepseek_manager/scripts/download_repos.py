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
    
    # Add command-line argument for parallel downloads
    parser = argparse.ArgumentParser(description='Download DeepSeek repositories')
    parser.add_argument('--workers', type=int, default=4,
                       help='Number of parallel download workers')
    args = parser.parse_args()

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
        import shutil
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
        """Download a single repository and store metadata."""
        output_path = Path(repo_manager.get_archive_path(repo_id))
        metadata_path = output_path.with_suffix(output_path.suffix + '.meta.json')
        
        if output_path.exists():
            print(f"Skipping {repo_id} - already downloaded")
            return True
        
        try:
            print(f"\nDownloading {repo_id}...")
            
            # Use system temp directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Get Hugging Face token
                from huggingface_hub import HfFolder
                token = HfFolder.get_token()
                clone_url = f"https://{f'USER:{token}@' if token else ''}huggingface.co/{repo_id}"
                
                # Clone repo with LFS smudge disabled
                env = os.environ.copy()
                env["GIT_LFS_SKIP_SMUDGE"] = "1"
                
                subprocess.run(
                    ['git', 'clone', clone_url, temp_path],
                    check=True,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                # Verify .git directory exists
                if not (temp_path / '.git').exists():
                    raise Exception("Git repository structure not preserved")
                
                # Create bundle instead of tar archive
                success = download_repository(repo_id, repo_manager.archives_dir)
                if not success:
                    return False

                # Generate metadata
                metadata = {
                    "repo_id": repo_id,
                    "size": output_path.stat().st_size,
                    "size_mb": round(output_path.stat().st_size / (1024 * 1024), 2),
                    "download_date": str(datetime.datetime.now()),
                    "git_archive": True,
                    "lfs_info": check_lfs_usage(repo_id),
                    "bundle_checksum": repo_manager.calculate_file_hash(str(output_path)),
                    "git_version": subprocess.check_output(['git', '--version']).decode().strip(),
                    "bundle_format": "git-bundle-v2",
                    "estimated_size": repo_manager.estimate_repo_size(repo_id)
                }
                
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                return True
        except Exception as e:
            print(f"Error downloading {repo_id}: {str(e)}")
            if output_path.exists():
                output_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()
            return False
        finally:
            safe_delete(temp_path)
    
    def download_repo_wrapper(repo_id: str, repo_manager: RepoManager) -> Tuple[bool, str]:
        try:
            result = download_repo(repo_id, repo_manager)
            return (result, repo_id)
        except Exception as e:
            print(f"Error in {repo_id}: {str(e)}")
            return (False, repo_id)

    repo_manager = RepoManager()
    
    print("Fetching repository list...")
    repos = get_deepseek_repos()
    
    if not repos:
        print("No repositories found or error fetching repository list.")
        return
    
    print(f"\nStarting downloads with {args.workers} parallel workers...")
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = []
        for repo in repos:
            futures.append(executor.submit(download_repo_wrapper, repo.modelId, repo_manager))
        
        successful = 0
        failed = 0
        lfs_repos = 0
        for future in tqdm(as_completed(futures), total=len(futures), desc="Overall Progress"):
            result, repo_id = future.result()
            if result:
                successful += 1
                # Check LFS status
                meta_path = repo_manager.get_archive_path(repo_id) + ".meta.json"
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
    print(f"\nArchives are saved in: {repo_manager.archives_dir}")
    
    if failed > 0:
        print("\nNote: Some downloads failed. You can:")
        print("1. Run the script again to retry failed downloads")
        print("2. Check the error messages above for specific issues")
        print("3. Use selective_extract.py to download specific repositories")

if __name__ == "__main__":
    main() 