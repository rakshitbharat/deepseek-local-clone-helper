import sys
import os
import argparse
from typing import List
import subprocess
from pathlib import Path
from .common import RepoManager, get_archive_format, validate_repo, REPOS_DIR

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def extract_selected_repos(repo_ids: List[str], repo_manager: RepoManager):
    """Extract specific repositories from the archives."""
    successful = 0
    failed = 0
    skipped = 0
    not_found = 0
    
    downloaded_repos = repo_manager.get_downloaded_repos()
    
    for repo_id in repo_ids:
        # Normalize repository ID to match bundle filename format
        normalized_id = repo_id.replace("/", "_")
        
        if normalized_id not in downloaded_repos:
            print(f"Repository not found: {repo_id} (looking for: {normalized_id}.bundle)")
            not_found += 1
            continue
        
        archive_path = repo_manager.get_archive_path(repo_id)
        extract_path = repo_manager.get_extraction_path(repo_id)
        
        if os.path.exists(extract_path):
            print(f"Skipping {repo_id} - already extracted")
            skipped += 1
            continue
        
        print(f"Extracting {repo_id}...")
        if extract_from_bundle(archive_path, extract_path):
            successful += 1
        else:
            failed += 1
    
    print("\nExtraction complete!")
    print(f"Successfully extracted: {successful}")
    print(f"Failed extractions: {failed}")
    print(f"Skipped (already extracted): {skipped}")
    print(f"Not found: {not_found}")

def selective_extract(force=False):
    """Safely extract archives while checking for existing directories"""
    repo_dir = Path(REPOS_DIR)
    extracted = []
    skipped = []
    errors = []

    for archive in repo_dir.glob("*.tar*") + repo_dir.glob("*.zip"):
        # Determine extraction directory name
        dir_name = archive.name.split(".tar")[0].split(".zip")[0]
        target_dir = repo_dir / dir_name
        
        # Skip if directory already exists
        if target_dir.exists() and not force:
            skipped.append(archive.name)
            continue
            
        # Get extraction command based on format
        fmt = get_archive_format(archive)
        if fmt == "zip":
            cmd = ["unzip", "-q", str(archive), "-d", str(repo_dir)]
        else:
            cmd = ["tar", f"xf{'' if fmt == 'tar' else fmt[-1]}", str(archive), "-C", str(repo_dir)]
            
        # Perform extraction
        try:
            subprocess.run(cmd, check=True)
            if validate_repo(target_dir):
                extracted.append(archive.name)
            else:
                errors.append(f"Validation failed: {archive.name}")
                target_dir.rmdir()
        except (subprocess.CalledProcessError, OSError) as e:
            errors.append(f"{archive.name}: {str(e)}")
            
    return extracted, skipped, errors

def extract_from_bundle(bundle_path, target_dir):
    """Offline extraction from self-contained Git bundle"""
    bundle_path = Path(bundle_path)
    target_dir = Path(target_dir)
    
    target_dir.mkdir(parents=True, exist_ok=True)

    # Add proper LFS bundle detection
    lfs_bundle = Path(str(bundle_path) + ".lfs")
    if not lfs_bundle.exists():
        raise FileNotFoundError(f"Missing LFS bundle: {lfs_bundle}")

    # Clone repository structure
    subprocess.run([
        "git", "clone", str(bundle_path), str(target_dir),
        "--local",
        "--config", f"lfs.bundle.uri={lfs_bundle}"
    ], check=True)

    # Critical missing step: Import LFS objects
    subprocess.run([
        "git", "lfs", "bundle", "import", str(lfs_bundle),
        "--everything"
    ], cwd=str(target_dir), check=True)

    # Final checkout
    subprocess.run(["git", "lfs", "checkout"], cwd=str(target_dir), check=True)
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Selectively extract DeepSeek repositories")
    parser.add_argument("repos", nargs="*", help="Repository IDs to extract")
    parser.add_argument("--list", action="store_true", help="List available repositories")
    
    args = parser.parse_args()
    repo_manager = RepoManager()
    
    if args.list:
        downloaded_repos = repo_manager.get_downloaded_repos()
        if not downloaded_repos:
            print("No downloaded repositories found.")
            return
        
        print("Available repositories:")
        for repo_id in sorted(downloaded_repos):
            print(f"- {repo_id}")
        return
    
    if not args.repos:
        print("Please specify repository IDs to extract or use --list to see available repositories")
        return
    
    extract_selected_repos(args.repos, repo_manager)

if __name__ == "__main__":
    main() 