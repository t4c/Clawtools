#!/usr/bin/env bash
set -e

DIR="/home/herpes/repos/Clawtools/local-ai-image-generator/app/models/components"
mkdir -p "$DIR"
cd "$DIR"

echo "=== [1/3] Downloading VAE ==="
curl -L -o ae.safetensors https://huggingface.co/ffxvs/vae-flux/resolve/main/ae.safetensors

echo "=== [2/3] Downloading CLIP-L ==="
curl -L -o clip_l.safetensors https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors

echo "=== [3/3] Downloading T5XXL ==="
curl -L -o t5-v1_1-xxl-encoder-Q8_0.gguf https://huggingface.co/city96/t5-v1_1-xxl-encoder-gguf/resolve/main/t5-v1_1-xxl-encoder-Q8_0.gguf

echo "=== All downloads completed successfully! ==="
