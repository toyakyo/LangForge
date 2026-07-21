# LangForge

專為遊戲玩家設計的 AI 即時截圖翻譯工具，支援主流雲端引擎與本地離線模式。

> 📖 [English README](https://github.com/toyakyo/LangForge/blob/master/README.md)

[![Version](https://img.shields.io/badge/版本-V1.5.1-blue?style=flat-square)](https://github.com/toyakyo/LangForge/releases) [![Platform](https://img.shields.io/badge/平台-Windows%2010%2F11-0078D6?style=flat-square&logo=windows)](https://github.com/toyakyo/LangForge) [![Open Source](https://img.shields.io/badge/開源-GitHub-333?style=flat-square&logo=github)](https://github.com/toyakyo/LangForge)

[📥 下載](https://goonsoft.tw2.nde.tw/tutorial/tutorial.php#download) • [📖 完整教學](https://goonsoft.tw2.nde.tw/tutorial/tutorial.php) • [💬 社群](https://www.facebook.com/groups/2150940378645437) • [☕ Ko-fi](https://ko-fi.com/toyakyo) • [💜 Patreon](https://www.patreon.com/cw/LangForge)

---

## 主要功能

- 🎮 遊戲截圖 AI 翻譯，結果以疊圖方式顯示於原畫面
- 🌐 支援 10 組主流雲端引擎：Gemini、Groq、Mistral、OpenAI、Claude、Grok、HuggingFace、Together AI、Cerebras、NVIDIA NIM
- 🦙 本地 OLLAMA 引擎（完全離線，無需 API Key）
- 🔍 本地 OCR 模式（EasyOCR + Google 翻譯，完全免費）
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

1. 從 [GitHub Releases](https://github.com/toyakyo/LangForge/releases) 下載 `LangForge_V1.5.1.zip`
2. 解壓縮後直接執行 `LangForge.exe`（無需安裝 Python）
3. 建議執行前驗證 SHA256：

```
EFE1E645BF88CB359B0D48BD4E29DDDABF157FABCC433D3AF5C359B123B6B793
```

```powershell
Get-FileHash .\LangForge.exe -Algorithm SHA256
```

> 若雜湊值不符，請勿執行，並從官方頁面重新下載。

### 方式二：從原始碼執行

```bash
git clone https://github.com/toyakyo/LangForge.git
cd LangForge
pip install -r requirements.txt
python LangForge.py
```

---

## 快速開始

### 零設定版（新手推薦）

1. 執行 `LangForge.exe`
2. 選擇 **🔍 本地 OCR + Google 翻譯**
3. 在「擷取設定」頁籤輸入遊戲視窗標題
4. 點擊「視窗擷取翻譯」完成！

> 無需 API Key，無需帳號。

### 雲端引擎版（翻譯品質最佳）

1. 至 [aistudio.google.com](https://aistudio.google.com/apikey) 申請免費 Gemini API Key
2. 在「翻譯操作」頁籤選擇 **☁ 雲端引擎 → Gemini**，貼上 Key 即可使用

> 建議同時設定 [Groq](https://console.groq.com/keys)、[Mistral](https://console.mistral.ai/)、[Together AI](https://api.together.xyz/settings/api-keys)、[Cerebras](https://cloud.cerebras.ai/) — LangForge 自動備援切換，免費翻譯次數大幅提升。

### 本地離線版（OLLAMA）

1. 安裝 [OLLAMA](https://ollama.com)
2. 執行 `ollama pull llava` 下載視覺模型
3. 執行 `ollama serve` 啟動服務
4. 在 LangForge 選擇 **🦙 本地引擎 (OLLAMA)**

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
| 🔍 本地 OCR | EasyOCR + Google 翻譯 | ✅ 完全免費 | 零設定，無配額限制 |

---

## 系統需求

| 項目 | 需求 |
| --- | --- |
| 作業系統 | Windows 10 / 11（64-bit 建議） |
| 網路 | 使用雲端引擎時需連線；OLLAMA 與 OCR 模式可離線使用 |
| API Key | 使用雲端引擎需至少一組；OLLAMA 及本地 OCR 模式無需 |
| 儲存空間 | 建議預留 1GB 以上（翻譯截圖與場次錄製會持續累積） |
| 顯示卡（OLLAMA） | 建議 NVIDIA GPU 4GB+ VRAM；僅 CPU 亦可但速度較慢 |
| OLLAMA（選用） | 使用本地引擎需另行安裝 [ollama.com](https://ollama.com) |
| EasyOCR（選用） | 使用本地 OCR 模式需安裝：`pip install easyocr` |

---

## 版本歷程

| 版本 | 日期 | 重點 |
| --- | --- | --- |
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

---

## 支持開發

LangForge 由個人獨立開發。如果這個工具讓你玩到了原本看不懂的遊戲，歡迎支持開發者持續更新 🙏

- ☕ Ko-fi：https://ko-fi.com/toyakyo
- 💜 Patreon：https://www.patreon.com/cw/LangForge
- 💬 Facebook 社群：https://www.facebook.com/groups/2150940378645437

---

*Copyright © 2026 GoOnSoft. All rights reserved.*  
*Built with ❤️ by Toya Kyo — Solo Developer from Taiwan 🇹🇼*
