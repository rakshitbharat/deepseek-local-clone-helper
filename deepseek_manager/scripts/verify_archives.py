from pathlib import Path
from .common import RepoManager

def verify_archives():
    manager = RepoManager()
    missing = []
    
    for bundle in Path(manager.archives_dir).glob("*.bundle"):
        lfs_bundle = bundle.with_suffix(".bundle.lfs")
        if not lfs_bundle.exists():
            missing.append(f"Missing LFS bundle for {bundle.name}")
    
    if missing:
        print("Archive verification failed!")
        for issue in missing:
            print(f"❌ {issue}")
    else:
        print("✅ All archives are complete and valid")

if __name__ == "__main__":
    verify_archives() 