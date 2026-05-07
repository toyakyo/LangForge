# LangForge

AI-powered game screenshot translator with support for multiple translation engines.

> 📖 [繁體中文說明請見 README_TW.md](README_TW.md)

## Features

- 🎮 Game screenshot translation with AI overlay
- 🌐 Support for multiple AI engines (Gemini, Groq, Mistral, OpenAI, Claude, Grok)
- 🦙 Local OLLAMA engine (offline, no API key required)
- 🔍 Local OCR mode (EasyOCR + Google Translate, completely free)
- 💾 Translation history & session recording with playback
- 🗺️ AI-powered guide analysis (strategy tips while you play)
- ⚡ Auto-capture with scene stability detection
- 🎨 Bilingual UI (Traditional Chinese / English)
- 🌗 Dark / Light theme toggle
- 🕹️ Platform editor for managing game platform & emulator lists

## Installation

### Option 1: Download Pre-built Executable (Recommended)

1. Download `LangForge_V1.1.1.zip` from [GitHub Releases](https://github.com/toyakyo/LangForge/releases)
2. Extract and run `LangForge.exe` directly (no Python required)
3. Verify SHA256:
   ```
   1E9DF0E89E91E9D799E56049E7F5FBA5D08C36E6706F4140F38E38413697FE80
   ```
   ```powershell
   Get-FileHash .\LangForge.exe -Algorithm SHA256
   ```

### Option 2: Run from Source

```bash
git clone https://github.com/toyakyo/LangForge.git
cd LangForge
pip install -r requirements.txt
python main.py
```

## Supported Engines

| Engine | Free Tier | Notes |
|--------|-----------|-------|
| Gemini (Google) | ✅ 500 RPD | Recommended for beginners |
| Groq | ✅ 1000 RPD | Fastest response |
| Mistral | ✅ 500 RPD | Vision support |
| OpenAI | 💳 Paid | Stable quality |
| Claude (Anthropic) | 💳 Paid | Strong semantic understanding |
| Grok (xAI) | 💳 Paid | Flagship multimodal |
| 🦙 OLLAMA | ✅ Free | Offline, no API key needed |
| 🔍 Local OCR | ✅ Free | EasyOCR + Google Translate |

## Requirements

- Windows 10 / 11 (64-bit recommended)
- Internet connection (for cloud engines; OLLAMA & OCR modes work offline)
- API Key for at least one cloud engine (not required for OLLAMA / OCR)

## Usage

1. Launch `LangForge.exe`
2. Enter API Key in the **Translate** tab
3. Set target window title in **Capture Settings**
4. Click **Capture & Translate** or use hotkey (`Ctrl+F2`)
5. Translation overlay appears on the screenshot

## Documentation

Full tutorial: https://goonsoft.tw2.nde.tw/tutorial/tutorial.php

## License

Copyright © 2026 GoOnSoft. All rights reserved.

## Support

- ☕ Ko-fi: https://ko-fi.com/toyakyo
- 💜 Patreon: https://www.patreon.com/cw/LangForge
- 💬 Facebook Community: https://www.facebook.com/groups/2150940378645437