import subprocess
import os
from pathlib import Path
from typing import List

REPOS_DIR = "deepseek_storage/extracted"

def get_archive_format(path):
    """Detect archive format from file extension"""
    if str(path).endswith(".zip"):
        return "zip"
    for fmt in [".tar.gz", ".tar.bz2", ".tar"]:
        if str(path).endswith(fmt):
            return fmt[1:]  # Return without leading dot
    return None

def validate_repo(repo_path):
    """More comprehensive validation of extracted repository"""
    required_git_files = [
        "HEAD",
        "config",
        "description",
        "info/exclude"
    ]
    
    # Check basic git structure
    git_dir = repo_path / ".git"
    if not git_dir.exists():
        return False
        
    # Check critical git components
    checks = [
        (git_dir / "objects").exists(),
        (git_dir / "refs").exists(),
        any((git_dir / "hooks").iterdir())  # At least some hook samples
    ]
    
    # Check required files
    for f in required_git_files:
        if not (git_dir / f).exists():
            return False
            
    return all(checks)

def create_archive(repo_path, output_path):
    """Create self-contained Git bundle with LFS objects"""
    try:
        # Create main bundle
        main_bundle = output_path.with_suffix(".bundle")
        subprocess.run([
            "git", "-C", str(repo_path),
            "bundle", "create", str(main_bundle),
            "--all", "--tags"
        ], check=True)
        
        # Create LFS bundle with proper extension
        lfs_bundle = main_bundle.with_suffix(".bundle.lfs")
        subprocess.run([
            "git", "-C", str(repo_path),
            "lfs", "bundle", "create", str(lfs_bundle),
            "--all"
        ], check=True)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Archive creation failed: {str(e)}")
        return False

class RepoManager:
    def __init__(self):
        self.base_dir = "deepseek_storage"
        self.archives_dir = os.path.join(self.base_dir, "archives")
        self.extracted_dir = REPOS_DIR
        os.makedirs(self.archives_dir, exist_ok=True)
        os.makedirs(self.extracted_dir, exist_ok=True)

    def get_archive_path(self, repo_id: str) -> Path:
        """Get path for bundle file"""
        safe_name = repo_id.replace("/", "_") + ".bundle"
        return Path(self.archives_dir) / safe_name

    def get_downloaded_repos(self) -> List[str]:
        """Get list of downloaded repositories"""
        return [f.stem for f in Path(self.archives_dir).glob("*.bundle")]

    def get_extraction_path(self, repo_id: str) -> Path:
        safe_name = repo_id.replace("/", "_")
        return Path(self.extracted_dir) / safe_name 