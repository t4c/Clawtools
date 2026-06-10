# 🖼️ Local AI Image Generator (Linux CUDA Fork)

### A ridiculously fast, purely local Stable Diffusion GUI running directly on C++. No Python bloat, no Anaconda nonsense, no Windows tears. Just raw C++ powering your Linux GPU.

---

> 🐧 **Note on this Fork:** This repository is a native Linux-only fork of the original Windows-centric [techjarves/Local-AI-Image-Generator](https://github.com/techjarves/Local-AI-Image-Generator).


---

## 🖤 Why this Fork?
The original codebase was a Windows slave. We brought out the whip and domesticated it for Linux:
*   **100% Native Linux:** No Wine, no WSL gymnastics.
*   **Automated CUDA Compilation:** If you have an Nvidia card, `./setup.sh` automatically compiles `stable-diffusion.cpp` with native CUDA acceleration on first run.
*   **True LAN Party Capabilities:** The server listens on `0.0.0.0` and the React frontend dynamically grabs the API route via `window.location.hostname`. You can let your heavy GPU sweat in the basement while generating images.

---

## ⚡ Setup & Start

### 1. Install Dependencies
You'll need the usual tools for some hot C++ action. On Debian/Ubuntu-based systems:
```bash
sudo apt update
sudo apt install build-essential cmake nodejs npm
# And of course, a working CUDA Toolkit (nvcc must be in your PATH!)
```

### 2. Clone & Start
Let the script do the dirty work:
```bash
chmod +x start.sh setup.sh
./start.sh
```
The script verifies your CUDA environment, clones and compiles `stable-diffusion.cpp` in the background, builds the frontend, and boots up the web server.

### 3. Feed the Models
We support `.safetensors` and `.gguf` weights (SD 1.5, SDXL, etc.).
*   Just drop your weights into `app/models/`
*   Or use the integrated **Model Manager** in the Web UI to download models directly via Hugging Face URLs.

### 4. Multi-File Models (Flux / Hunyuan / Qwen / Wan etc.)
For multi-file models like Flux (e.g. `flux1-dev-Q5_0.gguf`), the raw weights are not enough. The backend requires separate components like VAE and Text-Encoders.
Simply place them into the folder `app/models/components/`:
*   **VAE / Autoencoder:** `ae.safetensors` (or `ae.gguf`)
*   **CLIP-L Text-Encoder:** `clip_l.safetensors` (or `clip_l-f16.gguf`)
*   **T5XXL Text-Encoder:** `t5xxl.safetensors` (e.g. the high-performance `t5xxl_q8_0.gguf` version)

Once these files are present, the system will automatically detect them when loading a Flux model and start the C++ server with the correct `--diffusion-model`, `--clip_l`, `--t5xxl`, and `--vae` flags.

### 5. Have Fun
Open your browser at:
`http://localhost:1420` (or your Linux server's IP within the LAN)

---

## 📁 Storage Structure
```
local-ai-image-generator/
├── start.sh                   # Main Linux entry point
├── setup.sh                   # Fresh & crisp backend compilation
├── scripts/
│   └── serve.cjs              # Static Node.js file & process manager
└── app/
    ├── frontend/              # React Frontend (Vite)
    ├── models/                # Where your models sleep (.safetensors, .gguf)
    └── outputs/               # Where the hot results land (.png & .json Metadata)
```

---

## 🍆 Performance & VRAM Appetite
Since we build directly on top of C++ (`stable-diffusion.cpp`), VRAM consumption is kept strictly on a leash.
*   **CUDA GPU (e.g., RTX 3060):** Generates a 512x512 image (20 steps) in about **10 seconds**.
*   **CPU Fallback:** If you don't have a GPU (why do you even do this to yourself?), it will run painfully slow on CPU cores. Get CUDA.

---

## 🛡️ License
This repository is licensed under the MIT License. It uses [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) as its backend.
