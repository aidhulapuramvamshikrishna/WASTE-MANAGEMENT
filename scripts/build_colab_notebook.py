"""Generate ml/notebooks/colab_train.ipynb for running model training on Google Colab."""

import json
from pathlib import Path

notebook = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "colab": {
            "provenance": [],
            "gpuType": "T4"
        },
        "kernelspec": {
            "name": "python3",
            "display_name": "Python 3"
        },
        "language_info": {
            "name": "python"
        },
        "accelerator": "GPU"
    },
    "cells": [
        {
            "cell_type": "markdown",
            "id": "m01_intro",
            "metadata": {},
            "source": [
                "# EcoSort: Cloud Model Training on Google Colab (NVIDIA T4 GPU)\n",
                "\n",
                "This notebook trains the EcoSort waste classification models on a Google Colab T4 GPU with CUDA acceleration and automatic mixed precision (AMP):\n",
                "1. **`wastenet`** (Custom 10-layer CNN from scratch, 3.4M params) — **Milestone 2 (COMPLETE)**\n",
                "2. **`mobilenet_v3`** (Two-phase transfer learning from ImageNet-1K) — **Milestone 3**\n",
                "3. **`efficientnet_b0`** (Two-phase transfer learning from ImageNet-1K) — **Milestone 3**\n",
                "\n",
                "---\n",
                "\n",
                "### Prerequisites in your Google Drive:\n",
                "Your Drive folder can be named **`EcoSport`** or **`EcoSort`** (auto-detected):\n",
                "1. `waste12_train.zip` and `waste12_valtest.zip` in your Drive folder.\n",
                "2. Upload fresh code archive **`ml.zip`** (built locally via `make ml-zip`).\n",
                "3. Runtime: **Runtime > Change runtime type > T4 GPU**."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "id": "c01_gpu_drive",
            "metadata": {},
            "outputs": [],
            "source": [
                "# 1. Verify GPU acceleration and mount Google Drive\n",
                "import torch\n",
                "print(\"PyTorch Version:\", torch.__version__)\n",
                "assert torch.cuda.is_available(), \"CRITICAL: No GPU detected! Go to Runtime > Change runtime type > T4 GPU.\"\n",
                "print(f\"CUDA Device: {torch.cuda.get_device_name(0)}\")\n",
                "\n",
                "from google.colab import drive\n",
                "drive.mount(\"/content/drive\")"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "id": "c02_extract_code",
            "metadata": {},
            "outputs": [],
            "source": [
                "# 2. Extract ml package and install dependencies without reinstalling PyTorch\n",
                "import glob\n",
                "import os\n",
                "import sys\n",
                "\n",
                "# Auto-detect Drive folder (EcoSport or EcoSort)\n",
                "ml_zips = glob.glob(\"/content/drive/**/ml.zip\", recursive=True)\n",
                "assert ml_zips, \"Could not find ml.zip in Google Drive!\"\n",
                "print(f\"Found ml.zip at: {ml_zips[0]}\")\n",
                "\n",
                "!cp \"{ml_zips[0]}\" /content/ml.zip\n",
                "!unzip -q -o /content/ml.zip -d /content/\n",
                "\n",
                "# Install requirements excluding torch/torchvision so Colab's CUDA PyTorch build is preserved\n",
                "%cd /content/ml\n",
                "!grep -vE '^(torch|torchvision)==' requirements.txt > /tmp/req.txt && pip install -r /tmp/req.txt\n",
                "!pip install -e . --no-deps\n",
                "\n",
                "if \"/content/ml/src\" not in sys.path:\n",
                "    sys.path.insert(0, \"/content/ml/src\")\n",
                "\n",
                "import wasteml\n",
                "import torch\n",
                "print(\"SUCCESS: wasteml installed successfully from:\", wasteml.__file__)\n",
                "print(\"CUDA Available:\", torch.cuda.is_available(), f\"({torch.cuda.get_device_name(0)})\")"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "id": "c03_extract_dataset",
            "metadata": {},
            "outputs": [],
            "source": [
                "# 3. Unpack dataset and verify split counts (13,266 / 2,842 / 2,843)\n",
                "import glob\n",
                "import os\n",
                "import sys\n",
                "\n",
                "%cd /content\n",
                "!mkdir -p /content/waste12\n",
                "\n",
                "train_zips = glob.glob(\"/content/drive/**/waste12_train.zip\", recursive=True)\n",
                "valtest_zips = glob.glob(\"/content/drive/**/waste12_valtest.zip\", recursive=True)\n",
                "assert train_zips, \"Could not find waste12_train.zip in Google Drive!\"\n",
                "assert valtest_zips, \"Could not find waste12_valtest.zip in Google Drive!\"\n",
                "\n",
                "!cp \"{train_zips[0]}\" /content/\n",
                "!cp \"{valtest_zips[0]}\" /content/\n",
                "\n",
                "!unzip -q -o /content/waste12_train.zip -d /content/waste12/\n",
                "!unzip -q -o /content/waste12_valtest.zip -d /content/waste12/\n",
                "\n",
                "if \"/content/ml/src\" not in sys.path:\n",
                "    sys.path.insert(0, \"/content/ml/src\")\n",
                "\n",
                "from wasteml.constants import CLASS_NAMES\n",
                "os.environ[\"WASTE_DATA_DIR\"] = \"/content/waste12\"\n",
                "\n",
                "train_counts = sum(len(os.listdir(f\"/content/waste12/train/{c}\")) for c in CLASS_NAMES)\n",
                "val_counts = sum(len(os.listdir(f\"/content/waste12/val/{c}\")) for c in CLASS_NAMES)\n",
                "test_counts = sum(len(os.listdir(f\"/content/waste12/test/{c}\")) for c in CLASS_NAMES)\n",
                "\n",
                "print(f\"Train images: {train_counts:,} (target 13,266)\")\n",
                "print(f\"Val images:   {val_counts:,} (target 2,842)\")\n",
                "print(f\"Test images:  {test_counts:,} (target 2,843)\")\n",
                "assert train_counts == 13266 and val_counts == 2842 and test_counts == 2843\n",
                "print(\"SUCCESS: Dataset verified with zero discrepancies.\")"
            ]
        },
        {
            "cell_type": "markdown",
            "id": "m04_m3_heading",
            "metadata": {},
            "source": [
                "## Milestone 3: Transfer Learning Models\n",
                "\n",
                "Two-phase fine-tuning:\n",
                "- **Phase 1 (Epochs 1–3)**: Backbone frozen (`requires_grad=False`, BN layers in `eval` mode). Train only the classifier head (`lr=1e-3`).\n",
                "- **Phase 2 (Epochs 4–25)**: Unfreeze everything with differential learning rates (backbone `lr=3e-5`, head `lr=3e-4`). Early stopping (patience 8) active.\n",
                "- Checkpoints and logs write directly to Google Drive live."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "id": "c05_train_mobilenet",
            "metadata": {},
            "outputs": [],
            "source": [
                "# 4. Train MobileNetV3 (Milestone 3)\n",
                "import glob\n",
                "import os\n",
                "\n",
                "%cd /content/ml\n",
                "os.environ[\"WASTE_DATA_DIR\"] = \"/content/waste12\"\n",
                "\n",
                "drive_folders = [d for d in glob.glob(\"/content/drive/MyDrive/Eco*\") if os.path.isdir(d)]\n",
                "drive_dir = drive_folders[0] if drive_folders else \"/content/drive/MyDrive/EcoSort\"\n",
                "artifacts_dir = f\"{drive_dir}/artifacts/mobilenet_v3\"\n",
                "os.makedirs(artifacts_dir, exist_ok=True)\n",
                "print(f\"Saving MobileNetV3 checkpoints to: {artifacts_dir}\")\n",
                "\n",
                "!python -m wasteml.train --config configs/mobilenet_v3.yaml --device cuda --artifacts-dir \"{artifacts_dir}\"\n",
                "\n",
                "zip_path = f\"{drive_dir}/artifacts_mobilenet_v3.zip\"\n",
                "!zip -r \"{zip_path}\" \"{artifacts_dir}\"\n",
                "print(f\"SUCCESS: MobileNetV3 complete! Saved to: {zip_path}\")"
            ]
        },
        {
            "cell_type": "markdown",
            "id": "m04_resume_mobilenet",
            "metadata": {},
            "source": [
                "### Resume MobileNetV3 (if disconnected)\n",
                "```bash\n",
                "%cd /content/ml\n",
                "os.environ[\"WASTE_DATA_DIR\"] = \"/content/waste12\"\n",
                "!python -m wasteml.train --config configs/mobilenet_v3.yaml --device cuda --resume --artifacts-dir \"{artifacts_dir}\"\n",
                "```"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "id": "c06_train_efficientnet",
            "metadata": {},
            "outputs": [],
            "source": [
                "# 5. Train EfficientNet-B0 (Milestone 3)\n",
                "import glob\n",
                "import os\n",
                "\n",
                "%cd /content/ml\n",
                "os.environ[\"WASTE_DATA_DIR\"] = \"/content/waste12\"\n",
                "\n",
                "drive_folders = [d for d in glob.glob(\"/content/drive/MyDrive/Eco*\") if os.path.isdir(d)]\n",
                "drive_dir = drive_folders[0] if drive_folders else \"/content/drive/MyDrive/EcoSort\"\n",
                "artifacts_dir = f\"{drive_dir}/artifacts/efficientnet_b0\"\n",
                "os.makedirs(artifacts_dir, exist_ok=True)\n",
                "print(f\"Saving EfficientNet-B0 checkpoints to: {artifacts_dir}\")\n",
                "\n",
                "!python -m wasteml.train --config configs/efficientnet_b0.yaml --device cuda --artifacts-dir \"{artifacts_dir}\"\n",
                "\n",
                "zip_path = f\"{drive_dir}/artifacts_efficientnet_b0.zip\"\n",
                "!zip -r \"{zip_path}\" \"{artifacts_dir}\"\n",
                "print(f\"SUCCESS: EfficientNet-B0 complete! Saved to: {zip_path}\")"
            ]
        },
        {
            "cell_type": "markdown",
            "id": "m05_resume_efficientnet",
            "metadata": {},
            "source": [
                "### Resume EfficientNet-B0 (if disconnected)\n",
                "```bash\n",
                "%cd /content/ml\n",
                "os.environ[\"WASTE_DATA_DIR\"] = \"/content/waste12\"\n",
                "!python -m wasteml.train --config configs/efficientnet_b0.yaml --device cuda --resume --artifacts-dir \"{artifacts_dir}\"\n",
                "```"
            ]
        }
    ]
}

out_path = Path("ml/notebooks/colab_train.ipynb")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1)
print(f"Generated {out_path} ({out_path.stat().st_size} bytes)")
