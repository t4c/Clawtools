#!/usr/bin/env bash

# ==============================================================================
# Local AI Image Generator - Linux Startup Script
# ==============================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/app/backend/linux"
FRONTEND_DIST="$ROOT_DIR/app/dist"

# Prüfe ob Setup ausgeführt wurde
if [ ! -d "$BACKEND_DIR" ] || [ ! -f "$FRONTEND_DIST/index.html" ]; then
    echo -e "${YELLOW}Das Projekt wurde noch nicht eingerichtet. Starte Setup...${NC}"
    "$ROOT_DIR/setup.sh"
fi

# CUDA Umgebungsvariablen setzen (falls vorhanden, um reibungslosen Ablauf zu sichern)
if command -v nvidia-smi &> /dev/null; then
    # Versuche nvcc oder Standardpfade zu finden und in PATH/LD_LIBRARY_PATH einzubinden
    CUDA_BIN=""
    if command -v nvcc &> /dev/null; then
        CUDA_BIN="$(dirname "$(command -v nvcc")")"
    else
        for path in /usr/local/cuda/bin /usr/local/cuda-13.3/bin /usr/local/cuda-12.*/bin /usr/local/cuda-11.*/bin; do
            if [ -x "$path/nvcc" ]; then
                CUDA_BIN="$path"
                break
            fi
        done
    fi
    
    if [ -n "$CUDA_BIN" ]; then
        export PATH="$CUDA_BIN:$PATH"
        if [ -d "$(dirname "$CUDA_BIN")/lib64" ]; then
            export LD_LIBRARY_PATH="$(dirname "$CUDA_BIN")/lib64:$LD_LIBRARY_PATH"
        fi
    fi
fi

echo -e "${GREEN}Starte Local AI Image Generator...${NC}"

# Startet den Server und versucht, den Standardbrowser zu öffnen
echo -e "Server läuft unter: ${CYAN}http://localhost:1420${NC}"

if command -v xdg-open &> /dev/null && [ -n "$DISPLAY" ]; then
    (sleep 1.5 && xdg-open "http://localhost:1420") &
elif command -v open &> /dev/null; then
    (sleep 1.5 && open "http://localhost:1420") &
fi

node "$ROOT_DIR/scripts/serve.cjs"
