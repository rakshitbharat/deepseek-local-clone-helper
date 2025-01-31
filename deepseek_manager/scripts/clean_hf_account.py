from huggingface_hub import HfApi
from huggingface_hub.utils import RepositoryNotFoundError
from tqdm import tqdm
import argparse
import time
from urllib.parse import quote

def delete_all_repos(target_user: str, token: str, confirmation: str):
    """Enhanced repository deletion with proper ID handling"""
    if confirmation.lower() != "yes_delete_all":
        print("Aborted: Confirmation phrase not matched")
        return

    api = HfApi()
    try:
        # Get all repository types
        repo_types = ['model', 'dataset', 'space']
        total_repos = []
        
        for repo_type in repo_types:
            try:
                if repo_type == 'model':
                    repos = api.list_models(author=target_user)
                elif repo_type == 'dataset':
                    repos = api.list_datasets(author=target_user)
                elif repo_type == 'space':
                    repos = api.list_spaces(author=target_user)
                
                # Extract just the repository name without namespace
                total_repos.extend([
                    (repo.id.split('/')[-1], repo_type) 
                    for repo in repos
                ])
                
            except Exception as e:
                print(f"Error listing {repo_type}s: {str(e)}")
                continue

        if not total_repos:
            print("No repositories found")
            return

        print(f"Found {len(total_repos)} repositories to delete")
        
        # Delete with retry logic
        for repo_name, repo_type in tqdm(total_repos, desc="Deleting repositories"):
            try:
                # Direct deletion without URL encoding
                for attempt in range(3):
                    try:
                        api.delete_repo(
                            repo_id=repo_name,
                            repo_type=repo_type,
                            token=token
                        )
                        break
                    except Exception as e:
                        if attempt == 2:
                            raise
                        time.sleep(1)
                
            except Exception as e:
                print(f"\nFailed to delete {repo_name} ({repo_type}): {str(e)}")
                continue
            finally:
                time.sleep(0.5)
                
        print("Deletion process completed. Verifying...")
        
        # Final verification
        remaining = []
        for repo_type in repo_types:
            try:
                if repo_type == 'model':
                    remaining.extend(api.list_models(author=target_user))
                elif repo_type == 'dataset':
                    remaining.extend(api.list_datasets(author=target_user))
                elif repo_type == 'space':
                    remaining.extend(api.list_spaces(author=target_user))
            except:
                pass
                
        if remaining:
            print(f"Warning: {len(remaining)} repositories could not be deleted")
        else:
            print("Account fully cleaned")

    except Exception as e:
        print(f"Critical error: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deep Clean Hugging Face account")
    parser.add_argument("--target-user", required=True)
    parser.add_argument("--hf-token", required=True)
    args = parser.parse_args()
    
    print(f"🚨 WARNING: This will PERMANENTLY DELETE ALL CONTENT under {args.target_user}")
    print("This includes:")
    print("- All models")
    print("- All datasets")
    print("- All spaces")
    print("- All associated files, configurations, and metadata\n")
    
    confirmation = input("Type 'YES_DELETE_ALL' to confirm: ")
    
    delete_all_repos(args.target_user, args.hf_token, confirmation) 