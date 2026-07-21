# 🎮 LangForge

**AI-Powered Game Screenshot Translation Tool for Windows**

Capture your game screen · AI translates the text · Result overlays directly on the image  
Play any foreign-language game. Read everything. No interruptions.

[![Version](https://img.shields.io/badge/Version-V1.5.1-blue?style=flat-square)](https://github.com/toyakyo/LangForge/releases) [![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=flat-square&logo=windows)](https://github.com/toyakyo/LangForge) [![Open Source](https://img.shields.io/badge/Open%20Source-GitHub-333?style=flat-square&logo=github)](https://github.com/toyakyo/LangForge) [![Ko-fi](https://img.shields.io/badge/Support-Ko--fi-ff5f5f?style=flat-square&logo=ko-fi)](https://ko-fi.com/toyakyo) [![Patreon](https://img.shields.io/badge/Support-Patreon-orange?style=flat-square&logo=patreon)](https://www.patreon.com/cw/LangForge)

[📥 Download](https://goonsoft.tw2.nde.tw/tutorial/tutorial.php#download) • [📖 Documentation](https://goonsoft.tw2.nde.tw/tutorial/tutorial.php) • [💬 Community](https://www.facebook.com/groups/2150940378645437) • [☕ Ko-fi](https://ko-fi.com/toyakyo) • [💜 Patreon](https://www.patreon.com/cw/LangForge)

---

## 🌟 What is LangForge?

LangForge is an open-source AI-assisted game translation tool for Windows. It automatically detects your game window, captures the screen, and translates on-screen foreign text using your choice of AI engine — overlaying the result directly on the screenshot, positioned where the original text was.

Designed for players who want to enjoy Japanese, Korean, or any foreign-language game without switching windows or pausing to look things up.

> ⚠️ LangForge is under active development. Features and UI may change between versions.

---

## 🔥 Three Translation Modes

### 🔍 Local OCR + Google Translate — Zero Setup, Zero Cost

No API key. No account. No configuration whatsoever.  
LangForge uses **EasyOCR** locally to detect and position text, then routes through **Google Translate** (free, no quota limits) for the actual translation.  
**→ Best for: first-time users, or anyone who doesn't want to create API accounts.**

### 🦙 OLLAMA Local Engine — Full Offline AI

Runs entirely on your own machine. No internet after setup, no API costs, no data leaves your device.  
Requires installing [OLLAMA](https://ollama.com) and a vision-capable model (e.g. `llava`). A dedicated GPU is recommended.  
**→ Best for: privacy-focused users with decent hardware.**

### ☁️ Cloud Engines — Best Translation Quality

Supports **10 mainstream AI engines** including Gemini, Groq, Mistral (free tiers available) and OpenAI, Claude, Grok, HuggingFace, Together AI, Cerebras, NVIDIA NIM.  
LangForge automatically rotates engines when a free quota runs out — keeping translation running uninterrupted.  
**→ Best for: users who want the highest translation accuracy.**

---

## ✨ Features

| Feature | Description |
| --- | --- |
| 🖼️ **Overlay Translation** | Translated text positioned directly on the game screenshot |
| 🌐 **Multi-Language Output** | Japanese, English, Korean, French, German, Spanish, Italian, Portuguese, Russian, and more |
| 📐 **Horizontal / Vertical Layout** | Supports both Western (L→R) and Japanese-style (top→bottom, R→L) text direction |
| 🔤 **Auto Font Matching** | Overlay font auto-selected based on target language (JP, KR, RU, etc.) |
| 📋 **AI Walkthrough Analysis** | 3–5 actionable hints based on the current game screen |
| ⚡ **Auto-Capture** | Detects scene stability and triggers translation automatically |
| ⌨️ **Global Hotkeys** | Trigger translation or walkthrough without leaving your game |
| 🎬 **Session Recording** | Records your play session with playback and live delay mode |
| 🗂️ **Translation History** | SQLite-backed records with screenshot, organized by game and platform |
| 🔐 **Encrypted API Keys** | Keys encrypted with your machine ID (XOR + base64) before saving locally |
| 🖱️ **Click-to-Select Window** | Click directly on your game window to set it as target |
| 📟 **Simple Mode (Tab 7)** | Streamlined local-engine interface — pick your OLLAMA model and translate instantly |
| 🌗 **Dark / Light Theme** | Toggle UI theme from the View menu |
| 🌍 **Bilingual UI** | Supports 繁體中文 and English, toggle anytime from the menu |
| 🔄 **Auto Engine Rotation** | Automatically switches to the next available engine when free quota runs out |
| 📊 **Quota Dashboard** | Real-time view of today's usage per model, with RPM and RPD tracking |
| 🛠️ **Platform Editor** | Add, rename, or remove game platforms and emulators directly in the UI |
| 🔀 **One-Click Mode Switch** | Toggle between Advanced and Simple Mode instantly from the menu bar |

---

## 🚀 Getting Started

### Option A — Zero Setup (Recommended for First-Time Users)

1. Download and run `LangForge.exe`
2. Select **🔍 Local OCR + Google Translate** as your engine
3. Set your target game window title in the **Capture** tab
4. Click **Capture & Translate** — done!

> No API key needed. No account required.

### Option B — Cloud Engine (Best Quality, Free)

1. Get a free **Gemini API Key** from [aistudio.google.com](https://aistudio.google.com/apikey) (Google account required, no credit card)
2. Run LangForge, select **☁ Cloud Engine → Gemini**
3. Paste your key and start translating

> For maximum free quota, also set up [Groq](https://console.groq.com/keys), [Mistral](https://console.mistral.ai/), [Together AI](https://api.together.xyz/settings/api-keys) and [Cerebras](https://cloud.cerebras.ai/) — LangForge rotates them automatically.

### Option C — Fully Offline (OLLAMA)

1. Install [OLLAMA](https://ollama.com)
2. Run `ollama pull llava` to download a vision model
3. Start with `ollama serve`
4. In LangForge, select **🦙 Local Engine (OLLAMA)**

> **New in V1.5:** Use **Simple Mode (Tab 7)** for a streamlined OLLAMA experience — no API key, minimal setup.

### Option D — Running from Source

```bash
git clone https://github.com/toyakyo/LangForge.git
cd LangForge
pip install anthropic easyocr google-genai groq keyboard mistralai numpy openai pillow pywin32
python LangForge.py
```

---

## 📋 Supported AI Engines

| Engine | Recommended Model | Free Daily Quota | Notes |
| --- | --- | --- | --- |
| **Gemini** | gemini-3-flash | 500 RPD | New-gen Flash, recommended |
| **Gemini** | gemini-2.5-flash | 20 RPD | Stable, strong vision |
| **Groq** | qwen/qwen3.6-27b | 1,000 RPD | Multimodal, fast |
| **Mistral** | mistral-small-latest | 500 RPD | Vision support |
| **HuggingFace** | Llama-3.2-11B-Vision | Free tier | Open-source vision models |
| **Together AI** | Llama-Vision-Free | Unlimited (free) | Permanently free vision model |
| **Cerebras** | gemma-4-31b | ~2,100 RPD | 1,800+ tok/s, ultra fast |
| **NVIDIA NIM** | llama-3.2-11b-vision | Free credits | Enterprise-grade inference |
| **OpenAI** | gpt-4.1-mini / gpt-4.1 / gpt-4o | Paid | Most stable quality |
| **Claude** | Haiku / Sonnet / Opus | Paid | Strong semantic understanding |
| **Grok** | grok-2-vision-1212 / grok-4 | Paid | xAI flagship multimodal |
| **🦙 OLLAMA** | Any vision model | Unlimited (local) | Fully offline, no API key |
| **🔍 OCR + Google** | EasyOCR + Google Translate | Unlimited (free) | Zero setup required |

> ⚠️ Free quota numbers are subject to change. Check each provider's official announcements for the latest limits.

---

## 🔐 Security & Transparency

LangForge is verified using **Microsoft Process Monitor (Sysinternals)**.

The application makes **only the API calls required for translation** — to the AI engine you have selected. No data is sent to any developer-controlled server.

- ✅ API Keys stored locally in `configs.json`, encrypted with your machine ID
- ✅ No upload of screenshots or personal data
- ✅ No connection to developer servers
- ✅ No remote license verification
- ✅ SHA256 checksum published for every release
- ✅ Full source code available for inspection

**File Integrity Verification**

| Release | File | SHA256 |
| --- | --- | --- |
| V1.5.1 | `LangForge.exe` | `EFE1E645BF88CB359B0D48BD4E29DDDABF157FABCC433D3AF5C359B123B6B793` |
| V1.5 | `LangForge.exe` | `AC62B71FADE75FD6E06DFA228E9E2E1759ACD65252E14A9A80BD52BB96FEA083` |
| V1.1.1 | `LangForge.exe` | `1E9DF0E89E91E9D799E56049E7F5FBA5D08C36E6706F4140F38E38413697FE80` |

```powershell
# Verify in PowerShell
Get-FileHash .\LangForge.exe -Algorithm SHA256
```

> If the hash does not match, do **not** run the file. Re-download from the official page.

---

## 🛠️ Requirements

| Item | Requirement |
| --- | --- |
| OS | Windows 10 / 11 (64-bit recommended) |
| Network | Required for cloud engines; OLLAMA and OCR modes work offline |
| API Key | Required for cloud engines; not required for OLLAMA or OCR mode |
| Storage | 1GB+ recommended (translation history and session recordings accumulate locally) |
| GPU (OLLAMA) | NVIDIA GPU with 4GB+ VRAM recommended for local inference |
| OLLAMA | Optional — install from [ollama.com](https://ollama.com) for local engine |
| EasyOCR | Optional — `pip install easyocr` for local OCR mode |

---

## 📁 Project Structure

```
LangForge/
├── LangForge.py          # Main application
├── platforms.json        # Game platform definitions
├── emulators.json        # Emulator definitions
├── requirements.txt      # Python dependencies
├── configs.json          # User config (auto-generated, API keys encrypted)
├── favicon.ico           # App icon
└── translation_logs/     # SQLite DB + screenshots (auto-generated)
    ├── langforge.db
    └── screenshots/
```

---

## 🗺️ Roadmap

- [x] Cloud engine support (Gemini, Groq, Mistral, OpenAI, Claude, Grok)
- [x] HuggingFace / Together AI / Cerebras / NVIDIA NIM engines
- [x] OLLAMA local engine
- [x] Local OCR + Google Translate mode (zero setup)
- [x] Simple Mode (Tab 7) — streamlined local-engine interface
- [x] Session recording & playback with live delay mode
- [x] AI walkthrough analysis
- [x] Auto-capture with scene stability detection
- [x] Encrypted API key storage
- [x] Bilingual UI (繁中 / English)
- [x] Dark / Light theme toggle
- [x] Platform editor
- [x] One-click Advanced / Simple Mode switch
- [ ] Multi-language UI (beyond zh/en)
- [ ] macOS / Linux support (planned)

---

## 💜 Support the Project

LangForge is built by a solo developer in spare time. If it's helped you enjoy a game you couldn't read before — your support means a lot.

| Platform | Link | Type |
| --- | --- | --- |
| ☕ Ko-fi | [ko-fi.com/toyakyo](https://ko-fi.com/toyakyo) | One-time or monthly |
| 💜 Patreon | [patreon.com/cw/LangForge](https://www.patreon.com/cw/LangForge) | $1–3 / month |
| 💬 FB Community | [LangForge Official Community](https://www.facebook.com/groups/2150940378645437) | Free to join |

---

## 📬 Links

| | |
| --- | --- |
| 🌐 Official Docs | https://goonsoft.tw2.nde.tw/tutorial/tutorial.php |
| 📥 Download | https://goonsoft.tw2.nde.tw/tutorial/tutorial.php#download |
| 💬 FB Community | https://www.facebook.com/groups/2150940378645437 |
| ☕ Ko-fi | https://ko-fi.com/toyakyo |
| 💜 Patreon | https://www.patreon.com/cw/LangForge |

---

## ⚠️ Disclaimer

LangForge is provided as-is during active development and may not be fully stable. Use at your own risk.  
API usage costs (if any) are the responsibility of the user based on their chosen AI engine provider.  
Translation results are AI-generated and may not always be accurate.

---

*Copyright © 2026 GoOnSoft. All rights reserved.*  
*Built with ❤️ by Toya Kyo — Solo Developer from Taiwan 🇹🇼*
