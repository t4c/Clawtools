#!/usr/bin/env bash

# ==============================================================================
# Local AI Image Generator - Linux Setup Script
# ==============================================================================
set -e

# Color definitions for clean terminal feedback
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=== Local AI Image Generator - Linux First-Time Setup ===${NC}"
echo -e "This script prepares the Node.js/frontend environment and compiles the C++ backends.\n"

# ── Prerequisite Checks ───────────────────────────────────────────────────────
echo -e "${YELLOW}[1/4] Checking system prerequisites...${NC}"

# 1. CMake
if ! command -v cmake &> /dev/null; then
    echo -e "${RED}Error: 'cmake' is not installed.${NC}"
    echo -e "Please install cmake via your package manager (e.g. 'sudo apt install cmake')."
    exit 1
fi

# 2. C++ Compiler
if ! command -v g++ &> /dev/null && ! command -v clang++ &> /dev/null; then
    echo -e "${RED}Error: No C++ compiler (g++ or clang++) found.${NC}"
    echo -e "Please install build-essential (e.g. 'sudo apt install build-essential')."
    exit 1
fi

# 3. Node.js & NPM
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: 'node' or 'npm' not found in PATH.${NC}"
    echo -e "Please install Node.js (v18+) and NPM."
    exit 1
fi

echo -e "${GREEN}Prerequisites met! C++ compiler, CMake, and Node.js are available.${NC}"

# ── Prepare Backend Folder ────────────────────────────────────────────────────
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/app/backend/linux"
SRC_DIR="$ROOT_DIR/app/backend/stable-diffusion.cpp-src"

mkdir -p "$BACKEND_DIR"

# ── Download stable-diffusion.cpp ─────────────────────────────────────────────
echo -e "\n${YELLOW}[2/4] Cloning stable-diffusion.cpp (master-669-2d40a8b)...${NC}"
if [ ! -d "$SRC_DIR" ]; then
    echo -e "Cloning source repository..."
    git clone --depth 1 --branch master-669-2d40a8b https://github.com/leejet/stable-diffusion.cpp.git "$SRC_DIR"
    cd "$SRC_DIR"
    echo -e "Updating git submodules (ggml, libwebp, libwebm)..."
    git submodule update --init --recursive --depth 1
else
    echo -e "${GREEN}Source repository already exists at: $SRC_DIR${NC}"
    cd "$SRC_DIR"
fi

# ── Compiling Backends ────────────────────────────────────────────────────────
echo -e "\n${YELLOW}[3/4] Compiling stable-diffusion.cpp backends...${NC}"

# CUDA Detection
HAS_NVIDIA=false
if command -v nvidia-smi &> /dev/null; then
    HAS_NVIDIA=true
fi

# CUDA Toolkit Path Discovery
CUDA_BIN_PATH=""
if $HAS_NVIDIA; then
    if command -v nvcc &> /dev/null; then
        CUDA_BIN_PATH="$(dirname "$(command -v nvcc)")"
    else
        # Search in default paths
        for path in /usr/local/cuda/bin /usr/local/cuda-13.3/bin /usr/local/cuda-12.*/bin /usr/local/cuda-11.*/bin; do
            if [ -x "$path/nvcc" ]; then
                CUDA_BIN_PATH="$path"
                break
            fi
        done
    fi
fi

# 1. CUDA Backend Compilation
if [ -n "$CUDA_BIN_PATH" ]; then
    echo -e "${GREEN}NVIDIA GPU and CUDA Toolkit detected in '$CUDA_BIN_PATH'!${NC}"
    echo -e "Compiling high-performance CUDA backend..."
    
    export PATH="$CUDA_BIN_PATH:$PATH"
    if [ -d "$(dirname "$CUDA_BIN_PATH")/lib64" ]; then
        export LD_LIBRARY_PATH="$(dirname "$CUDA_BIN_PATH")/lib64:$LD_LIBRARY_PATH"
    fi

    # CMake Configuration & Build
    cmake -B build-cuda -DSD_CUDA=ON -DCMAKE_BUILD_TYPE=Release
    cmake --build build-cuda --config Release -j$(nproc)

    if [ -f "build-cuda/bin/sd-server" ]; then
        cp build-cuda/bin/sd-server "$BACKEND_DIR/sd-cuda"
        echo -e "${GREEN}CUDA backend successfully compiled and installed!${NC}"
    else
        echo -e "${RED}CUDA compilation failed. sd-server binary was not created.${NC}"
    fi
else
    echo -e "${YELLOW}No CUDA Toolkit or nvidia-smi found. Skipping CUDA backend.${NC}"
fi

# 2. Vulkan Backend Compilation (Fallback / AMD / Intel / Generic)
echo -e "\nAttempting to compile Vulkan backend..."
if cmake -B build-vulkan -DSD_VULKAN=ON -DCMAKE_BUILD_TYPE=Release &> /dev/null; then
    if cmake --build build-vulkan --config Release -j$(nproc); then
        if [ -f "build-vulkan/bin/sd-server" ]; then
            cp build-vulkan/bin/sd-server "$BACKEND_DIR/sd-vulkan"
            echo -e "${GREEN}Vulkan backend successfully compiled and installed!${NC}"
        fi
    else
        echo -e "${YELLOW}Vulkan compilation failed (missing libraries or shader compiler).${NC}"
    fi
else
    echo -e "${YELLOW}Vulkan headers or Vulkan-SDK not found. Skipping Vulkan backend.${NC}"
fi

# Warn if absolutely no GPU backend was compiled
if [ ! -f "$BACKEND_DIR/sd-cuda" ] && [ ! -f "$BACKEND_DIR/sd-vulkan" ]; then
    echo -e "${RED}Warning: Neither CUDA nor Vulkan backend could be compiled.${NC}"
    echo -e "The application will default to CPU fallback mode."
fi

# ── Frontend Build ────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}[4/4] Building React frontend...${NC}"
cd "$ROOT_DIR/app/frontend"
npm install
npm run build

echo -e "\n${GREEN}=== Setup successfully completed! ===${NC}"
echo -e "You can now start the project using the startup script."
echo -e "To do so, run: ${CYAN}./start.sh${NC}"
