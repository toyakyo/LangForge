# LangForge

專為遊戲玩家設計的 AI 即時截圖翻譯工具，支援主流雲端引擎與本地離線模式。

> 📖 [English README](README.md)

## 主要功能

- 🎮 遊戲截圖 AI 翻譯，結果以疊圖方式顯示於原畫面
- 🌐 支援主流雲端引擎：Gemini、Groq、Mistral、OpenAI、Claude、Grok
- 🦙 本地 OLLAMA 引擎（完全離線，無需 API Key）
- 🔍 本地 OCR 模式（EasyOCR + Google 翻譯，完全免費）
- 💾 歷史翻譯紀錄與場次錄製回放功能
- 🗺️ AI 攻略分析（遊玩中同步取得攻略建議）
- ⚡ 自動擷取翻譯（畫面穩定偵測，無需手動操作）
- 🎨 雙語介面（繁體中文 / English）
- 🌗 深色 / 淺色主題切換
- 🕹️ 平台編輯器（直接在程式內管理遊戲平台與模擬器清單）

## 安裝方式

### 方式一：下載執行檔（推薦）

1. 從 [GitHub Releases](https://github.com/toyakyo/LangForge/releases) 下載 `LangForge_V1.1.1.zip`
2. 解壓縮後直接執行 `LangForge.exe`（無需安裝 Python）
3. 建議執行前驗證 SHA256：
   ```
   1E9DF0E89E91E9D799E56049E7F5FBA5D08C36E6706F4140F38E38413697FE80
   ```
   ```powershell
   Get-FileHash .\LangForge.exe -Algorithm SHA256
   ```

### 方式二：從原始碼執行

```bash
git clone https://github.com/toyakyo/LangForge.git
cd LangForge
pip install -r requirements.txt
python main.py
```

## 支援引擎

| 引擎 | 免費額度 | 備註 |
|------|----------|------|
| Gemini（Google） | ✅ 500 RPD | 新手推薦，無需信用卡 |
| Groq | ✅ 1000 RPD | 回應速度最快 |
| Mistral | ✅ 500 RPD | 支援視覺輸入 |
| OpenAI | 💳 付費 | 翻譯品質穩定 |
| Claude（Anthropic） | 💳 付費 | 語意理解強 |
| Grok（xAI） | 💳 付費 | 旗艦多模態模型 |
| 🦙 OLLAMA | ✅ 完全免費 | 離線使用，無需 API Key |
| 🔍 本地 OCR | ✅ 完全免費 | EasyOCR + Google 翻譯 |

## 系統需求

- Windows 10 / 11（64-bit 建議）
- 使用雲端引擎時需網路連線；OLLAMA 與 OCR 模式可離線使用
- 使用雲端引擎需至少一組 API Key

## 使用方式

1. 執行 `LangForge.exe`
2. 在「翻譯操作」頁籤輸入 API Key
3. 在「擷取設定」頁籤設定目標遊戲視窗標題
4. 點擊「視窗擷取翻譯」或使用快捷鍵（`Ctrl+F2`）
5. 翻譯結果以疊圖方式顯示於截圖上

## 完整教學

https://goonsoft.tw2.nde.tw/tutorial/tutorial.php

## 授權

Copyright © 2026 GoOnSoft. All rights reserved.

## 支持開發

- ☕ Ko-fi：https://ko-fi.com/toyakyo
- 💜 Patreon：https://www.patreon.com/cw/LangForge
- 💬 Facebook 社群：https://www.facebook.com/groups/2150940378645437