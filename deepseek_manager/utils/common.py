import os
import hashlib
from typing import List, Dict

class RepoManager:
    def __init__(self, base_dir: str = "deepseek_storage"):
        self.base_dir = os.path.abspath(base_dir)
        self.archives_dir = os.path.join(self.base_dir, "archives")
        self.extracted_dir = os.path.join(self.base_dir, "extracted")
        self.create_directories()

    def create_directories(self):
        """Create necessary directories if they don't exist."""
        os.makedirs(self.archives_dir, exist_ok=True)
        os.makedirs(self.extracted_dir, exist_ok=True)

    def get_archive_path(self, repo_id: str) -> str:
        """Windows-safe path for repository bundles"""
        filename = repo_id.replace('/', '_') + '.bundle'
        return os.path.normpath(os.path.join(self.archives_dir, filename))

    def get_extraction_path(self, repo_id: str) -> str:
        """Windows-safe extraction path"""
        dirname = repo_id.replace('/', '_')
        return os.path.normpath(os.path.join(self.extracted_dir, dirname))

    def calculate_file_hash(self, filepath: str) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def get_downloaded_repos(self) -> List[str]:
        """Get list of downloaded repository bundles"""
        if not os.path.exists(self.archives_dir):
            return []
        return [f.replace('.bundle', '').replace('_', '/') 
                for f in os.listdir(self.archives_dir) 
                if f.endswith('.bundle')]

    def get_extracted_repos(self) -> List[str]:
        """Get list of extracted repositories."""
        if not os.path.exists(self.extracted_dir):
            return []
        return [d.replace('_', '/') 
                for d in os.listdir(self.extracted_dir)
                if os.path.isdir(os.path.join(self.extracted_dir, d))]

    def estimate_repo_size(self, repo_id: str) -> float:
        """Estimate repository size using Hugging Face API"""
        try:
            from huggingface_hub import HfApi
            api = HfApi()
            model_info = api.model_info(repo_id)
            return model_info.safetensors or model_info.size
        except:
            return 0.0  # Fallback if API call fails 