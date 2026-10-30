# LangForge

專為遊戲玩家設計的 AI 即時截圖翻譯工具，支援主流雲端引擎與本地離線模式。

> 📖 [English README](https://github.com/toyakyo/LangForge/blob/master/README.md)

[![Version](https://img.shields.io/badge/版本-V1.5.19-blue?style=flat-square)](https://github.com/toyakyo/LangForge/releases) [![Platform](https://img.shields.io/badge/平台-Windows%20%7C%20Linux%20%7C%20macOS-0078D6?style=flat-square&logo=windows)](https://github.com/toyakyo/LangForge) [![Open Source](https://img.shields.io/badge/開源-GitHub-333?style=flat-square&logo=github)](https://github.com/toyakyo/LangForge)

[📥 下載](https://goonsoft.tw2.nde.tw/tutorial/tutorial.php#download) • [📖 完整教學](https://goonsoft.tw2.nde.tw/tutorial/tutorial.php) • [💬 社群](https://www.facebook.com/groups/2150940378645437) • [☕ Ko-fi](https://ko-fi.com/toyakyo) • [💜 Patreon](https://www.patreon.com/cw/LangForge)

---

## 主要功能

- 🎮 遊戲截圖 AI 翻譯，結果以疊圖方式顯示於原畫面
- 🌐 支援 10 組主流雲端引擎：Gemini、Groq、Mistral、OpenAI、Claude、Grok、HuggingFace、Together AI、Cerebras、NVIDIA NIM
- 🦙 本地 OLLAMA 引擎（完全離線，無需 API Key）
- 📟 簡易模式（Tab 7）：精簡介面，專注本地引擎，依硬體挑選最適 OLLAMA 模型
- 💾 歷史翻譯紀錄與場次錄製回放功能（含即時延遲播放）
- 🗺️ AI 攻略分析（遊玩中同步取得攻略建議）
- ⚡ 自動擷取翻譯（畫面穩定偵測，無需手動操作）
- 🔤 疊圖字體依目標語言自動配對（日、韓、俄、歐文各自最佳化）
- 🎨 雙語介面（繁體中文 / English），選單列隨時切換
- 🌗 深色 / 淺色主題切換
- 🔀 一鍵切換進階模式與簡易模式
- 🛠️ 平台編輯器（直接在程式內新增、改名、刪除遊戲平台與模擬器）
- 🔐 API Key 以機器碼 XOR 加密後儲存於本機

---

## 安裝方式

### 方式一：下載執行檔（推薦）

1. 從[下載頁面](https://goonsoft.tw2.nde.tw/tutorial/tutorial.php#download)下載最新版 `LangForge_V1.5.18.zip`
2. 解壓縮後直接執行 `LangForge.exe`（無需安裝 Python）
3. 建議執行前驗證 SHA256：

```
0EEF1F73CF69909E17DE876AAA235D5A3CFB6CA5091482FECA10278E7DABDB0D
```

```powershell
Get-FileHash .\LangForge.exe -Algorithm SHA256
```

> 若雜湊值不符，請勿執行，並從官方頁面重新下載。

### Linux / macOS（實驗版）

1. 從[下載頁面](https://goonsoft.tw2.nde.tw/tutorial/tutorial.php#download)下載 Linux（Ubuntu 22.04 以上，X11）或 macOS（Apple Silicon）版壓縮檔，兩者的 SHA256 都列在下載頁
2. 解壓縮：`tar -xzf LangForge_<版本>_<linux|macos>.tar.gz`
3. Linux：先 `sudo apt install fonts-noto-cjk`，再 `chmod +x LangForge && ./LangForge`
4. macOS：`xattr -cr LangForge && chmod +x LangForge && ./LangForge`，並在系統設定允許終端機的「螢幕錄製」

> 實驗版擷取**整個主螢幕**，不支援依視窗標題擷取與全域快捷鍵；雲端引擎與 OLLAMA 可正常使用。詳見[完整教學](https://goonsoft.tw2.nde.tw/tutorial/tutorial.php#unix)。

### 方式二：從原始碼執行

```bash
git clone https://github.com/toyakyo/LangForge.git
cd LangForge
pip install -r requirements.txt
python LangForge.py
```

---

## 快速開始

### 雲端引擎版（翻譯品質最佳）

1. 至 [aistudio.google.com](https://aistudio.google.com/apikey) 申請免費 Gemini API Key
2. 在「翻譯操作」頁籤選擇 **☁ 雲端引擎 → Gemini**，貼上 Key 即可使用

> 建議同時設定 [Groq](https://console.groq.com/keys)、[Mistral](https://console.mistral.ai/)、[Together AI](https://api.together.xyz/settings/api-keys)、[Cerebras](https://cloud.cerebras.ai/) — LangForge 自動備援切換，免費翻譯次數大幅提升。

### 本地離線版（OLLAMA）

1. 安裝 [OLLAMA](https://ollama.com)
2. 執行 `ollama pull llava` 下載視覺模型
3. 執行 `ollama serve` 啟動服務
4. 在 LangForge 選擇 **🦙 本地引擎 (OLLAMA)**

> **V1.5.19 新增：** 程式內的「安裝 OLLAMA」與「下載預設模型」按鈕會先說明內容並請您確認，顯示真實的 `ollama pull` 下載進度，完成後向 OLLAMA 確認模型可用，並針對網路、儲存空間、OLLAMA 未啟動等情況提供明確錯誤訊息。OLLAMA 與模型皆為第三方軟體／內容，各有其使用條款；模型檔案由 OLLAMA 下載，非 LangForge 直接下載。

> **V1.5 新增：** 切換到 **簡易模式（Tab 7）** 可獲得更精簡的 OLLAMA 操作體驗，依硬體選擇最適合的模型。

---

## 支援引擎

| 引擎 | 推薦模型 | 免費額度 | 備註 |
| --- | --- | --- | --- |
| Gemini（Google） | gemini-3-flash | ✅ 500 RPD | 新手推薦，無需信用卡 |
| Gemini（Google） | gemini-2.5-flash | ✅ 20 RPD | 穩定版，視覺理解強 |
| Groq | qwen/qwen3.6-27b | ✅ 1000 RPD | 多模態，速度快 |
| Mistral | mistral-small-latest | ✅ 500 RPD | 視覺支援，高配額 |
| HuggingFace | Llama-3.2-11B-Vision | ✅ 免費額度 | 開源視覺模型 |
| Together AI | Llama-Vision-Free | ✅ 永久免費 | 無需付費的視覺模型 |
| Cerebras | gemma-4-31b | ✅ 免費額度 | 1800+ tok/s 超快推理 |
| NVIDIA NIM | llama-3.2-11b-vision | ✅ 免費 credits | 企業級推理穩定性 |
| OpenAI | gpt-4.1-mini | 💳 付費 | 翻譯品質穩定 |
| Claude（Anthropic） | claude-sonnet-4-6 | 💳 付費 | 語意理解強 |
| Grok（xAI） | grok-2-vision-1212 | 💳 付費 | 旗艦多模態模型 |
| 🦙 OLLAMA | 任意視覺模型 | ✅ 完全免費 | 離線使用，無需 API Key |

---

## 系統需求

| 項目 | 需求 |
| --- | --- |
| 作業系統 | Windows 10 / 11（64-bit 建議）。Linux（Ubuntu，X11）與 macOS（Apple Silicon）為實驗版：僅支援整個螢幕擷取，無視窗標題擷取與全域快捷鍵 |
| 網路 | 使用雲端引擎時需連線；OLLAMA 可離線使用 |
| API Key | 使用雲端引擎需至少一組；使用 OLLAMA 無需 |
| 儲存空間 | 建議預留 1GB 以上（翻譯截圖與場次錄製會持續累積） |
| 顯示卡（OLLAMA） | 建議 NVIDIA GPU 4GB+ VRAM；僅 CPU 亦可但速度較慢 |
| OLLAMA（選用） | 使用本地引擎需另行安裝 [ollama.com](https://ollama.com) |

---

## 版本歷程

| 版本 | 日期 | 重點 |
| --- | --- | --- |
| V1.5.19 | 2026-10-30 | 安裝 OLLAMA／下載模型前新增說明與確認視窗，顯示實際 `ollama pull` 進度並於完成後確認模型可用，補齊網路／空間／服務未啟動等錯誤提示；已安裝 OLLAMA 時改為直接啟動（Windows 原始碼版；Windows 打包檔待發布） |
| V1.5.18 | 2026-10-13 | 新增「關於 → 第三方授權」聲明；移除 chardet（LGPL）相依 |
| V1.5.17 | 2026-10-12 | 公開版不再附帶 OEM 授權相關資源檔 |
| V1.5.16 | 2026-10-09 | 移除本地 OCR 模式（EXE 約 205 MB → 約 49 MB）、修正 OLLAMA 安裝流程 |
| V1.5.15 | 2026-10-09 | Linux（Ubuntu）/ macOS 實驗版首次發布 |
| V1.5.1 | 2026-07-14 | 簡易模式自動擷取 3 秒最小間隔、一鍵切換模式按鈕、RPM 修正 |
| V1.5 | 2026-07-06 | 引擎擴增至 10 組、新增簡易模式（Tab 7） |
| V1.1.1 | 2026-05-07 | 疊字顯示設定、自動備援設定、遊戲名稱重新命名 |
| V1.1.0 | 2026-04-28 | 正式版發布、模型清單自動更新、字體語言配對 |
| V1.0.1-beta.8 | 2026-04-17 | 深色/淺色主題、平台編輯器、三層環境偵測 |
| V1.0.1-beta.7 | 2026-04-07 | Grok 引擎、場次錄製（Tab 6）、6 組引擎 |

---

## 完整教學

https://goonsoft.tw2.nde.tw/tutorial/tutorial.php

---

## 授權

Copyright © 2026 GoOnSoft. All rights reserved.

### 第三方授權

LangForge 為專有軟體，內含第三方開源元件（MIT、BSD、Apache-2.0、PSF、MPL-2.0 等）。其著作權聲明與授權全文請見 [THIRD-PARTY-LICENSES.md](THIRD-PARTY-LICENSES.md)，程式內亦可從「說明 → 關於 → 第三方授權」開啟。

---

## 支持開發

LangForge 由個人獨立開發。如果這個工具讓你玩到了原本看不懂的遊戲，歡迎支持開發者持續更新 🙏

- ☕ Ko-fi：https://ko-fi.com/toyakyo
- 💜 Patreon：https://www.patreon.com/cw/LangForge
- 💬 Facebook 社群：https://www.facebook.com/groups/2150940378645437

---

*Copyright © 2026 GoOnSoft. All rights reserved.*  
*Built with ❤️ by Toya Kyo — Solo Developer from Taiwan 🇹🇼*
