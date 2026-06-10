#!/usr/bin/env bash

# ==============================================================================
# Local AI Image Generator - Linux Setup Script
# ==============================================================================
set -e

# Farb-Definitionen für sauberes Terminal-Feedback
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=== Local AI Image Generator - Linux First-Time Setup ===${NC}"
echo -e "Dieses Script bereitet die portable Node.js/Frontend-Umgebung vor und kompiliert die C++ Backends.\n"

# ── Prerequisite Checks ───────────────────────────────────────────────────────
echo -e "${YELLOW}[1/4] Prüfe Systemvoraussetzungen...${NC}"

# 1. CMake
if ! command -v cmake &> /dev/null; then
    echo -e "${RED}Fehler: 'cmake' ist nicht installiert.${NC}"
    echo -e "Bitte installiere cmake über deinen Paketmanager (z.B. 'sudo apt install cmake')."
    exit 1
fi

# 2. C++ Compiler
if ! command -v g++ &> /dev/null && ! command -v clang++ &> /dev/null; then
    echo -e "${RED}Fehler: Kein C++ Compiler (g++ oder clang++) gefunden.${NC}"
    echo -e "Bitte installiere build-essential (z.B. 'sudo apt install build-essential')."
    exit 1
fi

# 3. Node.js & NPM
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    echo -e "${RED}Fehler: 'node' oder 'npm' nicht im PATH gefunden.${NC}"
    echo -e "Bitte installiere Node.js (v18+) und NPM."
    exit 1
fi

echo -e "${GREEN}Prerequisites erfüllt! C++ Compiler, CMake und Node.js sind vorhanden.${NC}"

# ── Prepare Backend Folder ────────────────────────────────────────────────────
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/app/backend/linux"
SRC_DIR="$ROOT_DIR/app/backend/stable-diffusion.cpp-src"

mkdir -p "$BACKEND_DIR"

# ── Download stable-diffusion.cpp ─────────────────────────────────────────────
echo -e "\n${YELLOW}[2/4] Klone stable-diffusion.cpp (master-669-2d40a8b)...${NC}"
if [ ! -d "$SRC_DIR" ]; then
    echo -e "Klone Source-Repository..."
    git clone --depth 1 --branch master-669-2d40a8b https://github.com/leejet/stable-diffusion.cpp.git "$SRC_DIR"
    cd "$SRC_DIR"
    echo -e "Aktualisiere Git-Submodule (ggml, libwebp, libwebm)..."
    git submodule update --init --recursive --depth 1
else
    echo -e "${GREEN}Source-Repository existiert bereits in: $SRC_DIR${NC}"
    cd "$SRC_DIR"
fi

# ── Compiling Backends ────────────────────────────────────────────────────────
echo -e "\n${YELLOW}[3/4] Kompiliere stable-diffusion.cpp Backends...${NC}"

# CUDA Erkennung
HAS_NVIDIA=false
if command -v nvidia-smi &> /dev/null; then
    HAS_NVIDIA=true
fi

# CUDA Toolkit Pfad-Ermittlung
CUDA_BIN_PATH=""
if $HAS_NVIDIA; then
    if command -v nvcc &> /dev/null; then
        CUDA_BIN_PATH="$(dirname "$(command -v nvcc")")"
    else
        # Suche an Standardpfaden
        for path in /usr/local/cuda/bin /usr/local/cuda-13.3/bin /usr/local/cuda-12.*/bin /usr/local/cuda-11.*/bin; do
            if [ -x "$path/nvcc" ]; then
                CUDA_BIN_PATH="$path"
                break
            fi
        done
    fi
fi

# 1. CUDA Backend Kompilierung
if [ -n "$CUDA_BIN_PATH" ]; then
    echo -e "${GREEN}NVIDIA GPU und CUDA Toolkit in '$CUDA_BIN_PATH' erkannt!${NC}"
    echo -e "Kompiliere hocheffizientes CUDA-Backend..."
    
    export PATH="$CUDA_BIN_PATH:$PATH"
    if [ -d "$(dirname "$CUDA_BIN_PATH")/lib64" ]; then
        export LD_LIBRARY_PATH="$(dirname "$CUDA_BIN_PATH")/lib64:$LD_LIBRARY_PATH"
    fi

    # CMake Konfiguration & Build
    cmake -B build-cuda -DSD_CUDA=ON -DCMAKE_BUILD_TYPE=Release
    cmake --build build-cuda --config Release -j$(nproc)

    if [ -f "build-cuda/bin/sd-server" ]; then
        cp build-cuda/bin/sd-server "$BACKEND_DIR/sd-cuda"
        echo -e "${GREEN}CUDA-Backend erfolgreich kompiliert und installiert!${NC}"
    else
        echo -e "${RED}CUDA-Kompilierung fehlgeschlagen. sd-server Binary wurde nicht erstellt.${NC}"
    fi
else
    echo -e "${YELLOW}Kein CUDA Toolkit oder nvidia-smi gefunden. CUDA-Backend wird übersprungen.${NC}"
fi

# 2. Vulkan Backend Kompilierung (Fallback / AMD / Intel / Generic)
echo -e "\nVersuche Vulkan-Backend zu kompilieren..."
if cmake -B build-vulkan -DSD_VULKAN=ON -DCMAKE_BUILD_TYPE=Release &> /dev/null; then
    if cmake --build build-vulkan --config Release -j$(nproc); then
        if [ -f "build-vulkan/bin/sd-server" ]; then
            cp build-vulkan/bin/sd-server "$BACKEND_DIR/sd-vulkan"
            echo -e "${GREEN}Vulkan-Backend erfolgreich kompiliert und installiert!${NC}"
        fi
    else
        echo -e "${YELLOW}Vulkan Compilation fehlgeschlagen (Fehlende Bibliotheken oder Shader-Compiler).${NC}"
    fi
else
    echo -e "${YELLOW}Vulkan Header oder Vulkan-SDK nicht gefunden. Vulkan-Backend übersprungen.${NC}"
fi

# Falls absolut kein GPU-Backend gebaut wurde, warnen
if [ ! -f "$BACKEND_DIR/sd-cuda" ] && [ ! -f "$BACKEND_DIR/sd-vulkan" ]; then
    echo -e "${RED}Warnung: Weder CUDA- noch Vulkan-Backend konnten kompiliert werden.${NC}"
    echo -e "Die Anwendung wird standardmäßig auf ein CPU-Fallback ausweichen."
fi

# ── Frontend Build ────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}[4/4] Baue React-Frontend...${NC}"
cd "$ROOT_DIR/app/frontend"
npm install
npm run build

echo -e "\n${GREEN}=== Setup erfolgreich abgeschlossen! ===${NC}"
echo -e "Du kannst das Projekt jetzt über das Start-Script starten."
echo -e "Führe dazu aus: ${CYAN}./start.sh${NC}"
