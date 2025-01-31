# DeepSeek Repository Manager

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![HuggingFace](https://img.shields.io/badge/🤗-HuggingFace-yellow.svg)](https://huggingface.co/deepseek-ai)

A comprehensive tool for managing DeepSeek AI repositories from Hugging Face, including downloading, mirroring, verification, and local execution capabilities.

## 📑 Table of Contents

- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Core Scripts](#-core-scripts)
- [Usage Examples](#-usage-examples)
- [Advanced Operations](#-advanced-operations)
- [Troubleshooting](#-troubleshooting)

## ✨ Features

- **Repository Management**
  - Download repositories from Hugging Face
  - Mirror repositories to another account
  - Create efficient Git bundles
  - Selective repository extraction
  - Space-efficient storage
  
- **Verification & Maintenance**
  - Archive integrity verification
  - Repository size analysis
  - Bundle validation
  - LFS support verification
  
- **Model Execution**
  - Local model inference
  - Quantization support
  - Configurable parameters
  - Memory-efficient execution

## 🔧 Prerequisites

- Python 3.7+
- Git with LFS support
- Hugging Face account (for some operations)
- Sufficient storage space (varies by model)
- NVIDIA GPU (recommended for model execution)

## 📦 Installation

```bash
# Clone the repository
git clone <repository-url>
cd deepseek-manager

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m deepseek_manager.scripts.verify_archives
```

## 🛠️ Core Scripts

| Script | Description | Key Features |
|--------|-------------|--------------|
| `clean_hf_account.py` | Clean Hugging Face account | - Delete all repositories<br>- Selective deletion<br>- Safety confirmations |
| `download_repos.py` | Download repositories | - Parallel downloads<br>- Resume support<br>- Progress tracking |
| `mirror_repos.py` | Mirror repositories | - Account-to-account mirroring<br>- LFS handling<br>- Automatic cleanup |
| `extract_repos.py` | Extract repositories | - Selective extraction<br>- Validation checks<br>- LFS support |
| `repo_sizes.py` | Analyze repository sizes | - Size calculations<br>- Sorting options<br>- Human-readable output |
| `run_model.py` | Execute models | - Multiple quantization options<br>- Interactive mode<br>- Configuration options |
| `selective_extract.py` | Targeted extraction | - Repository selection<br>- Bundle verification<br>- Extraction validation |
| `verify_archives.py` | Verify archive integrity | - Bundle validation<br>- LFS checks<br>- Metadata verification |
| `verify_repos.py` | Repository verification | - Git integrity checks<br>- LFS validation<br>- Detailed reporting |

## 🚀 Usage Examples

### Basic Operations

```bash
# Download repositories
python -m deepseek_manager.scripts.download_repos

# Check repository sizes
python -m deepseek_manager.scripts.repo_sizes --sort desc --top 10

# Extract specific repository
python -m deepseek_manager.scripts.selective_extract deepseek-ai/deepseek-coder-1.3b-instruct

# Run a model
python -m deepseek_manager.scripts.run_model --model deepseek-coder-1.3b-instruct --quant 4bit
```

### Account Management

```bash
# Clean Hugging Face account
python -m deepseek_manager.scripts.clean_hf_account --target-user YOUR_USERNAME --hf-token YOUR_TOKEN

# Mirror repositories
python -m deepseek_manager.scripts.mirror_repos --target-user TARGET_USER --hf-token YOUR_TOKEN
```

### Verification Operations

```bash
# Verify all archives
python -m deepseek_manager.scripts.verify_archives

# Check repository integrity
python -m deepseek_manager.scripts.verify_repos

# Analyze repository sizes
python -m deepseek_manager.scripts.repo_sizes --sort desc
```

## 🔄 Advanced Operations

### Custom Download Options

```bash
# Download with specific workers
python -m deepseek_manager.scripts.download_repos --workers 4

# Download specific repositories
python -m deepseek_manager.scripts.download_repos --repo deepseek-ai/deepseek-coder-1.3b-instruct

# Force re-download
python -m deepseek_manager.scripts.download_repos --force
```

### Model Execution Options

```bash
# Run with 4-bit quantization
python -m deepseek_manager.scripts.run_model --quant 4bit --max-tokens 500

# Run with 8-bit quantization
python -m deepseek_manager.scripts.run_model --quant 8bit --temperature 0.7

# Run without quantization
python -m deepseek_manager.scripts.run_model --quant none
```

## 🔍 Troubleshooting

### Common Issues

1. **Permission Errors**
   ```bash
   # Fix permissions
   chmod -R u+w deepseek_storage/
   ```

2. **LFS Issues**
   ```bash
   # Reinitialize LFS
   git lfs install
   git lfs pull
   ```

3. **Space Issues**
   ```bash
   # Check sizes before downloading
   python -m deepseek_manager.scripts.repo_sizes --sort desc
   ```

### Error Messages

- `Repository not found`: Check if the repository ID is correct
- `LFS not initialized`: Run `git lfs install` first
- `Invalid bundle`: Try re-downloading the repository
- `Insufficient space`: Free up space or use selective download

## 📝 Notes

- Always verify archives after downloading
- Use quantization for large models on limited hardware
- Keep sufficient free space for extraction operations
- Regular verification helps maintain repository health

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 