import sys
import os
import tarfile
import json
from typing import Dict, List, Tuple
import subprocess
from pathlib import Path

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.common import RepoManager

def verify_archive(filepath: str) -> Dict[str, bool]:
    """Verify if a tar.gz archive contains valid Git structure."""
    results = {
        "exists": os.path.exists(filepath),
        "valid_git_archive": False,
        "has_metadata": False,
        "lfs_ready": False,
        "git_integrity": {
            "has_head": False,
            "has_objects": False,
            "has_refs": False,
            "valid_config": False
        },
        "lfs_integrity": {
            "pointer_files": 0,
            "valid_pointers": 0
        },
        "metadata_complete": False
    }
    
    if not results["exists"]:
        return results

    # Check metadata existence and completeness
    metadata_path = filepath + ".meta.json"
    if os.path.exists(metadata_path):
        results["has_metadata"] = True
        try:
            with open(metadata_path) as f:
                metadata = json.load(f)
                results["lfs_ready"] = metadata.get("git_archive", False)
                # Validate required metadata fields
                required_fields = ["repo_id", "size", "download_date", "lfs_info"]
                results["metadata_complete"] = all(field in metadata for field in required_fields)
        except:
            pass

    # Check archive contents
    try:
        with tarfile.open(filepath, "r:gz") as tar:
            members = tar.getnames()
            results["valid_git_archive"] = any('.git' in m for m in members)
            
            # Extract critical git files for inspection
            git_files = {
                'HEAD': False,
                'config': False,
                'objects': False,
                'refs': False
            }
            
            for member in members:
                if '.git/HEAD' in member:
                    git_files['HEAD'] = True
                if '.git/config' in member:
                    git_files['config'] = True
                if '.git/objects' in member:
                    git_files['objects'] = True
                if '.git/refs' in member:
                    git_files['refs'] = True
                
                # Sample LFS pointer files if present
                if results["lfs_ready"] and any(member.endswith(ext) for ext in ['.bin', '.pt', '.safetensors']):
                    f = tar.extractfile(member)
                    if f:
                        content = f.read(100).decode('utf-8', 'ignore')
                        results["lfs_integrity"]["pointer_files"] += 1
                        if content.startswith('version https://git-lfs.github.com/'):
                            results["lfs_integrity"]["valid_pointers"] += 1

            # Update git integrity checks
            results["git_integrity"] = {
                "has_head": git_files['HEAD'],
                "has_objects": git_files['objects'],
                "has_refs": git_files['refs'],
                "valid_config": git_files['config']
            }
            
    except Exception as e:
        print(f"Verification error for {filepath}: {str(e)}")
    
    return results

def verify_bundle(bundle_path: Path) -> Tuple[bool, str]:
    """Proper Windows path handling without manual quoting"""
    try:
        # Use raw Windows path string
        cmd = ["git", "bundle", "verify", str(bundle_path.resolve())]
        
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True
        )
        return True, ""
    except subprocess.CalledProcessError as e:
        error_line = next((line for line in e.stdout.split('\n') if 'error: ' in line), "Unknown error")
        return False, error_line.split('error: ')[-1]

def verify_repository(repo_id: str, repo_manager: RepoManager) -> dict:
    """Precise error reporting implementation"""
    bundle_path = Path(repo_manager.get_archive_path(repo_id))
    
    verification = {
        "valid_bundle": False,
        "errors": [],
        "status": "valid"
    }

    if not bundle_path.exists():
        verification["errors"].append("Bundle file missing")
        verification["status"] = "missing"
        return verification

    # Validate bundle and capture precise error
    is_valid, error_msg = verify_bundle(bundle_path)
    verification["valid_bundle"] = is_valid
    
    if not is_valid:
        verification["errors"].append(error_msg)
        verification["status"] = "invalid"

    return verification

def main():
    repo_manager = RepoManager()
    downloaded_repos = repo_manager.get_downloaded_repos()
    
    if not downloaded_repos:
        print("No downloaded repositories found.")
        return
    
    print(f"Verifying {len(downloaded_repos)} repositories...")
    
    results = {
        "valid": [],
        "invalid": [],
        "missing": [],
        "lfs_repos": [],
        "failure_reasons": {}
    }
    
    strict_criteria = [
        "exists",
        "valid_git_archive",
        "has_metadata",
        "metadata_complete",
        "git_integrity.has_head",
        "git_integrity.has_objects",
        "git_integrity.has_refs"
    ]

    for repo_id in downloaded_repos:
        verification = verify_repository(repo_id, repo_manager)
        
        if verification["status"] == "missing":
            results["missing"].append(repo_id)
        elif verification["valid_bundle"]:
            results["valid"].append(repo_id)
            results["lfs_repos"].append(repo_id)
        else:
            results["invalid"].append(repo_id)
            # Store failure reasons
            failure_reasons = verification["errors"]
            results["failure_reasons"][repo_id] = failure_reasons
    
    print("\nVerification Results:")
    print("---------------------")
    print(f"Total repositories: {len(downloaded_repos)}")
    print(f"✅ Valid bundles: {len(results['valid'])}")
    print(f"❌ Invalid bundles: {len(results['invalid'])}")
    print(f"⚠️  Warnings detected: {sum(1 for v in results['failure_reasons'].values() if len(v) > 0)}")
    print(f"🔗 LFS-ready repos: {len(results['lfs_repos'])}")

    # Only show detailed error reports if there are invalid bundles
    if results["invalid"]:
        print("\nDetailed error report:")
        for repo_id in results["invalid"]:
            print(f"\n- {repo_id}")
            reasons = results["failure_reasons"].get(repo_id, [])
            if reasons:
                print("  Issues:")
                for reason in reasons:
                    print(f"  • {reason}")
            else:
                print("  • No specific error information captured")

    # Always show LFS summary, but only show full list if there are errors
    if results["lfs_repos"]:
        print("\n🔗 LFS Summary:")
        print(f"Total LFS-enabled repos: {len(results['lfs_repos'])}")
        print("Common LFS patterns:")
        pattern_counts = {}
        for repo_id in results["lfs_repos"]:
            meta_path = repo_manager.get_archive_path(repo_id) + ".meta.json"
            with open(meta_path) as f:
                patterns = json.load(f)["lfs_info"]["lfs_patterns"]
                for p in patterns:
                    pattern_counts[p] = pattern_counts.get(p, 0) + 1
        
        # Show top 5 most common patterns
        for pattern, count in sorted(pattern_counts.items(), key=lambda x: -x[1])[:5]:
            print(f"  {pattern}: {count} repos")
        
        # Show full repository list only if there were errors
        if results["invalid"]:
            print("\nFull LFS-Enabled Repositories:")
            for repo_id in results["lfs_repos"]:
                print(f"- {repo_id}")

if __name__ == "__main__":
    main() 