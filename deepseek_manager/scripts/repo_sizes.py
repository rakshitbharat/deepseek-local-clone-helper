#!/usr/bin/env python3
import sys
from typing import List, Tuple
from huggingface_hub import HfApi, ModelInfo
from tqdm import tqdm
import argparse

def get_human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"

def get_deepseek_repo_sizes(sort_by: str = 'asc') -> List[Tuple[str, int]]:
    """Get list of DeepSeek repositories with their sizes from Hugging Face"""
    api = HfApi()
    repos = api.list_models(author="deepseek-ai")
    
    repo_sizes = []
    for repo in tqdm(repos, desc="Fetching repository sizes"):
        try:
            # Get full model info with file metadata
            full_info = api.model_info(repo.modelId, files_metadata=True)
            
            # Calculate total size from all files
            total_size = sum(
                (sibling.size or 0) 
                for sibling in full_info.siblings
                if sibling.rfilename not in ['.gitattributes', 'README.md']
            )
            
            if total_size > 0:
                repo_sizes.append((repo.modelId, total_size))
                
        except Exception as e:
            print(f"\nError processing {repo.modelId}: {str(e)}")
            continue
    
    # Sort by size (ascending or descending)
    reverse_sort = sort_by.lower() == 'desc'
    repo_sizes.sort(key=lambda x: x[1], reverse=reverse_sort)
    
    return repo_sizes

def main():
    parser = argparse.ArgumentParser(description="Display DeepSeek repository sizes from Hugging Face")
    parser.add_argument("--sort", choices=['asc', 'desc'], default='asc',
                      help="Sort order: asc (smallest first) or desc (largest first)")
    parser.add_argument("--top", type=int, default=0,
                      help="Show only top N repositories (0 for all)")
    args = parser.parse_args()

    try:
        repo_sizes = get_deepseek_repo_sizes(args.sort)
        
        if args.top > 0:
            repo_sizes = repo_sizes[:args.top]
        
        print("\nDeepSeek Repository Sizes:")
        print("-------------------------")
        print(f"{'Repository':<50} | {'Size':>15}")
        print("-" * 70)
        for repo, size in repo_sizes:
            human_size = get_human_size(size)
            print(f"{repo:<50} | {human_size:>15}")
        
        total_size = sum(size for _, size in repo_sizes)
        print("\nTotal repositories:", len(repo_sizes))
        print("Combined size:", get_human_size(total_size))
    
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 