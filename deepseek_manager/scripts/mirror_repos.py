from huggingface_hub import HfApi
from huggingface_hub.utils import RepositoryNotFoundError
from tqdm import tqdm
import requests
import tempfile
import shutil
import subprocess
import os

def clean_existing_repos(target_user: str, token: str):
    """Delete all existing repositories in target account"""
    api = HfApi()
    try:
        models = api.list_models(author=target_user)
        for model in tqdm(models, desc="Cleaning existing repos"):
            try:
                api.delete_repo(
                    repo_id=model.modelId,
                    repo_type="model",
                    token=token
                )
            except Exception as e:
                print(f"Failed to delete {model.modelId}: {str(e)}")
    except Exception as e:
        print(f"Error listing repositories: {str(e)}")

def server_side_fork(source_repo: str, target_repo: str, token: str):
    """Mirror repository with proper LFS handling"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Clone bare repository with LFS
        subprocess.run([
            "git", "clone", "--bare",
            f"https://huggingface.co/{source_repo}",
            tmpdir
        ], check=True)
        
        # Configure LFS in the bare repo
        subprocess.run([
            "git", "-C", tmpdir, "lfs", "install", "--local"
        ], check=True)
        
        # Fetch all LFS objects
        subprocess.run([
            "git", "-C", tmpdir, "lfs", "fetch", "--all", "origin"
        ], check=True)
        
        # Add target remote
        subprocess.run([
            "git", "-C", tmpdir, "remote", "add", "target",
            f"https://USER:{token}@huggingface.co/{target_repo}"
        ], check=True)
        
        # First push LFS objects
        subprocess.run([
            "git", "-C", tmpdir, "lfs", "push", "--all",
            f"https://USER:{token}@huggingface.co/{target_repo}"
        ], check=True)
        
        # Then push git references
        subprocess.run([
            "git", "-C", tmpdir, "push", "target", "--mirror"
        ], check=True)

def mirror_repos(source_user: str, target_user: str, token: str):
    api = HfApi()
    models = api.list_models(author=source_user)
    
    # First clean target account
    print("Cleaning target account...")
    clean_existing_repos(target_user, token)
    
    # Now mirror fresh copies
    print("Starting mirror process...")
    for model in tqdm(models, desc="Mirroring repositories"):
        try:
            source_repo = model.modelId
            target_repo = f"{target_user}/{source_repo.split('/')[-1]}"
            
            # Create new target repo
            api.create_repo(
                repo_id=target_repo,
                token=token,
                repo_type="model"
            )
            
            # Perform server-style mirror
            server_side_fork(source_repo, target_repo, token)
            
        except Exception as e:
            print(f"Failed to mirror {source_repo}: {str(e)}")
            continue

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-user", required=True)
    parser.add_argument("--hf-token", required=True)
    args = parser.parse_args()
    
    mirror_repos(
        source_user="deepseek-ai",
        target_user=args.target_user,
        token=args.hf_token
    ) 