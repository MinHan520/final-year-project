#!/bin/bash
# init_aide_workspace.sh

echo "Initializing AIDE framework environment and directory architecture..."

# 1. Isolate the environment with the strict Python requirement
conda create -n aide_env python=3.10 -y
source $(conda info --base)/etc/profile.d/conda.sh
conda activate aide_env

# 2. Bind the specific PyTorch 2.0.1 distributions to CUDA 11.8
echo "Installing rigid PyTorch/CUDA dependencies..."
conda install pytorch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 pytorch-cuda=11.8 -c pytorch -c nvidia -y

# 3. Install auxiliary dependencies
echo "Installing auxiliary packages..."
pip install -r requirements.txt

# 4. Construct the hierarchical dataset and checkpoint directories
echo "Structuring the backend filesystem..."
mkdir -p dataset/progan/train/real
mkdir -p dataset/progan/train/fake
mkdir -p dataset/progan/eval/real
mkdir -p dataset/progan/eval/fake
mkdir -p pretrained_ckpts
mkdir -p results/progan_train

echo "Workspace initialization complete. Awaiting pre-trained weights."
