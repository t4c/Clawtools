# 🖼️ Local AI Image Generator (Linux CUDA Fork)

### Ein unverschämt schneller, rein lokaler Stable Diffusion GUI, der direkt auf C++ läuft. Kein Python-Bloat, kein Anaconda-Dreck, keine Windows-Tränen. Nur nacktes C++ auf deiner Linux-GPU.

---

> 🐧 **WARNUNG:** Dieser Fork ist **NUR FÜR LINUX**. Der Windows-Support wurde eiskalt wegrationalisiert, weil wir keine Lust auf Registry-Geficke und veraltete PowerShell-Skripte hatten. Wer Windows nutzen will, soll beim originalen Windows-Repo betteln gehen. Hier regiert Pinguin-Power mit automatischer CUDA-Kompilierung.

---

## 🖤 Warum dieser Fork?
Der originale Code war ein Windows-Knecht. Wir haben die Peitsche ausgepackt und das Projekt für Linux domestiziert:
*   **100% Linux native:** Kein Wine, kein WSL-Gefriemel.
*   **Automatische CUDA-Kompilierung:** Wenn du Nvidia auf der Kiste hast, kompiliert `./setup.sh` beim ersten Start vollautomatisch `stable-diffusion.cpp` mit nativer CUDA-Beschleunigung.
*   **Echte LAN-Party-Tauglichkeit:** Der Server lauscht auf `0.0.0.0` und das React-Frontend zieht sich die API-Route dynamisch via `window.location.hostname`. Du kannst deine dicke GPU im Keller glühen lassen, während du im Bett auf dem Handy heiße Bilder generierst.

---

## ⚡ Setup & Start

### 1. Abhängigkeiten installieren
Du brauchst die üblichen Werkzeuge für heiße C++ Action. Unter Debian/Ubuntu-basierten Systemen:
```bash
sudo apt update
sudo apt install build-essential cmake nodejs npm
# Und natürlich ein funktionierendes CUDA-Toolkit (nvcc muss im PATH sein!)
```

### 2. Klonen & Starten
Lass das Skript die Drecksarbeit machen:
```bash
chmod +x start.sh setup.sh
./start.sh
```
Das Skript prüft deine CUDA-Umgebung, klont und kompiliert `stable-diffusion.cpp` im Hintergrund, baut das Frontend und startet den Webserver.

### 3. Modelle füttern
Wir unterstützen `.safetensors` und `.gguf` (SD 1.5, SDXL etc.).
*   Wirf deine Gewichte einfach nach `app/models/`
*   Oder nutze den integrierten **Model Manager** im Web-UI, um Modelle direkt via Hugging Face URL runterzuladen.

### 4. Spaß haben
Öffne deinen Browser unter:
`http://localhost:1420` (oder die IP deines Linux-Servers im LAN)

---

## 📁 Struktur des Lagers
```
local-ai-image-generator/
├── start.sh                   # Der Haupt-Einstiegspunkt für Linux
├── setup.sh                   # Kompiliert das Backend frisch & knackig
├── scripts/
│   └── serve.cjs              # Der static Node.js File- & Prozess-Manager
└── app/
    ├── frontend/              # React-Frontend (Vite)
    ├── models/                # Hier schlafen deine Modelle (.safetensors, .gguf)
    └── outputs/               # Hier landen die heißen Ergebnisse (.png & .json Metadata)
```

---

## 🍆 Performance & VRAM-Hunger
Da wir direkt auf C++ (`stable-diffusion.cpp`) aufbauen, ist der VRAM-Verbrauch extrem gezügelt. 
*   **CUDA GPU (z.B. RTX 3060):** Generiert ein 512x512 Bild (20 Steps) in ca. **10 Sekunden**.
*   **CPU-Fallback:** Wenn du keine GPU hast (oder deine Treiber nicht befriedigt hast), läuft es elendig langsam auf den CPU-Kernen. Also besorg dir CUDA.

---

## 🛡️ Lizenz
Dieses Repository ist unter der MIT-Lizenz lizenziert. Es nutzt [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) als Backend.
