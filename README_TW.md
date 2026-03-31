# LangForge - 遊戲截圖翻譯工具

AI 驅動的遊戲截圖即時翻譯工具

## 功能特性

✨ **多引擎支援**
- Google Gemini
- Groq
- Mistral AI
- OpenAI
- Anthropic Claude
- 本地 OLLAMA
- Google 免費翻譯

🎮 **遊戲專用**
- 實時遊戲截圖翻譯
- 攻略資訊快速查詢
- 多平台支援（NES, SNES, N64, PS1, Dreamcast, RetroArch 等）
- 模擬器自動檢測

📝 **完整記錄**
- 翻譯歷史管理
- 攻略資訊保存
- 場次錄製功能
- 快捷鍵支援

⚙️ **高度可定制**
- 多語言介面（中文/英文）
- 自動翻譯設定
- 引擎切換
- API Key 管理

## 安裝

### 快速開始

1. 複製或下載本項目
```bash
git clone https://github.com/toyakyo/LangForge.git
cd LangForge
```

2. 安裝依賴
```bash
pip install -r requirements.txt
```

3. 運行應用
```bash
python main.py
```

### 打包成可執行文件

```bash
pip install pyinstaller
pyinstaller build_spec.py
```

生成的 .exe 檔案位於 `dist/LangForge/LangForge.exe`

## 使用指南

### 基本使用

1. 啟動應用後，在「翻譯操作」分頁設定：
   - 翻譯引擎（推薦 Gemini）
   - 遊戲語言（源語言）
   - 譯文語言（目標語言）

2. 在「擷取設定」分頁配置：
   - 目標遊戲視窗
   - 快捷鍵
   - 自動翻譯設定

3. 執行翻譯：
   - 使用快捷鍵或點擊「視窗擷取翻譯」按鈕
   - 翻譯結果會即時顯示

### API Key 設定

在「設定」分頁中設定各個翻譯引擎的 API Key：

- **Gemini**: https://makersuite.google.com/app/apikey
- **OpenAI**: https://platform.openai.com/api-keys
- **Claude**: https://console.anthropic.com/
- **Groq**: https://console.groq.com/
- **Mistral**: https://console.mistral.ai/

## 項目結構

詳見 [STRUCTURE.md](STRUCTURE.md)

```
LangForge/
├── langforge/
│   ├── config/          # 配置檔案
│   ├── core/            # 主程式
│   ├── asset/           # 資源檔案
│   └── translation_logs/ # 翻譯日誌
├── main.py              # 執行入口
├── build_spec.py        # 打包配置
└── README.md            # 本檔案
```

## 版本資訊

**當前版本**: V1.0.1-beta.5

**功能完整度**: 完全功能版本

## 系統需求

- Python 3.8+
- Windows 10+ (推薦)
- 4GB RAM 以上
- 網路連接（用於 API 調用）

## 故障排除

### 應用無法啟動
1. 確認 Python 版本 ≥ 3.8
2. 確認依賴已安裝：`pip install -r requirements.txt`
3. 檢查 langforge/core/langforge.py 是否存在

### API Key 不生效
1. 確認 API Key 已正確複製粘貼
2. 確認 API Key 未過期
3. 確認已啟用相應的 API 服務

### 翻譯結果不準確
1. 確認源語言設定正確
2. 嘗試其他翻譯引擎
3. 檢查遊戲截圖品質

## 貢獻

歡迎提交 Issue 和 Pull Request！

## 許可證

Copyright © 2026 GoOnSoft. All rights reserved.

## 作者

**Toya Kyo**

GitHub: https://github.com/toyakyo

## 相關資源

- GitHub: https://github.com/toyakyo/LangForge
- Tutorial: https://goonsoft.tw2.nde.tw/tutorial/tutorial.php
- Patreon: https://www.patreon.com/cw/LangForge
- Ko-fi: https://ko-fi.com/toyakyo

---

**感謝使用 LangForge！**
