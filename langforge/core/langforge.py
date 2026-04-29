"""LangForge V1.1.0
AI-powered game screenshot translation tool.

Copyright (c) 2026 Toya Kyo (GoOnSoft)
GitHub : https://github.com/toyakyo
License: Copyright © 2026 GoOnSoft. All rights reserved.

需要安裝的第三方套件（一鍵安裝）:
  pip install anthropic easyocr google-genai groq keyboard mistralai numpy openai pillow pywin32
"""

import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys, os, ctypes, shutil, io, json, time, re, base64
import hashlib
import warnings
import logging
import sqlite3
import copy
import webbrowser
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageGrab, ImageChops
import win32gui

try:
    import mistralai
    from mistralai import Mistral
except Exception as e:
    print(f"DEBUG: Mistral load error: {e}")
    Mistral = None

# ==========================================
# 三層環境自動偵測
# ==========================================
IS_FROZEN = getattr(sys, 'frozen', False)  # PyInstaller 標記
current_file = os.path.abspath(__file__)

# 偵測執行環境
if IS_FROZEN:
    # 環境 3：發佈模式 (EXE)
    ENV_MODE = 'RELEASE'
    BASE_DIR = os.path.dirname(sys.executable)

elif 'langforge' in current_file and os.path.sep + 'core' + os.path.sep in current_file:
    # 環境 2：Git 模組化結構
    # 路徑：D:\source\GitHub\LangForge\langforge\core\langforge.py
    ENV_MODE = 'GIT'
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))  # 往上3層到 LangForge/

else:
    # 環境 1：開發環境（單檔）
    # 路徑：D:\source\visualstudio2026\repo\LangForge\LangForge.py
    ENV_MODE = 'DEV'
    BASE_DIR = os.path.dirname(current_file)

# 定義各環境的相對路徑
if ENV_MODE == 'GIT':
    # Git 環境：使用模組化結構
    CONFIG_DIR = os.path.join(BASE_DIR, 'langforge', 'config')
    ASSET_DATA_DIR = os.path.join(BASE_DIR, 'langforge', 'asset', 'data')
    ASSET_ICONS_DIR = os.path.join(BASE_DIR, 'langforge', 'asset', 'icons')
    TRANSLATION_LOGS_DIR = os.path.join(BASE_DIR, 'langforge', 'translation_logs')
else:
    # 開發環境 & 發佈環境：所有檔案在同級目錄
    CONFIG_DIR = BASE_DIR
    ASSET_DATA_DIR = BASE_DIR
    ASSET_ICONS_DIR = BASE_DIR
    TRANSLATION_LOGS_DIR = os.path.join(BASE_DIR, 'translation_logs')

# 確保必要目錄存在
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(ASSET_DATA_DIR, exist_ok=True)
os.makedirs(TRANSLATION_LOGS_DIR, exist_ok=True)

try:
    import keyboard  # pip install keyboard

    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False


# ==========================================
# 讀取 platforms.json
# ==========================================
def _load_platforms():
    path = os.path.join(ASSET_DATA_DIR, "platforms.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("platforms", {})
    except Exception as e:
        import sys

        print(f"[LangForge] 載入 platforms.json 失敗: {e}", file=sys.stderr)
        return {}


PLATFORMS = _load_platforms()


# ==========================================
# 讀取 emulators.json
# ==========================================
def _load_emulators():
    path = os.path.join(ASSET_DATA_DIR, "emulators.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("platforms", {})
    except Exception as e:
        print(f"[LangForge] 載入 emulators.json 失敗: {e}", file=sys.stderr)
        return {}


EMULATORS = _load_emulators()


def _save_platforms(data: dict):
    path = os.path.join(ASSET_DATA_DIR, "platforms.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"platforms": data}, f, ensure_ascii=False, indent=2)


def _save_emulators(data: dict):
    path = os.path.join(ASSET_DATA_DIR, "emulators.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"platforms": data}, f, ensure_ascii=False, indent=2)


# ==========================================
# 應用程式圖示
# ==========================================
def _load_app_icon(window) -> None:
    """將 favicon.ico 套用至指定視窗的標題列與工作列。
    favicon.ico 需與程式放在同一目錄；找不到時靜默略過，不影響程式運作。
    優先使用 iconbitmap（Windows 原生 .ico 支援）；
    失敗時退回 iconphoto（跨平台備案，以 Pillow 轉換）。
    """
    # 嘗試多個可能的位置
    possible_paths = [
        os.path.join(ASSET_ICONS_DIR, "favicon.ico"),  # 模組化結構
        os.path.join(BASE_DIR, "favicon.ico"),          # 根目錄
        "favicon.ico",                                   # 當前目錄
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "favicon.ico"),  # 檔案同目錄
    ]
    
    ico_path = None
    for path in possible_paths:
        if os.path.exists(path):
            ico_path = path
            break
    
    if not ico_path:
        return
    
    try:
        # Windows 原生方式：直接吃 .ico，標題列 + 工作列均生效
        window.iconbitmap(ico_path)
    except Exception:
        try:
            # 備用：Pillow 轉 PhotoImage（跨平台；工作列圖示視平台而定）
            _ico_img = Image.open(ico_path).resize((32, 32), Image.LANCZOS)
            _ico_photo = ImageTk.PhotoImage(_ico_img)
            window.iconphoto(True, _ico_photo)
            # 防止 GC 回收（PhotoImage 必須有強參考才不會消失）
            window._icon_photo_ref = _ico_photo  # type: ignore[attr-defined]
        except Exception:
            pass  # 圖示載入失敗不中斷程式


# ==========================================
# 關於資訊常數
# ==========================================
ABOUT_VERSION = "V1.1.0"
DEBUG_COORD = False  # True = 輸出座標診斷 log（開發用，發布前設為 False）
ABOUT_GITHUB = "https://github.com/toyakyo"
ABOUT_AUTHOR = "Toya Kyo"
ABOUT_LICENSE = "Copyright © 2026 GoOnSoft. All rights reserved."
TUTORIAL_URL = "https://goonsoft.tw2.nde.tw/tutorial/tutorial.php"

# ==========================================
# 多語系 UI 字串
# ==========================================
UI_STRINGS = {
    "zh": {
        # ── 頁籤 ──
        "tab_translate": "  翻譯操作  ",
        "tab_capture": "  擷取設定  ",
        "tab_quota": "  引擎配額  ",
        "tab_history": "  歷史翻譯  ",
        "tab_guide": "  歷史攻略  ",
        "tab_session": "  歷史錄製  ",
        # ── Tab1 翻譯操作 ──
        "lbl_engine": "翻譯引擎:",
        "lbl_trans_options": "翻譯選項",
        "lf_cloud_engine": "翻譯引擎",
        "rb_engine_cloud": "☁ 雲端引擎",
        "rb_engine_local": "🦙 本地引擎 (OLLAMA)",
        "rb_engine_ocr": "🔍 本地OCR+Google翻譯",
        "msg_lang_changed_zh": "介面語言已設為中文，重新啟動後生效。",
        "msg_delete_cat": "刪除主類別「{cat}」及其所有平台？",
        "status_save_fail": "儲存失敗: {err}",
        "lbl_ollama_hint": "（建議 30～120，依模型大小調整）",
        "title_translate": "翻譯結果",
        "title_guide": "攻略資訊",
        "playback_done": "播放完畢",
        "btn_pause": "⏸ 暫停",
        "btn_resume": "▶ 繼續",
        "title_plat_editor": "平台編輯器",
        "lbl_plat_cat": "遊戲平台 (platforms.json)",
        "lbl_emu_cat": "模擬器 (emulators.json)",
        "lf_main_cat": "主類別",
        "lf_platform_list": "平台",
        "btn_add_short": "新增",
        "btn_rename": "改名",
        "btn_delete_short": "刪除",
        "btn_close": "關閉",
        "btn_save": "儲存",
        "status_saved": "✓ 已儲存",
        "status_no_win_detect": "未偵測到有效視窗",
        "progress_unknown": "（無法辨識進度）",
        "lbl_timeout_hint": "（建議 30～120，依模型大小調整）",
        "status_hotkey_set_fail": "快捷鍵設定失敗: {e}",
        "status_guide_hotkey_fail2": "攻略快捷鍵設定失敗: {e}",
        "status_win_exists": "目標視窗已存在: {name}",
        "status_img_loading": "讀取圖片中...",
        "status_img_load_fail": "圖片讀取失敗",
        "status_no_target_win": "請先設定目標視窗標題",
        "hint_no_target": "請建立擷取視窗",
        "status_quota_exhausted": "所有模型額度已用完",
        "status_auto_switched": "自動切換至 {model}",
        "status_no_key": "請輸入 API Key",
        "status_no_key_eng": "請輸入 {engine} API Key",
        "status_guide_json_fail": "攻略 JSON 解析失敗（詳見 PowerShell）",
        "status_429_wait": "429 限流，建議等 {sec} 秒後重試",
        "status_key_invalid": "API Key 無效或過期，請確認 Key",
        "status_key_invalid2": "API Key 無效或過期",
        "status_key_invalid_eng": "API Key 無效或過期，請確認 {engine} Key",
        "status_combo_done": "翻譯+攻略完成",
        "status_json_fail": "JSON 解析失敗（詳見 PowerShell）",
        "status_error": "錯誤: {msg}",
        "status_parse_error": "解析錯誤: {msg}",
        "status_done": "翻譯完成",
        "status_ocr_running": "OCR 辨識中...",
        "status_ocr_no_easyocr": "缺少 easyocr，請執行 pip install easyocr",
        "status_ocr_no_text": "OCR 未偵測到可信文字",
        "status_ocr_fail": "OCR 失敗: {msg}",
        "status_gt_fail": "Google 翻譯失敗: {msg}",
        "status_ocr_no_result": "OCR 無有效結果",
        "status_ocr_done": "OCR 翻譯完成（{n} 段）",
        "status_bad_request": "請求格式錯誤，該模型可能不支援圖片",
        "status_server_error": "{engine} 伺服器內部錯誤，請稍後重試",
        "status_network_fail": "網路連線失敗，請檢查網路",
        "status_api_fail": "API 失敗: {msg}",
        "lbl_queue": "佇列",
        "lbl_cooldown": "冷卻",
        "status_cooling": "{model} 冷卻中，請等 {wait} 秒",
        "status_analyzing": "{engine} ({model}) 分析中...",
        "status_combo_analyzing": "{engine} ({model}) 翻譯+攻略分析中...",
        "status_ocr_translating": "OCR → Google 翻譯中...",
        "status_ollama_running": "OLLAMA 推理中... (timeout={t}s)",
        "status_ollama_done": "OLLAMA 翻譯完成（{n} 段）",
        "status_ollama_empty": "OLLAMA 推理完成，但未辨識到可翻譯文字",
        "status_ollama_aborted": "OLLAMA 推理中斷（回應異常）",
        "status_guide_done": "攻略分析完成",
        "status_guide_fail": "攻略分析失敗",
        "status_combined_fail": "合併請求失敗",
        "status_win_missing": "找不到目標視窗",
        "status_pkg_missing": "缺少套件: {pkg}，請執行 pip install {pkg}",
        "status_429": "429 配額超限，請稍後或換模型",
        "status_503": "{model} 服務繁忙，請稍後重試",
        "status_503b": "{model} 服務繁忙，請稍後重試或換模型",
        "status_default_ok": "預設已儲存：{engine} / {model}",
        "all_games": "全部遊戲",
        "all_windows": "全部視窗",
        "all_platforms": "全部平台",
        "ind_auto": "自動",
        "ind_guide": "攻略",
        "ind_hotkey": "擷取鍵",
        "ind_guide_hotkey": "攻略鍵",
        "lbl_available": "可用",
        "stable_hint": "(差異門檻 0~255，次數×500ms=等待秒數)",
        "th_size": "大小",
        "btn_capture_trans": "視窗擷取翻譯",
        "btn_default_engine": "設為預設",
        "btn_ok": "確定",
        "lbl_diff_threshold": "差異門檻",
        "rb_winmode_corner": "角落模式",
        "lbl_api_key": "Gemini API Key:",
        "lbl_model": "模型:",
        "btn_default_engine": "設為預設",
        "lbl_custom_model": "自訂模型:",
        "btn_add": "新增",
        "btn_cancel": "取消",
        "btn_remove": "移除",
        "lf_lang": "語言設定",
        "lbl_src_lang": "遊戲語言:",
        "lbl_tgt_lang": "譯文語言:",
        "lbl_layout": "文字排版模式:",
        "rb_horizontal": "橫排（文句左至右）",
        "rb_vertical": "直排（文上至下、句右至左）",
        "lf_platform": "遊戲平台紀錄以",
        "rb_platform_mode": "遊戲平台為主",
        "rb_emulator_mode": "模擬器為主",
        "lbl_category": "主類別:",
        "lbl_platform": "平台:",
        "btn_capture_trans": "視窗擷取翻譯",
        "btn_file_trans": "選擇圖片翻譯",
        "btn_guide": "目前攻略資訊",
        "btn_auto_cap_on": "停止自動擷取",
        "btn_auto_cap_off": "自動擷取",
        "btn_auto_cap_tooltip": "自動擷取功能請至「擷取設定」頁籤中開啟",
        "btn_clear_queue": "清空要求任務",
        "btn_refresh_models": "更新模型",
        "btn_refresh_ollama": "重新偵測",
        "status_ready": "狀態: 就緒",
        # ── Tab2 擷取設定 ──
        "lbl_target_win": "目標視窗標題:",
        "lbl_target_win_tooltip": "輸入視窗標題的部分文字即可匹配",
        "btn_pick_window": "🖱 點選視窗",
        "lbl_pick_hint": "5秒內請點選目標視窗…",
        "lbl_crop_top": "裁切頂部(px):",
        "lbl_crop_hint": "（選單列高度，0=不裁切）",
        "lf_winmode": "視窗依附模式",
        "rb_winmode_main": "依附主視窗",
        "rb_winmode_mesen": "依附目標視窗",
        "rb_winmode_corner": "螢幕角落（翻譯右上 / 攻略右下）",
        "rb_winmode_sides": "目標視窗兩側（攻略左邊 / 翻譯右邊）",
        "lbl_hotkey": "擷取翻譯快捷鍵:",
        "btn_enable": "啟用",
        "btn_disable": "停用",
        "lbl_hotkey_off": "未啟用",
        "lbl_guide_hotkey": "攻略資訊快捷鍵:",
        "cb_combo_guide": "截取翻譯時同時要求攻略",
        # ── 自動翻譯 ──
        "lf_auto_trans": "自動擷取",
        "cb_auto_trans": "啟用畫面穩定自動翻譯",
        "lbl_diff_threshold": "差異門檻:",
        "lbl_stable_count": "穩定次數:",
        "status_on": "運行中",
        "status_off": "關閉中",
        "lbl_combo_on": "開啟中",
        "lbl_combo_off": "關閉中",
        "lbl_screen": "主視窗位置:",
        # ── Tab3 引擎配額 ──
        "lbl_quota_title": "今日各引擎使用量",
        "btn_refresh": "🔄 重新整理",
        # ── Tab4 歷史翻譯 ──
        "lbl_game": "遊戲:",
        "lbl_window": "視窗:",
        "lbl_platform_f": "平台:",
        "btn_delete": "刪除此筆",
        "th_id": "筆次",
        "th_time": "時間",
        "th_model": "模型",
        "th_rom": "ROM名稱",
        "th_window": "視窗",
        "th_platform": "平台",
        "lf_fix_platform": "修正平台",
        "lbl_fix_mode": "模式:",
        "lbl_fix_cat": "主類別:",
        "lbl_fix_plat": "平台:",
        "btn_apply_plat": "套用至此遊戲所有紀錄",
        "btn_overlay": "疊圖模式 ✓",
        "btn_plain": "純圖模式   ",
        # ── Tab5 歷史攻略 ──
        "th_progress": "進度摘要",
        "lbl_curr_prog": "【目前進度】",
        "lbl_curr_guide": "【攻略建議】",
        # ── Tab3 配額表欄位 ──
        "th_engine": "引擎",
        "th_used": "已用",
        "th_limit": "上限",
        "quota_no_limit": "無額度",
        "quota_conservative": "保守額度(50)",
        "quota_no_free": "⚠ 無免費額度",
        "quota_switch": "無免費額度 (limit=0)，請換模型",
        "quota_estimated": "推估{n}",
        # ── 選單列 ──
        "menu_file": "檔案",
        "menu_exit": "結束",
        "menu_view": "檢視",
        "menu_switch_lang": "切換介面語言",
        "menu_lang_zh": "中文",
        "menu_lang_en": "English",
        "menu_switch_theme": "切換視窗主題",
        "menu_theme_dark": "深色",
        "menu_theme_light": "淺色",
        "menu_edit_platforms": "平台編輯器",
        "menu_help": "說明",
        "menu_tutorial": "LangForge 教學",
        "menu_platform_editor": "平台編輯器",
        "menu_about": "關於 LangForge",
        # ── 狀態訊息 ──
        "status_reading": "讀取圖片中...",
        "status_img_fail": "圖片讀取失敗",
        "status_capturing": "擷取畫面中...",
        "status_no_win": "找不到目標視窗",
        "status_guide_analyzing": "攻略分析中...",
        "status_guide_done": "攻略分析完成",
        "status_trans_done": "翻譯完成",
        "status_no_key": "請輸入 API Key",
        "status_quota_done": "所有模型額度已用完",
        "status_key_needed": "請輸入 {engine} API Key",
        "status_keyboard_need": "需安裝 keyboard 模組: pip install keyboard",
        "status_hotkey_fail": "快捷鍵設定失敗: {err}",
        "status_guide_hotkey_fail": "攻略快捷鍵設定失敗: {err}",
        "status_win_exists": "目標視窗已存在: {name}",
        "status_win_added": "已新增: {name}",
        "status_win_notfound": "找不到: {name}",
        "status_win_removed": "已移除: {name}",
        "status_model_exists": "模型已存在: {model}",
        "status_model_added": "已新增: {model}",
        "status_model_removed": "已移除: {model}",
        "status_builtin_no_remove": "內建模型無法移除",
        "status_no_model_remove": "找不到可移除的模型",
        "status_default_saved": "預設已儲存：{engine} / {model}",
        "status_hotkey_on": "已啟用: {key}",
        "status_queue_full": "請求佇列已滿（上限10條），請稍後再試",
        "status_queue_waiting": "佇列等待中（{n} 個任務）",
        # ── OLLAMA ──
        "lf_ollama": "🦙 OLLAMA 本地引擎",
        "lbl_ollama_detected": "偵測到本地 OLLAMA，以下為已安裝的模型：",
        "cb_use_ollama": "優先使用 OLLAMA（忽略雲端 API Key）",
        "lbl_ollama_timeout": "Timeout(秒):",
        "cb_vision_filter": "僅顯示 VLM（視覺語言模型）",
        "lf_session": "場次錄製",
        "btn_start_session": "開始場次錄製",
        "btn_stop_session_inline": "結束錄製",
        "btn_stop_session": "結束場次",
        "btn_stop_session_inline": "結束錄製",
        "btn_open_playback": "開啟播放視窗",
        "session_idle": "未錄製",
        "session_recording": "錄製中...",
        "th_session_game": "遊戲",
        "th_session_start": "開始時間",
        "th_session_frames": "幀數",
        "th_session_plat": "平台",
        "btn_session_replay": "▶ 回放此場次",
        "btn_session_delete": "刪除場次",
        "session_no_select": "請先選取場次",
        "btn_stop_playback": "■ 停止播放",
        "status_ollama_timeout": "OLLAMA 推理逾時，請增加 Timeout 或換小模型",
        "status_ollama_fail": "OLLAMA 呼叫失敗: {err}",
        "status_ollama_no_model": "請選擇 OLLAMA 模型",
        # ── 硬編碼補全 ──
        "lf_actions": "功能",
        "lbl_hotkeys": "快捷鍵",
        "lbl_ocr_desc": "本地 EasyOCR 辨識文字座標，Google 翻譯",
        "session_elapsed": "錄製中  {t}",
        "session_elapsed_h": "{h}時{m:02d}分{s:02d}秒",
        "session_elapsed_m": "{m}分{s:02d}秒",
        "session_elapsed_s": "{s}秒",
        "title_playback_live": "🎬 LangForge 延遲播放 — {name}",
        "title_playback_replay": "🎬 回放 — {name}",
        "lbl_playback_lag": "{ts}  落後 {lag}",
        "lbl_session_ended_live": "錄製中",
        "lbl_session_info": "{name}  {start} → {end}  共 {frames} 幀  {plat}",
        "dlg_confirm_delete": "確認刪除",
        "dlg_delete_session": "刪除場次「{name}」及所有截圖？此操作不可復原。",
        "dlg_add_category": "新增主類別",
        "dlg_rename_category": "改名主類別",
        "dlg_add_platform": "新增平台",
        "dlg_rename_platform": "改名平台",
        "dlg_name_prompt": "名稱:",
        "dlg_new_name_prompt": "新名稱:",
        "status_model_list_updated": "已更新 {engine} 模型清單（{n} 個）",
        "status_fetching_models":     "{engine} 模型清單更新中...",
        "status_fetch_models_failed": "{engine} API 無回應，已套用內建清單",
        "lbl_guide_toggle_on": "開啟",
        "lbl_guide_toggle_off": "關閉",
        "dlg_file_title": "選擇圖片檔案",
        "dlg_file_types_img": "圖片檔案",
        "dlg_file_types_all": "所有檔案",
        "guide_section_header": "▎目前攻略內容",
        "guide_parse_fail": "（解析失敗）",
        "status_queue_cleared": "已清空佇列（{n} 筆）",
        "status_queue_empty": "佇列已是空的",
        "status_auto_switched": "自動切換至 {engine} / {model}",
        "status_quota_exhausted_hint": "所有引擎額度已用完，請明日再試或新增自訂引擎",
        "lf_overlay_settings": "疊字顯示設定",
        "lbl_font_size": "字體大小:",
        "lbl_auto_switch": "自動備援設定:",
        "cb_auto_switch_skip_no_key": "只考慮已填入 API Key 的引擎",
    },
    "en": {
        # ── Tabs ──
        "tab_translate": "  Translate  ",
        "tab_capture": "  Capture  ",
        "tab_quota": "  Quota  ",
        "tab_history": "  History  ",
        "tab_guide": "  Guide  ",
        "tab_session": "  Sessions  ",
        # ── Tab1 ──
        "lbl_engine": "Engine:",
        "lbl_trans_options": "Translation Options",
        "lf_cloud_engine": "Engine",
        "rb_engine_cloud": "☁ Cloud Engine",
        "rb_engine_local": "🦙 Local (OLLAMA)",
        "rb_engine_ocr": "🔍 Local OCR+Google Translate",
        "msg_lang_changed_zh": "UI language set to Chinese. Restart to apply.",
        "msg_delete_cat": 'Delete category "{cat}" and all its platforms?',
        "status_save_fail": "Save failed: {err}",
        "lbl_ollama_hint": "(Recommended 30~120, adjust by model size)",
        "title_translate": "Translation",
        "title_guide": "Guide Info",
        "playback_done": "Playback Complete",
        "btn_pause": "⏸ Pause",
        "btn_resume": "▶ Resume",
        "title_plat_editor": "Platform Editor",
        "lbl_plat_cat": "Game Platforms (platforms.json)",
        "lbl_emu_cat": "Emulators (emulators.json)",
        "lf_main_cat": "Category",
        "lf_platform_list": "Platform",
        "btn_add_short": "Add",
        "btn_rename": "Rename",
        "btn_delete_short": "Delete",
        "btn_close": "Close",
        "btn_save": "Save",
        "status_saved": "✓ Saved",
        "status_no_win_detect": "No valid window detected",
        "progress_unknown": "(Progress unrecognized)",
        "lbl_timeout_hint": "(Recommended 30~120, adjust by model size)",
        "status_hotkey_set_fail": "Hotkey setup failed: {e}",
        "status_guide_hotkey_fail2": "Guide hotkey setup failed: {e}",
        "status_win_exists": "Window already exists: {name}",
        "status_img_loading": "Loading image...",
        "status_img_load_fail": "Failed to load image",
        "status_no_target_win": "Please set target window title first",
        "hint_no_target": "Please add a capture window",
        "status_quota_exhausted": "All model quotas exhausted",
        "status_auto_switched": "Auto-switched to {model}",
        "status_no_key": "Please enter API Key",
        "status_no_key_eng": "Please enter {engine} API Key",
        "status_guide_json_fail": "Guide JSON parse failed (see PowerShell)",
        "status_429_wait": "429 rate limit, retry after {sec}s",
        "status_key_invalid": "API Key invalid or expired, please verify",
        "status_key_invalid2": "API Key invalid or expired",
        "status_key_invalid_eng": "API Key invalid or expired, check {engine} Key",
        "status_combo_done": "Translate+Guide done",
        "status_json_fail": "JSON parse failed (see PowerShell)",
        "status_error": "Error: {msg}",
        "status_parse_error": "Parse error: {msg}",
        "status_done": "Translation done",
        "status_ocr_running": "OCR analyzing...",
        "status_ocr_no_easyocr": "Missing easyocr, run pip install easyocr",
        "status_ocr_no_text": "No confident text detected by OCR",
        "status_ocr_fail": "OCR failed: {msg}",
        "status_gt_fail": "Google Translate failed: {msg}",
        "status_ocr_no_result": "OCR no valid results",
        "status_ocr_done": "OCR done ({n} segments)",
        "status_bad_request": "Bad request format, model may not support images",
        "status_server_error": "{engine} server error, try later",
        "status_network_fail": "Network connection failed, check your network",
        "status_api_fail": "API failed: {msg}",
        "lbl_queue": "Queue",
        "lbl_cooldown": "Cooldown",
        "status_cooling": "{model} cooldown, wait {wait}s",
        "status_analyzing": "{engine} ({model}) analyzing...",
        "status_combo_analyzing": "{engine} ({model}) translate+guide...",
        "status_ocr_translating": "OCR → Google Translate...",
        "status_ollama_running": "OLLAMA running... (timeout={t}s)",
        "status_ollama_done": "OLLAMA done ({n} segments)",
        "status_ollama_empty": "OLLAMA finished — no translatable text found",
        "status_ollama_aborted": "OLLAMA aborted (unexpected response)",
        "status_guide_done": "Guide analysis done",
        "status_guide_fail": "Guide analysis failed",
        "status_combined_fail": "Combined request failed",
        "status_win_missing": "Target window not found",
        "status_pkg_missing": "Missing package: {pkg}, run pip install {pkg}",
        "status_429": "429 quota exceeded, try later or switch model",
        "status_503": "{model} busy, try later",
        "status_503b": "{model} busy, try later or switch model",
        "status_default_ok": "Default saved: {engine} / {model}",
        "all_games": "All Games",
        "all_windows": "All Windows",
        "all_platforms": "All Platforms",
        "ind_auto": "Auto",
        "ind_guide": "Guide",
        "ind_hotkey": "Hotkey",
        "ind_guide_hotkey": "G.Key",
        "lbl_available": "Available",
        "stable_hint": "(Diff 0~255, Count×500ms=wait sec)",
        "th_size": "Size",
        "btn_open_playback": "Open Playback",
        "btn_session_delete": "Delete Session",
        "btn_session_replay": "▶ Replay Session",
        "btn_start_session": "Start Recording",
        "btn_stop_playback": "■ Stop Playback",
        "btn_stop_session": "End Session",
        "btn_stop_session_inline": "Stop Recording",
        "cb_use_ollama": "Use OLLAMA (ignore cloud API Key)",
        "cb_vision_filter": "Show VLM only (Vision Language Models)",
        "lbl_ollama_detected": "Local OLLAMA detected. Installed models:",
        "lbl_ollama_timeout": "Timeout(s):",
        "lf_ollama": "🦙 OLLAMA Local Engine",
        "lf_session": "Session Recording",
        "session_idle": "Idle",
        "session_no_select": "Please select a session",
        "session_recording": "Recording...",
        "status_builtin_no_remove": "Built-in models cannot be removed",
        "status_default_saved": "Default saved: {engine} / {model}",
        "status_guide_hotkey_fail": "Guide hotkey failed: {err}",
        "status_hotkey_fail": "Hotkey failed: {err}",
        "status_hotkey_on": "Enabled: {key}",
        "status_keyboard_need": "keyboard module required: pip install keyboard",
        "status_model_added": "Added: {model}",
        "status_model_exists": "Model already exists: {model}",
        "status_model_removed": "Removed: {model}",
        "status_no_model_remove": "No model found to remove",
        "status_ollama_fail": "OLLAMA call failed: {err}",
        "status_ollama_no_model": "Please select an OLLAMA model",
        "status_ollama_timeout": "OLLAMA timed out. Increase Timeout or use a smaller model",
        "status_queue_full": "Queue full (max 10). Please wait.",
        "status_queue_waiting": "Queued ({n} tasks)",
        "status_win_added": "Added: {name}",
        "status_win_notfound": "Not found: {name}",
        "status_win_removed": "Removed: {name}",
        "th_session_frames": "Frames",
        "th_session_game": "Game",
        "th_session_plat": "Platform",
        "th_session_start": "Started",
        "btn_capture_trans": "Capture & Translate",
        "btn_default_engine": "Set as Default",
        "btn_ok": "OK",
        "lbl_diff_threshold": "Diff Threshold",
        "rb_winmode_corner": "Corner",
        "lbl_api_key": "Gemini API Key:",
        "lbl_model": "Model:",
        "btn_default_engine": "Set as Default",
        "lbl_custom_model": "Custom Model:",
        "btn_add": "Add",
        "btn_cancel": "Cancel",
        "btn_remove": "Remove",
        "lf_lang": "Language",
        "lbl_src_lang": "Game Language:",
        "lbl_tgt_lang": "Target Language:",
        "lbl_layout": "Text Layout:",
        "rb_horizontal": "Horizontal (L→R)",
        "rb_vertical": "Vertical (Top→Bottom, R→L)",
        "lf_platform": "Record Game Platform as...",
        "rb_platform_mode": "By Platform",
        "rb_emulator_mode": "By Emulator",
        "lbl_category": "Category:",
        "lbl_platform": "Platform:",
        "btn_capture_trans": "Capture & Translate",
        "btn_file_trans": "File Translate",
        "btn_guide": "Guide Info",
        "btn_auto_cap_on": "Stop Auto Capture",
        "btn_auto_cap_off": "Auto Capture",
        "btn_auto_cap_tooltip": "Enable auto capture in the Capture Settings tab",
        "btn_clear_queue": "Clear Pending Tasks",
        "btn_refresh_models": "Refresh Models",
        "btn_refresh_ollama": "Re-detect",
        "status_ready": "Status: Ready",
        # ── Tab2 ──
        "lbl_target_win": "Target Window Title:",
        "lbl_target_win_tooltip": "Enter partial window title to match",
        "btn_pick_window": "🖱 Pick Window",
        "lbl_pick_hint": "Click target window within 5s…",
        "lbl_crop_top": "Crop Top (px):",
        "lbl_crop_hint": "(menu bar height, 0=no crop)",
        "lf_winmode": "Window Attach Mode",
        "rb_winmode_main": "Follow Main Window",
        "rb_winmode_mesen": "Follow Target Window",
        "rb_winmode_corner": "Screen Corner (Translate TR / Guide BR)",
        "rb_winmode_sides": "Target Window Sides (Guide Left / Translate Right)",
        "lbl_hotkey": "Capture Hotkey:",
        "btn_enable": "Enable",
        "btn_disable": "Disable",
        "lbl_hotkey_off": "Disabled",
        "lbl_guide_hotkey": "Guide Hotkey:",
        "cb_combo_guide": "Request guide on capture",
        # ── Auto Translate ──
        "lf_auto_trans": "Auto Capture",
        "cb_auto_trans": "Enable Scene-Stable Auto Translate",
        "lbl_diff_threshold": "Diff Threshold:",
        "lbl_stable_count": "Stable Count:",
        "status_on": "Running",
        "status_off": "Off",
        "lbl_combo_on": "ON",
        "lbl_combo_off": "OFF",
        "lbl_screen": "Main Window Position:",
        # ── Tab3 ──
        "lbl_quota_title": "Today's Engine Usage",
        "btn_refresh": "🔄 Refresh",
        # ── Tab4 ──
        "lbl_game": "Game:",
        "lbl_window": "Window:",
        "lbl_platform_f": "Platform:",
        "btn_delete": "Delete",
        "th_id": "#",
        "th_time": "Time",
        "th_model": "Model",
        "th_rom": "ROM Name",
        "th_window": "Window",
        "th_platform": "Platform",
        "lf_fix_platform": "Fix Platform",
        "lbl_fix_mode": "Mode:",
        "lbl_fix_cat": "Category:",
        "lbl_fix_plat": "Platform:",
        "btn_apply_plat": "Apply to All Records of This Game",
        "btn_overlay": "Overlay ✓",
        "btn_plain": "Plain     ",
        # ── Tab5 ──
        "th_progress": "Progress",
        "lbl_curr_prog": "[Current Progress]",
        "lbl_curr_guide": "[Guide Suggestions]",
        # ── Tab3 quota table columns ──
        "th_engine": "Engine",
        "th_used": "Used",
        "th_limit": "Limit",
        "quota_no_limit": "No Quota",
        "quota_conservative": "Est.(50)",
        "quota_no_free": "⚠ No Free Quota",
        "quota_switch": "No free quota (limit=0), please switch model",
        "quota_estimated": "Est.{n}",
        # ── Menu ──
        "menu_file": "File",
        "menu_exit": "Exit",
        "menu_view": "View",
        "menu_switch_lang": "Switch UI Language",
        "menu_lang_zh": "中文",
        "menu_lang_en": "English",
        "menu_switch_theme": "Switch Theme",
        "menu_theme_dark": "Dark",
        "menu_theme_light": "Light",
        "menu_edit_platforms": "Platform Editor",
        "menu_help": "Help",
        "menu_tutorial": "LangForge Tutorial",
        "menu_platform_editor": "Platform Editor",
        "menu_about": "About LangForge",
        # ── Status ──
        "status_reading": "Loading image...",
        "status_img_fail": "Image load failed",
        "status_capturing": "Capturing screen...",
        "status_no_win": "Target window not found",
        "status_guide_analyzing": "Analyzing guide...",
        "status_guide_done": "Guide analysis complete",
        "status_trans_done": "Translation complete",
        "status_no_key": "Please enter API Key",
        "status_quota_done": "All model quotas exhausted",
        "status_key_needed": "Please enter {engine} API Key",
        "status_keyboard_need": "keyboard module required: pip install keyboard",
        "status_hotkey_fail": "Hotkey setup failed: {err}",
        "status_guide_hotkey_fail": "Guide hotkey setup failed: {err}",
        "status_win_exists": "Window already exists: {name}",
        "status_win_added": "Added: {name}",
        "status_win_notfound": "Not found: {name}",
        "status_win_removed": "Removed: {name}",
        "status_model_exists": "Model already exists: {model}",
        "status_model_added": "Added: {model}",
        "status_model_removed": "Removed: {model}",
        "status_builtin_no_remove": "Built-in models cannot be removed",
        "status_no_model_remove": "No removable model found",
        "status_default_saved": "Default saved: {engine} / {model}",
        "status_hotkey_on": "Active: {key}",
        "status_queue_full": "Request queue full (max 10), please wait",
        "status_queue_waiting": "Queue waiting ({n} tasks)",
        # ── OLLAMA ──
        "lf_ollama": "🦙 OLLAMA Local Engine",
        "lbl_ollama_detected": "Local OLLAMA detected. Installed models:",
        "cb_use_ollama": "Use OLLAMA (ignore cloud API Key)",
        "lbl_ollama_timeout": "Timeout(s):",
        "cb_vision_filter": "VLM (Vision-Language Model) only",
        "lf_session": "Session Recording",
        "btn_start_session": "Start Session",
        "btn_stop_session_inline": "Stop Recording",
        "btn_stop_session": "Stop Session",
        "btn_open_playback": "Open Playback",
        "session_idle": "Idle",
        "session_recording": "Recording...",
        "th_session_game": "Game",
        "th_session_start": "Started",
        "th_session_frames": "Frames",
        "th_session_plat": "Platform",
        "btn_session_replay": "▶ Replay Session",
        "btn_session_delete": "Delete Session",
        "session_no_select": "Please select a session",
        "btn_stop_playback": "■ Stop Playback",
        "status_ollama_timeout": "OLLAMA timeout — increase Timeout or use a smaller model",
        "status_ollama_fail": "OLLAMA call failed: {err}",
        "status_ollama_no_model": "Please select an OLLAMA model",
        # ── hardcoded補全 ──
        "lf_actions": "Actions",
        "lbl_hotkeys": "Hotkeys",
        "lbl_ocr_desc": "Local EasyOCR detects text coords, Google Translate",
        "session_elapsed": "Recording  {t}",
        "session_elapsed_h": "{h}h {m:02d}m {s:02d}s",
        "session_elapsed_m": "{m}m {s:02d}s",
        "session_elapsed_s": "{s}s",
        "title_playback_live": "🎬 LangForge Live Playback — {name}",
        "title_playback_replay": "🎬 Replay — {name}",
        "lbl_playback_lag": "{ts}  behind {lag}",
        "lbl_session_ended_live": "Recording",
        "lbl_session_info": "{name}  {start} → {end}  {frames} frames  {plat}",
        "dlg_confirm_delete": "Confirm Delete",
        "dlg_delete_session": "Delete session \"{name}\" and all screenshots? This cannot be undone.",
        "dlg_add_category": "Add Category",
        "dlg_rename_category": "Rename Category",
        "dlg_add_platform": "Add Platform",
        "dlg_rename_platform": "Rename Platform",
        "dlg_name_prompt": "Name:",
        "dlg_new_name_prompt": "New name:",
        "status_model_list_updated": "{engine} model list updated ({n} models)",
        "status_fetching_models":     "Fetching {engine} model list...",
        "status_fetch_models_failed": "{engine} API unavailable, using built-in list",
        "lbl_guide_toggle_on": "On",
        "lbl_guide_toggle_off": "Off",
        "dlg_file_title": "Select Image File",
        "dlg_file_types_img": "Image Files",
        "dlg_file_types_all": "All Files",
        "guide_section_header": "▎Guide Content",
        "guide_parse_fail": "(parse failed)",
        "status_queue_cleared": "Queue cleared ({n} tasks)",
        "status_queue_empty": "Queue is already empty",
        "status_auto_switched": "Auto-switched to {engine} / {model}",
        "status_quota_exhausted_hint": "All engine quotas exhausted. Try again tomorrow or add a custom engine.",
        "lf_overlay_settings": "Overlay Settings",
        "lbl_font_size": "Font Size:",
        "lbl_auto_switch": "Auto-fallback:",
        "cb_auto_switch_skip_no_key": "Only engines with API Key filled in",
    },
}


def S(key: str) -> str:
    return UI_STRINGS.get(CURRENT_LANG, UI_STRINGS["zh"]).get(key, key)


CURRENT_LANG = "zh"  # 預設值；__init__ 讀取 config 後更新


# ==========================================
# 螢幕偵測
# ==========================================
def _get_monitors():
    try:
        import ctypes

        monitors = []

        def _cb(hMonitor, hdcMonitor, lprcMonitor, dwData):
            r = lprcMonitor.contents
            monitors.append({"x": r.left, "y": r.top, "w": r.right - r.left, "h": r.bottom - r.top})
            return 1

        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(ctypes.wintypes.RECT), ctypes.c_double
        )
        ctypes.windll.user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(_cb), 0)
        result = []
        for i, m in enumerate(monitors):
            label = f'Screen {i+1}  ({m["w"]}x{m["h"]})' if CURRENT_LANG == "en" else f'螢幕 {i+1}  ({m["w"]}x{m["h"]})'
            result.append({"index": i + 1, "label": label, **m})
        return result if result else [{"index": 1, "label": "螢幕 1", "x": 0, "y": 0, "w": 1920, "h": 1080}]
    except Exception:
        return [
            {
                "index": 1,
                "label": "Screen 1  (1920x1080)" if CURRENT_LANG == "en" else "螢幕 1  (1920x1080)",
                "x": 0,
                "y": 0,
                "w": 1920,
                "h": 1080,
            }
        ]


# ==========================================
# 配置與流量控制
# ==========================================
IMG_SMALL_THRESHOLD  = 512
IMG_MEDIUM_THRESHOLD = 1280

IMG_CLOUD_SMALL  = (None, 85)
IMG_CLOUD_MEDIUM = (1024, 80)
IMG_CLOUD_LARGE  = (1280, 75)

IMG_OLLAMA_SMALL  = (None, 85)
IMG_OLLAMA_MEDIUM = (800,  75)
IMG_OLLAMA_LARGE  = (1024, 70)

DISPLAY_WIDTH_SMALL      = 512
DISPLAY_WIDTH_MEDIUM_PX1 = 700    # 原圖 513～700px 時輸出
DISPLAY_WIDTH_MEDIUM_PX2 = 1024   # 原圖 701～1280px 時輸出
DISPLAY_WIDTH_LARGE      = 1280
DISPLAY_INIT_HEIGHT = 600
PLAYBACK_FPS_MS = 500  # 播放間隔 ms（2fps）
PLAYBACK_DELAY_SECONDS = 600  # 延遲播放秒數（10分鐘）
SESSION_CAPTURE_INTERVAL_MS = 500  # 場次截圖間隔 ms
SESSION_STABLE_COUNT = 4  # 畫面穩定判定次數
SESSION_STABLE_DIFF = 10  # 畫面穩定差異門檻
REQUEST_QUEUE_MAXSIZE = 10
_request_queue = queue.Queue(maxsize=REQUEST_QUEUE_MAXSIZE)

KEY_FILE = os.path.join(CONFIG_DIR, "configs.json")
DEFAULT_HOTKEY = "ctrl+f2"
LAST_REQUEST_TIME = {}  # {model_name: timestamp} 各模型獨立計時
COOLDOWN_SECONDS_DEFAULT = 13


# ==========================================
# API Key 混淆（XOR + base64，以機器 ID 為 salt）
# ==========================================
def _get_machine_salt() -> bytes:
    salt_src = ""
    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
        salt_src, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
    except Exception:
        pass
    if not salt_src:
        try:
            import uuid

            salt_src = str(uuid.getnode())
        except Exception:
            salt_src = "LangForge-fallback-salt-2026"
    raw = salt_src.encode("utf-8")
    return (raw * (48 // len(raw) + 1))[:48]


_OBFUSCATED_PREFIX = "LF1:"


def obfuscate_key(plaintext: str) -> str:
    if not plaintext:
        return ""
    import base64

    salt = _get_machine_salt()
    data = plaintext.encode("utf-8")
    xored = bytes(b ^ salt[i % len(salt)] for i, b in enumerate(data))
    return _OBFUSCATED_PREFIX + base64.b64encode(xored).decode("ascii")


def deobfuscate_key(encoded: str) -> str:
    if not encoded:
        return ""
    if not encoded.startswith(_OBFUSCATED_PREFIX):
        return encoded
    import base64

    try:
        xored = base64.b64decode(encoded[len(_OBFUSCATED_PREFIX) :])
        salt = _get_machine_salt()
        plain = bytes(b ^ salt[i % len(salt)] for i, b in enumerate(xored))
        return plain.decode("utf-8")
    except Exception:
        return encoded


STABLE_CHECK_INTERVAL_MS = 500  # 每次截圖間隔
STABLE_COUNT_DEFAULT = 4  # 連續穩定次數門檻（4×500ms=2秒）
STABLE_DIFF_DEFAULT = 10  # 像素差異平均值門檻（0~255）

# ══════════════════════════════════════════
# 語言 → 字體對應（依目標語言選擇合適字體）
# ══════════════════════════════════════════
# Windows 內建字體優先，依語言降序 fallback
LANG_FONT_CANDIDATES = {
    "Korean": ["malgun.ttf", "malgunbd.ttf", "gulim.ttc", "batang.ttc", "msjh.ttc"],
    "Japanese": ["meiryo.ttc", "yumin.ttf", "msgothic.ttc", "msjh.ttc"],
    "Russian": ["arial.ttf", "times.ttf", "msjh.ttc"],
    "French": ["arial.ttf", "msjh.ttc"],
    "German": ["arial.ttf", "msjh.ttc"],
    "Spanish": ["arial.ttf", "msjh.ttc"],
    "Italian": ["arial.ttf", "msjh.ttc"],
    "Portuguese": ["arial.ttf", "msjh.ttc"],
    "default": ["msjh.ttc", "msyh.ttc", "arial.ttf"],
}


def _get_font_for_lang(tgt_lang: str, size: int):
    import os

    # 從 tgt_lang 字串抽取語言關鍵字（去掉括號部分）
    lang_key = tgt_lang.split("(")[0].strip()
    # 找對應候選清單
    candidates = None
    for k in LANG_FONT_CANDIDATES:
        if k.lower() in lang_key.lower():
            candidates = LANG_FONT_CANDIDATES[k]
            break
    if candidates is None:
        candidates = LANG_FONT_CANDIDATES["default"]

    win_fonts = "C:/Windows/Fonts"
    for fname in candidates:
        fpath = os.path.join(win_fonts, fname)
        try:
            return ImageFont.truetype(fpath, size)
        except Exception:
            pass
    # 最終 fallback
    return ImageFont.load_default()


# ══════════════════════════════════════════
# 語言選項
# ══════════════════════════════════════════
GAME_LANGUAGES = [
    "All Foreign Text On The Screen(畫面上所有外文)",
    "Traditional Chinese(正體中文)",
    "Japanese(日文)",
    "English(英文)",
    "Simplified Chinese(簡體中文)",
    "Korean(韓文)",
    "French(法文)",
    "German(德文)",
    "Spanish(西班牙文)",
    "Italian(義大利文)",
    "Portuguese(葡萄牙文)",
    "Russian(俄文)",
]

TARGET_LANGUAGES = [
    "Traditional Chinese(正體中文)",
    "Simplified Chinese(簡體中文)",
    "English(英文)",
    "Japanese(日文)",
    "Korean(韓文)",
    "French(法文)",
    "German(德文)",
    "Spanish(西班牙文)",
    "Italian(義大利文)",
    "Portuguese(葡萄牙文)",
    "Russian(俄文)",
]

# ══════════════════════════════════════════
# 每個模型的每日限額（RPD）— 依各平台後台實際數據（2026/04）
# ══════════════════════════════════════════
MODEL_DAILY_LIMITS = {
    # ── Gemini ──
    "gemini-3-flash":           500,   # 新一代 Flash，免費配額縮減版
    "gemini-3.1-flash-lite":    500,   # 最便宜新一代，免費配額縮減版
    "gemini-2.5-flash":          20,   # RPM=5，免費 20 RPD
    "gemini-2.5-flash-lite":    500,   # GA，高配額 500 RPD
    "gemini-3.1-pro":             0,   # 付費，無免費配額
    # ── Groq 免費版 ──
    "meta-llama/llama-4-scout-17b-16e-instruct": 1000,   # RPM=30
    "openai/gpt-oss-120b": 500,             # Maverick 替代，RPM=30
    # ── Mistral ──
    "mistral-small-latest": 500,            # 視覺支援，RPM=30
    "mistral-medium-latest": 500,           # 旗艦視覺（最新穩定），RPM=20
    # ── OpenAI（付費） ──
    "gpt-4.1-mini": 500,
    "gpt-4.1": 500,
    "gpt-4o": 500,
    # ── Claude（付費） ──
    "claude-sonnet-4-6": 500,
    "claude-haiku-4-5-20251001": 500,
    "claude-opus-4-6": 500,
    # ── Grok / xAI（付費） ──
    "grok-2-vision-1212": 500,
    "grok-4": 500,
}

# 各模型 RPM（用於冷卻計算；未列的使用預設）
MODEL_RPM = {
    "gemini-3-flash":        15,
    "gemini-3.1-flash-lite": 30,
    "gemini-2.5-flash":       5,
    "gemini-2.5-flash-lite": 30,
    "gemini-3.1-pro":        10,
    "meta-llama/llama-4-scout-17b-16e-instruct": 30,
    "openai/gpt-oss-120b": 30,
    "mistral-small-latest": 30,
    "mistral-medium-latest": 20,
    "gpt-4.1-mini": 60,
    "gpt-4.1": 30,
    "gpt-4o": 30,
}

# ══════════════════════════════════════════
# 引擎定義（順序：Gemini → Groq → Mistral → OpenAI → Claude → Grok）
# ══════════════════════════════════════════
ENGINE_ORDER = ["gemini", "groq", "mistral", "openai", "claude", "grok"]

ENGINE_DISPLAY = {
    "gemini": "Gemini",
    "groq": "Groq",
    "mistral": "Mistral",
    "openai": "OpenAI",
    "claude": "Claude",
    "grok": "Grok",
}

ENGINE_MODELS = {
    "gemini": [
        "gemini-3-flash",                  # 推薦：新一代 Flash，效能優於 2.5
        "gemini-3.1-flash-lite",           # 高配額免費，適合大量請求
        "gemini-2.5-flash",                # 穩定版，免費 20 RPD
        "gemini-2.5-flash-lite",           # GA，高配額 500 RPD
        "gemini-3.1-pro",                  # 付費旗艦
    ],
    "groq": [
        "meta-llama/llama-4-scout-17b-16e-instruct",  # 推薦：1000 RPD，視覺
        "openai/gpt-oss-120b",                         # 高品質推理（Maverick 替代）
    ],
    "mistral": [
        "mistral-small-latest",   # 視覺支援，高配額
        "mistral-medium-latest",  # 旗艦視覺（指向最新穩定版）
    ],
    "openai": [
        "gpt-4.1-mini",  # 低成本視覺，推薦
        "gpt-4.1",       # 高效能視覺
        "gpt-4o",        # 多模態旗艦
    ],
    "claude": [
        "claude-sonnet-4-6",          # 最新 Sonnet
        "claude-haiku-4-5-20251001",  # 快速低成本
        "claude-opus-4-6",            # 旗艦
    ],
    "grok": [
        "grok-2-vision-1212",  # 穩定視覺模型
        "grok-4",              # 旗艦多模態（2025/07）
    ],
}

ENGINE_DEFAULT_MODEL = {
    "gemini": "gemini-3-flash",
    "groq": "meta-llama/llama-4-scout-17b-16e-instruct",
    "mistral": "mistral-small-latest",
    "openai": "gpt-4.1-mini",
    "claude": "claude-sonnet-4-6",
    "grok": "grok-2-vision-1212",
}

ALL_MODELS = []
for models in ENGINE_MODELS.values():
    ALL_MODELS.extend(models)


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


# ==========================================
# JSON 配置管理（按模型追蹤配額）
# ==========================================
def _get_pacific_date():
    from datetime import datetime, timezone, timedelta

    utc_now = datetime.now(timezone.utc)
    # 判斷是否為日光節約時間（3月第2週日～11月第1週日）
    year = utc_now.year
    # 3月第2個週日
    mar1 = datetime(year, 3, 1, tzinfo=timezone.utc)
    dst_start = mar1 + timedelta(days=(6 - mar1.weekday()) % 7 + 7)  # 第2個週日
    dst_start = dst_start.replace(hour=10)  # UTC 10:00 = PST 02:00
    # 11月第1個週日
    nov1 = datetime(year, 11, 1, tzinfo=timezone.utc)
    dst_end = nov1 + timedelta(days=(6 - nov1.weekday()) % 7)  # 第1個週日
    dst_end = dst_end.replace(hour=9)  # UTC 09:00 = PDT 02:00
    if dst_start <= utc_now < dst_end:
        offset = timedelta(hours=-7)  # PDT
    else:
        offset = timedelta(hours=-8)  # PST
    pacific_now = utc_now + offset
    return pacific_now.strftime("%Y-%m-%d")


def _default_used_today():
    return {m: 0 for m in ALL_MODELS}


def _detect_ui_lang() -> str:
    try:
        import locale

        lang = locale.getlocale()[0] or ""
        if not lang:
            lang = locale.setlocale(locale.LC_ALL, "")
    except Exception:
        lang = ""
    return "zh" if lang.lower().startswith("zh") else "en"


def load_config():
    today = _get_pacific_date()
    default = {eng: "" for eng in ENGINE_ORDER}
    default.update({"used_today": _default_used_today(), "date": today})
    default["hotkey"] = DEFAULT_HOTKEY
    default["ui_lang"] = _detect_ui_lang()  # 依系統語系自動決定預設介面語言

    if not os.path.exists(KEY_FILE):
        return default
    try:
        with open(KEY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data.get("date") != today:
            data["date"] = today
            data["used_today"] = _default_used_today()

        used = data.get("used_today")
        if isinstance(used, int):
            new_used = _default_used_today()
            new_used["gemini-2.5-flash"] = used
            data["used_today"] = new_used
        elif isinstance(used, dict):
            # 舊版 engine-level → 遷移
            old_engines = ["gemini", "openai", "claude"]
            if any(k in used for k in old_engines) and not any(k in used for k in ALL_MODELS):
                new_used = _default_used_today()
                for eng in old_engines:
                    if eng in used:
                        dm = ENGINE_DEFAULT_MODEL.get(eng, "")
                        if dm:
                            new_used[dm] = used[eng]
                data["used_today"] = new_used
            else:
                for m in ALL_MODELS:
                    data["used_today"].setdefault(m, 0)
        else:
            data["used_today"] = _default_used_today()

        for provider in ENGINE_ORDER:
            data.setdefault(provider, "")
            if data[provider]:
                raw = data[provider]
                data[provider] = deobfuscate_key(raw)
                encrypted = raw.startswith(_OBFUSCATED_PREFIX)
        data.setdefault("hotkey", DEFAULT_HOTKEY)
        data.setdefault("ui_lang", _detect_ui_lang())
        data.setdefault("overlay_font_size", OVERLAY_FONT_SIZE_DEFAULT)
        data.setdefault("auto_switch_skip_no_key", True)
        data.setdefault("cached_models", {})
        data.setdefault("learned_zero_quota", [])
        data.setdefault("custom_quota", {})
        data.setdefault("estimated_quota_models", [])
        # 還原學習到的 limit=0 模型
        for _m in data.get("learned_zero_quota", []):
            MODEL_DAILY_LIMITS[_m] = 0
        # 還原使用者/程式自訂的配額覆寫
        for _m, _v in data.get("custom_quota", {}).items():
            MODEL_DAILY_LIMITS[_m] = _v
        data["auto_trans"] = False  # 自動翻譯不記憶，每次啟動固定關閉
        return data
    except Exception as e:
        log(f"載入配置失敗: {e}")
        return default


def save_config(data):
    try:
        data["date"] = _get_pacific_date()
        # 儲存前將 API Key 混淆，避免明文寫入 configs.json
        save_data = dict(data)
        for provider in ENGINE_ORDER:
            if save_data.get(provider):
                save_data[provider] = obfuscate_key(save_data[provider])
        with open(KEY_FILE, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"儲存配置失敗: {e}")


# ==========================================
# 翻譯 Prompt（五引擎共用，動態語言帶入）
# ==========================================
def build_translate_prompt(src_lang: str, tgt_lang: str) -> str:
    if src_lang.startswith("All Foreign Text"):
        src_desc = "所有非母語的外文文字（無論何種語言）"
        no_text_cond = "沒有需要翻譯的外文"
    else:
        src_desc = f"{src_lang} 文字"
        no_text_cond = f"沒有 {src_lang} 文字"
    return (
        f"你是遊戲翻譯專家。請辨識這張遊戲截圖中所有的 {src_desc}，"
        f"並將每一段翻譯成 {tgt_lang}。"
        f"注意：'tw' 欄位必須填入 {tgt_lang} 的翻譯結果，絕對不要填入原文。\n"
        "【專有名詞規則】以下類型請直接保留原文，不要翻譯：\n"
        "- 角色名稱、人名（例如：ルナナ、アグラニ 等）\n"
        "- 遊戲內地名、場所名稱（例如：アグラニの村、ダーマ神殿 等）\n"
        "- 遊戲專有技能名、道具名、組織名、種族名\n"
        "- 難以用目標語言表達、只能音譯的固有名詞\n"
        "若整段文字只有角色名稱或專有名詞（無實質對話內容），仍需回傳，'tw' 填入原文。\n"
        "回傳格式為純 JSON 列表（不要包含 markdown 標記），每個元素包含：\n"
        f"- 'tw': 翻譯結果（{tgt_lang}，專有名詞保留原文，其餘翻譯）\n"
        "- 'x': 文字區塊左上角的水平位置（必須是 0.0~1.0 之間的小數比例值，絕對不可以是像素數值）\n"
        "- 'y': 文字區塊左上角的垂直位置（必須是 0.0~1.0 之間的小數比例值，絕對不可以是像素數值）\n"
        "- 'w': 文字區塊的寬度（必須是 0.0~1.0 之間的小數比例值）\n"
        "- 'h': 文字區塊的高度（必須是 0.0~1.0 之間的小數比例值）\n"
        "重要：x/y/w/h 全部必須是 0.0~1.0 的浮點數，例如畫面下方 75% 處寫 0.75，不可寫 480 這類像素值。\n"
        "每個視覺上獨立的文字框必須單獨回傳為一個 segment，不同位置的文字不可合併。\n"
        "特別注意：角色名稱框（通常在對話框上方或左側）與對話內容框是兩個不同位置，必須分為兩個 segment 各自回傳，x/y 分別對應各自框的位置。\n"
        "即使多個文字框內容相關（如角色名稱與其對話），只要位置不同就各自獨立回傳，x/y 準確對應各自的位置。\n"
        '範例: [{"tw": "翻譯文字", "x": 0.05, "y": 0.75, "w": 0.4, "h": 0.08}]\n'
        f"如果{no_text_cond}，回傳空列表 []。只回傳 JSON，不要有其他文字。"
    )


def build_guide_prompt(rom_name: str, region: str, tgt_lang: str) -> str:
    return (
        f"你是資深遊戲攻略專家。這是一張來自『{rom_name}』（{region}版本）的遊戲截圖。\n"
        f"請根據截圖中的畫面，以 {tgt_lang} 回覆以下兩段資訊：\n\n"
        "1.【目前進度】用一句話描述玩家目前所在位置與劇情進度。\n"
        "2.【目前攻略內容】列出 3~5 條具體的攻略建議，包含：\n"
        "   - 必拿道具或必做事項\n"
        "   - 首要任務與方向指引\n"
        "   - 隱藏要素或補給提示\n"
        "   - 下一個目標地點\n\n"
        "回傳格式為純 JSON（不要包含 markdown 標記）：\n"
        '{{"progress": "目前進度描述", "guide": ["攻略建議1", "攻略建議2", "攻略建議3"]}}\n'
        "只回傳 JSON，不要有其他文字。"
    )


def build_combined_prompt(rom_name: str, region: str, src_lang: str, tgt_lang: str) -> str:
    if src_lang.startswith("All Foreign Text"):
        src_desc = "所有外文文字"
        no_text_cond = "沒有需要翻譯的外文"
    else:
        src_desc = f"{src_lang} 文字"
        no_text_cond = f"沒有 {src_lang} 文字"
    return (
        f"你是遊戲翻譯與攻略專家。這是一張來自『{rom_name}』（{region}版本）的遊戲截圖。\n"
        "請同時完成以下兩件任務，並以單一 JSON 回傳（不要包含 markdown 標記）：\n\n"
        f"任務一【翻譯】辨識截圖中所有 {src_desc}，翻譯成 {tgt_lang}。\n"
        "【專有名詞規則】以下類型請直接保留原文，不要翻譯：\n"
        "- 角色名稱、人名\n"
        "- 遊戲內地名、場所名稱\n"
        "- 遊戲專有技能名、道具名、組織名、種族名\n"
        "- 難以用目標語言表達、只能音譯的固有名詞\n"
        "若整段文字只有角色名稱或專有名詞，仍需回傳，'tw' 填入原文。\n"
        f"任務二【攻略】根據畫面分析目前進度並給出 {tgt_lang} 攻略建議。\n\n"
        "回傳格式：\n"
        '{{"translations": [{{"tw": "翻譯文字（專有名詞保留原文）", "x": 0.05, "y": 0.75, "w": 0.4, "h": 0.08}}], '
        '"progress": "目前進度描述", '
        '"guide": ["攻略建議1", "攻略建議2", "攻略建議3"]}}\n'
        "注意：\n"
        f"- 'tw' 欄位必須填入 {tgt_lang} 的翻譯結果（專有名詞除外保留原文），絕對不要翻譯專有名詞\n"
        "- x/y/w/h 必須是 0.0~1.0 的浮點數比例值，絕對不可以是像素數值（例如畫面下方 75% 處寫 0.75，不可寫 480）\n"
        "- 角色名稱框與對話內容框位置不同，必須分為兩個 segment 各自回傳\n"
        "- guide 列出 3~5 條具體攻略建議\n"
        f"- 如果{no_text_cond}，translations 為空列表\n"
        "只回傳 JSON，不要有其他文字。"
    )



# ==========================================
# 五引擎 API 呼叫
# ==========================================
def _get_display_width(orig_w: int) -> int:
    if orig_w <= IMG_SMALL_THRESHOLD:
        return DISPLAY_WIDTH_SMALL
    elif orig_w <= 700:
        return DISPLAY_WIDTH_MEDIUM_PX1
    elif orig_w <= IMG_MEDIUM_THRESHOLD:
        return DISPLAY_WIDTH_MEDIUM_PX2
    else:
        return DISPLAY_WIDTH_LARGE


def _prepare_img_for_engine(image_pil, engine_type: str = "cloud"):
    orig_w = image_pil.width
    if engine_type == "ollama":
        if orig_w <= IMG_SMALL_THRESHOLD:
            max_w, quality = IMG_OLLAMA_SMALL
        elif orig_w <= IMG_MEDIUM_THRESHOLD:
            max_w, quality = IMG_OLLAMA_MEDIUM
        else:
            max_w, quality = IMG_OLLAMA_LARGE
    else:
        if orig_w <= IMG_SMALL_THRESHOLD:
            max_w, quality = IMG_CLOUD_SMALL
        elif orig_w <= IMG_MEDIUM_THRESHOLD:
            max_w, quality = IMG_CLOUD_MEDIUM
        else:
            max_w, quality = IMG_CLOUD_LARGE

    if max_w and orig_w > max_w:
        scale = max_w / orig_w
        new_h = int(image_pil.height * scale)
        image_pil = image_pil.resize((max_w, new_h), Image.LANCZOS)
        log(f"[IMG] {engine_type} 縮圖: {orig_w}px → {max_w}px, quality={quality}")
    else:
        log(f"[IMG] {engine_type} 不縮圖: {orig_w}px, quality={quality}")
    return image_pil, quality


def _img_to_jpeg_b64(image_pil, quality: int = 75):
    buf = io.BytesIO()
    image_pil.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _img_to_jpeg_bytes(image_pil, quality: int = 75):
    buf = io.BytesIO()
    image_pil.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _parse_json_response(text):
    cleaned = re.sub(r"```json\s*|```", "", text).strip()

    # 第一次嘗試：直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # ── 自動修復常見格式錯誤 ──
    fixed = cleaned

    # 1) 數值後面多餘引號: 0.092" → 0.092
    fixed = re.sub(r'(\d+\.\d+)"(\s*[},\]])', r"\1\2", fixed)

    # 2) 數值被錯誤包成字串: "0.5" → 0.5（在 x/y/w/h 欄位）
    fixed = re.sub(r'"(\d+\.\d+)"(\s*[},\]])', r"\1\2", fixed)

    # 3) 尾巴多餘逗號: [... , ] → [... ]
    fixed = re.sub(r",\s*([}\]])", r"\1", fixed)

    # 4) 缺少逗號在 }{ 之間: }{ → },{
    fixed = re.sub(r"}\s*{", "},{", fixed)

    # 5) 單引號替換成雙引號
    if "'" in fixed and '"' not in fixed:
        fixed = fixed.replace("'", '"')

    # 5.5) 中文括號引號 「」 被當作字串引號，漏掉 JSON 雙引號
    #      」, " → 」", "  以及  ", 「 → ", "「
    fixed = re.sub(r'」\s*,\s*"', '」", "', fixed)
    fixed = re.sub(r"」\s*}", '」"}', fixed)
    fixed = re.sub(r"」\s*\]", '」"]', fixed)

    # 6) 擷取最外層 JSON（物件 {} 或陣列 []，去掉前後多餘文字）
    # 先嘗試修復尾部多餘的 ] 或 }（常見於 LLM 輸出的 {...}] 或 [...}）
    for _ in range(3):
        fixed_try = re.sub(r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})\s*[\]\}]+$", lambda m: m.group(1), fixed)
        if fixed_try != fixed:
            fixed = fixed_try
            try:
                result = json.loads(fixed)
                log("JSON 自動修復成功（移除尾部多餘括號）")
                return result
            except json.JSONDecodeError:
                pass
            break

    m_obj = re.search(r"\{.*\}", fixed, re.DOTALL)
    m_arr = re.search(r"\[.*\]", fixed, re.DOTALL)
    # 優先取較早出現且較長的匹配
    candidates = []
    if m_obj:
        candidates.append(m_obj.group(0))
    if m_arr:
        candidates.append(m_arr.group(0))
    for candidate in sorted(candidates, key=len, reverse=True):
        try:
            result = json.loads(candidate)
            log("JSON 自動修復成功")
            return result
        except json.JSONDecodeError:
            continue

    # 所有修復都失敗，拋出原始錯誤
    raise ValueError(f"JSON_PARSE_FAIL|json.JSONDecodeError|{text}")


# ==========================================
# 雲端引擎 SDK Client 快取（避免每次呼叫重新建立）
# ==========================================
_ENGINE_CLIENTS: dict = {}  # key: (engine, api_key)


def _get_client(engine: str, api_key: str):
    key = (engine, api_key)
    if key in _ENGINE_CLIENTS:
        return _ENGINE_CLIENTS[key]

    if engine == "gemini":
        from google import genai
        client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
    elif engine == "groq":
        from groq import Groq
        client = Groq(api_key=api_key)
    
    elif engine == "mistral":
        try:
         from mistralai import Mistral
         client = Mistral(api_key=api_key)
        except ImportError:
         raise ImportError(
            "mistralai Package failed to load correctly \n RUN: pip install mistralai\n"
        )

    elif engine == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    elif engine == "claude":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    elif engine == "grok":
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
    else:
        raise ValueError(f"未知引擎: {engine}")

    _ENGINE_CLIENTS[key] = client
    return client


def _invalidate_client(engine: str, api_key: str):
    _ENGINE_CLIENTS.pop((engine, api_key), None)


def call_gemini(api_key, model, image_pil, prompt):
    """Gemini API (google-genai SDK)"""
    from google.genai import types
    client = _get_client("gemini", api_key)
    image_pil, quality = _prepare_img_for_engine(image_pil, "cloud")
    img_bytes = _img_to_jpeg_bytes(image_pil, quality)
    response = client.models.generate_content(
        model=model,
        contents=[
            prompt,
            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
        ],
    )
    return _parse_json_response(response.text)


def call_groq(api_key, model, image_pil, prompt):
    """Groq API (groq SDK — OpenAI 相容 chat.completions + vision)"""
    client = _get_client("groq", api_key)
    image_pil, quality = _prepare_img_for_engine(image_pil, "cloud")
    img_b64 = _img_to_jpeg_b64(image_pil, quality)
    chat_completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                    },
                ],
            }
        ],
        max_completion_tokens=2048,
    )
    return _parse_json_response(chat_completion.choices[0].message.content)


def call_mistral(api_key, model, image_pil, prompt):
    """Mistral API (mistralai SDK — chat.complete + vision)"""
    client = _get_client("mistral", api_key)
    image_pil, quality = _prepare_img_for_engine(image_pil, "cloud")
    img_b64 = _img_to_jpeg_b64(image_pil, quality)
    chat_response = client.chat.complete(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": f"data:image/jpeg;base64,{img_b64}"},
                ],
            }
        ],
        max_tokens=2048,
    )
    return _parse_json_response(chat_response.choices[0].message.content)


def call_openai(api_key, model, image_pil, prompt):
    """OpenAI Responses API (openai SDK)"""
    client = _get_client("openai", api_key)
    image_pil, quality = _prepare_img_for_engine(image_pil, "cloud")
    img_b64 = _img_to_jpeg_b64(image_pil, quality)
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{img_b64}"},
                ],
            }
        ],
    )
    return _parse_json_response(response.output_text)


def call_claude(api_key, model, image_pil, prompt):
    """Claude Messages API (anthropic SDK)"""
    client = _get_client("claude", api_key)
    image_pil, quality = _prepare_img_for_engine(image_pil, "cloud")
    img_b64 = _img_to_jpeg_b64(image_pil, quality)
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return _parse_json_response(message.content[0].text)


def call_grok(api_key, model, image_pil, prompt):
    """Grok / xAI API（OpenAI-compatible，endpoint: api.x.ai）"""
    client = _get_client("grok", api_key)
    image_pil, quality = _prepare_img_for_engine(image_pil, "cloud")
    img_b64 = _img_to_jpeg_b64(image_pil, quality)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ],
            }
        ],
        max_tokens=2048,
    )
    return _parse_json_response(response.choices[0].message.content)


ENGINE_CALLERS = {
    "gemini": call_gemini,
    "groq": call_groq,
    "mistral": call_mistral,
    "openai": call_openai,
    "claude": call_claude,
    "grok": call_grok,
}


# ==========================================
# OLLAMA 本地引擎
# ==========================================
OLLAMA_BASE_URL = "http://localhost:11434"

GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
OVERLAY_FONT_SIZE_MIN     = 10
OVERLAY_FONT_SIZE_MAX     = 36
OVERLAY_FONT_SIZE_DEFAULT = 22
OVERLAY_FONT_SIZE_MAX_DEFAULT = 22   # 自動縮放最大字級
OVERLAY_FONT_SIZE_MIN_CLAMP   = 10   # 自動縮放最小下限
QUOTA_ESTIMATED_DEFAULT = 50         # 未知配額模型首次翻譯成功後套用的保守預設值

OCR_CONF_THRESHOLD = 0.1      # EasyOCR 最低信心值
OCR_MAX_WIDTH = 1280          # 送入 EasyOCR 前限制最大寬度（px）
OCR_TRANSLATE_WORKERS = 8     # Google 翻譯並行執行緒數


def _google_translate(text: str, src_lang: str, tgt_lang: str) -> str:

    try:
        params = urllib.parse.urlencode(
            {
                "client": "gtx",
                "sl": src_lang,
                "tl": tgt_lang,
                "dt": "t",
                "q": text,
            }
        )
        url = f"{GOOGLE_TRANSLATE_URL}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        translated = "".join(part[0] for part in data[0] if part[0])
        return translated.strip() if translated else text
    except Exception:
        return text


LANG_TO_BCP47 = {
    "All Foreign Text On The Screen(畫面上所有外文)": "auto",
    "Traditional Chinese(正體中文)": "zh-TW",
    "Japanese(日文)": "ja",
    "English(英文)": "en",
    "Simplified Chinese(簡體中文)": "zh-CN",
    "Korean(韓文)": "ko",
    "French(法文)": "fr",
    "German(德文)": "de",
    "Spanish(西班牙文)": "es",
    "Italian(義大利文)": "it",
    "Portuguese(葡萄牙文)": "pt",
    "Russian(俄文)": "ru",
}

# EasyOCR 不支援 "auto"；"auto" 模式改為常用多語言組合
_EASYOCR_AUTO_LANGS = ["ja", "en", "ch_sim", "ch_tra", "ko"]

def _resize_for_ocr(image_pil):
    w, h = image_pil.width, image_pil.height
    if w <= OCR_MAX_WIDTH:
        return image_pil, 1.0
    scale = OCR_MAX_WIDTH / w
    new_h = int(h * scale)
    resized = image_pil.resize((OCR_MAX_WIDTH, new_h), Image.LANCZOS)
    return resized, scale


def _bcp47_to_easyocr(bcp47: str) -> list:
    if bcp47 == "auto":
        return _EASYOCR_AUTO_LANGS
    code = bcp47.split("-")[0]
    # EasyOCR 用 ch_sim / ch_tra 而非 zh
    if code == "zh":
        region = bcp47.split("-")[1] if "-" in bcp47 else ""
        return ["ch_tra", "en"] if region.upper() in ("TW", "HK") else ["ch_sim", "en"]
    return [code]

OLLAMA_TIMEOUT = 180  # 預設推理 timeout（秒）；大型視覺模型（如 QWEN2.5VL）需要較長時間


def _detect_ollama_vision_models() -> list:

    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        models = [m["name"] for m in data.get("models", [])]
        log(f"[OLLAMA] 找到 {len(models)} 個已安裝模型")
        return models
    except Exception:
        return []


# 已知具備視覺能力的模型名稱關鍵字（小寫比對）
OLLAMA_VISION_KEYWORDS = [
    # LLaVA 系列
    "llava",
    "bakllava",
    # Meta vision
    "llama3.2-vision",
    # Qwen vision
    "qwen2.5-vl",
    "qwen2.5vl",  # 部分標籤可能省略 dash
    "qwen3-vl",
    "qwen3vl",
    # Google Gemma 視覺系列（gemma3 部分版本、gemma4 全系列均支援視覺）
    "gemma4",
    "gemma3",
    # 翻譯+視覺
    "translategemma",
    # MiniCPM 視覺
    "minicpm-v",
    # InternVL
    "internvl",
]


def _filter_vision_models(all_models: list) -> list:
    result = []
    for m in all_models:
        name_lower = m.lower()
        if any(kw in name_lower for kw in OLLAMA_VISION_KEYWORDS):
            result.append(m)
    return result if result else all_models  # 沒有符合時回傳全部，避免清單變空


def call_ollama(model: str, image_pil, prompt: str, timeout: int = OLLAMA_TIMEOUT):
    """OLLAMA 原生 /api/chat 視覺呼叫。
    以獨立執行緒發送請求，主執行緒等待 timeout 秒；逾時則拋出 TimeoutError。
    """

    image_pil, quality = _prepare_img_for_engine(image_pil, "ollama")
    img_b64 = _img_to_jpeg_b64(image_pil, quality)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt, "images": [img_b64]}],
        "stream": False,
        "options": {"num_predict": 2048},
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/chat", data=body, headers={"Content-Type": "application/json"}, method="POST"
    )

    result_holder = [None]  # [response_text | Exception]
    done_evt = threading.Event()

    def _worker():
        try:
            # 連線與讀取都在子執行緒進行，本身不設 socket timeout
            with urllib.request.urlopen(req, timeout=timeout + 5) as resp:
                raw = resp.read().decode("utf-8")
            result_holder[0] = raw
        except Exception as exc:
            result_holder[0] = exc
        finally:
            done_evt.set()

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    finished = done_evt.wait(timeout=timeout)

    if not finished:
        # 逾時：daemon thread 會自然結束，這裡直接拋例外
        raise TimeoutError(
            f"OLLAMA 推理逾時（>{timeout}s），模型 {model} 回應過慢，" f"請縮短 Timeout 秒數或換較小的模型。"
        )

    outcome = result_holder[0]
    if isinstance(outcome, Exception):
        raise outcome

    result = json.loads(outcome)
    text = result.get("message", {}).get("content", "")
    log(f"[OLLAMA] 原始回應前200字: {text[:200]!r}")
    return _parse_json_response(text)


# ==========================================
# Segment 預處理：合併相近區塊（防疊字輔助）
# ==========================================
def _merge_segments(segments: list, x_thresh: float = 0.08, y_thresh: float = 0.12) -> list:
    """將 x 座標相近（差距 < x_thresh）且 y 座標鄰近（差距 < y_thresh）
    的 segment 合併為一個，譯文以空格串接。
    步驟：
    1. 依 x 分群（DBSCAN 概念的簡化版：單維度貪婪合併）
    2. 同群內依 y 排序，相鄰 y 差距 < y_thresh 的視為同組
    3. 同組 segment 合併：tw 以換行連接，x/y 取最小值，w/h 取涵蓋範圍
    """
    if not segments:
        return segments

    # 先依 x 排序
    segs = sorted(segments, key=lambda s: float(s.get("x", 0)))

    # x 分群
    x_groups = []
    current_group = [segs[0]]
    for s in segs[1:]:
        group_anchor_x = float(current_group[0].get("x", 0))
        if abs(float(s.get("x", 0)) - group_anchor_x) <= x_thresh:
            current_group.append(s)
        else:
            x_groups.append(current_group)
            current_group = [s]
    x_groups.append(current_group)

    result = []
    for group in x_groups:
        # 群內依 y 排序
        group_sorted = sorted(group, key=lambda s: float(s.get("y", 0)))
        # y 分組（相鄰差距 < y_thresh 合併）
        y_groups = [[group_sorted[0]]]
        for s in group_sorted[1:]:
            last_y = float(y_groups[-1][-1].get("y", 0))
            if float(s.get("y", 0)) - last_y <= y_thresh:
                y_groups[-1].append(s)
            else:
                y_groups.append([s])
        # 各 y 組合併
        for yg in y_groups:
            if len(yg) == 1:
                result.append(yg[0])
            else:
                xs = [float(s.get("x", 0)) for s in yg]
                ys = [float(s.get("y", 0)) for s in yg]
                ws = [float(s.get("w", 0.1)) for s in yg]
                hs = [float(s.get("h", 0.05)) for s in yg]
                x0 = min(xs)
                y0 = min(ys)
                x1 = max(xi + wi for xi, wi in zip(xs, ws))
                y1 = max(yi + hi for yi, hi in zip(ys, hs))
                merged_tw = "\n".join(s.get("tw", "").strip() for s in yg if s.get("tw", "").strip())
                result.append(
                    {
                        "tw": merged_tw,
                        "x": round(x0, 4),
                        "y": round(y0, 4),
                        "w": round(x1 - x0, 4),
                        "h": round(y1 - y0, 4),
                    }
                )
    return result


# ==========================================
# 渲染引擎（安全邊距 + 自動換行 + 防疊字）
# ==========================================
PADDING = 15  # 畫布四周安全邊距 (px)


def draw_wrapped_text_safe(draw, text, x, y, font, canvas_w, canvas_h, fill):
    """
    在 (x, y) 繪製自動換行文字，保證：
    - 左右上下都留 PADDING 邊距
    - 自動換行不超出右邊界
    - 超出下邊界的行直接截斷不畫
    回傳：實際佔用的底部 y 座標（供防疊字用）
    """
    # 清除換行符號（API 可能回傳多行文字導致 textlength 報錯）
    text = text.replace("\n", " ").replace("\r", "")

    # 強制座標在安全區域內
    x = max(x, PADDING)
    y = max(y, PADDING)

    # 可用寬度 = 畫布寬 - 左邊位置 - 右邊距
    max_width = canvas_w - x - PADDING
    if max_width < 30:
        # 太靠右放不下，移到左邊距重新計算
        x = PADDING
        max_width = canvas_w - PADDING * 2

    # 底部安全邊界
    y_limit = canvas_h - PADDING

    # 斷行
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        if draw.textlength(test_line, font=font) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = char
    if current_line:
        lines.append(current_line)

    # 逐行繪製
    line_height = font.size + 4
    current_y = y
    for line in lines:
        if current_y + line_height > y_limit:
            break  # 超出底部安全邊界，停止繪製
        draw.text((x, current_y), line, fill=fill, font=font, anchor="la")
        current_y += line_height

    return current_y  # 回傳佔用到的底部 y


# ==========================================
# UI
# ==========================================


# ==========================================
# 視窗主題（深色 / 淺色）
# ==========================================
THEMES = {
    "dark": {
        "bg":           "#2b2b2b",
        "fg":           "#e8e8e8",
        "entry_bg":     "#3c3f41",
        "entry_fg":     "#e8e8e8",
        "select_bg":    "#4c6a92",
        "select_fg":    "#ffffff",
        "frame_bg":     "#2b2b2b",
        "label_bg":     "#2b2b2b",
        "label_fg":     "#e8e8e8",
        "button_bg":    "#4c4c4c",
        "button_fg":    "#e8e8e8",
        "treeview_bg":  "#3c3f41",
        "treeview_fg":  "#e8e8e8",
        "treeview_sel": "#4c6a92",
        "nb_bg":        "#3c3f41",
        "lf_fg":        "#cccccc",
        # Treeview row tags
        "tag_odd":      "#353535",
        "tag_even":     "#3c3f41",
        "tag_current_bg": "#1e4d7a",
        "tag_no_quota": "#ff6b6b",
        "tag_sep":      "#444444",
        # 狀態列語意色（深色模式下調亮）
        "status_info":  "#5bc8ff",
        "status_ok":    "#6dcc6d",
        "status_warn":  "#ffb347",
        "status_err":   "#ff6b6b",
        "status_idle":  "#aaaaaa",
    },
    "light": {
        "bg":           "#f0f0f0",
        "fg":           "#000000",
        "entry_bg":     "#ffffff",
        "entry_fg":     "#000000",
        "select_bg":    "#0078d7",
        "select_fg":    "#ffffff",
        "frame_bg":     "#f0f0f0",
        "label_bg":     "#f0f0f0",
        "label_fg":     "#000000",
        "button_bg":    "#e1e1e1",
        "button_fg":    "#000000",
        "treeview_bg":  "#ffffff",
        "treeview_fg":  "#000000",
        "treeview_sel": "#0078d7",
        "nb_bg":        "#f0f0f0",
        "lf_fg":        "#000000",
        # Treeview row tags
        "tag_odd":      "#f5f5f5",
        "tag_even":     "#ffffff",
        "tag_current_bg": "#d0eaff",
        "tag_no_quota": "#cc0000",
        "tag_sep":      "#e0e0e0",
        # 狀態列語意色
        "status_info":  "#0055cc",
        "status_ok":    "#007700",
        "status_warn":  "#cc6600",
        "status_err":   "#cc0000",
        "status_idle":  "#666666",
    },
}
CURRENT_THEME = "light"  # 預設淺色


def apply_theme(root, theme_name: str):
    """套用深色或淺色主題到所有 ttk + tk widget。"""
    global CURRENT_THEME
    CURRENT_THEME = theme_name
    t = THEMES.get(theme_name, THEMES["light"])

    style = ttk.Style(root)
    style.theme_use("clam")  # clam 主題支援最完整的自訂

    # ── TFrame / TLabelframe ──
    style.configure("TFrame",      background=t["bg"])
    style.configure("TLabelframe", background=t["bg"], foreground=t["lf_fg"])
    style.configure("TLabelframe.Label", background=t["bg"], foreground=t["lf_fg"])

    # ── TLabel ──
    style.configure("TLabel", background=t["bg"], foreground=t["fg"])

    # ── TButton ──
    _disabled_bg = "#3a3a3a" if theme_name == "dark" else "#c0c0c0"
    _disabled_fg = "#666666" if theme_name == "dark" else "#888888"
    style.configure("TButton",
        background=t["button_bg"], foreground=t["button_fg"],
        bordercolor=t["button_bg"], focuscolor=t["button_bg"])
    style.map("TButton",
        background=[("disabled", _disabled_bg), ("active", t["select_bg"]), ("pressed", t["select_bg"])],
        foreground=[("disabled", _disabled_fg), ("active", t["select_fg"])])

    # ── TEntry ──
    style.configure("TEntry",
        fieldbackground=t["entry_bg"], foreground=t["entry_fg"],
        insertcolor=t["fg"], bordercolor=t["button_bg"])

    # ── TCombobox ──
    style.configure("TCombobox",
        fieldbackground=t["entry_bg"], foreground=t["entry_fg"],
        background=t["button_bg"], arrowcolor=t["fg"])
    style.map("TCombobox",
        fieldbackground=[("readonly", t["entry_bg"])],
        foreground=[("readonly", t["entry_fg"])])

    # ── TCheckbutton / TRadiobutton ──
    for w in ("TCheckbutton", "TRadiobutton"):
        style.configure(w, background=t["bg"], foreground=t["fg"])
        style.map(w, background=[("active", t["bg"])])

    # ── TNotebook ──
    style.configure("TNotebook",      background=t["nb_bg"])
    style.configure("TNotebook.Tab",
        background=t["button_bg"], foreground=t["fg"], padding=[8, 3])
    style.map("TNotebook.Tab",
        background=[("selected", t["bg"])],
        foreground=[("selected", t["fg"])])

    # ── Treeview ──
    style.configure("Treeview",
        background=t["treeview_bg"], foreground=t["treeview_fg"],
        fieldbackground=t["treeview_bg"], rowheight=22)
    style.configure("Treeview.Heading",
        background=t["button_bg"], foreground=t["fg"])
    style.map("Treeview",
        background=[("selected", t["treeview_sel"])],
        foreground=[("selected", t["select_fg"])])

    # ── TSeparator ──
    style.configure("TSeparator", background=t["button_bg"])

    # ── TScrollbar ──
    style.configure("TScrollbar",
        background=t["button_bg"], troughcolor=t["bg"],
        arrowcolor=t["fg"])

    # ── disabled 按鈕明顯灰化（auto_cap_btn 專用） ──
    style.map("TButton",
        foreground=[("disabled", "#888888" if theme_name == "light" else "#666666")],
        background=[("disabled", "#cccccc" if theme_name == "light" else "#383838")],
    )

    # ── tk.Text / tk.Label 背景（需遍歷）──
    root.configure(bg=t["bg"])
    # 翻譯/攻略輸出視窗導覽列固定深色，跳過這兩個 Toplevel 的遞迴
    _FIXED_TITLES = {"翻譯結果", "Translation", "攻略資訊", "Guide Info"}
    skip = set()
    for child in root.winfo_children():
        try:
            if child.winfo_class() == "Toplevel":
                # 標題固定的輸出視窗 或 標記 _lf_no_theme 的視窗（如 Splash）均跳過
                if child.title() in _FIXED_TITLES or getattr(child, "_lf_no_theme", False):
                    skip.add(id(child))
        except Exception:
            pass
    _apply_tk_widgets(root, t, skip=skip)


def _apply_tk_widgets(widget, t: dict, skip: set = None):
    """遞迴套用主題到所有 tk（非 ttk）widget。
    skip：widget id() 集合，符合的 Toplevel 及其整棵子樹略過。"""
    if skip is None:
        skip = set()
    if id(widget) in skip:
        return
    try:
        cls = widget.__class__.__name__
        if cls in ("Text",):
            widget.configure(
                bg=t["entry_bg"], fg=t["entry_fg"],
                insertbackground=t["fg"],
                selectbackground=t["select_bg"], selectforeground=t["select_fg"])
        elif cls == "Label":
            widget.configure(bg=t["label_bg"], fg=t["label_fg"])
        elif cls in ("Frame", "Toplevel"):
            widget.configure(bg=t["bg"])
        elif cls == "Scale":
            widget.configure(bg=t["bg"], fg=t["fg"], troughcolor=t["entry_bg"])
    except Exception:
        pass
    for child in widget.winfo_children():
        _apply_tk_widgets(child, t, skip=skip)


def _calc_dir_size_kb(dirpath: str) -> int:
    total = 0
    try:
        for root, dirs, files in os.walk(dirpath):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    except OSError:
        pass
    return max(1, total // 1024)


class _Tooltip:
    """簡易 Tooltip：滑鼠停留時顯示提示文字。"""

    def __init__(self, widget, text: str):
        self._widget = widget
        self._text = text
        self._win = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _show(self, event=None):
        if self._win:
            return
        x = self._widget.winfo_rootx() + 20
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        self._win = tw = tk.Toplevel()
        tw.wm_overrideredirect(True)
        tw.wm_attributes("-topmost", True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw, text=self._text, justify="left", background="#ffffcc", relief="solid", borderwidth=1, font=("Arial", 8)
        ).pack()

    def _hide(self, event=None):
        if self._win:
            self._win.destroy()
            self._win = None


def _calc_font_size(item_count: int) -> int:
    fs_max = OVERLAY_FONT_SIZE_MAX_DEFAULT
    if item_count <= 3:
        size = fs_max
    elif item_count <= 8:
        ratio = 1.0 - (item_count - 3) / 5 * 0.3
        size = int(fs_max * ratio)
    else:
        ratio = 0.7 - (item_count - 8) / 10 * 0.2
        ratio = max(ratio, OVERLAY_FONT_SIZE_MIN_CLAMP / fs_max)
        size = int(fs_max * ratio)
    return max(size, OVERLAY_FONT_SIZE_MIN_CLAMP)


def _fetch_models_from_api(eng: str, api_key: str) -> list:
    try:
        if eng == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            # 排除非視覺模型：embedding、tts、imagen、veo、music、aqa、text-bison 等純文字
            skip = {"embedding", "tts", "imagen", "veo", "music", "aqa", "text-", "chat-"}
            result = []
            for m in data.get("models", []):
                name = m.get("name", "")
                if "gemini" not in name:
                    continue
                if any(s in name for s in skip):
                    continue
                if "generateContent" not in m.get("supportedGenerationMethods", []):
                    continue
                # 僅保留已知支援視覺的系列
                model_id = name.replace("models/", "")
                vlm_series = {"gemini-1.5", "gemini-2", "gemini-3", "gemini-pro-vision", "gemini-ultra"}
                if not any(s in model_id for s in vlm_series):
                    continue
                result.append(model_id)
            return sorted(result)

        elif eng == "openai":
            req = urllib.request.Request(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            # VLM 名稱關鍵字：gpt-4o 系列、gpt-4-turbo（含 vision）、o1/o3/o4 旗艦推理模型
            vlm_include = {"gpt-4o", "gpt-4-turbo", "gpt-4-vision", "o1", "o3", "o4"}
            exclude = {"instruct", "embedding", "tts", "whisper", "dall-e", "audio", "realtime"}
            result = []
            for m in data.get("data", []):
                mid = m.get("id", "")
                if not any(k in mid for k in vlm_include):
                    continue
                if any(k in mid for k in exclude):
                    continue
                result.append(mid)
            return sorted(result)

        elif eng == "groq":
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            # VLM 名稱關鍵字：llava、vision、-vl、scout（llama4 vision）、maverick
            vlm_keywords = {"llava", "vision", "-vl", "scout", "maverick", "llama-4", "minicpm", "qwen2-vl", "qwen2vl"}
            exclude = {"whisper", "tts", "guard"}
            result = []
            for m in data.get("data", []):
                mid = m.get("id", "")
                if any(k in mid for k in exclude):
                    continue
                if m.get("context_window", 0) < 8000:
                    continue
                if not any(k in mid.lower() for k in vlm_keywords):
                    continue
                result.append(mid)
            return sorted(result)

        elif eng == "mistral":
            req = urllib.request.Request(
                "https://api.mistral.ai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            result = []
            for m in data.get("data", []):
                caps = m.get("capabilities", {})
                if caps.get("vision") is True:
                    result.append(m.get("id", ""))
            return sorted(result)

        elif eng == "claude":
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                }
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            # claude-3 及以上全系列支援視覺；排除 claude-2、instant、legacy 純文字模型
            exclude = {"instant", "claude-2", "claude-1"}
            vlm_include = {"claude-3", "claude-sonnet", "claude-haiku", "claude-opus"}
            result = []
            for m in data.get("data", []):
                mid = m.get("id", "")
                if any(k in mid for k in exclude):
                    continue
                if any(k in mid for k in vlm_include):
                    result.append(mid)
            return sorted(result)

        elif eng == "grok":
            return list(ENGINE_MODELS.get("grok", []))

    except Exception as e:
        log(f"[_fetch_models_from_api] {eng}: {e}")
    return []


class LangForgeApp:
    def __init__(self, root, splash=None):
        self.root = root
        self.root.title("LangForge  V1.1.0")
        _load_app_icon(self.root)

        global CURRENT_LANG

        def _splash(msg: str):
            if splash:
                splash.update_text(msg)

        _splash("載入設定與資料庫..." if CURRENT_LANG != "en" else "Loading config & database...")
        self.config = load_config()
        self._init_db()
        self.last_res = []

        # 語系在 config 讀取後立即套用，確保後續 splash 訊息使用正確語言
        CURRENT_LANG = self.config.get("ui_lang", "zh")

        # 視窗位置快取（需在 _find_mesen_window 第一次呼叫前初始化）
        self._mesen_cache_rect = None
        self._mesen_cache_title = ""
        self._mesen_cache_ts = 0.0
        self._last_disp_geom = ""
        self._last_guide_geom = ""
        self._reposition_after_id = None  # Configure debounce timer
        self._position_polling_paused = False  # 自動翻譯開啟時暫停 polling
        self._position_poll_job = None  # position polling after() job ID
        self._capture_in_progress = False  # 防止 capture thread 重入
        self._save_config_after_id = None  # trace_add debounce timer

        # OLLAMA 本地引擎偵測（非同步，不阻塞啟動）
        _splash("偵測本地 OLLAMA..." if CURRENT_LANG != "en" else "Detecting local OLLAMA...")
        self._ollama_models = _detect_ollama_vision_models()
        self._ollama_available = len(self._ollama_models) > 0

        # 套用介面語系
        CURRENT_LANG = self.config.get("ui_lang", "zh")

        # 套用已儲存的螢幕位置
        self._monitors = _get_monitors()
        saved_screen = self.config.get("main_screen", 1)
        _mon = next((m for m in self._monitors if m["index"] == saved_screen), self._monitors[0])
        main_w, main_h = 580, 900
        # 優先還原上次關閉時的實際座標；首次啟動時 fallback 至 main_screen 螢幕左上角
        saved_x = self.config.get("main_win_x", None)
        saved_y = self.config.get("main_win_y", None)
        if saved_x is not None and saved_y is not None:
            self.root.geometry(f"{main_w}x{main_h}+{saved_x}+{saved_y}")
        else:
            self.root.geometry(f"{main_w}x{main_h}+{_mon['x']}+{_mon['y']}")
        # 主視窗等 Splash 關閉後才顯示（在 __init__ 末尾的 splash.close 之後 deiconify）

        # ═══════════════════════════════════
        # 選單列
        # ═══════════════════════════════════
        _splash("建立使用者介面..." if CURRENT_LANG != "en" else "Building UI...")

        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label=S("menu_edit_platforms"), command=self._open_platform_editor)
        file_menu.add_separator()
        file_menu.add_command(label=S("menu_exit"), command=self.root.destroy)
        menubar.add_cascade(label=S("menu_file"), menu=file_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        lang_menu = tk.Menu(view_menu, tearoff=0)
        lang_menu.add_command(label=S("menu_lang_zh"), command=lambda: self._switch_lang("zh"))
        lang_menu.add_command(label=S("menu_lang_en"), command=lambda: self._switch_lang("en"))
        view_menu.add_cascade(label=S("menu_switch_lang"), menu=lang_menu)
        theme_menu = tk.Menu(view_menu, tearoff=0)
        theme_menu.add_command(label=S("menu_theme_dark"),  command=lambda: self._switch_theme("dark"))
        theme_menu.add_command(label=S("menu_theme_light"), command=lambda: self._switch_theme("light"))
        view_menu.add_cascade(label=S("menu_switch_theme"), menu=theme_menu)
        menubar.add_cascade(label=S("menu_view"), menu=view_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label=S("menu_tutorial"), command=lambda: webbrowser.open(TUTORIAL_URL))
        help_menu.add_command(label=S("menu_about"), command=self._show_about)
        menubar.add_cascade(label=S("menu_help"), menu=help_menu)

        self.root.config(menu=menubar)

        frm = ttk.Frame(root, padding=8)
        frm.pack(fill="both", expand=True)

        # ═══════════════════════════════════
        # Notebook（頁籤容器）
        # ═══════════════════════════════════
        nb = ttk.Notebook(frm)
        nb.pack(fill="both", expand=True)

        tab1 = ttk.Frame(nb, padding=8)
        tab2 = ttk.Frame(nb, padding=8)
        tab3 = ttk.Frame(nb, padding=8)
        tab4 = ttk.Frame(nb, padding=8)
        tab5 = ttk.Frame(nb, padding=8)
        tab6 = ttk.Frame(nb, padding=8)
        nb.add(tab1, text=S("tab_translate"))
        nb.add(tab2, text=S("tab_capture"))
        nb.add(tab3, text=S("tab_quota"))
        nb.add(tab4, text=S("tab_history"))
        nb.add(tab5, text=S("tab_guide"))
        nb.add(tab6, text=S("tab_session"))

        # ══════════════════════════════════════════
        # Tab 1 — 翻譯操作
        # ══════════════════════════════════════════

        # ── 雙列狀態列（貼底，必須最先 pack）──
        status_wrap = ttk.Frame(tab1)
        status_wrap.pack(side="bottom", fill="x", pady=(2, 0))

        # 第一列：欄1 分析狀態、欄2 冷卻、欄3 留空、欄4 耗時
        status_row1 = ttk.Frame(status_wrap)
        status_row1.pack(fill="x")

        # 欄4 耗時先 pack side=right，讓 expand 的欄1 不吃掉右側空間
        self.elapsed_label = ttk.Label(status_row1, text="", foreground="gray", font=("Arial", 9), anchor="e", width=8)
        self.elapsed_label.pack(side="right")
        self._trans_start_time = None
        self._elapsed_timer_id = None

        # 欄2 冷卻（固定寬度，不截字）
        self.cooldown_label = ttk.Label(
            status_row1, text="", foreground="gray", font=("Arial", 9), anchor="w", width=10
        )
        self.cooldown_label.pack(side="right", padx=(4, 6))
        self._cooldown_timer_id = None

        # 欄1 分析狀態（fill 剩餘空間，不截字）
        self.status = ttk.Label(status_row1, text=S("status_ready"), foreground="blue", font=("Arial", 9), anchor="w")
        self.status.pack(side="left", fill="x", expand=True)

        # 第二列：欄1 場次狀態、欄2 佇列狀態、欄3 四開關指示燈
        status_row2 = ttk.Frame(status_wrap)
        status_row2.pack(fill="x")

        self._session_status_label = ttk.Label(
            status_row2, text=S("session_idle"), foreground="gray", font=("Arial", 8), anchor="w"
        )
        self._session_status_label.pack(side="left", padx=(0, 6))

        self.queue_label = ttk.Label(status_row2, text="", foreground="gray", font=("Arial", 8), anchor="w")
        self.queue_label.pack(side="left", expand=True)

        indicator_frame = ttk.Frame(status_row2)
        indicator_frame.pack(side="right")
        self._ind_auto = tk.Label(
            indicator_frame, text=S("ind_auto"), font=("Arial", 8), fg="gray", bg="#f0f0f0", relief="flat", padx=3
        )
        self._ind_auto.pack(side="left", padx=(0, 2))
        self._ind_combo = tk.Label(
            indicator_frame, text=S("ind_guide"), font=("Arial", 8), fg="gray", bg="#f0f0f0", relief="flat", padx=3
        )
        self._ind_combo.pack(side="left", padx=(0, 2))
        self._ind_hotkey = tk.Label(
            indicator_frame, text=S("ind_hotkey"), font=("Arial", 8), fg="gray", bg="#f0f0f0", relief="flat", padx=3
        )
        self._ind_hotkey.pack(side="left", padx=(0, 2))
        self._ind_guide_hotkey = tk.Label(
            indicator_frame,
            text=S("ind_guide_hotkey"),
            font=("Arial", 8),
            fg="gray",
            bg="#f0f0f0",
            relief="flat",
            padx=3,
        )
        self._ind_guide_hotkey.pack(side="left")
        self._update_indicators()

        # ── 引擎模式切換（雲端 / 本地） ──
        eng_mode_row1 = ttk.Frame(tab1)
        eng_mode_row1.pack(fill="x", pady=(0, 2))
        ttk.Label(eng_mode_row1, text=S("lbl_trans_options"), font=("Arial", 9, "bold")).pack(side="left")

        # OLLAMA 未偵測到時，本地選項 disabled
        _local_state = "normal" if self._ollama_available else "disabled"
        _saved_mode = self.config.get("engine_mode", "cloud")
        if not self._ollama_available and _saved_mode == "local":
            _saved_mode = "cloud"  # OLLAMA 不可用時本地模式才強制回雲端
        self.engine_mode_var = tk.StringVar(value=_saved_mode)

        eng_mode_row = ttk.Frame(tab1)
        eng_mode_row.pack(fill="x", pady=(0, 4))
        ttk.Radiobutton(
            eng_mode_row,
            text=S("rb_engine_cloud"),
            variable=self.engine_mode_var,
            value="cloud",
            command=self._on_engine_mode_change,
        ).pack(side="left", padx=(4, 0))
        ttk.Radiobutton(
            eng_mode_row,
            text=S("rb_engine_local"),
            variable=self.engine_mode_var,
            value="local",
            state=_local_state,
            command=self._on_engine_mode_change,
        ).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(
            eng_mode_row,
            text=S("rb_engine_ocr"),
            variable=self.engine_mode_var,
            value="ocr",
            command=self._on_engine_mode_change,
        ).pack(side="left", padx=(8, 0))

        # ── 引擎內容容器 ──
        self.engine_container = ttk.Frame(tab1)
        self.engine_container.pack(fill="x")

        # ── 雲端引擎區塊（LabelFrame GROUP）──
        self.cloud_frame = ttk.LabelFrame(self.engine_container, text=S("lf_cloud_engine"))

        # 引擎下拉選單
        _saved_eng = self.config.get("default_engine", "gemini")
        if _saved_eng not in ENGINE_ORDER:
            _saved_eng = "gemini"
        self.engine_var = tk.StringVar(value=_saved_eng)
        self._engine_display_var = tk.StringVar(value=ENGINE_DISPLAY.get(_saved_eng, _saved_eng))
        engine_row = ttk.Frame(self.cloud_frame)
        engine_row.pack(fill="x", padx=6, pady=(6, 2))
        self.engine_combo = ttk.Combobox(
            engine_row,
            textvariable=self._engine_display_var,
            values=sorted([ENGINE_DISPLAY[e] for e in ENGINE_ORDER]),
            state="readonly",
            width=28,
        )
        self.engine_combo.pack(side="left")
        self.engine_combo.bind("<<ComboboxSelected>>", lambda e: self._on_engine_combo_change())

        # API Key
        self.key_label = ttk.Label(self.cloud_frame, text="Gemini API Key:", font=("Arial", 9, "bold"))
        self.key_label.pack(anchor="w", padx=6, pady=(4, 0))
        self.api_entry = ttk.Entry(self.cloud_frame, show="*", width=52)
        self.api_entry.pack(padx=6, pady=2, fill="x")

        # 模型選擇
        model_row = ttk.Frame(self.cloud_frame)
        model_row.pack(fill="x", padx=6, pady=2)
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(model_row, textvariable=self.model_var, width=38, state="readonly")
        self.model_combo.pack(side="left", fill="x", expand=True)
        self.model_combo.bind(
            "<<ComboboxSelected>>", lambda e: (self._refresh_quota(), self._update_cooldown_display())
        )
        ttk.Button(model_row, text=S("btn_default_engine"), command=self._set_default_engine).pack(side="left", padx=(4, 0))

        # 自訂模型
        custom_frame = ttk.Frame(self.cloud_frame)
        custom_frame.pack(fill="x", padx=6, pady=(2, 0))
        ttk.Label(custom_frame, text=S("lbl_custom_model"), font=("Arial", 8)).pack(side="left")
        self.custom_model_var = tk.StringVar()
        ttk.Button(custom_frame, text=S("btn_refresh_models"), command=self._refresh_model_list, width=8).pack(side="right", padx=(2, 0))
        ttk.Button(custom_frame, text=S("btn_remove"), command=self._remove_custom_model, width=5).pack(side="right", padx=2)
        ttk.Button(custom_frame, text=S("btn_add"), command=self._add_custom_model, width=5).pack(side="right", padx=2)
        self.custom_model_entry = ttk.Entry(custom_frame, textvariable=self.custom_model_var)
        self.custom_model_entry.pack(side="left", padx=(4, 0), fill="x", expand=True)

        # 配額顯示
        self.quota_label = ttk.Label(self.cloud_frame, text="", foreground="brown", font=("Arial", 9, "bold"))
        self.quota_label.pack(anchor="w", padx=6, pady=(4, 6))

        self._init_engine_ui()

        # ── 本地引擎區塊（OLLAMA） ──
        self.local_frame = ttk.Frame(self.engine_container)

        if self._ollama_available:
            ollama_inner = ttk.LabelFrame(self.local_frame, text=S("lf_ollama"))
            ollama_inner.pack(fill="x", padx=2, pady=(0, 4))

            # 過濾開關列
            filter_row = ttk.Frame(ollama_inner)
            filter_row.pack(fill="x", padx=6, pady=(4, 2))
            ttk.Label(filter_row, text=S("lbl_ollama_detected"), font=("Arial", 8), foreground="gray").pack(side="left")
            self.vision_filter_var = tk.BooleanVar(value=self.config.get("ollama_vision_filter", True))
            ttk.Checkbutton(
                filter_row,
                text=S("cb_vision_filter"),
                variable=self.vision_filter_var,
                command=self._on_vision_filter_toggle,
            ).pack(side="right")

            # 模型下拉（初始依過濾開關決定清單）
            _init_models = (
                _filter_vision_models(self._ollama_models) if self.vision_filter_var.get() else self._ollama_models
            )
            _saved_model = self.config.get("ollama_model", _init_models[0])
            if _saved_model not in _init_models:
                _saved_model = _init_models[0]
            self.ollama_model_var = tk.StringVar(value=_saved_model)
            self.ollama_combo = ttk.Combobox(
                ollama_inner, textvariable=self.ollama_model_var, values=_init_models, state="readonly", width=44
            )
            self.ollama_combo.pack(padx=6, pady=(0, 2), fill="x")
            self.ollama_combo.bind("<<ComboboxSelected>>", self._on_use_ollama_toggle)
            timeout_row = ttk.Frame(ollama_inner)
            timeout_row.pack(fill="x", padx=6, pady=(2, 2))
            ttk.Label(timeout_row, text=S("lbl_ollama_timeout"), font=("Arial", 9)).pack(side="left")
            self.ollama_timeout_var = tk.StringVar(value=str(self.config.get("ollama_timeout", OLLAMA_TIMEOUT)))
            ttk.Entry(timeout_row, textvariable=self.ollama_timeout_var, width=6).pack(side="left", padx=4)
            ttk.Label(timeout_row, text=S("lbl_timeout_hint"), font=("Arial", 8), foreground="gray").pack(side="left")
            self.ollama_timeout_var.trace_add("write", lambda *_: self._debounce_save_config())

            # 右下角：重新偵測 OLLAMA 模型
            ollama_btn_row = ttk.Frame(ollama_inner)
            ollama_btn_row.pack(fill="x", padx=6, pady=(2, 6))
            ttk.Button(
                ollama_btn_row, text=S("btn_refresh_ollama"), command=self._refresh_ollama_models, width=10
            ).pack(side="right")
        else:
            self.ollama_model_var = tk.StringVar(value="")
            self.ollama_timeout_var = tk.StringVar(value=str(OLLAMA_TIMEOUT))
            self.vision_filter_var = tk.BooleanVar(value=True)
            self.ollama_combo = None

        # 高度補齊 spacer（讓 local_frame 與 cloud_frame 等高，防止切換時下方 UI 跳動）
        ttk.Frame(self.local_frame, height=40).pack(fill="x")

        # ── OCR 引擎區塊 ──
        self.ocr_frame = ttk.Frame(self.engine_container)
        ocr_inner = ttk.LabelFrame(
            self.ocr_frame,
            text="🔍 " + S("rb_engine_ocr").lstrip("🔍 "),
        )
        ocr_inner.pack(fill="x", padx=2, pady=(0, 4))
        ttk.Label(
            ocr_inner,
            text=S("lbl_ocr_desc"),
            font=("Arial", 8),
            foreground="gray",
        ).pack(anchor="w", padx=6, pady=(4, 2))
        ttk.Label(ocr_inner, text="", font=("Arial", 8), foreground="steelblue").pack(anchor="w", padx=6, pady=(0, 4))
        # 高度補齊 spacer
        ttk.Frame(self.ocr_frame, height=80).pack(fill="x")

        # use_ollama_var：本地模式開啟即視為啟用
        self.use_ollama_var = tk.BooleanVar(value=(_saved_mode == "local"))

        # 初始顯示正確區塊
        if not hasattr(self, "ocr_frame"):
            self.ocr_frame = ttk.Frame(self.engine_container)
        self._apply_engine_mode(animate=False)

        # ── 功能按鈕群組（上2下3排列） ──
        func_frame = ttk.LabelFrame(tab1, text=S("lf_actions"))
        func_frame.pack(fill="x", pady=(8, 0), padx=2)

        func_row1 = ttk.Frame(func_frame)
        func_row1.pack(fill="x", padx=6, pady=(6, 3))

        # 上排左：自動擷取（disabled 時明顯灰化）
        _auto_enabled = False
        self.auto_cap_btn = ttk.Button(
            func_row1,
            text=S("btn_auto_cap_on") if _auto_enabled else S("btn_auto_cap_off"),
            command=self._on_auto_cap_btn,
            state="normal" if _auto_enabled else "disabled",
        )
        self.auto_cap_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self._auto_cap_tooltip = _Tooltip(self.auto_cap_btn, S("btn_auto_cap_tooltip"))

        # 上排右：開始/結束場次錄製（單一按鈕，切換文字）
        self._btn_session_start = ttk.Button(
            func_row1,
            text=S("btn_start_session"),
            command=self._on_session_toggle,
        )
        self._btn_session_start.pack(side="left", expand=True, fill="x")

        func_row2 = ttk.Frame(func_frame)
        func_row2.pack(fill="x", padx=6, pady=(0, 3))

        # 下排：視窗擷取翻譯、目前攻略資訊、選擇圖片翻譯
        self.btn_capture = ttk.Button(func_row2, text=S("btn_capture_trans"), command=self.start_worker)
        self.btn_capture.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.btn_guide = ttk.Button(func_row2, text=S("btn_guide"), command=self.start_guide_worker)
        self.btn_guide.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.btn_file = ttk.Button(func_row2, text=S("btn_file_trans"), command=self.pick_image_file)
        self.btn_file.pack(side="left", expand=True, fill="x")

        func_row3 = ttk.Frame(func_frame)
        func_row3.pack(fill="x", padx=6, pady=(0, 6))

        # 第三排：清空佇列
        ttk.Button(func_row3, text=S("btn_clear_queue"), command=self._clear_queue).pack(
            side="left", expand=True, fill="x"
        )

        # ══════════════════════════════════════════
        # Tab 2 — 擷取設定
        # ══════════════════════════════════════════

        # ── 1. 主視窗位置 ──
        screen_lf = ttk.LabelFrame(tab2, text=S("lbl_screen").rstrip(":"))
        screen_lf.pack(fill="x", pady=(0, 6), padx=2)
        screen_inner = ttk.Frame(screen_lf)
        screen_inner.pack(fill="x", padx=6, pady=6)
        screen_labels = [m["label"] for m in self._monitors]
        saved_scr_idx = self.config.get("main_screen", 1)
        _scr_mon = next((m for m in self._monitors if m["index"] == saved_scr_idx), self._monitors[0])
        self.screen_var = tk.StringVar(value=_scr_mon["label"])
        self.screen_combo = ttk.Combobox(
            screen_inner, textvariable=self.screen_var, values=screen_labels, state="readonly", width=32
        )
        self.screen_combo.pack(side="left")
        self.screen_combo.bind("<<ComboboxSelected>>", self._on_screen_change)

        # ── 2. 目標視窗 ──
        target_lf = ttk.LabelFrame(tab2, text=S("lbl_target_win").rstrip(":"))
        target_lf.pack(fill="x", pady=(0, 6), padx=2)

        target_row = ttk.Frame(target_lf)
        target_row.pack(fill="x", padx=6, pady=(6, 2))
        saved_targets = self.config.get("target_windows", [])
        self.title_var = tk.StringVar(value=saved_targets[0] if saved_targets else "")
        self.target_combo = ttk.Combobox(target_row, textvariable=self.title_var, width=30)
        self.target_combo["values"] = saved_targets
        if not saved_targets:
            self.target_combo.set(S("hint_no_target"))
            self.target_combo.config(foreground="gray")
        self.target_combo.pack(side="left")
        self.target_combo.bind("<<ComboboxSelected>>", lambda e: self.target_combo.config(foreground=""))
        _Tooltip(self.target_combo, S("lbl_target_win_tooltip"))
        ttk.Button(target_row, text=S("btn_add"), command=self._add_target_window, width=5).pack(side="left", padx=(4, 2))
        ttk.Button(target_row, text=S("btn_remove"), command=self._remove_target_window, width=5).pack(side="left", padx=2)

        pick_row = ttk.Frame(target_lf)
        pick_row.pack(fill="x", padx=6, pady=(2, 2))
        self.pick_window_btn = ttk.Button(pick_row, text=S("btn_pick_window"), command=self._start_pick_window, width=12)
        self.pick_window_btn.pack(side="left")
        self.pick_cancel_btn = ttk.Button(pick_row, text=S("btn_cancel"), command=self._cancel_pick_window, width=6, state="disabled")
        self.pick_cancel_btn.pack(side="left", padx=(4, 0))
        self.pick_hint_label = ttk.Label(pick_row, text="", foreground="orange", font=("Arial", 9))
        self.pick_hint_label.pack(side="left", padx=(8, 0))
        self._pick_countdown_id = None

        crop_row = ttk.Frame(target_lf)
        crop_row.pack(fill="x", padx=6, pady=(2, 6))
        ttk.Label(crop_row, text=S("lbl_crop_top"), font=("Arial", 9)).pack(side="left")
        self.crop_top_var = tk.StringVar(value=str(self.config.get("crop_top", 0)))
        ttk.Entry(crop_row, textvariable=self.crop_top_var, width=5).pack(side="left", padx=3)
        ttk.Label(crop_row, text=S("lbl_crop_hint"), font=("Arial", 8), foreground="gray").pack(side="left")

        # ── 3. 語言設定 ──
        lang_frame = ttk.LabelFrame(tab2, text=S("lf_lang"))
        lang_frame.pack(fill="x", pady=(0, 6), padx=2)

        src_row = ttk.Frame(lang_frame)
        src_row.pack(fill="x", pady=(6, 2), padx=6)
        ttk.Label(src_row, text=S("lbl_src_lang"), font=("Arial", 9), width=10).pack(side="left")
        self.src_lang_var = tk.StringVar(value=self.config.get("src_lang", "Japanese(日文)"))
        src_combo = ttk.Combobox(src_row, textvariable=self.src_lang_var, values=GAME_LANGUAGES, state="readonly", width=38)
        src_combo.pack(side="left", padx=4)

        tgt_row = ttk.Frame(lang_frame)
        tgt_row.pack(fill="x", pady=(2, 6), padx=6)
        ttk.Label(tgt_row, text=S("lbl_tgt_lang"), font=("Arial", 9), width=10).pack(side="left")
        self.tgt_lang_var = tk.StringVar(value=self.config.get("tgt_lang", "Traditional Chinese(正體中文)"))
        tgt_combo = ttk.Combobox(tgt_row, textvariable=self.tgt_lang_var, values=TARGET_LANGUAGES, state="readonly", width=38)
        tgt_combo.pack(side="left", padx=4)

        # ── 4. 文字排版模式 ──
        layout_lf = ttk.LabelFrame(tab2, text=S("lbl_layout").rstrip(":"))
        layout_lf.pack(fill="x", pady=(0, 6), padx=2)
        self.text_dir_var = tk.StringVar(value=self.config.get("text_direction", "horizontal"))
        layout_inner = ttk.Frame(layout_lf)
        layout_inner.pack(fill="x", padx=6, pady=6)
        ttk.Radiobutton(layout_inner, text=S("rb_horizontal"), variable=self.text_dir_var, value="horizontal").pack(side="left")
        ttk.Radiobutton(layout_inner, text=S("rb_vertical"), variable=self.text_dir_var, value="vertical").pack(side="left", padx=(12, 0))

        # ── 5. 遊戲平台紀錄 ──
        platform_frame = ttk.LabelFrame(tab2, text=S("lf_platform"))
        platform_frame.pack(fill="x", pady=(0, 6), padx=2)

        pmode_row = ttk.Frame(platform_frame)
        pmode_row.pack(fill="x", pady=(6, 2), padx=6)
        self.platform_mode_var = tk.StringVar(value=self.config.get("platform_mode", "platform"))
        ttk.Radiobutton(pmode_row, text=S("rb_platform_mode"), variable=self.platform_mode_var, value="platform", command=self._on_platform_mode_change).pack(side="left")
        ttk.Radiobutton(pmode_row, text=S("rb_emulator_mode"), variable=self.platform_mode_var, value="emulator", command=self._on_platform_mode_change).pack(side="left", padx=(12, 0))

        pcat_row = ttk.Frame(platform_frame)
        pcat_row.pack(fill="x", pady=(2, 2), padx=6)
        ttk.Label(pcat_row, text=S("lbl_category"), font=("Arial", 9), width=8).pack(side="left")
        _active_data = PLATFORMS if self.platform_mode_var.get() == "platform" else EMULATORS
        platform_categories = list(_active_data.keys())
        self.platform_category_var = tk.StringVar(value=self.config.get("platform_category", platform_categories[0] if platform_categories else ""))
        self.platform_category_combo = ttk.Combobox(pcat_row, textvariable=self.platform_category_var, values=platform_categories, state="readonly", width=34)
        self.platform_category_combo.pack(side="left", padx=4)
        self.platform_category_combo.bind("<<ComboboxSelected>>", self._on_platform_category_change)

        pval_row = ttk.Frame(platform_frame)
        pval_row.pack(fill="x", pady=(2, 6), padx=6)
        ttk.Label(pval_row, text=S("lbl_platform"), font=("Arial", 9), width=8).pack(side="left")
        init_cat = self.platform_category_var.get()
        init_platforms = _active_data.get(init_cat, [])
        saved_platform = self.config.get("platform", init_platforms[0] if init_platforms else "")
        self.platform_var = tk.StringVar(value=saved_platform)
        self.platform_combo = ttk.Combobox(pval_row, textvariable=self.platform_var, values=init_platforms, state="readonly", width=34)
        self.platform_combo.pack(side="left", padx=4)
        self.platform_combo.bind("<<ComboboxSelected>>", self._on_platform_change)

        # ── 6. 視窗依附模式（2排×2） ──
        winmode_frame = ttk.LabelFrame(tab2, text=S("lf_winmode"))
        winmode_frame.pack(fill="x", pady=(0, 6), padx=2)
        self.winmode_var = tk.StringVar(value=self.config.get("winmode", "mesen"))
        wm_row1 = ttk.Frame(winmode_frame)
        wm_row1.pack(fill="x", padx=6, pady=(6, 2))
        ttk.Radiobutton(wm_row1, text=S("rb_winmode_main"),   variable=self.winmode_var, value="main",   command=self._on_winmode_change).pack(side="left", expand=True, fill="x")
        ttk.Radiobutton(wm_row1, text=S("rb_winmode_mesen"),  variable=self.winmode_var, value="mesen",  command=self._on_winmode_change).pack(side="left", expand=True, fill="x")
        wm_row2 = ttk.Frame(winmode_frame)
        wm_row2.pack(fill="x", padx=6, pady=(2, 6))
        ttk.Radiobutton(wm_row2, text=S("rb_winmode_corner"), variable=self.winmode_var, value="corner", command=self._on_winmode_change).pack(side="left", expand=True, fill="x")
        ttk.Radiobutton(wm_row2, text=S("rb_winmode_sides"),  variable=self.winmode_var, value="sides",  command=self._on_winmode_change).pack(side="left", expand=True, fill="x")

        # ── 7. 快捷鍵 ──
        hotkey_lf = ttk.LabelFrame(tab2, text=S("lbl_hotkeys"))
        hotkey_lf.pack(fill="x", pady=(0, 6), padx=2)

        hk_row = ttk.Frame(hotkey_lf)
        hk_row.pack(fill="x", padx=6, pady=(6, 2))
        ttk.Label(hk_row, text=S("lbl_hotkey"), font=("Arial", 9), width=16).pack(side="left")
        self.hotkey_var = tk.StringVar(value=self.config.get("hotkey", DEFAULT_HOTKEY))
        self.hotkey_entry = ttk.Entry(hk_row, textvariable=self.hotkey_var, width=14)
        self.hotkey_entry.pack(side="left", padx=4)
        self.hotkey_btn = ttk.Button(hk_row, text=S("btn_enable"), command=self._toggle_hotkey, width=6)
        self.hotkey_btn.pack(side="left", padx=2)
        self.hotkey_active = False
        self.hotkey_status = ttk.Label(hk_row, text=S("lbl_hotkey_off"), foreground="gray", font=("Arial", 8))
        self.hotkey_status.pack(side="left", padx=4)

        ghk_row = ttk.Frame(hotkey_lf)
        ghk_row.pack(fill="x", padx=6, pady=(2, 6))
        ttk.Label(ghk_row, text=S("lbl_guide_hotkey"), font=("Arial", 9), width=16).pack(side="left")
        self.guide_hotkey_var = tk.StringVar(value=self.config.get("guide_hotkey", "ctrl+f3"))
        ttk.Entry(ghk_row, textvariable=self.guide_hotkey_var, width=14).pack(side="left", padx=4)
        self.guide_hotkey_btn = ttk.Button(ghk_row, text=S("btn_enable"), command=self._toggle_guide_hotkey, width=6)
        self.guide_hotkey_btn.pack(side="left", padx=2)
        self.guide_hotkey_active = False
        self.guide_hotkey_status = ttk.Label(ghk_row, text=S("lbl_hotkey_off"), foreground="gray", font=("Arial", 8))
        self.guide_hotkey_status.pack(side="left", padx=4)

        # ── 8. 自動擷取（二欄式）──
        auto_lf = ttk.LabelFrame(tab2, text=S("lf_auto_trans"), padding=4)
        auto_lf.pack(fill="x", pady=(0, 6), padx=2)

        auto_cols = ttk.Frame(auto_lf)
        auto_cols.pack(fill="x")

        # 左欄
        auto_left = ttk.Frame(auto_cols)
        auto_left.pack(side="left", fill="both", expand=True)

        # 行1：啟用 checkbox + 狀態
        auto_row1 = ttk.Frame(auto_left)
        auto_row1.pack(fill="x")
        self.auto_trans_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(auto_row1, text=S("cb_auto_trans"), variable=self.auto_trans_var, command=self._on_auto_trans_toggle).pack(side="left")
        init_color = "green" if self.auto_trans_var.get() else "gray"
        self.auto_trans_status = ttk.Label(auto_row1, text=S("status_on") if self.auto_trans_var.get() else S("status_off"), foreground=init_color, font=("Arial", 9))
        self.auto_trans_status.pack(side="left", padx=6)

        # 行2：差異門檻 + 穩定次數（同排）
        auto_row2 = ttk.Frame(auto_left)
        auto_row2.pack(fill="x", pady=(4, 0))
        self.stable_diff_var = tk.StringVar(value=str(self.config.get("stable_diff", STABLE_DIFF_DEFAULT)))
        diff_lbl = ttk.Label(auto_row2, text=S("lbl_diff_threshold"), font=("Arial", 9))
        diff_lbl.pack(side="left")
        _Tooltip(diff_lbl, S("stable_hint"))
        ttk.Entry(auto_row2, textvariable=self.stable_diff_var, width=5).pack(side="left", padx=(2, 10))
        self.stable_diff_var.trace_add("write", lambda *_: self._debounce_save_config())

        self.stable_count_var = tk.StringVar(value=str(self.config.get("stable_count", STABLE_COUNT_DEFAULT)))
        count_lbl = ttk.Label(auto_row2, text=S("lbl_stable_count"), font=("Arial", 9))
        count_lbl.pack(side="left")
        _Tooltip(count_lbl, S("stable_hint"))
        ttk.Entry(auto_row2, textvariable=self.stable_count_var, width=5).pack(side="left", padx=(2, 0))
        self.stable_count_var.trace_add("write", lambda *_: self._debounce_save_config())

        # 右欄
        ttk.Separator(auto_cols, orient="vertical").pack(side="left", fill="y", padx=8)
        auto_right = ttk.Frame(auto_cols)
        auto_right.pack(side="left", fill="y")

        # 行1：截取翻譯時同時要求攻略
        self.combo_guide_var = tk.BooleanVar(value=self.config.get("combo_guide", False))
        ttk.Checkbutton(auto_right, text=S("cb_combo_guide"), variable=self.combo_guide_var, command=self._on_combo_guide_toggle).pack(anchor="w")
        # 行2：狀態
        self.combo_guide_status = ttk.Label(auto_right, text=S("lbl_combo_off"), foreground="gray", font=("Arial", 9))
        self.combo_guide_status.pack(anchor="w", pady=(2, 0))
        self._update_combo_guide_status()

        # ══════════════════════════════════════════
        # Tab 3 — 引擎配額
        # ══════════════════════════════════════════
        ttk.Label(tab3, text=S("lbl_quota_title"), font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 6))

        quota_scroll_frame = ttk.Frame(tab3)
        quota_scroll_frame.pack(fill="both", expand=True)

        # Treeview 取代 Text widget
        cols = ("engine", "model", "used", "limit", "rpm")
        self.quota_table = ttk.Treeview(quota_scroll_frame, columns=cols, show="headings", selectmode="none", height=20)
        self.quota_table.heading("engine", text=S("th_engine"), anchor="w")
        self.quota_table.heading("model", text=S("th_model"), anchor="w")
        self.quota_table.heading("used", text=S("th_used"), anchor="e")
        self.quota_table.heading("limit", text=S("th_limit"), anchor="e")
        self.quota_table.heading("rpm", text="RPM", anchor="e")
        self.quota_table.column("engine", width=62, stretch=False, anchor="w")
        self.quota_table.column("model", width=230, stretch=True, anchor="w")
        self.quota_table.column("used", width=44, stretch=False, anchor="e")
        self.quota_table.column("limit", width=56, stretch=False, anchor="e")
        self.quota_table.column("rpm", width=44, stretch=False, anchor="e")
        # 交替底色 tag
        self.quota_table.tag_configure("odd", background="#f5f5f5")
        self.quota_table.tag_configure("even", background="#ffffff")
        self.quota_table.tag_configure("current", background="#d0eaff", font=("Arial", 9, "bold"))
        self.quota_table.tag_configure("no_quota", foreground="#cc0000")
        self.quota_table.tag_configure("unknown_quota", foreground="#cc7700")
        self.quota_table.tag_configure("sep", background="#e0e0e0")
        quota_sb = ttk.Scrollbar(quota_scroll_frame, orient="vertical", command=self.quota_table.yview)
        self.quota_table.configure(yscrollcommand=quota_sb.set)
        quota_sb.pack(side="right", fill="y")
        self.quota_table.pack(side="left", fill="both", expand=True)

        ttk.Button(tab3, text=S("btn_refresh"), command=self._refresh_quota_table).pack(pady=(6, 0))

        # ══════════════════════════════════════════
        # Tab 4 — 歷史翻譯資料
        # ══════════════════════════════════════════

        # ── 上半：遊戲篩選 + Treeview 清單 ──
        # ── 上半：遊戲篩選（兩列）+ Treeview 清單 ──
        # 第一列：遊戲、視窗
        t4_filter1 = ttk.Frame(tab4)
        t4_filter1.pack(fill="x", pady=(0, 2))
        ttk.Label(t4_filter1, text=S("lbl_game"), font=("Arial", 9)).pack(side="left")
        self.t4_game_var = tk.StringVar(value=S("all_games"))
        self.t4_game_combo = ttk.Combobox(t4_filter1, textvariable=self.t4_game_var, width=18, state="readonly")
        self.t4_game_combo.pack(side="left", padx=(2, 6))
        self.t4_game_combo.bind("<<ComboboxSelected>>", lambda e: self._t4_load_list())
        ttk.Label(t4_filter1, text=S("lbl_window"), font=("Arial", 9)).pack(side="left")
        self.t4_window_var = tk.StringVar(value=S("all_windows"))
        self.t4_window_combo = ttk.Combobox(t4_filter1, textvariable=self.t4_window_var, width=12, state="readonly")
        self.t4_window_combo.pack(side="left", padx=(2, 0))
        self.t4_window_combo.bind("<<ComboboxSelected>>", lambda e: self._t4_load_list())

        # 第二列：平台、刪除
        t4_filter2 = ttk.Frame(tab4)
        t4_filter2.pack(fill="x", pady=(0, 2))
        ttk.Label(t4_filter2, text=S("lbl_platform_f"), font=("Arial", 9)).pack(side="left")
        self.t4_platform_var = tk.StringVar(value=S("all_platforms"))
        self.t4_platform_combo = ttk.Combobox(t4_filter2, textvariable=self.t4_platform_var, width=12, state="readonly")
        self.t4_platform_combo.pack(side="left", padx=(2, 0))
        self.t4_platform_combo.bind("<<ComboboxSelected>>", lambda e: self._t4_load_list())
        ttk.Button(t4_filter2, text=S("btn_delete"), command=self._t4_delete).pack(side="right")

        t4_tree_frame = ttk.Frame(tab4)
        t4_tree_frame.pack(fill="x")
        self.t4_tree = ttk.Treeview(
            t4_tree_frame,
            columns=("rom_name", "time", "target_window", "platform"),
            show="headings",
            height=5,
            selectmode="browse",
        )
        self.t4_tree.heading("rom_name", text=S("th_rom"))
        self.t4_tree.heading("time", text=S("th_time"))
        self.t4_tree.heading("target_window", text=S("th_window"))
        self.t4_tree.heading("platform", text=S("th_platform"))
        self.t4_tree.column("rom_name", width=160, stretch=True)
        self.t4_tree.column("time", width=135, anchor="center", stretch=False)
        self.t4_tree.column("target_window", width=80, stretch=False)
        self.t4_tree.column("platform", width=90, stretch=False)
        t4_tree_sb = ttk.Scrollbar(t4_tree_frame, orient="vertical", command=self.t4_tree.yview)
        self.t4_tree.configure(yscrollcommand=t4_tree_sb.set)
        t4_tree_sb.pack(side="right", fill="y")
        self.t4_tree.pack(side="left", fill="x", expand=True)
        self.t4_tree.bind("<<TreeviewSelect>>", self._t4_on_select)

        # ── 修正平台區塊 ──
        t4_fix_frame = ttk.LabelFrame(tab4, text=S("lf_fix_platform"))
        t4_fix_frame.pack(fill="x", pady=(4, 0))

        # 模式選擇列（遊戲平台 / 模擬器）
        t4_fix_mode_row = ttk.Frame(t4_fix_frame)
        t4_fix_mode_row.pack(fill="x", padx=6, pady=(4, 2))
        ttk.Label(t4_fix_mode_row, text=S("lbl_fix_mode"), font=("Arial", 9), width=8).pack(side="left")
        self.t4_fix_mode_var = tk.StringVar(value="platform")
        ttk.Radiobutton(
            t4_fix_mode_row,
            text=S("rb_platform_mode"),
            variable=self.t4_fix_mode_var,
            value="platform",
            command=self._on_t4_fix_mode_change,
        ).pack(side="left", padx=(4, 8))
        ttk.Radiobutton(
            t4_fix_mode_row,
            text=S("rb_emulator_mode"),
            variable=self.t4_fix_mode_var,
            value="emulator",
            command=self._on_t4_fix_mode_change,
        ).pack(side="left")

        t4_fix_row1 = ttk.Frame(t4_fix_frame)
        t4_fix_row1.pack(fill="x", padx=6, pady=(2, 2))
        ttk.Label(t4_fix_row1, text=S("lbl_fix_cat"), font=("Arial", 9), width=8).pack(side="left")
        fix_categories = list(PLATFORMS.keys())
        self.t4_fix_category_var = tk.StringVar(value=fix_categories[0] if fix_categories else "")
        self.t4_fix_category_combo = ttk.Combobox(
            t4_fix_row1, textvariable=self.t4_fix_category_var, values=fix_categories, state="readonly", width=30
        )
        self.t4_fix_category_combo.pack(side="left", padx=4)
        self.t4_fix_category_combo.bind("<<ComboboxSelected>>", self._on_t4_fix_category_change)

        t4_fix_row2 = ttk.Frame(t4_fix_frame)
        t4_fix_row2.pack(fill="x", padx=6, pady=(2, 6))
        ttk.Label(t4_fix_row2, text=S("lbl_fix_plat"), font=("Arial", 9), width=8).pack(side="left")
        init_fix_cat = self.t4_fix_category_var.get()
        init_fix_plats = PLATFORMS.get(init_fix_cat, [])
        self.t4_fix_platform_var = tk.StringVar(value=init_fix_plats[0] if init_fix_plats else "")
        self.t4_fix_platform_combo = ttk.Combobox(
            t4_fix_row2, textvariable=self.t4_fix_platform_var, values=init_fix_plats, state="readonly", width=30
        )
        self.t4_fix_platform_combo.pack(side="left", padx=4)
        ttk.Button(t4_fix_row2, text=S("btn_apply_plat"), command=self._t4_apply_platform).pack(
            side="left", padx=(8, 0)
        )

        ttk.Separator(tab4, orient="horizontal").pack(fill="x", pady=4)

        # ── 下半：疊圖切換 + 截圖 + 譯文 ──
        t4_ctrl = ttk.Frame(tab4)
        t4_ctrl.pack(fill="x", pady=(0, 4))
        self.t4_overlay_var = tk.BooleanVar(value=True)
        self.t4_toggle_btn = ttk.Button(t4_ctrl, text=S("btn_overlay"), width=12, command=self._t4_toggle_overlay)
        self.t4_toggle_btn.pack(side="left")

        # 截圖顯示（tk.Label，靠左，最大寬度 550）
        self.t4_img_label = tk.Label(tab4, bg="#111", anchor="nw")
        self.t4_img_label.pack(fill="x")

        # 暫存當筆資料（供疊圖/純圖切換用）
        self._t4_current_segments = []
        self._t4_current_img_path = None
        self._t4_current_db_id = None
        self._t4_tk_img = None  # 防止 GC

        # ══════════════════════════════════════════
        # Tab 5 — 歷史攻略資料
        # ══════════════════════════════════════════

        # ── 上半：遊戲篩選 + Treeview 清單 ──
        t5_filter = ttk.Frame(tab5)
        t5_filter.pack(fill="x", pady=(0, 4))
        ttk.Label(t5_filter, text=S("lbl_game"), font=("Arial", 9)).pack(side="left")
        self.t5_game_var = tk.StringVar(value=S("all_games"))
        self.t5_game_combo = ttk.Combobox(t5_filter, textvariable=self.t5_game_var, width=28, state="readonly")
        self.t5_game_combo.pack(side="left", padx=4)
        self.t5_game_combo.bind("<<ComboboxSelected>>", lambda e: self._t5_load_list())
        ttk.Button(t5_filter, text=S("btn_delete"), command=self._t5_delete).pack(side="right")

        t5_tree_frame = ttk.Frame(tab5)
        t5_tree_frame.pack(fill="x")
        self.t5_tree = ttk.Treeview(
            t5_tree_frame, columns=("rom_name", "time", "progress"), show="headings", height=6, selectmode="browse"
        )
        self.t5_tree.heading("rom_name", text=S("th_rom"))
        self.t5_tree.heading("time", text=S("th_time"))
        self.t5_tree.heading("progress", text=S("th_progress"))
        self.t5_tree.column("rom_name", width=160, stretch=True)
        self.t5_tree.column("time", width=135, anchor="center", stretch=False)
        self.t5_tree.column("progress", width=160)
        t5_tree_sb = ttk.Scrollbar(t5_tree_frame, orient="vertical", command=self.t5_tree.yview)
        self.t5_tree.configure(yscrollcommand=t5_tree_sb.set)
        t5_tree_sb.pack(side="right", fill="y")
        self.t5_tree.pack(side="left", fill="x", expand=True)
        self.t5_tree.bind("<<TreeviewSelect>>", self._t5_on_select)

        ttk.Separator(tab5, orient="horizontal").pack(fill="x", pady=4)

        # ── 下半：縮圖 + 進度 + 攻略 ──
        t5_bottom = ttk.Frame(tab5)
        t5_bottom.pack(fill="both", expand=True)

        # 左側縮圖
        t5_img_frame = ttk.Frame(t5_bottom)
        t5_img_frame.pack(side="left", anchor="n", padx=(0, 8))
        self.t5_guide_img_label = ttk.Label(t5_img_frame, text="", background="#cccccc", width=18)
        self.t5_guide_img_label.pack()
        self._t5_guide_tk_img = None  # 防止 GC

        # 右側文字
        t5_text_frame = ttk.Frame(t5_bottom)
        t5_text_frame.pack(side="left", fill="both", expand=True)
        ttk.Label(t5_text_frame, text=S("lbl_curr_prog"), font=("Arial", 10, "bold")).pack(anchor="w")
        self.t5_progress_label = ttk.Label(
            t5_text_frame, text="", font=("Arial", 14, "bold"), wraplength=310, justify="left"
        )
        self.t5_progress_label.pack(anchor="w", pady=(2, 8))

        ttk.Label(t5_text_frame, text=S("lbl_curr_guide"), font=("Arial", 10, "bold")).pack(anchor="w")
        t5_txt_frame = ttk.Frame(t5_text_frame)
        t5_txt_frame.pack(fill="both", expand=True)
        t5_txt_sb = ttk.Scrollbar(t5_txt_frame, orient="vertical")
        t5_txt_sb.pack(side="right", fill="y")
        self.t5_guide_text = tk.Text(
            t5_txt_frame,
            wrap="word",
            state="disabled",
            font=("Arial", 12),
            spacing1=4,
            spacing3=8,
            yscrollcommand=t5_txt_sb.set,
        )
        t5_txt_sb.config(command=self.t5_guide_text.yview)
        self.t5_guide_text.pack(side="left", fill="both", expand=True)

        self._t5_current_db_id = None

        # ══════════════════════════════════════════
        # Tab 6 — 歷史錄製
        # ══════════════════════════════════════════

        # ── 篩選列 ──
        t6_filter = ttk.Frame(tab6)
        t6_filter.pack(fill="x", pady=(0, 2))
        ttk.Label(t6_filter, text=S("lbl_game"), font=("Arial", 9)).pack(side="left")
        self.t6_game_var = tk.StringVar(value=S("all_games"))
        self.t6_game_combo = ttk.Combobox(t6_filter, textvariable=self.t6_game_var, width=24, state="readonly")
        self.t6_game_combo.pack(side="left", padx=4)
        self.t6_game_combo.bind("<<ComboboxSelected>>", lambda e: self._t6_load_list())
        ttk.Button(t6_filter, text=S("btn_session_delete"), command=self._t6_delete_session).pack(side="right")

        # ── 場次清單 Treeview ──
        t6_tree_frame = ttk.Frame(tab6)
        t6_tree_frame.pack(fill="x")
        self.t6_tree = ttk.Treeview(
            t6_tree_frame,
            columns=("game", "started_at", "frames", "platform", "size"),
            show="headings",
            height=6,
            selectmode="browse",
        )
        self.t6_tree.heading("game", text=S("th_session_game"))
        self.t6_tree.heading("started_at", text=S("th_session_start"))
        self.t6_tree.heading("frames", text=S("th_session_frames"))
        self.t6_tree.heading("platform", text=S("th_session_plat"))
        self.t6_tree.heading("size", text=S("th_size"))
        self.t6_tree.column("game", width=130, stretch=True)
        self.t6_tree.column("started_at", width=130, anchor="center", stretch=False)
        self.t6_tree.column("frames", width=50, anchor="e", stretch=False)
        self.t6_tree.column("platform", width=80, stretch=False)
        self.t6_tree.column("size", width=65, anchor="e", stretch=False)
        t6_sb = ttk.Scrollbar(t6_tree_frame, orient="vertical", command=self.t6_tree.yview)
        self.t6_tree.configure(yscrollcommand=t6_sb.set)
        t6_sb.pack(side="right", fill="y")
        self.t6_tree.pack(side="left", fill="x", expand=True)
        self.t6_tree.bind("<<TreeviewSelect>>", self._t6_on_select)

        ttk.Separator(tab6, orient="horizontal").pack(fill="x", pady=4)

        # ── 操作區：回放按鈕 + 狀態資訊 ──
        t6_ctrl = ttk.Frame(tab6)
        t6_ctrl.pack(fill="x", pady=(0, 4))
        self._btn_t6_replay = ttk.Button(
            t6_ctrl, text=S("btn_session_replay"), command=self._t6_replay_session, state="disabled"
        )
        self._btn_t6_replay.pack(side="left", padx=(0, 8))
        self._t6_info_label = ttk.Label(t6_ctrl, text="", font=("Arial", 9), foreground="gray")
        self._t6_info_label.pack(side="left")

        # ── 縮圖預覽（選取場次後顯示第一幀縮圖）──
        self.t6_thumb_label = tk.Label(tab6, bg="#111", anchor="nw")
        self.t6_thumb_label.pack(fill="both", expand=True)
        self._t6_thumb_img = None
        self._t6_current_session_id = None

        # ── 切換頁籤事件（Tab3/4/5/6 各自刷新） ──
        nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # ═══════════════════════════════════
        # 翻譯結果視窗
        # ═══════════════════════════════════
        self.display = tk.Toplevel(root)
        self.display.withdraw()  # 立即隱藏，防止建立時閃現
        self.display.title(S("title_translate"))
        _load_app_icon(self.display)
        self.display.attributes("-topmost", True)
        self.display.configure(bg="black")
        mesen_rect = self._find_mesen_window()
        if mesen_rect:
            disp_x = mesen_rect[2] + 10
            disp_y = mesen_rect[1]
        else:
            disp_x = main_w + 10
            disp_y = 0
        self.display.geometry(f"{DISPLAY_WIDTH_SMALL}x{DISPLAY_INIT_HEIGHT}+{disp_x}+{disp_y}")

        # 導覽列（底部，半透明黑底）
        nav_bar = tk.Frame(self.display, bg="#222222")
        nav_bar.pack(side="bottom", fill="x")
        self._nav_prev_btn = tk.Button(
            nav_bar,
            text="▲",
            bg="#222222",
            fg="white",
            relief="flat",
            font=("Arial", 10, "bold"),
            activebackground="#444444",
            activeforeground="white",
            command=self._nav_prev,
            width=3,
        )
        self._nav_prev_btn.pack(side="left", padx=4)
        self._nav_label = tk.Label(nav_bar, text="", bg="#222222", fg="#aaaaaa", font=("Arial", 8))
        self._nav_label.pack(side="left", expand=True)
        self._nav_next_btn = tk.Button(
            nav_bar,
            text="▼",
            bg="#222222",
            fg="white",
            relief="flat",
            font=("Arial", 10, "bold"),
            activebackground="#444444",
            activeforeground="white",
            command=self._nav_next,
            width=3,
        )
        self._nav_next_btn.pack(side="right", padx=4)

        self.canvas_label = tk.Label(self.display, bg="black")
        self.canvas_label.pack(fill="both", expand=True)
        self.display.withdraw()  # 啟動時隱藏，首次翻譯完成後才顯示
        self.display.protocol("WM_DELETE_WINDOW", self._on_display_close)

        # 翻譯歷史導覽狀態
        self._nav_rom_name = ""  # 目前遊戲
        self._nav_ids = []  # 同遊戲所有 id（DESC）
        self._nav_index = 0  # 目前在清單中的位置（0=最新）

        # ═══════════════════════════════════
        # 攻略資訊視窗
        # ═══════════════════════════════════
        self.guide_display = tk.Toplevel(root)
        self.guide_display.withdraw()  # 立即隱藏，防止建立時閃現
        self.guide_display.title(S("title_guide"))
        _load_app_icon(self.guide_display)
        self.guide_display.attributes("-topmost", True)
        self.guide_display.configure(bg="#1a1a2e")
        guide_x = disp_x + DISPLAY_WIDTH_SMALL + 10
        self.guide_display.geometry(f"{DISPLAY_WIDTH_SMALL}x{DISPLAY_INIT_HEIGHT}+{guide_x}+{disp_y}")

        # 攻略導覽列（底部）
        guide_nav_bar = tk.Frame(self.guide_display, bg="#2a2a4e")
        guide_nav_bar.pack(side="bottom", fill="x")
        self._guide_nav_prev_btn = tk.Button(
            guide_nav_bar,
            text="▲",
            bg="#2a2a4e",
            fg="white",
            relief="flat",
            font=("Arial", 10, "bold"),
            activebackground="#444466",
            activeforeground="white",
            command=self._guide_nav_prev,
            width=3,
        )
        self._guide_nav_prev_btn.pack(side="left", padx=4)
        self._guide_nav_label = tk.Label(guide_nav_bar, text="", bg="#2a2a4e", fg="#aaaaaa", font=("Arial", 8))
        self._guide_nav_label.pack(side="left", expand=True)
        self._guide_nav_next_btn = tk.Button(
            guide_nav_bar,
            text="▼",
            bg="#2a2a4e",
            fg="white",
            relief="flat",
            font=("Arial", 10, "bold"),
            activebackground="#444466",
            activeforeground="white",
            command=self._guide_nav_next,
            width=3,
        )
        self._guide_nav_next_btn.pack(side="right", padx=4)

        self.guide_canvas = tk.Label(self.guide_display, bg="#1a1a2e")
        self.guide_canvas.pack(fill="both", expand=True)
        self.guide_display.withdraw()  # 啟動時隱藏
        self.guide_display.protocol("WM_DELETE_WINDOW", self._on_guide_display_close)

        # 攻略導覽狀態
        self._guide_nav_rom_name = ""
        self._guide_nav_ids = []
        self._guide_nav_index = 0

        self.root.bind("<Configure>", self._on_main_move)
        self._start_position_polling()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # ── 畫面穩定自動翻譯 ──
        self._stable_prev_img = None
        self._stable_count = 0
        self._stable_last_hash = ""
        self._auto_trans_job = None

        # 視窗位置快取（避免每次 polling 都呼叫 EnumWindows 與 geometry）
        self._mesen_cache_rect = None  # (left,top,right,bottom) 上次找到的位置
        self._mesen_cache_title = ""  # 快取時對應的 target title
        self._mesen_cache_ts = 0.0  # 快取時間戳
        self._last_disp_geom = ""  # 上次設定的翻譯視窗 geometry
        self._last_guide_geom = ""  # 上次設定的攻略視窗 geometry
        _MESEN_CACHE_TTL = 0.5  # 快取有效期（秒），與 polling 間隔一致
        # 若 config 記錄為啟用，啟動輪詢
        # 自動翻譯不儲存，啟動時不自動開啟

        # ── 場次錄製實例變數 ──
        self._session_id = None
        self._session_start_time = 0.0
        self._session_elapsed_job = None
        self._session_seq = 0
        self._session_game_name = ""
        self._session_dir = ""
        self._session_running = False
        self._session_translating = False  # 防止翻譯 thread 堆積
        self._session_capture_job = None
        self._session_prev_gray = None
        self._session_stable_cnt = 0
        self._session_last_hash = ""
        self._playback_window = None
        self._playback_job = None
        self._playback_seq = 0
        self._playback_last_trans = None
        self._playback_auto_open_job = None

        # ── 請求佇列 worker thread ──
        self._worker_thread = threading.Thread(target=self._request_worker, daemon=True)
        self._worker_thread.start()

        # ── 套用已儲存主題 ──
        saved_theme = self.config.get("ui_theme", "light")
        apply_theme(self.root, saved_theme)
        self._apply_treeview_tags(saved_theme)

        # ── 關閉 Splash，同時顯示主視窗 ──
        if splash:
            splash.update_text("完成！" if CURRENT_LANG != "en" else "Ready!")
            def _finish():
                splash.close()
                self.root.deiconify()
            self.root.after(300, _finish)
        else:
            self.root.deiconify()

    # ══════════════════════════════════════════
    # Tab 切換事件
    # ══════════════════════════════════════════
    def _on_tab_changed(self, event):
        nb = event.widget
        idx = nb.index("current")
        if idx == 2:  # Tab 3 — 引擎配額
            self._refresh_quota_table()
        elif idx == 3:  # Tab 4 — 歷史翻譯
            self._t4_refresh_games()
            self._t4_load_list()
        elif idx == 4:  # Tab 5 — 歷史攻略
            self._t5_refresh_games()
            self._t5_load_list()
        elif idx == 5:  # Tab 6 — 歷史錄製
            self._t6_refresh_games()
            self._t6_load_list()

    def _refresh_quota_table(self):
        global CURRENT_LANG
        CURRENT_LANG = self.config.get("ui_lang", "zh")
        used_today = self.config.get("used_today", {})
        no_quota = S("quota_no_limit")
        cur_eng = self.engine_var.get()
        cur_model = self.model_var.get()

        # 更新欄位標頭文字（切換語系後即時生效）
        self.quota_table.heading("engine", text=S("th_engine"))
        self.quota_table.heading("model", text=S("th_model"))
        self.quota_table.heading("used", text=S("th_used"))
        self.quota_table.heading("limit", text=S("th_limit"))

        # 清空舊資料
        for row in self.quota_table.get_children():
            self.quota_table.delete(row)

        row_idx = 0
        seen_iids = set()  # 防止重複 iid
        for eng in ENGINE_ORDER:
            models = self._get_engine_models(eng)
            # 去重，保留順序
            seen_models = []
            for m in models:
                if m not in seen_models:
                    seen_models.append(m)
            for m in seen_models:
                iid = f"{eng}|{m}"
                if iid in seen_iids:
                    continue
                seen_iids.add(iid)
                used = used_today.get(m, 0)
                limit = MODEL_DAILY_LIMITS.get(m, -1)
                rpm = MODEL_RPM.get(m, "-")
                estimated_models = self.config.get("estimated_quota_models", [])
                if limit == -1:
                    limit_str = "?"
                elif limit == 0:
                    limit_str = no_quota
                elif m in estimated_models:
                    limit_str = S("quota_estimated").format(n=limit)
                else:
                    limit_str = str(limit)
                rpm_str = str(rpm) if rpm != "-" else "-"

                # 決定 tag
                is_current = eng == cur_eng and m == cur_model
                is_no_quota = limit == 0
                is_unknown = limit == -1
                if is_current:
                    tags = ("current",)
                elif is_no_quota:
                    tags = ("no_quota",)
                elif is_unknown:
                    tags = ("unknown_quota",)
                else:
                    tags = ("odd",) if row_idx % 2 == 0 else ("even",)

                self.quota_table.insert(
                    "", "end", iid=iid, values=(eng, m, used, limit_str, rpm_str), tags=tags
                )
                row_idx += 1

            # 引擎間空白分隔行
            sep_iid = f"sep_{eng}"
            if sep_iid not in seen_iids:
                seen_iids.add(sep_iid)
                self.quota_table.insert("", "end", iid=sep_iid, values=("", "", "", "", ""), tags=("sep",))

    # ══════════════════════════════════════════
    # Tab 4 — 歷史翻譯：內部方法
    # ══════════════════════════════════════════

    # ══════════════════════════════════════════
    # ══════════════════════════════════════════
    # 選單列方法
    # ══════════════════════════════════════════

    def _switch_lang(self, lang: str):
        if self.config.get("ui_lang") == lang:
            return
        self.config["ui_lang"] = lang
        save_config(self.config)

        if lang == "zh":
            messagebox.showinfo("LangForge", S("msg_lang_changed_zh"))
        else:
            messagebox.showinfo("LangForge", "UI language set to English. Please restart to apply.")

    def _switch_theme(self, theme_name: str):
        if self.config.get("ui_theme") == theme_name:
            return
        self.config["ui_theme"] = theme_name
        save_config(self.config)
        apply_theme(self.root, theme_name)
        self._apply_treeview_tags(theme_name)
        # 重設狀態列預設色
        t = THEMES.get(theme_name, THEMES["light"])
        if hasattr(self, "status") and self.status.winfo_exists():
            self.status.config(foreground=t["status_idle"])

    def _apply_treeview_tags(self, theme_name: str):
        if not hasattr(self, "quota_table") or not self.quota_table.winfo_exists():
            return
        t = THEMES.get(theme_name, THEMES["light"])
        self.quota_table.tag_configure("odd",     background=t["tag_odd"])
        self.quota_table.tag_configure("even",    background=t["tag_even"])
        self.quota_table.tag_configure("current", background=t["tag_current_bg"],
                                       foreground=t["fg"], font=("Arial", 9, "bold"))
        self.quota_table.tag_configure("no_quota", foreground=t["tag_no_quota"])
        self.quota_table.tag_configure("unknown_quota", foreground="#cc7700")
        self.quota_table.tag_configure("sep",     background=t["tag_sep"])

    # ══════════════════════════════════════════
    # 場次錄製
    # ══════════════════════════════════════════
    def _on_session_toggle(self):
        if self._session_running:
            self._stop_session()
        else:
            self._start_session()

    def _start_session(self):

        game_name = self.title_var.get().strip() or "unknown"
        platform = self.platform_var.get().strip()
        ts = time.strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[\\/:*?"<>|]', "_", game_name)
        session_dir = os.path.join(self.LOG_DIR, "sessions", f"{ts}_{safe_name}")
        os.makedirs(session_dir, exist_ok=True)

        conn = sqlite3.connect(self.DB_PATH)
        cur = conn.execute(
            "INSERT INTO sessions (game_name, platform, started_at) VALUES (?,?,?)",
            (game_name, platform, time.strftime("%Y-%m-%d %H:%M:%S")),
        )
        session_id = cur.lastrowid
        conn.commit()
        conn.close()

        self._session_id = session_id
        self._session_seq = 0
        self._session_game_name = game_name
        self._session_dir = session_dir
        self._btn_session_start.config(text=S("btn_stop_session_inline"))
        self._session_running = True
        self._session_prev_gray = None
        self._session_stable_cnt = 0
        self._session_last_hash = ""
        self._session_translating = False  # 防止翻譯 thread 堆積

        self._session_status_label.config(text=S("session_recording"), foreground="red")

        self._playback_auto_open_job = self.root.after(PLAYBACK_DELAY_SECONDS * 1000, self._open_playback_window)
        self._session_start_time = time.time()
        self._session_elapsed_job = None
        self._session_elapsed_tick()
        self._session_capture_loop()
        log(f"場次開始: session_id={session_id}, dir={session_dir}")

    def _stop_session(self):

        self._session_running = False
        if self._session_capture_job:
            self.root.after_cancel(self._session_capture_job)
            self._session_capture_job = None
        if self._playback_auto_open_job:
            self.root.after_cancel(self._playback_auto_open_job)
            self._playback_auto_open_job = None

        if self._session_id:
            conn = sqlite3.connect(self.DB_PATH)
            conn.execute(
                "UPDATE sessions SET ended_at=?, total_frames=? WHERE id=?",
                (time.strftime("%Y-%m-%d %H:%M:%S"), self._session_seq, self._session_id),
            )
            conn.commit()
            conn.close()

        if getattr(self, "_session_elapsed_job", None):
            self.root.after_cancel(self._session_elapsed_job)
            self._session_elapsed_job = None
        self._btn_session_start.config(text=S("btn_start_session"))
        self._session_status_label.config(text=S("session_idle"), foreground="gray")
        log(f"場次結束: session_id={self._session_id}, 共 {self._session_seq} 幀")

    def _session_elapsed_tick(self):
        if not self._session_running:
            return
        elapsed = int(time.time() - self._session_start_time)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        if h > 0:
            t_str = S("session_elapsed_h").format(h=h, m=m, s=s)
        elif m > 0:
            t_str = S("session_elapsed_m").format(m=m, s=s)
        else:
            t_str = S("session_elapsed_s").format(s=s)
        self._session_status_label.config(text=S("session_elapsed").format(t=t_str), foreground="red")
        self._session_elapsed_job = self.root.after(1000, self._session_elapsed_tick)

    def _session_capture_loop(self):
        if not self._session_running:
            return
        try:
            image_pil = self._try_capture()
            if image_pil is not None:
                import numpy as np

                self._session_seq += 1
                ts_str = time.strftime("%Y-%m-%d %H:%M:%S")
                filename = f'{self._session_seq:06d}_{time.strftime("%H%M%S")}.jpg'
                img_path = os.path.join(self._session_dir, filename)
                image_pil.save(img_path, format="JPEG", quality=85)

                rel_path = os.path.relpath(img_path, self.LOG_DIR)
                self._db_conn.execute(
                    "INSERT INTO frames (session_id, seq, ts, img_path) VALUES (?,?,?,?)",
                    (self._session_id, self._session_seq, ts_str, rel_path),
                )
                self._db_conn.commit()

                gray = image_pil.convert("L")
                if self._session_prev_gray is not None:
                    diff = ImageChops.difference(gray, self._session_prev_gray)
                    avg_diff = np.mean(np.array(diff))
                    if avg_diff < SESSION_STABLE_DIFF:
                        self._session_stable_cnt += 1
                    else:
                        self._session_stable_cnt = 0
                    if self._session_stable_cnt >= SESSION_STABLE_COUNT:
                        img_hash = hashlib.md5(image_pil.tobytes()).hexdigest()
                        if img_hash != self._session_last_hash and not self._session_translating:
                            self._session_last_hash = img_hash
                            self._session_stable_cnt = 0
                            self._session_translating = True
                            seq_to_translate = self._session_seq
                            snap = {
                                "mode":          self.engine_mode_var.get(),
                                "src_lang":      self.src_lang_var.get(),
                                "tgt_lang":      self.tgt_lang_var.get(),
                                "eng":           self.engine_var.get(),
                                "api_key":       self.api_entry.get().strip(),
                                "model":         self.model_var.get(),
                                "ollama_model":  self.ollama_model_var.get() if hasattr(self, "ollama_model_var") else "",
                                "ollama_timeout": self.ollama_timeout_var.get() if hasattr(self, "ollama_timeout_var") else str(OLLAMA_TIMEOUT),
                            }
                            threading.Thread(
                                target=self._session_translate, args=(image_pil, seq_to_translate, snap), daemon=True
                            ).start()
                self._session_prev_gray = gray
        except Exception as e:
            log(f"場次截圖失敗: {e}")
        self._session_capture_job = self.root.after(SESSION_CAPTURE_INTERVAL_MS, self._session_capture_loop)

    def _session_translate(self, image_pil, seq, snap=None):
        if snap is None:
            snap = {}
        try:
            mode     = snap.get("mode",     self.engine_mode_var.get())
            src_lang = snap.get("src_lang", self.src_lang_var.get())
            tgt_lang = snap.get("tgt_lang", self.tgt_lang_var.get())

            if mode == "ocr":
                # ── OCR 模式：EasyOCR + Google 翻譯（縮放 + 並行）──
                import easyocr, numpy as np

                ocr_langs = _bcp47_to_easyocr(LANG_TO_BCP47.get(src_lang, "ja"))
                if not hasattr(self, "_easyocr_reader") or self._easyocr_langs != ocr_langs:
                    warnings.filterwarnings("ignore")
                    logging.getLogger("easyocr").setLevel(logging.ERROR)
                    self._easyocr_reader = easyocr.Reader(ocr_langs, gpu=False, verbose=False)
                    self._easyocr_langs = ocr_langs

                orig_w, orig_h = image_pil.width, image_pil.height
                ocr_img, scale = _resize_for_ocr(image_pil)
                img_np = np.array(ocr_img)
                ocr_results = self._easyocr_reader.readtext(img_np)
                ocr_results = [r for r in ocr_results if r[2] >= OCR_CONF_THRESHOLD]
                if not ocr_results:
                    return
                src_bcp = LANG_TO_BCP47.get(src_lang, "auto")
                tgt_bcp = LANG_TO_BCP47.get(tgt_lang, "zh-TW")
                texts = [text for _, text, _ in ocr_results]
                with ThreadPoolExecutor(max_workers=min(OCR_TRANSLATE_WORKERS, len(texts))) as pool:
                    translated_list = list(pool.map(
                        lambda t: _google_translate(t, src_bcp, tgt_bcp), texts
                    ))
                result = []
                for (bbox, text, conf), tw in zip(ocr_results, translated_list):
                    xs = [p[0] / scale for p in bbox]
                    ys = [p[1] / scale for p in bbox]
                    result.append({
                        "tw": tw,
                        "x": round(min(xs) / orig_w, 4),
                        "y": round(min(ys) / orig_h, 4),
                        "w": round((max(xs) - min(xs)) / orig_w, 4),
                        "h": round((max(ys) - min(ys)) / orig_h, 4),
                    })
                model = "OCR+GoogleTranslate"

            elif mode == "local":
                # ── OLLAMA 本地模式 ──
                ollama_model = snap.get("ollama_model", self.ollama_model_var.get() if hasattr(self, "ollama_model_var") else "")
                if not ollama_model:
                    return
                prompt = build_translate_prompt(src_lang, tgt_lang)
                try:
                    ollama_timeout = int(snap.get("ollama_timeout", OLLAMA_TIMEOUT))
                    if ollama_timeout <= 0:
                        ollama_timeout = OLLAMA_TIMEOUT
                except (ValueError, TypeError):
                    ollama_timeout = OLLAMA_TIMEOUT
                result = call_ollama(ollama_model, image_pil, prompt, timeout=ollama_timeout)
                model = ollama_model

            else:
                # ── 雲端引擎 ──
                eng     = snap.get("eng",     self.engine_var.get())
                api_key = snap.get("api_key", self.api_entry.get().strip())
                model   = snap.get("model",   self.model_var.get())
                prompt = build_translate_prompt(src_lang, tgt_lang)
                caller = ENGINE_CALLERS[eng]
                result = caller(api_key, model, image_pil, prompt)

            if isinstance(result, list) and result:
                trans_json = json.dumps(result, ensure_ascii=False)
                self._db_conn.execute(
                    "UPDATE frames SET translation=? WHERE session_id=? AND seq=?", (trans_json, self._session_id, seq)
                )
                self._db_conn.commit()
                log(f"場次翻譯回寫: session={self._session_id}, seq={seq}")
                if mode not in ("local", "ocr"):

                    def _update_quota(m=model):
                        self.config["used_today"][m] = self.config["used_today"].get(m, 0) + 1
                        save_config(self.config)
                        self.root.after(0, self._refresh_quota)

                    self.root.after(0, _update_quota)
        except Exception as e:
            log(f"場次翻譯失敗: seq={seq}, {e}")
        finally:
            self._session_translating = False
        if self._playback_window and self._playback_window.winfo_exists():
            self._playback_window.lift()
            return
        if not self._session_id:
            return

        self._playback_window = tk.Toplevel(self.root)
        self._playback_window.title(S("title_playback_live").format(name=self._session_game_name))
        self._playback_window.configure(bg="black")
        self._playback_window.attributes("-topmost", True)
        _load_app_icon(self._playback_window)

        scr_w = self.root.winfo_screenwidth()
        scr_h = self.root.winfo_screenheight()
        saved_x = self.config.get("playback_x", 10)
        saved_y = self.config.get("playback_y", scr_h - 700)
        self._playback_window.geometry(f"{DISPLAY_WIDTH_SMALL}x600+{saved_x}+{saved_y}")

        def _on_move(e=None):
            self.config["playback_x"] = self._playback_window.winfo_x()
            self.config["playback_y"] = self._playback_window.winfo_y()
            save_config(self.config)

        self._playback_window.bind("<Configure>", _on_move)

        info_frame = tk.Frame(self._playback_window, bg="#1a1a1a")
        info_frame.pack(fill="x")
        self._pb_info_label = tk.Label(info_frame, text="", fg="#aaaaaa", bg="#1a1a1a", font=("Arial", 8))
        self._pb_info_label.pack(side="left", padx=8, pady=2)

        btn_frame_pb = tk.Frame(self._playback_window, bg="#1a1a1a")
        btn_frame_pb.pack(side="bottom", fill="x")
        tk.Button(
            btn_frame_pb, text=S("btn_stop_playback"), command=self._stop_playback, bg="#333", fg="white", relief="flat"
        ).pack(pady=4, padx=8, fill="x")

        self._pb_canvas = tk.Label(self._playback_window, bg="black")
        self._pb_canvas.pack(fill="both", expand=True)
        self._playback_window.protocol("WM_DELETE_WINDOW", self._stop_playback)

        delay_frames = int(PLAYBACK_DELAY_SECONDS / (SESSION_CAPTURE_INTERVAL_MS / 1000))
        if self._session_seq > delay_frames:
            # 錄製時間充足：從延遲點開始
            self._playback_seq = self._session_seq - delay_frames
        else:
            # 錄製時間不足 10 分鐘：從第 1 幀開始播放所有已錄內容
            self._playback_seq = 1
        self._playback_last_trans = None
        self._playback_loop()

    def _playback_loop(self):
        if not self._playback_window or not self._playback_window.winfo_exists():
            return
        delay_frames = int(PLAYBACK_DELAY_SECONDS / (SESSION_CAPTURE_INTERVAL_MS / 1000))
        if self._session_running:
            # 錄製中：保持延遲，等錄製端超前足夠幀數才播
            if self._playback_seq > self._session_seq - delay_frames:
                self._playback_job = self.root.after(PLAYBACK_FPS_MS, self._playback_loop)
                return
        else:
            # 場次已結束：播到最後一幀就停止
            if self._playback_seq > self._session_seq:
                self._pb_info_label.config(text=S("playback_done"))
                return


        try:
            row = self._db_conn.execute(
                "SELECT ts, img_path, translation FROM frames WHERE session_id=? AND seq=?",
                (self._session_id, self._playback_seq),
            ).fetchone()

            if row:
                ts_str, img_path, trans_json = row
                full_path = os.path.join(self.LOG_DIR, img_path)
                image_pil = Image.open(full_path)
                orig_w, orig_h = image_pil.size
                pb_w = _get_display_width(orig_w)
                scale = pb_w / orig_w
                pb_h = int(orig_h * scale)
                image_pil = image_pil.resize((pb_w, pb_h), Image.LANCZOS)

                if trans_json:
                    self._playback_last_trans = json.loads(trans_json)

                if self._playback_last_trans:
                    out_img = self._render_to_image(self._playback_last_trans, image_pil, pb_w, pb_h)
                else:
                    out_img = image_pil

                tk_img = ImageTk.PhotoImage(out_img)
                self._pb_canvas.config(image=tk_img)
                self._pb_canvas._img_ref = tk_img
                self._playback_window.geometry(f"{pb_w}x{pb_h + 50}")

                lag_secs = self._session_seq - self._playback_seq
                lag_min = lag_secs // 2 // 60
                lag_sec = (lag_secs // 2) % 60
                self._pb_info_label.config(text=S("lbl_playback_lag").format(ts=ts_str, lag=f"{lag_min:02d}:{lag_sec:02d}"))

            self._playback_seq += 1
            # 同步進度條（Tab6 回放模式）
            if hasattr(self, "_pb_progress_var"):
                try:
                    self._pb_progress_var.set(self._playback_seq)
                except Exception:
                    pass
        except Exception as e:
            log(f"播放失敗: seq={self._playback_seq}, {e}")
            self._playback_seq += 1

        # 暫停中不繼續排下一幀
        if getattr(self, "_pb_paused", False):
            return
        self._playback_job = self.root.after(PLAYBACK_FPS_MS, self._playback_loop)

    def _stop_playback(self):
        if self._playback_job:
            self.root.after_cancel(self._playback_job)
            self._playback_job = None
        if self._playback_window and self._playback_window.winfo_exists():
            self._playback_window.destroy()
        self._playback_window = None
        log("播放已停止")

    # ══════════════════════════════════════════
    # Tab6 — 歷史錄製
    # ══════════════════════════════════════════
    def _t6_refresh_games(self):
        try:
            rows = self._db_conn.execute("SELECT DISTINCT game_name FROM sessions ORDER BY game_name").fetchall()
            games = [S("all_games")] + [r[0] for r in rows]
            self.t6_game_combo["values"] = games
            if self.t6_game_var.get() not in games:
                self.t6_game_var.set(S("all_games"))
        except Exception as e:
            log(f"[Tab6] refresh games 失敗: {e}")

    def _t6_load_list(self):
        T6_PAGE_SIZE = 500
        try:
            game = self.t6_game_var.get()
            if game == S("all_games"):
                rows = self._db_conn.execute(
                    "SELECT id, game_name, started_at, total_frames, platform, dir_size_kb "
                    f"FROM sessions ORDER BY started_at DESC LIMIT {T6_PAGE_SIZE}"
                ).fetchall()
            else:
                rows = self._db_conn.execute(
                    "SELECT id, game_name, started_at, total_frames, platform, dir_size_kb "
                    f"FROM sessions WHERE game_name=? ORDER BY started_at DESC LIMIT {T6_PAGE_SIZE}",
                    (game,),
                ).fetchall()

            new_ids = {str(r[0]) for r in rows}
            existing_ids = set(self.t6_tree.get_children())
            for iid in existing_ids - new_ids:
                self.t6_tree.delete(iid)
            for r in reversed(rows):
                sid, gname, started, frames, plat, size_kb = r
                size_str = f"{size_kb/1024:.1f} MB" if (size_kb or 0) >= 1024 else f"{size_kb or 0} KB"
                if str(sid) not in existing_ids:
                    self.t6_tree.insert("", 0, iid=str(sid), values=(gname, started, frames or 0, plat or "", size_str))
        except Exception as e:
            log(f"[Tab6] load list 失敗: {e}")

    def _t6_on_select(self, event=None):
        sel = self.t6_tree.selection()
        if not sel:
            return
        sid = int(sel[0])
        self._t6_current_session_id = sid
        try:
            row = self._db_conn.execute(
                "SELECT img_path, ts FROM frames WHERE session_id=? ORDER BY seq ASC LIMIT 1", (sid,)
            ).fetchone()
            info = self._db_conn.execute(
                "SELECT game_name, started_at, ended_at, total_frames, platform FROM sessions WHERE id=?", (sid,)
            ).fetchone()

            # 資訊標籤
            if info:
                gname, started, ended, frames, plat = info
                ended_str = S("lbl_session_ended_live") if not ended else ended
                self._t6_info_label.config(
                    text=S("lbl_session_info").format(
                        name=gname, start=started, end=ended_str,
                        frames=frames or 0, plat=plat or ""
                    ),
                    foreground="steelblue"
                )

            # 縮圖
            if row:
                full_path = os.path.join(self.LOG_DIR, row[0])
                try:
                    img = Image.open(full_path).convert("RGB")
                    # 縮放至適合顯示
                    label_w = max(self.t6_thumb_label.winfo_width(), 400)
                    label_h = max(self.root.winfo_height() - 350, 100)
                    scale = min(label_w / img.width, label_h / img.height, 1.0)
                    img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
                    self._t6_thumb_img = ImageTk.PhotoImage(img)
                    self.t6_thumb_label.config(image=self._t6_thumb_img)
                except Exception:
                    self.t6_thumb_label.config(image="")

            self._btn_t6_replay.config(state="normal")
        except Exception as e:
            log(f"[Tab6] on_select 失敗: {e}")

    def _t6_delete_session(self):

        sel = self.t6_tree.selection()
        if not sel:
            self._t6_info_label.config(text=S("session_no_select"), foreground="red")
            return
        sid = int(sel[0])
        row = self.t6_tree.item(sel[0], "values")
        game_name = row[0] if row else str(sid)
        if not messagebox.askyesno(S("dlg_confirm_delete"), S("dlg_delete_session").format(name=game_name)):
            return
        try:
            conn = sqlite3.connect(self.DB_PATH)
            # 找截圖目錄
            first = conn.execute("SELECT img_path FROM frames WHERE session_id=? LIMIT 1", (sid,)).fetchone()
            conn.execute("DELETE FROM frames WHERE session_id=?", (sid,))
            conn.execute("DELETE FROM sessions WHERE id=?", (sid,))
            conn.commit()
            conn.close()
            # 刪除截圖目錄
            if first:
                img_dir = os.path.dirname(os.path.join(self.LOG_DIR, first[0]))
                if os.path.isdir(img_dir):

                    shutil.rmtree(img_dir, ignore_errors=True)
                    # 若父目錄（sessions/）已空，一併移除
                    parent_dir = os.path.dirname(img_dir)
                    if os.path.isdir(parent_dir) and not os.listdir(parent_dir):
                        os.rmdir(parent_dir)
            log(f"[Tab6] 已刪除場次 {sid}")
            self.t6_thumb_label.config(image="")
            self._t6_info_label.config(text="", foreground="gray")
            self._btn_t6_replay.config(state="disabled")
            self._t6_load_list()
            self._t6_refresh_games()
        except Exception as e:
            log(f"[Tab6] delete 失敗: {e}")

    def _t6_replay_session(self):

        sid = self._t6_current_session_id
        if not sid:
            return

        # 若播放視窗已存在先關閉
        if self._playback_window and self._playback_window.winfo_exists():
            self._stop_playback()

        # 取場次資訊
        try:
            info = self._db_conn.execute(
                "SELECT game_name, total_frames FROM sessions WHERE id=?", (sid,)
            ).fetchone()
        except Exception as e:
            log(f"[Tab6] replay 取資訊失敗: {e}")
            return

        if not info:
            return
        game_name, total_frames = info

        # 建立播放視窗
        self._playback_window = tk.Toplevel(self.root)
        self._playback_window.title(S("title_playback_replay").format(name=game_name))
        self._playback_window.configure(bg="black")
        self._playback_window.attributes("-topmost", True)
        _load_app_icon(self._playback_window)

        scr_w = self.root.winfo_screenwidth()
        scr_h = self.root.winfo_screenheight()
        saved_x = self.config.get("playback_x", 10)
        saved_y = self.config.get("playback_y", scr_h - 700)
        self._playback_window.geometry(f"{DISPLAY_WIDTH_SMALL}x620+{saved_x}+{saved_y}")

        info_frame = tk.Frame(self._playback_window, bg="#1a1a1a")
        info_frame.pack(fill="x")
        self._pb_info_label = tk.Label(info_frame, text="", fg="#aaaaaa", bg="#1a1a1a", font=("Arial", 8))
        self._pb_info_label.pack(side="left", padx=8, pady=2)

        # 進度列
        pb_prog_frame = tk.Frame(self._playback_window, bg="#1a1a1a")
        pb_prog_frame.pack(fill="x", padx=8)
        self._pb_progress_var = tk.DoubleVar(value=0)
        self._pb_scale = tk.Scale(
            pb_prog_frame,
            variable=self._pb_progress_var,
            from_=1,
            to=max(1, total_frames),
            orient="horizontal",
            bg="#1a1a1a",
            fg="white",
            troughcolor="#333",
            highlightthickness=0,
            command=lambda v: self._t6_seek(int(float(v))),
        )
        self._pb_scale.pack(fill="x")

        btn_frame_pb = tk.Frame(self._playback_window, bg="#1a1a1a")
        btn_frame_pb.pack(side="bottom", fill="x")
        # 播放/暫停 + 停止
        self._pb_paused = False
        self._pb_pause_btn = tk.Button(
            btn_frame_pb,
            text=S("btn_pause"),
            command=self._t6_toggle_pause,
            bg="#333",
            fg="white",
            relief="flat",
            width=10,
        )
        self._pb_pause_btn.pack(side="left", pady=4, padx=(8, 4))
        tk.Button(
            btn_frame_pb, text=S("btn_stop_playback"), command=self._stop_playback, bg="#333", fg="white", relief="flat"
        ).pack(side="left", pady=4, padx=4, fill="x", expand=True)

        self._pb_canvas = tk.Label(self._playback_window, bg="black")
        self._pb_canvas.pack(fill="both", expand=True)
        self._playback_window.protocol("WM_DELETE_WINDOW", self._stop_playback)

        # 設定回放狀態（借用現有播放機制，session_running=False → 播到底停止）
        self._session_id = sid
        self._session_seq = total_frames
        self._session_game_name = game_name
        self._session_running = False
        self._playback_seq = 1
        self._playback_last_trans = None
        self._playback_job = None
        self._playback_loop()

    def _t6_seek(self, seq: int):
        if self._playback_job:
            self.root.after_cancel(self._playback_job)
            self._playback_job = None
        self._playback_seq = max(1, seq)
        if not self._pb_paused:
            self._playback_loop()

    def _t6_toggle_pause(self):
        self._pb_paused = not self._pb_paused
        if hasattr(self, "_pb_pause_btn") and self._pb_pause_btn.winfo_exists():
            self._pb_pause_btn.config(text=S("btn_resume") if self._pb_paused else S("btn_pause"))
        if not self._pb_paused:
            if self._playback_job:
                self.root.after_cancel(self._playback_job)
            self._playback_loop()
        else:
            if self._playback_job:
                self.root.after_cancel(self._playback_job)
                self._playback_job = None

    def _render_to_image(self, segments, image_pil, out_w, out_h):
        try:
            segments = _merge_segments([s for s in segments if isinstance(s, dict)], x_thresh=0.05, y_thresh=0.02)
            items = []
            for s in segments:
                tw = s.get("tw", "").replace("\n", " ").replace("\r", "").strip()
                if tw:
                    sx = max(0.0, min(1.0, float(s.get("x", 0.05))))
                    sy = max(0.0, min(1.0, float(s.get("y", 0.1))))
                    items.append((tw, sx, sy))
            if not items:
                return image_pil

            items.sort(key=lambda t: t[2])
            tgt_lang_str = self.tgt_lang_var.get() if hasattr(self, "tgt_lang_var") else "Traditional Chinese(正體中文)"
            font_size = _calc_font_size(len(items))
            font = _get_font_for_lang(tgt_lang_str, font_size)
            if font is None:

                font = ImageFont.load_default()

            bg_rgba = image_pil.convert("RGBA")
            black_bg = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 255))
            blended = Image.blend(black_bg, bg_rgba, alpha=0.30)
            draw = ImageDraw.Draw(blended)

            line_h = font_size + 4
            col_next_y = {}
            for tw, sx, sy in items:
                col = int(sx * 8)
                draw_x = max(PADDING, int(sx * out_w))
                col_ny = col_next_y.get(col, PADDING)
                raw_y = int(sy * out_h)
                draw_y = raw_y if raw_y >= col_ny else col_ny
                if draw_y + line_h > out_h - PADDING:
                    continue
                draw_wrapped_text_safe(draw, tw, draw_x + 1, draw_y + 1, font, out_w, out_h, (0, 0, 0))
                draw_wrapped_text_safe(draw, tw, draw_x, draw_y, font, out_w, out_h, "white")
                text_w = out_w - draw_x - PADDING
                avg_cw = font_size * 0.55
                cpl = max(1, int(text_w / avg_cw))
                nlines = max(1, -(-len(tw) // cpl))
                col_next_y[col] = draw_y + nlines * line_h + 2

            return blended.convert("RGB")
        except Exception as e:
            log(f"[render_to_image] 失敗: {e}")
            return image_pil

    def _open_platform_editor(self):
        global PLATFORMS, EMULATORS
        win = tk.Toplevel(self.root)
        win.title(S("title_plat_editor"))
        win.geometry("640x480")
        win.resizable(True, True)
        _load_app_icon(win)

        # ── 工作資料（獨立副本，儲存前不影響全域）──

        work = {
            "platform": copy.deepcopy(PLATFORMS),
            "emulator": copy.deepcopy(EMULATORS),
        }

        # ── 頂部：模式選擇 ──
        top = ttk.Frame(win, padding=6)
        top.pack(fill="x")
        mode_var = tk.StringVar(value="platform")
        ttk.Radiobutton(top, text=S("lbl_plat_cat"), variable=mode_var, value="platform").pack(side="left")
        ttk.Radiobutton(top, text=S("lbl_emu_cat"), variable=mode_var, value="emulator").pack(side="left", padx=(12, 0))

        # ── 中段：左欄（主類別）+ 右欄（平台清單）──
        mid = ttk.Frame(win, padding=(6, 0, 6, 0))
        mid.pack(fill="both", expand=True)

        # 左欄
        left = ttk.LabelFrame(mid, text=S("lf_main_cat"), padding=4)
        left.pack(side="left", fill="y", padx=(0, 4))
        cat_lb = tk.Listbox(left, width=18, selectmode="single", exportselection=False)
        cat_lb.pack(fill="both", expand=True)
        cat_btn_row = ttk.Frame(left)
        cat_btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(cat_btn_row, text=S("btn_add_short"), width=6, command=lambda: _add_cat()).pack(side="left")
        ttk.Button(cat_btn_row, text=S("btn_rename"), width=6, command=lambda: _rename_cat()).pack(side="left", padx=2)
        ttk.Button(cat_btn_row, text=S("btn_delete_short"), width=6, command=lambda: _del_cat()).pack(side="left")

        # 右欄
        right = ttk.LabelFrame(mid, text=S("lf_platform_list"), padding=4)
        right.pack(side="left", fill="both", expand=True)
        plat_lb = tk.Listbox(right, selectmode="single", exportselection=False)
        plat_lb.pack(fill="both", expand=True)
        plat_btn_row = ttk.Frame(right)
        plat_btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(plat_btn_row, text=S("btn_add_short"), width=6, command=lambda: _add_plat()).pack(side="left")
        ttk.Button(plat_btn_row, text=S("btn_rename"), width=6, command=lambda: _rename_plat()).pack(
            side="left", padx=2
        )
        ttk.Button(plat_btn_row, text=S("btn_delete_short"), width=6, command=lambda: _del_plat()).pack(side="left")
        ttk.Button(plat_btn_row, text="↑", width=3, command=lambda: _move_plat(-1)).pack(side="left", padx=(8, 0))
        ttk.Button(plat_btn_row, text="↓", width=3, command=lambda: _move_plat(1)).pack(side="left", padx=2)

        # ── 底部：儲存/關閉 ──
        bot = ttk.Frame(win, padding=6)
        bot.pack(fill="x", side="bottom")
        status_lbl = ttk.Label(bot, text="", foreground="green", font=("Arial", 9))
        status_lbl.pack(side="left")
        ttk.Button(bot, text=S("btn_close"), command=win.destroy).pack(side="right")
        ttk.Button(bot, text=S("btn_save"), command=lambda: _save()).pack(side="right", padx=(0, 6))

        # ── 輔助函式 ──
        def _data():
            return work[mode_var.get()]

        def _refresh_cats():
            cat_lb.delete(0, "end")
            for c in _data().keys():
                cat_lb.insert("end", c)
            plat_lb.delete(0, "end")

        def _cur_cat():
            sel = cat_lb.curselection()
            return cat_lb.get(sel[0]) if sel else None

        def _refresh_plats():
            plat_lb.delete(0, "end")
            cat = _cur_cat()
            if cat:
                for p in _data().get(cat, []):
                    plat_lb.insert("end", p)

        def _cur_plat_idx():
            sel = plat_lb.curselection()
            return sel[0] if sel else None

        def _ask(title, prompt, init=""):
            d = tk.Toplevel(win)
            d.title(title)
            d.geometry("300x110")
            d.grab_set()
            ttk.Label(d, text=prompt, font=("Arial", 9)).pack(padx=10, pady=(10, 4))
            var = tk.StringVar(value=init)
            e = ttk.Entry(d, textvariable=var, width=30)
            e.pack(padx=10)
            e.focus_set()
            result = [None]

            def _ok(*_):
                result[0] = var.get().strip()
                d.destroy()

            ttk.Button(d, text=S("btn_ok"), command=_ok).pack(pady=6)
            e.bind("<Return>", _ok)
            win.wait_window(d)
            return result[0]

        def _add_cat():
            name = _ask(S("dlg_add_category"), S("dlg_name_prompt"))
            if name and name not in _data():
                _data()[name] = []
                _refresh_cats()

        def _rename_cat():
            cat = _cur_cat()
            if not cat:
                return
            name = _ask(S("dlg_rename_category"), S("dlg_new_name_prompt"), init=cat)
            if name and name != cat and name not in _data():
                data = _data()
                items = list(data.items())
                idx = list(data.keys()).index(cat)
                items[idx] = (name, items[idx][1])
                work[mode_var.get()] = dict(items)
                _refresh_cats()
                cat_lb.selection_set(idx)
                _refresh_plats()

        def _del_cat():
            cat = _cur_cat()
            if not cat:
                return
            if tk.messagebox.askyesno("LangForge", S("msg_delete_cat").format(cat=cat), parent=win):
                del _data()[cat]
                _refresh_cats()

        def _add_plat():
            cat = _cur_cat()
            if not cat:
                return
            name = _ask(S("dlg_add_platform"), S("dlg_name_prompt"))
            if name and name not in _data()[cat]:
                _data()[cat].append(name)
                _refresh_plats()

        def _rename_plat():
            cat = _cur_cat()
            idx = _cur_plat_idx()
            if cat is None or idx is None:
                return
            old = _data()[cat][idx]
            name = _ask(S("dlg_rename_platform"), S("dlg_new_name_prompt"), init=old)
            if name and name != old:
                _data()[cat][idx] = name
                _refresh_plats()
                plat_lb.selection_set(idx)

        def _del_plat():
            cat = _cur_cat()
            idx = _cur_plat_idx()
            if cat is None or idx is None:
                return
            _data()[cat].pop(idx)
            _refresh_plats()

        def _move_plat(direction):
            cat = _cur_cat()
            idx = _cur_plat_idx()
            if cat is None or idx is None:
                return
            lst = _data()[cat]
            new_idx = idx + direction
            if 0 <= new_idx < len(lst):
                lst[idx], lst[new_idx] = lst[new_idx], lst[idx]
                _refresh_plats()
                plat_lb.selection_set(new_idx)

        def _save():
            global PLATFORMS, EMULATORS

            try:
                _save_platforms(copy.deepcopy(work["platform"]))
                _save_emulators(copy.deepcopy(work["emulator"]))
                PLATFORMS = work["platform"]
                EMULATORS = work["emulator"]
                # 重新整理 Tab1 平台下拉
                self._on_platform_mode_change()
                status_lbl.config(text=S("status_saved"), foreground="green")
                win.after(2000, lambda: status_lbl.config(text=""))
                log("[PlatformEditor] 儲存完成")
            except Exception as e:
                status_lbl.config(text=S("status_save_fail").format(err=e), foreground="red")
                log(f"[PlatformEditor] 儲存失敗: {e}")

        # 模式切換時刷新
        def _on_mode_change(*_):
            _refresh_cats()

        mode_var.trace_add("write", _on_mode_change)

        # 主類別點選時刷新平台
        cat_lb.bind("<<ListboxSelect>>", lambda e: _refresh_plats())

        # 初始載入
        _refresh_cats()

    def _show_about(self):

        FB_URL      = "https://www.facebook.com/groups/2150940378645437"
        KOFI_URL    = "https://ko-fi.com/toyakyo"
        PATREON_URL = "https://patreon.com/cw/LangForge"
        win = tk.Toplevel(self.root)
        win.title(S("menu_about"))
        _load_app_icon(win)
        win.resizable(False, False)
        win.grab_set()
        win.update_idletasks()
        w, h = 460, 310
        mx = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        my = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{mx}+{my}")
        ttk.Label(win, text="LangForge", font=("Arial", 14, "bold")).pack(pady=(16, 4))
        author = ABOUT_AUTHOR if ABOUT_AUTHOR else "-"
        license_ = ABOUT_LICENSE if ABOUT_LICENSE else "-"
        is_zh = self.config.get("ui_lang", "zh") == "zh"
        if is_zh:
            info = f"版本:  {ABOUT_VERSION}\n作者:  {author}\n授權:  {license_}"
        else:
            info = f"Version:  {ABOUT_VERSION}\nAuthor:   {author}\nLicense:  {license_}"
        ttk.Label(win, text=info, font=("Arial", 10), justify="left").pack(padx=20, pady=4)

        ttk.Separator(win, orient="horizontal").pack(fill="x", padx=20, pady=(6, 4))
        gh_link = tk.Label(
            win, text=f"GitHub: {ABOUT_GITHUB}", font=("Arial", 9, "underline"), fg="#333", cursor="hand2"
        )
        gh_link.pack(padx=20, anchor="w")
        gh_link.bind("<Button-1>", lambda e: webbrowser.open(ABOUT_GITHUB))
        fb_label = (
            "官方社群：LangForge 官方社群 | AI遊戲翻譯工具"
            if is_zh
            else "Community: LangForge Official | AI Game Translator"
        )
        fb_link = tk.Label(win, text=fb_label, font=("Arial", 9, "underline"), fg="#1877f2", cursor="hand2")
        fb_link.pack(padx=20, anchor="w")
        fb_link.bind("<Button-1>", lambda e: webbrowser.open(FB_URL))

        # Ko-fi 贊助連結
        kofi_label = "☕ 贊助支持 (Ko-fi): ko-fi.com/toyakyo" if is_zh else "☕ Support on Ko-fi: ko-fi.com/toyakyo"
        kofi_link = tk.Label(win, text=kofi_label, font=("Arial", 9, "underline"), fg="#29abe0", cursor="hand2")
        kofi_link.pack(padx=20, anchor="w")
        kofi_link.bind("<Button-1>", lambda e: webbrowser.open(KOFI_URL))

        # Patreon 贊助連結
        patreon_label = "🎖 贊助支持 (Patreon): patreon.com/cw/LangForge" if is_zh else "🎖 Support on Patreon: patreon.com/cw/LangForge"
        patreon_link = tk.Label(win, text=patreon_label, font=("Arial", 9, "underline"), fg="#ff424d", cursor="hand2")
        patreon_link.pack(padx=20, anchor="w")
        patreon_link.bind("<Button-1>", lambda e: webbrowser.open(PATREON_URL))

        ttk.Button(win, text=S("btn_ok"), command=win.destroy, width=10).pack(pady=(8, 0))

    # ══════════════════════════════════════════
    # Tab 1 — 遊戲平台聯動
    # ══════════════════════════════════════════

    def _active_platform_data(self):
        return EMULATORS if self.platform_mode_var.get() == "emulator" else PLATFORMS

    def _on_platform_mode_change(self):
        data = self._active_platform_data()
        cats = list(data.keys())
        self.platform_category_combo["values"] = cats
        cat = cats[0] if cats else ""
        self.platform_category_var.set(cat)
        plats = data.get(cat, [])
        self.platform_combo["values"] = plats
        self.platform_var.set(plats[0] if plats else "")
        self.config["platform_mode"] = self.platform_mode_var.get()
        self.config["platform_category"] = cat
        self.config["platform"] = self.platform_var.get()
        save_config(self.config)

    def _on_platform_category_change(self, event=None):
        data = self._active_platform_data()
        cat = self.platform_category_var.get()
        plats = data.get(cat, [])
        self.platform_combo["values"] = plats
        self.platform_var.set(plats[0] if plats else "")
        self.config["platform_category"] = cat
        self.config["platform"] = self.platform_var.get()
        save_config(self.config)

    def _on_platform_change(self, event=None):
        self.config["platform"] = self.platform_var.get()
        save_config(self.config)

    # ══════════════════════════════════════════
    # Tab 4 — 修正平台聯動
    # ══════════════════════════════════════════

    def _on_t4_fix_mode_change(self):
        data = PLATFORMS if self.t4_fix_mode_var.get() == "platform" else EMULATORS
        cats = list(data.keys())
        self.t4_fix_category_combo["values"] = cats
        self.t4_fix_category_var.set(cats[0] if cats else "")
        self._on_t4_fix_category_change()

    def _on_t4_fix_category_change(self, event=None):
        data = PLATFORMS if self.t4_fix_mode_var.get() == "platform" else EMULATORS
        cat = self.t4_fix_category_var.get()
        plats = data.get(cat, [])
        self.t4_fix_platform_combo["values"] = plats
        self.t4_fix_platform_var.set(plats[0] if plats else "")

    def _t4_apply_platform(self):

        sel = self.t4_tree.selection()
        if not sel:
            log("[Tab4] 套用平台：未選取任何紀錄")
            return
        db_id = int(sel[0])
        try:
            conn = sqlite3.connect(self.DB_PATH)
            row = conn.execute("SELECT rom_name FROM translations WHERE id=?", (db_id,)).fetchone()
            if not row:
                conn.close()
                return
            rom_name = row[0]
            new_platform = self.t4_fix_platform_var.get().strip()
            conn.execute("UPDATE translations SET platform=? WHERE rom_name=?", (new_platform, rom_name))
            conn.commit()
            affected = conn.execute("SELECT changes()").fetchone()[0]
            conn.close()
            log(f"[Tab4] 已將「{rom_name}」共 {affected} 筆紀錄的平台更新為「{new_platform}」")
            self._t4_refresh_games()
            self._t4_load_list()
        except Exception as e:
            log(f"[Tab4] 套用平台失敗: {e}")

    def _t4_refresh_games(self):
        try:
            conn = self._db_conn
            game_rows = conn.execute("SELECT DISTINCT rom_name FROM translations ORDER BY rom_name").fetchall()
            win_rows  = conn.execute("SELECT DISTINCT target_window FROM translations ORDER BY target_window").fetchall()
            plat_rows = conn.execute("SELECT DISTINCT platform FROM translations ORDER BY platform").fetchall()
            game_names = [S("all_games")] + [r[0] for r in game_rows]
            self.t4_game_combo["values"] = game_names
            if self.t4_game_var.get() not in game_names:
                self.t4_game_var.set(S("all_games"))
            win_names = [S("all_windows")] + [r[0] for r in win_rows if r[0]]
            self.t4_window_combo["values"] = win_names
            if self.t4_window_var.get() not in win_names:
                self.t4_window_var.set(S("all_windows"))
            plat_names = [S("all_platforms")] + [r[0] for r in plat_rows if r[0]]
            self.t4_platform_combo["values"] = plat_names
            if self.t4_platform_var.get() not in plat_names:
                self.t4_platform_var.set(S("all_platforms"))
        except Exception as e:
            log(f"[Tab4] 刷新遊戲清單失敗: {e}")

    def _t4_load_list(self):
        T4_PAGE_SIZE = 500
        try:
            game = self.t4_game_var.get()
            window = self.t4_window_var.get()
            platform = self.t4_platform_var.get()
            conds, params = [], []
            if game != S("all_games"):
                conds.append("rom_name=?")
                params.append(game)
            if window != S("all_windows"):
                conds.append("target_window=?")
                params.append(window)
            if platform != S("all_platforms"):
                conds.append("platform=?")
                params.append(platform)
            where = ("WHERE " + " AND ".join(conds)) if conds else ""
            rows = self._db_conn.execute(
                f"SELECT id, timestamp, model, target_window, platform, rom_name FROM translations "
                f"{where} ORDER BY id DESC LIMIT {T4_PAGE_SIZE}",
                params,
            ).fetchall()

            # 差異更新：只刪除不在新結果的舊 row，只新增不在舊 row 的新資料
            new_ids = {str(row[0]) for row in rows}
            existing_ids = set(self.t4_tree.get_children())
            for iid in existing_ids - new_ids:
                self.t4_tree.delete(iid)
            for row in reversed(rows):
                iid = str(row[0])
                if iid not in existing_ids:
                    self.t4_tree.insert(
                        "", 0, iid=iid,
                        values=(row[5] or "", row[1], row[3] or "", row[4] or "")
                    )
        except Exception as e:
            log(f"[Tab4] 載入清單失敗: {e}")

    def _t4_on_select(self, event):
        sel = self.t4_tree.selection()
        if not sel:
            return
        db_id = int(sel[0])
        self._t4_current_db_id = db_id
        self._t4_render_cache = None  # 切換紀錄時清除圖片快取
        try:
            row = self._db_conn.execute(
                "SELECT lines, screenshot_path FROM translations WHERE id=?", (db_id,)
            ).fetchone()
            if not row:
                return
            raw_lines, ss_rel = row[0], row[1]

            parsed = json.loads(raw_lines)
            segments = []
            for i, item in enumerate(parsed):
                if isinstance(item, str):
                    segments.append({"tw": item, "x": 0.05, "y": round(i * 0.09 + 0.05, 4), "w": 0.9, "h": 0.08})
                else:
                    segments.append(item)

            self._t4_current_segments = segments
            self._t4_current_img_path = os.path.join(self.LOG_DIR, ss_rel) if ss_rel else None
            self._t4_render()
        except Exception as e:
            log(f"[Tab4] 載入詳細失敗: {e}")

    def _t4_toggle_overlay(self):
        self.t4_overlay_var.set(not self.t4_overlay_var.get())
        if self.t4_overlay_var.get():
            self.t4_toggle_btn.config(text=S("btn_overlay"))
        else:
            self.t4_toggle_btn.config(text=S("btn_plain"))
        self._t4_render()

    def _t4_render(self):
        if not self._t4_current_img_path:
            return
        try:
            # 動態取得可用寬高
            self.t4_img_label.update_idletasks()
            avail_w = self.t4_img_label.winfo_width()
            if avail_w < 100:
                avail_w = self.root.winfo_width() - 32
            MAX_W = max(avail_w, 200)
            label_y = self.t4_img_label.winfo_rooty() - self.root.winfo_rooty()
            avail_h = max(self.root.winfo_height() - label_y - 10, 150)

            # ── 縮放圖片快取：相同路徑+尺寸直接複用，避免重複 open+resize ──
            cache_key = (self._t4_current_img_path, MAX_W, avail_h)
            cached = getattr(self, "_t4_render_cache", None)
            if cached and cached[0] == cache_key:
                img, out_w, out_h, orig_w, orig_h = cached[1]
            else:
                img = Image.open(self._t4_current_img_path).convert("RGB")
                orig_w, orig_h = img.width, img.height
                scale = min(MAX_W / orig_w, avail_h / orig_h, 1.0)
                out_w = int(orig_w * scale)
                out_h = int(orig_h * scale)
                img = img.resize((out_w, out_h), Image.LANCZOS)
                self._t4_render_cache = (cache_key, (img, out_w, out_h, orig_w, orig_h))

            if self.t4_overlay_var.get() and self._t4_current_segments:
                # ── 疊圖：原圖 30% + 黑底 + 白字 ──
                bg_rgba = img.convert("RGBA")
                black_bg = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 255))
                blended = Image.blend(black_bg, bg_rgba, alpha=0.30)
                out_img = blended.convert("RGB")
                draw = ImageDraw.Draw(out_img)

                tgt_lang_str = self.tgt_lang_var.get() if hasattr(self, "tgt_lang_var") else "Traditional Chinese(正體中文)"
                font = _get_font_for_lang(tgt_lang_str, 16)

                for s in self._t4_current_segments:
                    tw = s.get("tw", "").replace("\n", " ").replace("\r", "").strip()
                    if not tw:
                        continue
                    sx = float(s.get("x", 0.05))
                    sy = float(s.get("y", 0.1))
                    if sx > 1.0:
                        sx = sx / orig_w
                    if sy > 1.0:
                        sy = sy / orig_h
                    dx = max(PADDING, int(sx * out_w))
                    dy = max(PADDING, int(sy * out_h))
                    draw_wrapped_text_safe(draw, tw, dx + 1, dy + 1, font, out_w, out_h, (0, 0, 0))
                    draw_wrapped_text_safe(draw, tw, dx, dy, font, out_w, out_h, "white")
            else:
                out_img = img

            self._t4_tk_img = ImageTk.PhotoImage(out_img)
            self.t4_img_label.config(image=self._t4_tk_img, width=out_w, height=out_h)
        except Exception as e:
            log(f"[Tab4] 開啟截圖失敗: {e}")

    def _t4_delete(self):

        if self._t4_current_db_id is None:
            return
        try:
            conn = sqlite3.connect(self.DB_PATH)
            conn.execute("DELETE FROM translations WHERE id=?", (self._t4_current_db_id,))
            conn.commit()
            conn.close()
            log(f"[Tab4] 已刪除翻譯紀錄 id={self._t4_current_db_id}")
            # 清空暫存與 UI
            self._t4_current_db_id = None
            self._t4_current_segments = []
            self._t4_current_img_path = None
            self.t4_img_label.config(image="", width=1, height=1)
            self._t4_refresh_games()
            self._t4_load_list()
        except Exception as e:
            log(f"[Tab4] 刪除失敗: {e}")

    # ══════════════════════════════════════════
    # Tab 5 — 歷史攻略：內部方法
    # ══════════════════════════════════════════

    def _t5_refresh_games(self):
        try:
            rows = self._db_conn.execute("SELECT DISTINCT rom_name FROM guides ORDER BY rom_name").fetchall()
            names = [S("all_games")] + [r[0] for r in rows]
            self.t5_game_combo["values"] = names
            if self.t5_game_var.get() not in names:
                self.t5_game_var.set(S("all_games"))
        except Exception as e:
            log(f"[Tab5] 刷新遊戲清單失敗: {e}")

    def _t5_load_list(self):
        T5_PAGE_SIZE = 500
        try:
            game = self.t5_game_var.get()
            if game == S("all_games"):
                rows = self._db_conn.execute(
                    f"SELECT id, timestamp, model, progress, rom_name FROM guides ORDER BY id DESC LIMIT {T5_PAGE_SIZE}"
                ).fetchall()
            else:
                rows = self._db_conn.execute(
                    f"SELECT id, timestamp, model, progress, rom_name FROM guides WHERE rom_name=? ORDER BY id DESC LIMIT {T5_PAGE_SIZE}",
                    (game,),
                ).fetchall()

            new_ids = {str(row[0]) for row in rows}
            existing_ids = set(self.t5_tree.get_children())
            for iid in existing_ids - new_ids:
                self.t5_tree.delete(iid)
            for row in reversed(rows):
                iid = str(row[0])
                if iid not in existing_ids:
                    progress_short = (row[3] or "")[:20]
                    self.t5_tree.insert("", 0, iid=iid, values=(row[4] or "", row[1], progress_short))
        except Exception as e:
            log(f"[Tab5] 載入清單失敗: {e}")

    def _t5_on_select(self, event):
        sel = self.t5_tree.selection()
        if not sel:
            return
        db_id = int(sel[0])
        self._t5_current_db_id = db_id

        try:
            row = self._db_conn.execute(
                "SELECT progress, guide_content, screenshot_path FROM guides WHERE id=?", (db_id,)
            ).fetchone()
            if not row:
                return
            progress, guide_json, ss_rel = row[0], row[1], row[2]
            try:
                guide_list = json.loads(guide_json) if guide_json else []
            except Exception:
                guide_list = []

            # ── 縮圖快取：相同路徑直接複用 ──
            if ss_rel:
                ss_path = os.path.join(self.LOG_DIR, ss_rel)
                cached_thumb = getattr(self, "_t5_thumb_cache", None)
                if cached_thumb and cached_thumb[0] == ss_path:
                    self._t5_guide_tk_img = cached_thumb[1]
                else:
                    try:
                        img = Image.open(ss_path).convert("RGB")
                        img.thumbnail((128, 128), Image.LANCZOS)
                        self._t5_guide_tk_img = ImageTk.PhotoImage(img)
                        self._t5_thumb_cache = (ss_path, self._t5_guide_tk_img)
                    except Exception:
                        self._t5_guide_tk_img = None
                        self._t5_thumb_cache = None
                if self._t5_guide_tk_img:
                    self.t5_guide_img_label.config(image=self._t5_guide_tk_img, text="")
                else:
                    self.t5_guide_img_label.config(image="", text="(no img)")
            else:
                self._t5_guide_tk_img = None
                self.t5_guide_img_label.config(image="", text="")

            # 進度標籤
            self.t5_progress_label.config(text=progress or "")

            # 攻略建議
            CIRCLE_NUMS = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]
            self.t5_guide_text.config(state="normal")
            self.t5_guide_text.delete("1.0", "end")
            for i, item in enumerate(guide_list):
                num = CIRCLE_NUMS[i] if i < len(CIRCLE_NUMS) else f"{i + 1}."
                self.t5_guide_text.insert("end", f"{num} {item}\n\n")
            self.t5_guide_text.config(state="disabled")
        except Exception as e:
            log(f"[Tab5] 載入詳細攻略失敗: {e}")

    def _t5_delete(self):

        if self._t5_current_db_id is None:
            return
        try:
            conn = sqlite3.connect(self.DB_PATH)
            conn.execute("DELETE FROM guides WHERE id=?", (self._t5_current_db_id,))
            conn.commit()
            conn.close()
            log(f"[Tab5] 已刪除攻略紀錄 id={self._t5_current_db_id}")
            self._t5_current_db_id = None
            self._t5_thumb_cache = None
            self.t5_progress_label.config(text="")
            self._t5_guide_tk_img = None
            self.t5_guide_img_label.config(image="", text="")
            self.t5_guide_text.config(state="normal")
            self.t5_guide_text.delete("1.0", "end")
            self.t5_guide_text.config(state="disabled")
            self._t5_refresh_games()
            self._t5_load_list()
        except Exception as e:
            log(f"[Tab5] 刪除失敗: {e}")

    # ══════════════════════════════════════════
    # 畫面穩定自動翻譯
    # ══════════════════════════════════════════

    def _debounce_save_config(self):
        if self._save_config_after_id:
            self.root.after_cancel(self._save_config_after_id)
        self._save_config_after_id = self.root.after(800, self._flush_config)

    def _flush_config(self):
        self._save_config_after_id = None
        self._save_auto_trans_config()
        self._on_use_ollama_toggle()

    def _save_auto_trans_config(self):
        try:
            self.config["stable_diff"] = int(self.stable_diff_var.get())
        except (ValueError, AttributeError):
            pass
        try:
            self.config["stable_count"] = int(self.stable_count_var.get())
        except (ValueError, AttributeError):
            pass
        save_config(self.config)

    def _on_auto_trans_toggle(self):
        enabled = self.auto_trans_var.get()
        # 自動翻譯狀態不儲存到 config
        if enabled:
            self.auto_trans_status.config(text=S("status_on"), foreground="green")
            self._stable_count = 0
            self._stable_prev_img = None
            self._stable_last_hash = ""
            self._position_polling_paused = True
            self._stable_check_loop()
            # 自動翻譯開啟時停用三個手動按鈕
            for btn in ("btn_capture", "btn_guide", "btn_file"):
                if hasattr(self, btn):
                    getattr(self, btn).config(state="disabled")
        else:
            self.auto_trans_status.config(text=S("status_off"), foreground="gray")
            self._position_polling_paused = False
            if self._auto_trans_job:
                self.root.after_cancel(self._auto_trans_job)
                self._auto_trans_job = None
            # 自動翻譯關閉時恢復三個手動按鈕
            for btn in ("btn_capture", "btn_guide", "btn_file"):
                if hasattr(self, btn):
                    getattr(self, btn).config(state="normal")
        # 同步 Tab1 自動擷取按鈕
        self._sync_auto_cap_btn()
        self._update_indicators()

    def _sync_auto_cap_btn(self):
        if not hasattr(self, "auto_cap_btn"):
            return
        enabled = self.auto_trans_var.get()
        self.auto_cap_btn.config(
            text=S("btn_auto_cap_on") if enabled else S("btn_auto_cap_off"), state="normal" if enabled else "disabled"
        )

    def _on_auto_cap_btn(self):
        self.auto_trans_var.set(False)
        self._on_auto_trans_toggle()

    def _grab_window_hwnd(self, hwnd, crop_top=0):
        """給定 hwnd，回傳擷取的 PIL Image（支援多螢幕 DPI 縮放）。
        進程已設為 Per-Monitor DPI Aware，座標為實體像素，不需額外縮放。"""
        # 取得 client 區域的實體像素座標
        cr = win32gui.GetClientRect(hwnd)
        cp0 = win32gui.ClientToScreen(hwnd, (0, 0))
        px1 = cp0[0]
        py1 = cp0[1] + crop_top
        px2 = cp0[0] + cr[2]
        py2 = cp0[1] + cr[3]

        # 防呆：視窗最小化或在螢幕外時座標可能無效
        if px2 <= px1 or py2 <= py1:
            raise ValueError(f"無效的擷取範圍 ({px1},{py1})-({px2},{py2})，視窗可能已最小化或移出螢幕")

        # all_screens=True 讓 Pillow 抓整個虛擬桌面（含副螢幕）
        return ImageGrab.grab(bbox=(px1, py1, px2, py2), all_screens=True).convert("RGB")

    def _try_capture(self):
        try:
            target = self.title_var.get().lower().strip()
            if not target:
                return None

            # ── hwnd 快取：先驗證上次找到的 hwnd 是否仍有效 ──
            cached_hwnd = getattr(self, "_try_capture_hwnd", None)
            cached_target = getattr(self, "_try_capture_target", None)
            hwnd = None

            if cached_hwnd and cached_target == target:
                try:
                    if win32gui.IsWindow(cached_hwnd) and win32gui.IsWindowVisible(cached_hwnd):
                        title = win32gui.GetWindowText(cached_hwnd).lower()
                        if target in title:
                            hwnd = cached_hwnd
                except Exception:
                    pass

            if not hwnd:
                # 快取失效，重新 EnumWindows 掃描
                def _handler(h, _):
                    nonlocal hwnd
                    if target in win32gui.GetWindowText(h).lower():
                        hwnd = h
                        return False
                    return True
                win32gui.EnumWindows(_handler, None)
                self._try_capture_hwnd = hwnd
                self._try_capture_target = target

            if not hwnd:
                return None
            try:
                crop_top = int(self.crop_top_var.get())
            except ValueError:
                crop_top = 0
            if crop_top < 0:
                crop_top = 0
            return self._grab_window_hwnd(hwnd, crop_top)
        except Exception:
            self._try_capture_hwnd = None  # 出錯時清除快取
            return None

    def _clear_queue(self):
        cleared = 0
        while not _request_queue.empty():
            try:
                _request_queue.get_nowait()
                _request_queue.task_done()
                cleared += 1
            except Exception:
                break
        self._update_queue_label(0)
        if cleared > 0:
            log(f"已清空佇列，移除 {cleared} 筆待處理任務")
            self._set_status(S("status_queue_cleared").format(n=cleared), "orange")
        else:
            self._set_status(S("status_queue_empty"), "gray")

    def _enqueue_task(self, task: dict) -> bool:
        """將任務放入佇列，佇列滿時回傳 False 並顯示提示。
        在主執行緒呼叫，順帶快照所有 UI 狀態供 worker thread 安全存取。
        """
        # ── 快照 UI 狀態（主執行緒讀取，worker thread 直接用快照值）──
        task.setdefault("snap_src_lang",     self.src_lang_var.get())
        task.setdefault("snap_tgt_lang",     self.tgt_lang_var.get())
        task.setdefault("snap_engine_mode",  self.engine_mode_var.get())
        task.setdefault("snap_engine",       self.engine_var.get())
        task.setdefault("snap_model",        self.model_var.get())
        task.setdefault("snap_api_key",      self.api_entry.get().strip())
        task.setdefault("snap_ollama_model", self.ollama_model_var.get() if hasattr(self, "ollama_model_var") else "")
        task.setdefault("snap_ollama_timeout", self.ollama_timeout_var.get() if hasattr(self, "ollama_timeout_var") else str(OLLAMA_TIMEOUT))
        task.setdefault("snap_target_window", self.title_var.get().strip())
        task.setdefault("snap_platform",     self.platform_var.get().strip())
        try:
            _request_queue.put_nowait(task)
            qsize = _request_queue.qsize()
            log(f"任務已加入佇列 (目前 {qsize}/{REQUEST_QUEUE_MAXSIZE})")
            self.root.after(0, lambda q=qsize: self._update_queue_label(q))
            if qsize >= REQUEST_QUEUE_MAXSIZE:
                self._set_status(S("status_queue_full"), "orange")
            return True
        except queue.Full:
            self._set_status(S("status_queue_full"), "orange")
            log("佇列已滿，本次請求丟棄")
            return False

    def _request_worker(self):
        while True:
            task = _request_queue.get()
            if task is None:
                _request_queue.task_done()
                break
            try:
                t = task["type"]
                img   = task["image_pil"]
                src   = task.get("source", "file")
                title = task.get("win_title", "")
                # 把 snap_* 快照單獨傳入，避免與位置參數衝突
                snaps = {k: v for k, v in task.items() if k.startswith("snap_")}
                if t == "translate":
                    self._do_translate(img, src, title, **snaps)
                elif t == "guide":
                    self._do_guide(img, title, **snaps)
                elif t == "combined":
                    self._do_combined_translate(img, title, **snaps)
            except Exception as e:
                log(f"[Worker] 執行失敗: {e}")
            finally:
                _request_queue.task_done()
                self.root.after(0, lambda: self._update_queue_label(_request_queue.qsize()))

    def _trigger_auto_translate(self, image_pil):
        mode = self.engine_mode_var.get()
        # 本地/OCR 模式不需要冷卻判斷
        if mode not in ("local", "ocr"):
            model = self.model_var.get()
            if self._get_remaining_cooldown(model) > 0:
                return
            if not self._check_cooldown_and_quota():
                return
        # 佇列中已有待處理任務時跳過，避免自動翻譯堆積
        if not _request_queue.empty():
            return
        win_title = self.title_var.get().strip()
        if self.combo_guide_var.get():
            self._enqueue_task(
                {"type": "combined", "image_pil": image_pil, "win_title": win_title, "source": "capture"}
            )
        else:
            self._enqueue_task(
                {"type": "translate", "image_pil": image_pil, "win_title": win_title, "source": "capture"}
            )

    def _stable_check_loop(self):
        if not self.auto_trans_var.get():
            return

        try:
            diff_threshold = int(self.stable_diff_var.get())
            stable_count_needed = int(self.stable_count_var.get())
        except ValueError:
            diff_threshold = STABLE_DIFF_DEFAULT
            stable_count_needed = STABLE_COUNT_DEFAULT

        image_pil = self._try_capture()

        if image_pil is not None:
            import numpy as np
            gray = image_pil.convert("L")

            if self._stable_prev_img is not None:
                if gray.size == self._stable_prev_img.size:
                    diff = ImageChops.difference(gray, self._stable_prev_img)
                    avg_diff = np.mean(np.array(diff))

                    if avg_diff < diff_threshold:
                        self._stable_count += 1
                    else:
                        self._stable_count = 0

                    if self._stable_count >= stable_count_needed:
                        img_hash = hashlib.md5(image_pil.tobytes()).hexdigest()
                        if img_hash != self._stable_last_hash:
                            self._stable_last_hash = img_hash
                            self._stable_count = 0
                            self._trigger_auto_translate(image_pil)
                else:
                    self._stable_count = 0
            else:
                self._stable_count = 0

            self._stable_prev_img = gray

        # 自動翻譯模式下兼顧視窗跟隨（取代 polling）
        self._reposition_windows()
        self._auto_trans_job = self.root.after(STABLE_CHECK_INTERVAL_MS, self._stable_check_loop)

    # ══════════════════════════════════════════
    # 關閉清理
    # ══════════════════════════════════════════
    def on_close(self):
        # 場次錄製清理
        if getattr(self, "_session_running", False):
            self._stop_session()
        if getattr(self, "_playback_job", None):
            self.root.after_cancel(self._playback_job)
        # 送出結束信號讓 request worker 正常退出
        try:
            _request_queue.put_nowait(None)
        except queue.Full:
            pass
        # 關閉時儲存當前語言設定與視窗位置
        try:
            self._save_current_key_to_config()  # 確保 api_entry 當前值寫回 config
            self.config["src_lang"] = self.src_lang_var.get()
            self.config["tgt_lang"] = self.tgt_lang_var.get()
            self.config["platform_category"] = self.platform_category_var.get()
            self.config["platform"] = self.platform_var.get()
            self.config["platform_mode"] = self.platform_mode_var.get()
            self.config["engine_mode"] = self.engine_mode_var.get()
            # 儲存主視窗實際座標（供下次啟動還原位置）
            self.config["main_win_x"] = self.root.winfo_x()
            self.config["main_win_y"] = self.root.winfo_y()
            # OLLAMA 設定
            if self._ollama_available:
                self.config["use_ollama"] = self.use_ollama_var.get()
                self.config["ollama_model"] = self.ollama_model_var.get()
                try:
                    t = int(self.ollama_timeout_var.get())
                    if t > 0:
                        self.config["ollama_timeout"] = t
                except (ValueError, AttributeError):
                    pass
            save_config(self.config)
        except Exception:
            pass
        # 取消自動翻譯輪詢
        try:
            if self._auto_trans_job:
                self.root.after_cancel(self._auto_trans_job)
                self._auto_trans_job = None
        except Exception:
            pass
        # 取消視窗位置 polling
        try:
            if getattr(self, "_position_poll_job", None):
                self.root.after_cancel(self._position_poll_job)
                self._position_poll_job = None
        except Exception:
            pass
        try:
            if HAS_KEYBOARD:
                if getattr(self, "_hotkey_handle", None) is not None:
                    keyboard.remove_hotkey(self._hotkey_handle)
                    self._hotkey_handle = None
                if getattr(self, "_guide_hotkey_handle", None) is not None:
                    keyboard.remove_hotkey(self._guide_hotkey_handle)
                    self._guide_hotkey_handle = None
        except Exception as e:
            log(f"關閉時清理 hotkey 失敗: {e}")
        finally:
            try:
                if hasattr(self, "display") and self.display.winfo_exists():
                    self.display.destroy()
            except:
                pass
            try:
                if hasattr(self, "guide_display") and self.guide_display.winfo_exists():
                    self.guide_display.destroy()
            except:
                pass
            try:
                if hasattr(self, "_db_conn") and self._db_conn:
                    self._db_conn.close()
            except Exception:
                pass
            self.root.destroy()

    # ══════════════════════════════════════════
    # 狀態列更新
    # ══════════════════════════════════════════
    def _safe_save_config(self):
        if threading.current_thread() is threading.main_thread():
            save_config(self.config)
        else:
            self.root.after(0, lambda: save_config(self.config))

    def _set_status(self, text, color="blue"):
        # 簡化：移除訊息中的模型名稱前綴（格式：「引擎 (模型) 訊息」→「訊息」）

        simplified = re.sub(r"^[A-Za-z]+\s*\([^)]+\)\s*", "", text).strip()
        if not simplified:
            simplified = text

        # 語意色 → 主題對應色
        t = THEMES.get(CURRENT_THEME, THEMES["light"])
        _color_map = {
            "blue":       t["status_info"],
            "green":      t["status_ok"],
            "orange":     t["status_warn"],
            "red":        t["status_err"],
            "gray":       t["status_idle"],
            "steelblue":  t["status_info"],
            "brown":      t["status_warn"],
        }
        resolved = _color_map.get(color, color)

        def _update():
            if hasattr(self, "status") and self.status.winfo_exists():
                self.status.config(text=simplified, foreground=resolved)

        self.root.after(0, _update)

    def _start_elapsed_timer(self):
        if getattr(self, "_elapsed_timer_id", None):
            self.root.after_cancel(self._elapsed_timer_id)
            self._elapsed_timer_id = None
        # 本地模式時清空冷卻欄
        if getattr(self, "engine_mode_var", None) and self.engine_mode_var.get() in ("local", "ocr"):
            if hasattr(self, "cooldown_label") and self.cooldown_label.winfo_exists():
                self.cooldown_label.config(text="")
        self._trans_start_time = time.time()
        self._elapsed_tick()

    def _elapsed_tick(self):
        if not getattr(self, "_trans_start_time", None):
            return
        if not (hasattr(self, "elapsed_label") and self.elapsed_label.winfo_exists()):
            return
        secs = int(time.time() - self._trans_start_time)
        self.elapsed_label.config(text=f"{secs}s", foreground="steelblue")
        self._elapsed_timer_id = self.root.after(1000, self._elapsed_tick)

    def _stamp_elapsed(self):
        if not getattr(self, "_trans_start_time", None):
            return
        if getattr(self, "_elapsed_timer_id", None):
            self.root.after_cancel(self._elapsed_timer_id)
            self._elapsed_timer_id = None
        secs = int(time.time() - self._trans_start_time)
        self._trans_start_time = None

        def _freeze(s=secs):
            if hasattr(self, "elapsed_label") and self.elapsed_label.winfo_exists():
                self.elapsed_label.config(text=f"{s}s", foreground="steelblue")

        self.root.after(0, _freeze)

    # ══════════════════════════════════════════
    # 引擎 / 模型 UI
    # ══════════════════════════════════════════
    def _init_engine_ui(self):
        # 若 config 有記錄預設引擎，啟動時套用
        def_eng = self.config.get("default_engine", "")
        def_model = self.config.get("default_model", "")
        if def_eng and def_eng in ENGINE_ORDER:
            self.engine_var.set(def_eng)
        eng = self.engine_var.get()
        self.key_label.config(text=f"{ENGINE_DISPLAY[eng]} API Key:")
        self.api_entry.delete(0, tk.END)
        self.api_entry.insert(0, self.config.get(eng, ""))
        all_models = self._get_engine_models(eng)
        self.model_combo["values"] = all_models
        # 套用預設模型（若屬於該引擎）
        if def_model and def_model in all_models:
            self.model_var.set(def_model)
        else:
            self.model_var.set(ENGINE_DEFAULT_MODEL.get(eng, all_models[0] if all_models else ""))
        self._refresh_quota()
        self._update_cooldown_display()

    def _on_engine_combo_change(self):
        display = self._engine_display_var.get()
        eng = next((k for k, v in ENGINE_DISPLAY.items() if v == display), display)
        self.engine_var.set(eng)
        self._on_engine_change()

    def _on_engine_change(self):
        self._save_current_key_to_config()
        eng = self.engine_var.get()
        self.key_label.config(text=f"{ENGINE_DISPLAY[eng]} API Key:")
        self.api_entry.delete(0, tk.END)
        self.api_entry.insert(0, self.config.get(eng, ""))
        self.model_combo["values"] = self._get_engine_models(eng)
        self.model_var.set(ENGINE_DEFAULT_MODEL[eng])
        self._refresh_quota()

    def _set_default_engine(self):
        eng = self.engine_var.get()
        model = self.model_var.get()
        self.config["default_engine"] = eng
        self.config["default_model"] = model
        save_config(self.config)
        log(f"已設定預設引擎: {eng} / {model}")
        self._set_status(S("status_default_ok").format(engine=ENGINE_DISPLAY[eng], model=model), "green")

    def _save_current_key_to_config(self):
        for eng in ENGINE_ORDER:
            if self.key_label.cget("text") == f"{ENGINE_DISPLAY[eng]} API Key:":
                new_key = self.api_entry.get()
                old_key = self.config.get(eng, "")
                if new_key != old_key:
                    _invalidate_client(eng, old_key)
                self.config[eng] = new_key
                break

    def _refresh_model_list(self):
        eng = self.engine_var.get()
        api_key = self.api_entry.get().strip()

        if api_key and eng != "grok":
            self._set_status(S("status_fetching_models").format(engine=ENGINE_DISPLAY.get(eng, eng)), "orange")
            self.root.update_idletasks()

            def _do_fetch():
                fetched = _fetch_models_from_api(eng, api_key)
                self.root.after(0, lambda f=fetched: _apply_fetched(f))

            def _apply_fetched(fetched):
                if fetched:
                    custom = self.config.get("custom_models", {}).get(eng, [])
                    all_models = fetched + [m for m in custom if m not in fetched]
                    cached = self.config.setdefault("cached_models", {})
                    cached[eng] = fetched
                    # 方案2：不在 MODEL_DAILY_LIMITS 且非學習到 limit=0 的新模型標記為 -1（未知）
                    learned_zero = self.config.get("learned_zero_quota", [])
                    custom_quota = self.config.get("custom_quota", {})
                    unknown = []
                    for m in fetched:
                        if m in custom_quota:
                            MODEL_DAILY_LIMITS[m] = custom_quota[m]
                        elif m not in MODEL_DAILY_LIMITS and m not in learned_zero:
                            MODEL_DAILY_LIMITS[m] = -1
                            unknown.append(m)
                    if unknown:
                        log(f"[quota] 新模型配額未知（標記為 ?）: {unknown}")
                    save_config(self.config)
                else:
                    built_in = list(ENGINE_MODELS.get(eng, []))
                    custom = self.config.get("custom_models", {}).get(eng, [])
                    all_models = built_in + [m for m in custom if m not in built_in]
                    self._set_status(S("status_fetch_models_failed").format(engine=ENGINE_DISPLAY.get(eng, eng)), "red")
                self.model_combo["values"] = all_models
                current = self.model_var.get()
                if current not in all_models:
                    self.model_var.set(all_models[0] if all_models else "")
                self._refresh_quota()
                self._refresh_quota_table()
                if fetched:
                    self._set_status(S("status_model_list_updated").format(engine=ENGINE_DISPLAY.get(eng, eng), n=len(all_models)), "green")

            threading.Thread(target=_do_fetch, daemon=True).start()

        else:
            cached = self.config.get("cached_models", {}).get(eng, [])
            built_in = list(ENGINE_MODELS.get(eng, []))
            base = cached if cached else built_in
            custom = self.config.get("custom_models", {}).get(eng, [])
            all_models = base + [m for m in custom if m not in base]
            self.model_combo["values"] = all_models
            current = self.model_var.get()
            if current not in all_models:
                self.model_var.set(ENGINE_DEFAULT_MODEL.get(eng, all_models[0] if all_models else ""))
            self._refresh_quota()
            self._refresh_quota_table()
            self._set_status(S("status_model_list_updated").format(engine=ENGINE_DISPLAY.get(eng, eng), n=len(all_models)), "green")

    def _add_custom_model(self):
        model_name = self.custom_model_var.get().strip()
        if not model_name:
            return
        eng = self.engine_var.get()
        custom_key = f"custom_models_{eng}"
        custom_list = self.config.get(custom_key, [])
        if model_name in custom_list or model_name in ENGINE_MODELS[eng]:
            log(f"模型已存在: {model_name}")
            self._set_status(S("status_model_exists").format(model=model_name), "orange")
            return
        custom_list.append(model_name)
        self.config[custom_key] = custom_list
        save_config(self.config)
        # 更新下拉選單
        self.model_combo["values"] = self._get_engine_models(eng)
        self.model_var.set(model_name)
        self.custom_model_var.set("")
        self._refresh_quota()
        log(f"已新增自訂模型: {eng} / {model_name}")
        self._set_status(S("status_model_added").format(model=model_name), "green")

    def _remove_custom_model(self):
        model_name = self.model_var.get()
        eng = self.engine_var.get()
        custom_key = f"custom_models_{eng}"
        custom_list = self.config.get(custom_key, [])
        if model_name in custom_list:
            custom_list.remove(model_name)
            self.config[custom_key] = custom_list
            save_config(self.config)
            all_models = self._get_engine_models(eng)
            self.model_combo["values"] = all_models
            self.model_var.set(all_models[0] if all_models else "")
            self._refresh_quota()
            log(f"已移除自訂模型: {eng} / {model_name}")
            self._set_status(S("status_model_removed").format(model=model_name), "green")
        elif model_name in ENGINE_MODELS[eng]:
            log(f"內建模型無法移除: {model_name}")
            self._set_status(S("status_builtin_no_remove"), "orange")
        else:
            self._set_status(S("status_no_model_remove"), "orange")

    def _get_engine_models(self, eng):
        cached = self.config.get("cached_models", {}).get(eng, [])
        built_in = list(ENGINE_MODELS.get(eng, []))
        base = cached if cached else built_in
        custom = list(self.config.get(f"custom_models_{eng}", []))
        return base + [m for m in custom if m not in base]

    def _refresh_quota(self):
        global CURRENT_LANG
        CURRENT_LANG = self.config.get("ui_lang", "zh")
        eng = self.engine_var.get()
        model = self.model_var.get()
        used_today = self.config.get("used_today", {})

        used = used_today.get(model, 0)
        limit = MODEL_DAILY_LIMITS.get(model, -1)
        rpm = MODEL_RPM.get(model, 0)

        if limit == 0:
            self.quota_label.config(text=f"▶ {model}:  {S('quota_no_free')}", foreground="red")
        elif limit == -1:
            self.quota_label.config(text=f"▶ {model}:  {used}/? RPD  (配額未知)", foreground="#cc7700")
        else:
            rpm_str = f"RPM={rpm}" if rpm > 0 else ""
            color = "brown" if used < limit else "red"
            self.quota_label.config(text=f"▶ {model}:  {used}/{limit} RPD  {rpm_str}", foreground=color)

    # ══════════════════════════════════════════
    # 視窗跟隨
    # ══════════════════════════════════════════
    # ══════════════════════════════════════════
    # 全域快捷鍵
    # ══════════════════════════════════════════
    def _toggle_hotkey(self):
        if not HAS_KEYBOARD:
            self._set_status(S("status_keyboard_need"), "red")
            return
        if self.hotkey_active:
            self._unregister_hotkey()
        else:
            self._register_hotkey()

    def _register_hotkey(self):
        key_str = self.hotkey_var.get().strip()
        if not key_str:
            return
        try:
            self._hotkey_handle = keyboard.add_hotkey(key_str, self._hotkey_triggered)
            self.hotkey_active = True
            self.hotkey_btn.config(text=S("btn_disable"))
            self.hotkey_status.config(text=S("status_hotkey_on").format(key=key_str), foreground="green")
            self.config["hotkey"] = key_str
            save_config(self.config)
            log(f"快捷鍵已註冊: {key_str}")
            self._update_indicators()
        except Exception as e:
            log(f"快捷鍵註冊失敗: {e}")
            self._set_status(S("status_hotkey_set_fail").format(e=e), "red")

    def _unregister_hotkey(self):
        try:
            # 使用 add_hotkey() 回傳的 handle 精確移除，不影響攻略快捷鍵
            handle = getattr(self, "_hotkey_handle", None)
            if handle is not None:
                keyboard.remove_hotkey(handle)
                self._hotkey_handle = None
            self.hotkey_active = False
            self.hotkey_btn.config(text=S("btn_enable"))
            self.hotkey_status.config(text=S("lbl_hotkey_off"), foreground="gray")
            log("快捷鍵已停用")
            self._update_indicators()
        except Exception as e:
            log(f"快捷鍵停用失敗: {e}")

    def _hotkey_triggered(self):
        self.root.after(0, self.start_worker)

    # ══════════════════════════════════════════
    # 攻略快捷鍵
    # ══════════════════════════════════════════
    def _toggle_guide_hotkey(self):
        if not HAS_KEYBOARD:
            self._set_status(S("status_keyboard_need"), "red")
            return
        if self.guide_hotkey_active:
            self._unregister_guide_hotkey()
        else:
            self._register_guide_hotkey()

    def _register_guide_hotkey(self):
        key_str = self.guide_hotkey_var.get().strip()
        if not key_str:
            return
        try:
            self._guide_hotkey_handle = keyboard.add_hotkey(key_str, self._guide_hotkey_triggered)
            self.guide_hotkey_active = True
            self.guide_hotkey_btn.config(text=S("btn_disable"))
            self.guide_hotkey_status.config(text=S("status_hotkey_on").format(key=key_str), foreground="green")
            self.config["guide_hotkey"] = key_str
            save_config(self.config)
            log(f"攻略快捷鍵已註冊: {key_str}")
            self._update_indicators()
        except Exception as e:
            log(f"攻略快捷鍵註冊失敗: {e}")
            self._set_status(S("status_guide_hotkey_fail2").format(e=e), "red")

    def _unregister_guide_hotkey(self):
        try:
            # 使用 add_hotkey() 回傳的 handle 精確移除，不影響翻譯快捷鍵
            handle = getattr(self, "_guide_hotkey_handle", None)
            if handle is not None:
                keyboard.remove_hotkey(handle)
                self._guide_hotkey_handle = None
            self.guide_hotkey_active = False
            self.guide_hotkey_btn.config(text=S("btn_enable"))
            self.guide_hotkey_status.config(text=S("lbl_hotkey_off"), foreground="gray")
            log("攻略快捷鍵已停用")
            self._update_indicators()
        except Exception as e:
            log(f"攻略快捷鍵停用失敗: {e}")

    def _guide_hotkey_triggered(self):
        self.root.after(0, self.start_guide_worker)

    def _find_mesen_window(self, force: bool = False):
        """找到目標視窗，回傳 (left, top, right, bottom) 或 None。
        結果快取 500ms，避免 polling 每次都執行 EnumWindows。
        force=True 強制略過快取（如切換目標視窗時）。
        """
        target = self.title_var.get().lower()
        now = time.time()
        # 快取命中：title 相同且未過期
        if not force and self._mesen_cache_title == target and now - self._mesen_cache_ts < 0.5:
            return self._mesen_cache_rect
        # 快取失效：重新 EnumWindows
        result = [None]

        def _handler(h, _):
            if target in win32gui.GetWindowText(h).lower():
                result[0] = win32gui.GetWindowRect(h)
                return False
            return True

        try:
            win32gui.EnumWindows(_handler, None)
        except Exception:
            pass
        # 更新快取
        self._mesen_cache_rect = result[0]
        self._mesen_cache_title = target
        self._mesen_cache_ts = now
        return result[0]

    def _on_display_close(self):
        self.display.withdraw()

    def _on_guide_display_close(self):
        self.guide_display.withdraw()

    def _ensure_display(self):
        if not hasattr(self, "display") or not self.display.winfo_exists():
            # 視窗已被 destroy（on_close 流程），不重建
            return
        self.display.deiconify()
        self.display.lift()

    def _ensure_guide_display(self):
        if not hasattr(self, "guide_display") or not self.guide_display.winfo_exists():
            return
        self.guide_display.deiconify()

    def _on_main_move(self, event=None):
        if self._reposition_after_id:
            self.root.after_cancel(self._reposition_after_id)
        self._reposition_after_id = self.root.after(100, self._reposition_debounced)

    def _reposition_debounced(self):
        self._reposition_after_id = None
        self._reposition_windows()

    def _set_display_geom(self, geom: str):
        if geom != self._last_disp_geom:
            self.display.geometry(geom)
            self._last_disp_geom = geom

    def _set_guide_geom(self, geom: str):
        if geom != self._last_guide_geom:
            self.guide_display.geometry(geom)
            self._last_guide_geom = geom

    def _reposition_windows(self):
        try:
            if not self.display.winfo_exists():
                return
            mode = self.winmode_var.get() if hasattr(self, "winmode_var") else "mesen"
            dw = self.display.winfo_width()
            dh = self.display.winfo_height()
            has_guide = hasattr(self, "guide_display") and self.guide_display.winfo_exists()

            if mode == "main":
                mx = self.root.winfo_x()
                my = self.root.winfo_y()
                mw = self.root.winfo_width()
                dx, dy = mx + mw + 10, my

            elif mode == "corner":
                # 取得主視窗目前所在螢幕的邊界
                mx = self.root.winfo_x()
                my = self.root.winfo_y()
                mon = next(
                    (m for m in self._monitors if m["x"] <= mx < m["x"] + m["w"] and m["y"] <= my < m["y"] + m["h"]),
                    self._monitors[0],
                )
                sw, sh, sx, sy = mon["w"], mon["h"], mon["x"], mon["y"]
                # 翻譯視窗右上角
                self._set_display_geom(f"+{sx + sw - dw - 10}+{sy}")
                # 攻略視窗右下角
                if has_guide:
                    gh = self.guide_display.winfo_height()
                    gw = self.guide_display.winfo_width()
                    self._set_guide_geom(f"+{sx + sw - gw - 10}+{sy + sh - gh - 50}")
                return

            elif mode == "sides":
                # 依附目標視窗兩側：攻略在左、翻譯在右
                mesen_rect = self._find_mesen_window()
                if mesen_rect:
                    # mesen_rect = (left, top, right, bottom)
                    target_left = mesen_rect[0]
                    target_right = mesen_rect[2]
                    target_top = mesen_rect[1]
                    gw = self.guide_display.winfo_width() if has_guide else 0
                    # 翻譯視窗：目標視窗右邊
                    dx, dy = target_right + 10, target_top
                    # 攻略視窗：目標視窗左邊（貼齊左側，往左推出攻略視窗寬度）
                    if has_guide:
                        guide_x = target_left - gw - 10
                        self._set_guide_geom(f"+{guide_x}+{target_top}")
                else:
                    # 找不到目標視窗，fallback 與 mesen 模式相同
                    mx = self.root.winfo_x()
                    my = self.root.winfo_y()
                    mw = self.root.winfo_width()
                    dx, dy = mx + mw + 10, my

            else:  # 'mesen'
                mesen_rect = self._find_mesen_window()
                if mesen_rect:
                    dx, dy = mesen_rect[2] + 10, mesen_rect[1]
                else:
                    mx = self.root.winfo_x()
                    my = self.root.winfo_y()
                    mw = self.root.winfo_width()
                    dx, dy = mx + mw + 10, my

            # main / mesen / sides 模式：設定翻譯視窗位置
            self._set_display_geom(f"+{dx}+{dy}")
            # sides 模式且找到目標視窗時，攻略視窗已在上方個別定位，不再覆蓋
            if has_guide and mode != "sides":
                self._set_guide_geom(f"+{dx + dw + 10}+{dy}")
            elif has_guide and mode == "sides":
                # sides fallback（找不到目標視窗）：攻略跟在翻譯右側
                self._set_guide_geom(f"+{dx + dw + 10}+{dy}")

        except:
            pass

    def _on_screen_change(self, event=None):
        label = self.screen_var.get()
        mon = next((m for m in self._monitors if m["label"] == label), None)
        if mon is None:
            return
        self.config["main_screen"] = mon["index"]
        save_config(self.config)
        self.root.geometry(f'+{mon["x"] + 10}+{mon["y"] + 10}')
        self.root.after(100, self._reposition_windows)

    def _on_winmode_change(self):
        self.config["winmode"] = self.winmode_var.get()
        save_config(self.config)
        self._reposition_windows()
        log(f"視窗模式: {self.winmode_var.get()}")

    def _on_combo_guide_toggle(self):
        self.config["combo_guide"] = self.combo_guide_var.get()
        save_config(self.config)
        self._update_combo_guide_status()
        state = S("lbl_guide_toggle_on") if self.combo_guide_var.get() else S("lbl_guide_toggle_off")
        log(f"截取翻譯同時攻略: {state}")

    def _update_combo_guide_status(self):
        if self.combo_guide_var.get():
            self.combo_guide_status.config(text=S("lbl_combo_on"), foreground="green")
        else:
            self.combo_guide_status.config(text=S("lbl_combo_off"), foreground="gray")
        self._update_indicators()

    def _on_overlay_font_size_change(self, *args):
        val = self.overlay_font_size_var.get()
        self._fs_value_label.config(text=f"{val} px")
        self.config["overlay_font_size"] = val
        save_config(self.config)

    def _on_auto_switch_skip_change(self):
        self.config["auto_switch_skip_no_key"] = self.auto_switch_skip_no_key_var.get()
        save_config(self.config)

    # ══════════════════════════════════════════
    # 自訂雲端引擎管理
    # ══════════════════════════════════════════
    def _refresh_ollama_models(self):
        new_models = _detect_ollama_vision_models()
        self._ollama_models = new_models
        self._ollama_available = len(new_models) > 0
        if not self._ollama_available:
            self._set_status("未偵測到 OLLAMA 模型" if CURRENT_LANG != "en" else "No OLLAMA models detected", "orange")
            return
        filtered = _filter_vision_models(new_models) if self.vision_filter_var.get() else new_models
        if self.ollama_combo:
            self.ollama_combo["values"] = filtered
            if self.ollama_model_var.get() not in filtered:
                self.ollama_model_var.set(filtered[0] if filtered else "")
        count = len(new_models)
        self._set_status(
            f"{'偵測到' if CURRENT_LANG != 'en' else 'Detected'} {count} {'個 OLLAMA 模型' if CURRENT_LANG != 'en' else 'OLLAMA model(s)'}",
            "green"
        )
        log(f"[OLLAMA] 重新偵測完成，找到 {count} 個模型")

    def _on_use_ollama_toggle(self, event=None):
        self.config["use_ollama"] = self.use_ollama_var.get()
        self.config["ollama_model"] = self.ollama_model_var.get()
        try:
            t = int(self.ollama_timeout_var.get())
            if t > 0:
                self.config["ollama_timeout"] = t
        except (ValueError, AttributeError):
            pass
        save_config(self.config)

    def _on_vision_filter_toggle(self):
        if not self._ollama_available or self.ollama_combo is None:
            return
        filtered = self.vision_filter_var.get()
        self.config["ollama_vision_filter"] = filtered
        new_list = _filter_vision_models(self._ollama_models) if filtered else self._ollama_models
        self.ollama_combo["values"] = new_list
        # 若目前選取的模型不在新清單中，自動切到第一個
        if self.ollama_model_var.get() not in new_list:
            self.ollama_model_var.set(new_list[0])
        log(f"[OLLAMA] 視覺過濾: {filtered}，清單剩 {len(new_list)} 個模型")
        save_config(self.config)

    def _update_queue_label(self, qsize: int = 0):
        if not hasattr(self, "queue_label") or not self.queue_label.winfo_exists():
            return
        if qsize <= 0:
            self.queue_label.config(text="", foreground="gray")
        elif qsize >= REQUEST_QUEUE_MAXSIZE:
            self.queue_label.config(text=f'{S("lbl_queue")} {qsize}/{REQUEST_QUEUE_MAXSIZE} ⚠', foreground="red")
        else:
            self.queue_label.config(text=f'{S("lbl_queue")} {qsize}/{REQUEST_QUEUE_MAXSIZE}', foreground="steelblue")

    def _on_engine_mode_change(self):
        mode = self.engine_mode_var.get()
        self.config["engine_mode"] = mode
        self.use_ollama_var.set(mode == "local")
        self.config["use_ollama"] = mode == "local"
        save_config(self.config)
        self._apply_engine_mode(animate=True)

    def _apply_engine_mode(self, animate: bool = True):
        mode = self.engine_mode_var.get()
        ocr_frame = getattr(self, "ocr_frame", None)

        self.cloud_frame.pack_forget()
        self.local_frame.pack_forget()
        if ocr_frame:
            ocr_frame.pack_forget()

        if mode == "cloud":
            self.cloud_frame.pack(fill="x")
        elif mode == "local":
            self.local_frame.pack(fill="x")
        else:
            if ocr_frame:
                ocr_frame.pack(fill="x")

    def _update_indicators(self):
        if not hasattr(self, "_ind_auto"):
            return
        _ON = "#111111"
        _OFF = "#aaaaaa"
        # 自動擷取
        auto_on = getattr(self, "auto_trans_var", None)
        auto_on = auto_on.get() if auto_on else False
        self._ind_auto.config(fg=_ON if auto_on else _OFF)
        # 翻譯同時攻略
        combo_on = getattr(self, "combo_guide_var", None)
        combo_on = combo_on.get() if combo_on else False
        self._ind_combo.config(fg=_ON if combo_on else _OFF)
        # 擷取快捷鍵
        hk_on = getattr(self, "hotkey_active", False)
        self._ind_hotkey.config(fg=_ON if hk_on else _OFF)
        # 攻略快捷鍵
        ghk_on = getattr(self, "guide_hotkey_active", False)
        self._ind_guide_hotkey.config(fg=_ON if ghk_on else _OFF)

    def _start_pick_window(self):
        if getattr(self, "_pick_countdown_id", None):
            self.root.after_cancel(self._pick_countdown_id)
        self.pick_window_btn.config(state="disabled")
        self.pick_cancel_btn.config(state="normal")
        self._pick_window_tick(5)

    def _cancel_pick_window(self):
        if getattr(self, "_pick_countdown_id", None):
            self.root.after_cancel(self._pick_countdown_id)
            self._pick_countdown_id = None
        self.pick_window_btn.config(state="normal")
        self.pick_cancel_btn.config(state="disabled")
        self.pick_hint_label.config(text="", foreground="orange")
        log("[PickWindow] 已取消")

    def _pick_window_tick(self, remaining: int):
        if remaining > 0:
            self.pick_hint_label.config(text=S("lbl_pick_hint") + f" ({remaining})", foreground="orange")
            self._pick_countdown_id = self.root.after(1000, self._pick_window_tick, remaining - 1)
        else:
            # 時間到，抓前景視窗
            try:
                hwnd = win32gui.GetForegroundWindow()
                title = win32gui.GetWindowText(hwnd).strip()
            except Exception:
                title = ""

            if title and title != self.root.title():
                # 自動加入清單並選取
                targets = list(self.config.get("target_windows", []))
                if title not in targets:
                    targets.append(title)
                    self.config["target_windows"] = targets
                    save_config(self.config)
                self.target_combo["values"] = targets
                self.title_var.set(title)
                self.target_combo.config(foreground="")
                self.pick_hint_label.config(text=f"✓ {title}", foreground="green")
                log(f"[PickWindow] 已選取: {title}")
            else:
                self.pick_hint_label.config(text=S("status_no_win_detect"), foreground="red")

            self.pick_window_btn.config(state="normal")
            self.pick_cancel_btn.config(state="disabled")
            self._pick_countdown_id = None

    def _add_target_window(self):
        self._mesen_cache_ts = 0.0  # 清快取，強制下次重新偵測
        self._try_capture_hwnd = None  # 清除 hwnd 快取
        name = self.title_var.get().strip()
        # 忽略提示文字
        if not name or name == S("hint_no_target"):
            return
        targets = list(self.config.get("target_windows", []))
        if name in targets:
            self._set_status(S("status_win_exists").format(name=name), "orange")
            return
        targets.append(name)
        self.config["target_windows"] = targets
        save_config(self.config)
        self.target_combo["values"] = targets
        self.target_combo.config(foreground="")
        log(f"已新增目標視窗: {name}")
        self._set_status(S("status_win_added").format(name=name), "green")

    def _remove_target_window(self):
        self._mesen_cache_ts = 0.0  # 清快取
        self._try_capture_hwnd = None  # 清除 hwnd 快取
        name = self.title_var.get().strip()
        targets = list(self.config.get("target_windows", []))
        if name not in targets:
            self._set_status(S("status_win_notfound").format(name=name), "orange")
            return
        targets.remove(name)
        self.config["target_windows"] = targets
        save_config(self.config)
        self.target_combo["values"] = targets
        if targets:
            self.title_var.set(targets[0])
            self.target_combo.config(foreground="")
        else:
            self.target_combo.set(S("hint_no_target"))
            self.target_combo.config(foreground="gray")
        log(f"已移除目標視窗: {name}")
        self._set_status(S("status_win_removed").format(name=name), "green")

    def _start_position_polling(self):
        """每 500ms 偵測 Mesen 視窗位置，自動跟隨移動。
        自動翻譯開啟時暫停（由 _stable_check_loop 代勞 reposition）。
        """
        if not self._position_polling_paused:
            self._reposition_windows()
        self._position_poll_job = self.root.after(500, self._start_position_polling)

    # ══════════════════════════════════════════

    # ══════════════════════════════════════════
    # 選擇圖片檔案翻譯
    # ══════════════════════════════════════════
    def pick_image_file(self):
        if self._capture_in_progress:
            return
        filepath = filedialog.askopenfilename(
            title=S("dlg_file_title"),
            filetypes=[
                (S("dlg_file_types_img"), "*.png *.jpg *.jpeg *.bmp *.gif *.webp"),
                (S("dlg_file_types_all"), "*.*"),
            ],
        )
        if not filepath:
            return
        if self.engine_mode_var.get() not in ("local", "ocr") and not self._check_cooldown_and_quota():
            return
        self._capture_in_progress = True
        self._start_elapsed_timer()
        self._set_status(S("status_img_loading"), "orange")
        threading.Thread(target=self._file_translate_task, args=(filepath,), daemon=True).start()

    def _file_translate_task(self, filepath):
        try:
            img = Image.open(filepath).convert("RGB")
        except Exception as e:
            log(f"圖片讀取失敗: {e}")
            self._set_status(S("status_img_load_fail"), "red")
            self._capture_in_progress = False
            return
        self._enqueue_task({"type": "translate", "image_pil": img, "win_title": "", "source": "file"})
        self._capture_in_progress = False

    # ══════════════════════════════════════════
    # 視窗擷取翻譯
    # ══════════════════════════════════════════
    def start_worker(self):
        if self._capture_in_progress:
            return
        if self.engine_mode_var.get() not in ("local", "ocr") and not self._check_cooldown_and_quota():
            return
        self._capture_in_progress = True
        self._start_elapsed_timer()
        self._set_status(S("status_capturing"), "orange")
        threading.Thread(target=self._window_capture_task, daemon=True).start()

    def _window_capture_task(self):
        try:
            target = self.title_var.get().lower().strip()
            if not target:
                self._set_status(S("status_no_target_win"), "red")
                self._stamp_elapsed()
                return
            hwnd = None

            def _handler(h, _):
                nonlocal hwnd
                if target in win32gui.GetWindowText(h).lower():
                    hwnd = h
                    return False
                return True

            win32gui.EnumWindows(_handler, None)
            if not hwnd:
                self._set_status(S("status_win_missing"), "red")
                return

            try:
                crop_top = int(self.crop_top_var.get())
            except ValueError:
                crop_top = 0
            if crop_top < 0:
                crop_top = 0

            # 儲存設定
            if self.config.get("crop_top") != crop_top:
                self.config["crop_top"] = crop_top
                save_config(self.config)

            img = self._grab_window_hwnd(hwnd, crop_top)
            win_title = win32gui.GetWindowText(hwnd)
            if self.combo_guide_var.get():
                self._enqueue_task({"type": "combined", "image_pil": img, "win_title": win_title, "source": "capture"})
            else:
                self._enqueue_task({"type": "translate", "image_pil": img, "win_title": win_title, "source": "capture"})
        finally:
            self._capture_in_progress = False

    # ══════════════════════════════════════════
    # 共用翻譯流程
    # ══════════════════════════════════════════
    def _get_cooldown(self, model=None):
        if model is None:
            model = self.model_var.get()
        rpm = MODEL_RPM.get(model, 0)
        if rpm > 0:
            return max(int(60 / rpm) + 1, 3)
        return COOLDOWN_SECONDS_DEFAULT

    def _get_remaining_cooldown(self, model=None):
        if model is None:
            model = self.model_var.get()
        last_time = LAST_REQUEST_TIME.get(model, 0)
        cooldown = self._get_cooldown(model)
        elapsed = time.time() - last_time
        remaining = cooldown - elapsed
        return max(0, remaining)

    def _check_cooldown_and_quota(self):
        model = self.model_var.get()
        used = self.config["used_today"].get(model, 0)
        limit = MODEL_DAILY_LIMITS.get(model, -1)

        remaining = self._get_remaining_cooldown(model)
        if remaining > 0:
            wait = int(remaining) + 1
            log(f"{model} 冷卻中，請等 {wait} 秒...")
            self._set_status(S("status_cooling").format(model=model, wait=wait), "orange")
            return False

        # RPD 用完 → 自動切換下一個可用模型/引擎
        # limit=-1 表示配額未知，讓實際 API 呼叫決定（不預先跳過）
        if limit != -1 and (limit <= 0 or used >= limit):
            log(f"{model} 已無額度 ({used}/{limit})，嘗試自動切換...")
            if self._auto_switch_model():
                # 切換成功，重新檢查新模型的冷卻
                return self._check_cooldown_and_quota()
            else:
                self._set_status(S("status_quota_exhausted_hint"), "red")
                return False

        LAST_REQUEST_TIME[model] = time.time()  # 記錄本次請求時間（用於冷卻計算）
        self._start_cooldown_timer()
        return True

    def _auto_switch_model(self):
        current_eng = self.engine_var.get()
        current_model = self.model_var.get()
        search_order = []
        cur_models = self._get_engine_models(current_eng)
        cur_idx = cur_models.index(current_model) if current_model in cur_models else -1
        for m in cur_models[cur_idx + 1 :]:
            search_order.append((current_eng, m))
        cur_eng_idx = ENGINE_ORDER.index(current_eng) if current_eng in ENGINE_ORDER else 0
        for offset in range(1, len(ENGINE_ORDER)):
            eng = ENGINE_ORDER[(cur_eng_idx + offset) % len(ENGINE_ORDER)]
            skip_no_key = True
            if skip_no_key and not self.config.get(eng, "").strip():
                continue
            for m in self._get_engine_models(eng):
                search_order.append((eng, m))
        for eng, model in search_order:
            used = self.config["used_today"].get(model, 0)
            limit = MODEL_DAILY_LIMITS.get(model, -1)
            # limit=-1 未知配額視為可用（實際呼叫才知道）；limit=0 跳過；其他檢查使用量
            if limit == -1 or (limit > 0 and used < limit):
                log(f"自動切換: {ENGINE_DISPLAY[eng]} / {model} ({used}/{limit})")
                if eng != current_eng:
                    self._save_current_key_to_config()
                    self.engine_var.set(eng)
                    self.key_label.config(text=f"{ENGINE_DISPLAY[eng]} API Key:")
                    self.api_entry.delete(0, tk.END)
                    self.api_entry.insert(0, self.config.get(eng, ""))
                    self.model_combo["values"] = self._get_engine_models(eng)
                self.model_var.set(model)
                self._refresh_quota()
                self._update_cooldown_display()
                self._set_status(
                    S("status_auto_switched").format(engine=ENGINE_DISPLAY.get(eng, eng), model=model),
                    "blue"
                )
                return True
        log("所有引擎/模型的每日額度皆已用完")
        self._set_status(S("status_quota_exhausted_hint"), "red")
        return False

    def _start_cooldown_timer(self):
        if self._cooldown_timer_id:
            self.root.after_cancel(self._cooldown_timer_id)
        self._update_cooldown_display()

    def _update_cooldown_display(self):
        if not hasattr(self, "cooldown_label"):
            return
        model = self.model_var.get()
        remaining = self._get_remaining_cooldown(model)
        if remaining > 0:
            secs = int(remaining) + 1
            self.cooldown_label.config(text=f'⏱ {S("lbl_cooldown")}: {secs}s', foreground="orange")
            self._cooldown_timer_id = self.root.after(1000, self._update_cooldown_display)
        else:
            self.cooldown_label.config(text=f'✓ {S("lbl_available")}', foreground="green")
            self._cooldown_timer_id = None

    def _parse_429_retry_delay(self, error_str):
        m = re.search(r'retry\s*(?:Delay|in)["\s:]*(\d+\.?\d*)\s*s', error_str, re.IGNORECASE)
        if m:
            return int(float(m.group(1))) + 1
        return None

    def _is_quota_zero(self, error_str):
        return "limit: 0" in error_str

    def _log_json_debug(self, eng, model, json_err, raw_text):
        sep = "=" * 72
        log(sep)
        log("JSON PARSE FAIL - DEBUG INFO")
        log(f"  Engine:  {ENGINE_DISPLAY.get(eng, eng)}")
        log(f"  Model:   {model}")
        log(f"  Time:    {time.strftime('%Y-%m-%d %H:%M:%S')}")
        log(f"  Error:   {json_err}")
        log(f"  Length:  {len(raw_text)} chars")
        log("-" * 72)
        max_show = 3000
        log("[RAW API RESPONSE]")
        log(raw_text[:max_show])
        if len(raw_text) > max_show:
            log(f"  ... (truncated, full={len(raw_text)})")
        log("-" * 72)
        cleaned = re.sub(r"```json\s*|```", "", raw_text).strip()
        col_match = re.search(r"char(?:acter)?\s*(\d+)", json_err)
        if col_match:
            col = int(col_match.group(1))
            s = max(0, col - 50)
            e = min(len(cleaned), col + 50)
            snippet = cleaned[s:e]
            arrow_pos = min(50, col - s)
            log("[ERROR POSITION]")
            log(f"  Near char {col}:")
            log(f"  ...{snippet}...")
            log(f"     {' ' * arrow_pos}^^^")
            cs = max(0, col - 5)
            ce = min(len(cleaned), col + 5)
            log("[CHAR-BY-CHAR]")
            for ci in range(cs, ce):
                c = cleaned[ci]
                tag = " <-- ERROR" if ci == col else ""
                log(f"  [{ci}] '{c}' (U+{ord(c):04X}){tag}")
        log("-" * 72)
        log("[POSSIBLE CAUSE]")
        if "Expecting ',' delimiter" in json_err:
            log("  -> JSON missing comma, model may have extra text or incomplete JSON")
        elif "Expecting ':'" in json_err:
            log("  -> JSON key-value format error")
        elif "Unterminated string" in json_err:
            log("  -> Unclosed quote, response may be truncated")
        elif "Extra data" in json_err:
            log("  -> Extra text after JSON end")
        elif "Expecting value" in json_err:
            log("  -> Invalid char where JSON value expected")
        else:
            log("  -> Model response is not valid JSON")
        log("  -> Try: switch model or capture clearer image")
        log(sep)

    # ══════════════════════════════════════════
    # 遊戲攻略
    # ══════════════════════════════════════════
    def start_guide_worker(self):
        if self._capture_in_progress:
            return
        if not self._check_cooldown_and_quota():
            return
        self._capture_in_progress = True
        threading.Thread(target=self._guide_capture_task, daemon=True).start()

    def _guide_capture_task(self):
        try:
            target = self.title_var.get().lower()
            hwnd = None

            def _handler(h, _):
                nonlocal hwnd
                if target in win32gui.GetWindowText(h).lower():
                    hwnd = h
                    return False
                return True

            win32gui.EnumWindows(_handler, None)
            if not hwnd:
                self._set_status(S("status_win_missing"), "red")
                return

            try:
                crop_top = int(self.crop_top_var.get())
            except ValueError:
                crop_top = 0
            if crop_top < 0:
                crop_top = 0

            img = self._grab_window_hwnd(hwnd, crop_top)
            win_title = win32gui.GetWindowText(hwnd)
            self._enqueue_task({"type": "guide", "image_pil": img, "win_title": win_title, "source": "capture"})
        finally:
            self._capture_in_progress = False

    def _rescue_guide_from_text(self, text: str):
        progress = ""
        guide_list = []
        if not text:
            return progress, guide_list
        # 嘗試用 regex 直接抽取 progress 字串值
        m_prog = re.search(r'"progress"\s*:\s*"([^"]*)"', text)
        if m_prog:
            progress = m_prog.group(1)
        # 嘗試抽取 guide 陣列內容（提取所有 "..." 字串項目）
        m_guide = re.search(r'"guide"\s*:\s*\[([^\]]*)\]', text, re.DOTALL)
        if m_guide:
            raw_items = m_guide.group(1)
            guide_list = re.findall(r'"([^"]+)"', raw_items)
        return progress, guide_list

    def _do_guide(self, image_pil, win_title, **task):
        eng     = task.get("snap_engine",  self.engine_var.get())
        model   = task.get("snap_model",   self.model_var.get())
        api_key = task.get("snap_api_key", self.api_entry.get().strip())
        tgt_lang = task.get("snap_tgt_lang", self.tgt_lang_var.get())

        if not api_key:
            self._set_status(S("status_no_key"), "red")
            return

        # 從視窗標題取得 ROM 名稱與區域版本
        rom_name = win_title
        if " - " in win_title:
            rom_name = win_title.split(" - ", 1)[1]
        region = "Japan"
        if "(USA)" in rom_name or "(U)" in rom_name:
            region = "USA"
        elif "(Europe)" in rom_name or "(E)" in rom_name:
            region = "Europe"
        elif "(Japan)" in rom_name or "(J)" in rom_name:
            region = "Japan"

        # 去除 ROM 名稱中的區域標籤避免重複
        display_name = re.sub(r"\s*\((USA|Japan|Europe|J|U|E)\)", "", rom_name).strip()
        guide_prompt = build_guide_prompt(display_name, region, tgt_lang)

        self._set_status(S("status_guide_analyzing"), "blue")
        log(f"攻略請求: {model} / {rom_name} ({region})")

        try:
            caller = ENGINE_CALLERS[eng]
            raw = caller(api_key, model, image_pil, guide_prompt)

            # 解析結果
            if isinstance(raw, list) and len(raw) > 0:
                raw = raw[0]
            progress = raw.get("progress", S("progress_unknown")) if isinstance(raw, dict) else str(raw)
            guide_list = raw.get("guide", []) if isinstance(raw, dict) else []

            # 更新配額
            self.config["used_today"][model] = self.config["used_today"].get(model, 0) + 1
            self._safe_save_config()
            self.root.after(0, self._refresh_quota)

            # 儲存到 DB
            self._save_guide_log(rom_name, model, progress, guide_list, image_pil=image_pil)

            # 顯示結果到翻譯視窗
            self.root.after(0, lambda: self._render_guide(progress, guide_list, image_pil))
            self._set_status(S("status_guide_done"), "green")
            log(f"{model} 攻略分析成功")

        except ValueError as e:
            err_str = str(e)
            log(f"攻略分析失敗: {err_str}")
            # ── JSON 解析失敗時：嘗試從原始文字直接救援 progress/guide ──
            if err_str.startswith("JSON_PARSE_FAIL|"):
                raw_text = err_str.split("|", 2)[2] if err_str.count("|") >= 2 else ""
                progress, guide_list = self._rescue_guide_from_text(raw_text)
                if progress or guide_list:
                    log(f"攻略救援解析成功: progress={bool(progress)}, guide={len(guide_list)} 項")
                    self.config["used_today"][model] = self.config["used_today"].get(model, 0) + 1
                    self._safe_save_config()
                    self.root.after(0, self._refresh_quota)
                    self._save_guide_log(rom_name, model, progress, guide_list, image_pil=image_pil)
                    self.root.after(0, lambda _p=progress, _g=guide_list: self._render_guide(_p, _g, image_pil))
                    self._set_status(S("status_guide_done"), "green")
                    return
            self._set_status(S("status_guide_json_fail"), "red")

        except Exception as e:
            err_str = str(e)
            log(f"攻略分析失敗: {err_str}")

            # ── 套件未安裝 ──
            if isinstance(e, (ModuleNotFoundError, ImportError)):
                missing = err_str.replace("No module named ", "").strip("'")
                self._set_status(S("status_pkg_missing").format(pkg=missing), "red")
            elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "rate_limit" in err_str.lower():
                retry_sec = self._parse_429_retry_delay(err_str)
                if retry_sec:
                    self._set_status(S("status_429_wait").format(sec=retry_sec), "red")
                else:
                    self._set_status(S("status_429"), "red")
            elif "503" in err_str or "UNAVAILABLE" in err_str:
                self._set_status(S("status_503b").format(model=model), "red")
            elif "401" in err_str or "403" in err_str or "UNAUTHENTICATED" in err_str:
                self._set_status(S("status_key_invalid"), "red")
            else:
                self._set_status(S("status_guide_fail"), "red")

    def _render_guide(self, progress, guide_list, image_pil):
        if not hasattr(self, "guide_display") or not self.guide_display.winfo_exists():
            return

        # 尺寸與翻譯結果視窗相同
        out_w = self.display.winfo_width()
        out_h = self.display.winfo_height()
        if out_w < 100 or out_h < 100:
            out_w, out_h = image_pil.width, image_pil.height

        # 深色背景畫布
        out_img = Image.new("RGB", (out_w, out_h), (26, 26, 46))  # #1a1a2e
        draw = ImageDraw.Draw(out_img)

        tgt_lang_str = self.tgt_lang_var.get() if hasattr(self, "tgt_lang_var") else "Traditional Chinese(正體中文)"
        font_header = _get_font_for_lang(tgt_lang_str, 22)
        font_body = _get_font_for_lang(tgt_lang_str, 16)
        font_small = _get_font_for_lang(tgt_lang_str, 13)

        pad = PADDING + 5
        y = pad

        # ── 頂部裝飾線 ──
        draw.line([(pad, y), (out_w - pad, y)], fill=(80, 200, 255), width=2)
        y += 10

        # ── 標題：目前進度 ──
        draw.text((pad, y), "▎目前進度", font=font_header, fill=(255, 215, 0))  # 金色
        y += 32

        # 進度內容
        progress_clean = progress.replace("\n", " ").replace("\r", "")
        y = draw_wrapped_text_safe(draw, progress_clean, pad + 8, y, font_body, out_w, out_h, (230, 230, 230))
        y += 20

        # ── 分隔線 ──
        draw.line([(pad, y), (out_w - pad, y)], fill=(60, 60, 100), width=1)
        y += 12

        # ── 標題：目前攻略內容 ──
        draw.text((pad, y), S("guide_section_header"), font=font_header, fill=(255, 215, 0))
        y += 32

        # 攻略條目
        colors = [
            (100, 220, 255),  # 淺藍
            (150, 255, 150),  # 淺綠
            (255, 200, 100),  # 淺橘
            (200, 180, 255),  # 淺紫
            (255, 160, 180),  # 淺粉
        ]
        for idx, item in enumerate(guide_list):
            if y > out_h - 30:
                break
            item_clean = item.replace("\n", " ").replace("\r", "")
            bullet_color = colors[idx % len(colors)]
            # 圓點符號
            draw.text((pad + 4, y), "●", font=font_small, fill=bullet_color)
            # 內容文字
            y = draw_wrapped_text_safe(draw, item_clean, pad + 24, y, font_body, out_w, out_h, (220, 220, 220))
            y += 10

        # ── 底部裝飾線 ──
        bottom_y = min(y + 10, out_h - pad)
        draw.line([(pad, bottom_y), (out_w - pad, bottom_y)], fill=(80, 200, 255), width=2)

        # 調整視窗大小並顯示
        self.guide_display.geometry(f"{out_w}x{out_h}")
        self._ensure_guide_display()
        self.guide_tk_img = ImageTk.PhotoImage(out_img)
        self.guide_canvas.config(image=self.guide_tk_img)

    def _save_guide_log(self, rom_name, model, progress, guide_list, image_pil=None):

        try:
            ss_rel = None
            if image_pil is not None:
                safe_name = re.sub(r'[\\/:*?"<>|]', "_", rom_name).strip() or "unknown_rom"
                ss_dir = os.path.join(self.LOG_DIR, "guide_screenshots", safe_name)
                os.makedirs(ss_dir, exist_ok=True)
                ts = time.strftime("%Y%m%d_%H%M%S")
                ss_filename = f"{ts}.jpg"
                ss_path = os.path.join(ss_dir, ss_filename)
                thumb = image_pil.copy()
                thumb.thumbnail((256, 256), Image.LANCZOS)
                thumb.save(ss_path, format="JPEG", quality=85)
                ss_rel = os.path.join("guide_screenshots", safe_name, ss_filename)

            conn = sqlite3.connect(self.DB_PATH)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            guide_json = json.dumps(guide_list, ensure_ascii=False)
            conn.execute(
                "INSERT INTO guides (rom_name, timestamp, model, progress, guide_content, screenshot_path) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (rom_name, timestamp, model, progress, guide_json, ss_rel),
            )
            conn.commit()
            count = conn.execute("SELECT COUNT(*) FROM guides WHERE rom_name = ?", (rom_name,)).fetchone()[0]
            conn.close()
            log(f"攻略紀錄已儲存: {rom_name} (第 {count} 筆)")
            self._guide_nav_rom_name = rom_name
            self._guide_nav_index = 0
            self.root.after(0, self._guide_nav_reload)
        except Exception as e:
            log(f"儲存攻略紀錄失敗: {e}")

    # ══════════════════════════════════════════
    # 合併翻譯+攻略（單一 REQUEST）
    # ══════════════════════════════════════════
    def _do_combined_translate(self, image_pil, win_title, **task):
        eng      = task.get("snap_engine",  self.engine_var.get())
        api_key  = task.get("snap_api_key", self.api_entry.get().strip())
        model    = task.get("snap_model",   self.model_var.get())
        src_lang = task.get("snap_src_lang", self.src_lang_var.get())
        tgt_lang = task.get("snap_tgt_lang", self.tgt_lang_var.get())

        if not api_key:
            self._set_status(S("status_no_key_eng").format(engine=ENGINE_DISPLAY[eng]), "red")
            return

        # 取得 ROM 名稱與區域版本
        rom_name = win_title
        if " - " in win_title:
            rom_name = win_title.split(" - ", 1)[1]
        region = "Japan"
        if "(USA)" in rom_name or "(U)" in rom_name:
            region = "USA"
        elif "(Europe)" in rom_name or "(E)" in rom_name:
            region = "Europe"
        elif "(Japan)" in rom_name or "(J)" in rom_name:
            region = "Japan"
        display_name = re.sub(r"\s*\((USA|Japan|Europe|J|U|E)\)", "", rom_name).strip()

        combined_prompt = build_combined_prompt(display_name, region, src_lang, tgt_lang)

        self._set_status(S("status_combo_analyzing").format(engine=ENGINE_DISPLAY[eng], model=model), "orange")
        log(f"合併請求: {model} / {display_name} ({region})")

        try:
            caller = ENGINE_CALLERS[eng]
            raw = caller(api_key, model, image_pil, combined_prompt)

            # 解析合併回應
            if isinstance(raw, list) and len(raw) > 0:
                raw = raw[0]

            if isinstance(raw, dict):
                translations = raw.get("translations", [])
                progress = raw.get("progress", S("progress_unknown"))
                guide_list = raw.get("guide", [])
            else:
                translations = []
                progress = S("guide_parse_fail")
                guide_list = []

            # 更新配額（只消耗一次）
            self.config["used_today"][model] = self.config["used_today"].get(model, 0) + 1
            self.config[eng] = api_key
            self._safe_save_config()
            self.root.after(0, self._refresh_quota)

            # 儲存翻譯紀錄
            if translations:
                self.last_res = translations
                self._save_translation_log(
                    translations, model, win_title, image_pil,
                    target_window=task.get("snap_target_window", self.title_var.get().strip()),
                    platform=task.get("snap_platform", self.platform_var.get().strip()),
                )

            # 儲存攻略紀錄
            if progress or guide_list:
                self._save_guide_log(rom_name, model, progress, guide_list, image_pil=image_pil)

            # 渲染翻譯結果
            self.root.after(0, lambda _t=translations, _img=image_pil: self.render(_t, _img, "capture"))

            # 渲染攻略結果
            self.root.after(0, lambda _p=progress, _g=guide_list, _img=image_pil: self._render_guide(_p, _g, _img))

            self._set_status(S("status_combo_done"), "green")
            self._stamp_elapsed()
            log(f"{model} 合併請求成功: {len(translations)} 段翻譯, {len(guide_list)} 條攻略")

        except ValueError as e:
            err_msg = str(e)
            if err_msg.startswith("JSON_PARSE_FAIL|"):
                parts = err_msg.split("|", 2)
                json_err = parts[1] if len(parts) > 1 else "unknown"
                raw_text = parts[2] if len(parts) > 2 else ""
                self._log_json_debug(eng, model, json_err, raw_text)
                self._set_status(S("status_json_fail"), "red")
            else:
                log(f"ValueError: {err_msg}")
                self._set_status(S("status_error").format(msg=err_msg[:60]), "red")

        except Exception as e:
            err_str = str(e)
            log(f"合併請求失敗: {err_str}")
            # ── 套件未安裝 ──
            if isinstance(e, (ModuleNotFoundError, ImportError)):
                missing = err_str.replace("No module named ", "").strip("'")
                self._set_status(S("status_pkg_missing").format(pkg=missing), "red")
            elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "rate_limit" in err_str.lower():
                retry_sec = self._parse_429_retry_delay(err_str)
                if retry_sec:
                    self._set_status(S("status_429_wait").format(sec=retry_sec), "red")
                else:
                    self._set_status(S("status_429"), "red")
            elif "503" in err_str or "UNAVAILABLE" in err_str:
                self._set_status(S("status_503").format(model=model), "red")
            elif "401" in err_str or "403" in err_str:
                self._set_status(S("status_key_invalid2"), "red")
            else:
                self._set_status(S("status_combined_fail"), "red")

    # ══════════════════════════════════════════
    # 本地 OCR + 雲端 AI 翻譯
    # ══════════════════════════════════════════
    def _do_ocr_translate(self, image_pil, source="file", win_title="", src_lang=None, tgt_lang=None, **task):
        # 優先使用傳入的快照值，避免在 worker thread 讀取 UI 變數
        if src_lang is None:
            src_lang = self.src_lang_var.get()
        if tgt_lang is None:
            tgt_lang = self.tgt_lang_var.get()
        target_win = task.get("snap_target_window", self.title_var.get().strip())
        platform   = task.get("snap_platform",      self.platform_var.get().strip())

        # ── Step1：EasyOCR 辨識 ──
        self._set_status(S("status_ocr_running"), "orange")
        try:
            import easyocr
        except ImportError:
            self._set_status(S("status_ocr_no_easyocr"), "red")
            self._stamp_elapsed()
            return

        try:
            ocr_langs = _bcp47_to_easyocr(LANG_TO_BCP47.get(src_lang, "ja"))
            if not hasattr(self, "_easyocr_reader") or self._easyocr_langs != ocr_langs:
                log(f"[OCR] 初始化 EasyOCR langs={ocr_langs}")
                warnings.filterwarnings("ignore")
                logging.getLogger("easyocr").setLevel(logging.ERROR)
                logging.getLogger("torch").setLevel(logging.ERROR)
                self._easyocr_reader = easyocr.Reader(ocr_langs, gpu=False, verbose=False)
                self._easyocr_langs = ocr_langs

            import numpy as np
            # 縮放圖片以加速 EasyOCR（保留原始尺寸用於座標還原）
            orig_w, orig_h = image_pil.width, image_pil.height
            ocr_img, scale = _resize_for_ocr(image_pil)
            img_np = np.array(ocr_img)
            ocr_results = self._easyocr_reader.readtext(img_np)
            ocr_results = [r for r in ocr_results if r[2] >= OCR_CONF_THRESHOLD]
            if not ocr_results:
                self._set_status(S("status_ocr_no_text"), "gray")
                self._stamp_elapsed()
                return
            log(f"[OCR] 偵測到 {len(ocr_results)} 個文字區塊（信心值 ≥ {OCR_CONF_THRESHOLD}，縮放比={scale:.2f}）")
        except Exception as e:
            self._set_status(S("status_ocr_fail").format(msg=str(e)[:60]), "red")
            self._stamp_elapsed()
            return

        # ── Step2：Google 翻譯（並行）──
        self._set_status(S("status_ocr_translating"), "orange")
        try:
            src_bcp = LANG_TO_BCP47.get(src_lang, "auto")
            tgt_bcp = LANG_TO_BCP47.get(tgt_lang, "zh-TW")
            texts = [text for _, text, _ in ocr_results]

            with ThreadPoolExecutor(max_workers=min(OCR_TRANSLATE_WORKERS, len(texts))) as pool:
                translated_list = list(pool.map(
                    lambda t: _google_translate(t, src_bcp, tgt_bcp), texts
                ))
        except Exception as e:
            self._set_status(S("status_gt_fail").format(msg=str(e)[:60]), "red")
            self._stamp_elapsed()
            return

        # ── Step3：組合 segments（座標還原至原始尺寸）──
        segments = []
        for (bbox, text, conf), tw in zip(ocr_results, translated_list):
            # bbox 座標是縮放後的，需除以 scale 還原，再正規化至 0~1
            xs = [p[0] / scale for p in bbox]
            ys = [p[1] / scale for p in bbox]
            segments.append({
                "tw": tw,
                "x": round(min(xs) / orig_w, 4),
                "y": round(min(ys) / orig_h, 4),
                "w": round((max(xs) - min(xs)) / orig_w, 4),
                "h": round((max(ys) - min(ys)) / orig_h, 4),
            })

        if not segments:
            self._set_status(S("status_ocr_no_result"), "gray")
            self._stamp_elapsed()
            return

        # ── Step4：儲存 + 渲染 ──
        self._set_status(S("status_ocr_done").format(n=len(segments)), "green")
        self._stamp_elapsed()

        if source == "capture" and segments:
            self._save_translation_log(
                segments, "OCR+GoogleTranslate", win_title, image_pil,
                target_window=target_win,
                platform=platform,
            )

        self.root.after(0, lambda _s=segments, _img=image_pil: self.render(_s, _img, source))

    def _do_translate(self, image_pil, source="file", win_title="", **task):
        # 任務實際開始執行時重置計時器（在主執行緒透過 after 同步執行）
        if threading.current_thread() is threading.main_thread():
            self._start_elapsed_timer()
        else:
            evt = threading.Event()
            self.root.after(0, lambda: (self._start_elapsed_timer(), evt.set()))
            evt.wait(timeout=2)

        # 優先使用 enqueue 時的快照值，確保 worker thread 不直接讀取 UI 變數
        src_lang     = task.get("snap_src_lang",     self.src_lang_var.get())
        tgt_lang     = task.get("snap_tgt_lang",     self.tgt_lang_var.get())
        engine_mode  = task.get("snap_engine_mode",  self.engine_mode_var.get() if getattr(self, "engine_mode_var", None) else "cloud")
        eng          = task.get("snap_engine",       self.engine_var.get())
        model        = task.get("snap_model",        self.model_var.get())
        api_key      = task.get("snap_api_key",      self.api_entry.get().strip())
        ollama_model = task.get("snap_ollama_model", self.ollama_model_var.get() if hasattr(self, "ollama_model_var") else "")
        target_win   = task.get("snap_target_window", self.title_var.get().strip())
        platform     = task.get("snap_platform",     self.platform_var.get().strip())
        try:
            ollama_timeout = int(task.get("snap_ollama_timeout", self.ollama_timeout_var.get() if hasattr(self, "ollama_timeout_var") else str(OLLAMA_TIMEOUT)))
            if ollama_timeout <= 0:
                ollama_timeout = OLLAMA_TIMEOUT
        except (ValueError, AttributeError):
            ollama_timeout = OLLAMA_TIMEOUT

        translate_prompt = build_translate_prompt(src_lang, tgt_lang)

        # ── OCR 模式優先判斷 ──
        if engine_mode == "ocr":
            self._do_ocr_translate(
                image_pil, source, win_title,
                src_lang=src_lang, tgt_lang=tgt_lang,
                snap_target_window=target_win,
                snap_platform=platform,
            )
            return

        # ── OLLAMA 優先判斷 ──
        use_ollama = (engine_mode == "local" and self._ollama_available)
        if use_ollama:
            if not ollama_model:
                self._set_status(S("status_ollama_no_model"), "red")
                return
            self._set_status(S("status_ollama_running").format(t=ollama_timeout), "orange")
            try:
                res = call_ollama(ollama_model, image_pil, translate_prompt, timeout=ollama_timeout)
                if isinstance(res, list) and len(res) == 0:
                    self._set_status(S("status_ollama_empty"), "gray")
                    self._stamp_elapsed()
                    return
            except TimeoutError as e:
                log(f"OLLAMA timeout: {e}")
                self._set_status(S("status_ollama_timeout"), "red")
                self._stamp_elapsed()
                return
            except ValueError as e:
                err_msg = str(e)
                if err_msg.startswith("JSON_PARSE_FAIL|"):
                    parts = err_msg.split("|", 2)
                    self._log_json_debug(
                        "ollama", ollama_model,
                        parts[1] if len(parts) > 1 else "unknown",
                        parts[2] if len(parts) > 2 else "",
                    )
                    self._set_status(S("status_ollama_aborted"), "red")
                else:
                    log(f"OLLAMA 解析錯誤: {err_msg[:80]}")
                    self._set_status(S("status_ollama_aborted"), "red")
                self._stamp_elapsed()
                return
            except Exception as e:
                log(f"OLLAMA 呼叫失敗: {e}")
                self._set_status(S("status_ollama_fail").format(err=str(e)[:60]), "red")
                self._stamp_elapsed()
                return
            self.last_res = res
            self.config["used_today"][ollama_model] = self.config["used_today"].get(ollama_model, 0) + 1
            self._safe_save_config()
            self._set_status(S("status_ollama_done").format(n=len(res)), "green")
            self._stamp_elapsed()
            log(f"OLLAMA ({ollama_model}) 翻譯成功，共 {len(res)} 段")
            if source == "capture" and res:
                self._save_translation_log(
                    res, ollama_model, win_title, image_pil,
                    target_window=target_win, platform=platform,
                )
            self.root.after(0, lambda _r=res, _img=image_pil, _s=source: self.render(_r, _img, _s))
            return

        # ── 雲端引擎流程 ──
        if not api_key:
            self._set_status(S("status_no_key_eng").format(engine=ENGINE_DISPLAY[eng]), "red")
            self._stamp_elapsed()
            return

        self._set_status(S("status_analyzing").format(engine=ENGINE_DISPLAY[eng], model=model), "orange")

        try:
            caller = ENGINE_CALLERS[eng]
            res = caller(api_key, model, image_pil, translate_prompt)

        except ValueError as e:
            # _parse_json_response 拋出的 JSON 解析失敗，包含原始回應
            err_msg = str(e)
            if err_msg.startswith("JSON_PARSE_FAIL|"):
                parts = err_msg.split("|", 2)
                json_err = parts[1] if len(parts) > 1 else "unknown"
                raw_text = parts[2] if len(parts) > 2 else ""
                self._log_json_debug(eng, model, json_err, raw_text)
                self._set_status(S("status_json_fail"), "red")
            else:
                log(f"ValueError: {err_msg}")
                self._set_status(S("status_error").format(msg=err_msg[:60]), "red")
            res = []

        except Exception as e:
            err_str = str(e)
            log(f"{ENGINE_DISPLAY[eng]} API 呼叫失敗: {err_str}")

            # ── 套件未安裝 ──
            if isinstance(e, (ModuleNotFoundError, ImportError)):
                missing = err_str.replace("No module named ", "").strip("'")
                self._set_status(S("status_pkg_missing").format(pkg=missing), "red")
            elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                if self._is_quota_zero(err_str):
                    MODEL_DAILY_LIMITS[model] = 0
                    learned = self.config.setdefault("learned_zero_quota", [])
                    if model not in learned:
                        learned.append(model)
                        save_config(self.config)
                    log(f"[quota] 學習到 {model} limit=0，已記錄，嘗試自動切換...")
                    self.root.after(0, self._refresh_quota)
                    self.root.after(0, self._refresh_quota_table)
                    if self._auto_switch_model():
                        log(f"[quota] limit=0 觸發自動切換成功，重新送出翻譯請求...")
                        # 用新引擎/模型的快照重新加入佇列
                        new_snap = {
                            "snap_src_lang":      task.get("snap_src_lang", src_lang),
                            "snap_tgt_lang":      task.get("snap_tgt_lang", tgt_lang),
                            "snap_engine_mode":   engine_mode,
                            "snap_engine":        self.engine_var.get(),
                            "snap_model":         self.model_var.get(),
                            "snap_api_key":       self.api_entry.get().strip(),
                            "snap_ollama_model":  task.get("snap_ollama_model", ""),
                            "snap_ollama_timeout": task.get("snap_ollama_timeout", str(OLLAMA_TIMEOUT)),
                            "snap_target_window": target_win,
                            "snap_platform":      platform,
                        }
                        retry_task = {"type": "translate", "image_pil": image_pil,
                                      "source": source, "win_title": win_title}
                        retry_task.update(new_snap)
                        try:
                            _request_queue.put_nowait(retry_task)
                            log(f"[quota] 重試任務已加入佇列")
                        except Exception:
                            self._set_status(S("status_quota_exhausted_hint"), "red")
                    else:
                        self._set_status(S("quota_switch").format(model=model), "red")
                else:
                    retry_sec = self._parse_429_retry_delay(err_str)
                    if retry_sec:
                        self._set_status(S("status_429_wait").format(sec=retry_sec), "red")
                    else:
                        self._set_status(S("status_429"), "red")
            # ── 503 服務繁忙 ──
            elif "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str.lower():
                self._set_status(S("status_503b").format(model=model), "red")
            # ── 401/403 認證失敗 ──
            elif "401" in err_str or "403" in err_str or "UNAUTHENTICATED" in err_str or "PERMISSION_DENIED" in err_str:
                self._set_status(S("status_key_invalid_eng").format(engine=ENGINE_DISPLAY[eng]), "red")
            # ── 400 請求錯誤 ──
            elif "400" in err_str or "INVALID_ARGUMENT" in err_str:
                self._set_status(S("status_bad_request"), "red")
            # ── 500 內部錯誤 ──
            elif "500" in err_str or "INTERNAL" in err_str:
                self._set_status(S("status_server_error").format(engine=ENGINE_DISPLAY[eng]), "red")
            # ── 網路問題 ──
            elif "connect" in err_str.lower() or "timeout" in err_str.lower() or "ConnectionError" in err_str:
                self._set_status(S("status_network_fail"), "red")
            # ── 其他 ──
            else:
                self._set_status(S("status_api_fail").format(msg=err_str[:60]), "red")
            res = []

        if res:
            self.last_res = res
            self.config["used_today"][model] = self.config["used_today"].get(model, 0) + 1
            self.config[eng] = api_key
            # 非內建模型：翻譯成功表示此模型可用，持久化配額資訊
            built_in_models = [m for models in ENGINE_MODELS.values() for m in models]
            if model not in built_in_models:
                cur_limit = MODEL_DAILY_LIMITS.get(model, -1)
                if cur_limit == -1:
                    # 成功代表有額度，用保守預設值標記為「已確認可用」
                    MODEL_DAILY_LIMITS[model] = QUOTA_ESTIMATED_DEFAULT
                    self.config.setdefault("custom_quota", {})[model] = QUOTA_ESTIMATED_DEFAULT
                    # 記錄哪些模型是保守估算，供 Tab3 顯示區別
                    estimated = self.config.setdefault("estimated_quota_models", [])
                    if model not in estimated:
                        estimated.append(model)
                    log(f"[quota] {model} 翻譯成功，配額標記為保守額度 {QUOTA_ESTIMATED_DEFAULT} RPD")
                else:
                    self.config.setdefault("custom_quota", {})[model] = cur_limit
            self._safe_save_config()
            self.root.after(0, self._refresh_quota)
            self._set_status(S("status_done"), "green")
            self._stamp_elapsed()
            log(f"{model} 翻譯成功，共 {len(res)} 段")

            # 畫面擷取模式：儲存翻譯紀錄
            if source == "capture" and res:
                self._save_translation_log(
                    res, model, win_title, image_pil,
                    target_window=target_win, platform=platform,
                )
        else:
            self._stamp_elapsed()

        self.root.after(0, lambda _r=res, _img=image_pil, _s=source: self.render(_r, _img, _s))

    # ══════════════════════════════════════════
    # ══════════════════════════════════════════
    # 翻譯紀錄儲存（SQLite + 截圖）
    # ══════════════════════════════════════════
    LOG_DIR = TRANSLATION_LOGS_DIR
    DB_PATH = os.path.join(LOG_DIR, "translations.db")

    def _init_db(self):

        os.makedirs(self.LOG_DIR, exist_ok=True)
        conn = sqlite3.connect(self.DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rom_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                model TEXT NOT NULL,
                lines TEXT NOT NULL,
                screenshot_path TEXT,
                target_window TEXT,
                platform TEXT
            )
        """)
        # 舊資料庫相容：若欄位不存在則自動新增
        cursor = conn.execute("PRAGMA table_info(translations)")
        columns = [row[1] for row in cursor.fetchall()]
        if "target_window" not in columns:
            conn.execute("ALTER TABLE translations ADD COLUMN target_window TEXT")
        if "platform" not in columns:
            conn.execute("ALTER TABLE translations ADD COLUMN platform TEXT")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS guides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rom_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                model TEXT NOT NULL,
                progress TEXT NOT NULL,
                guide_content TEXT NOT NULL,
                screenshot_path TEXT
            )
        """)
        # 舊資料庫相容：若欄位不存在則自動新增
        cursor2 = conn.execute("PRAGMA table_info(guides)")
        guide_cols = [row[1] for row in cursor2.fetchall()]
        if "screenshot_path" not in guide_cols:
            conn.execute("ALTER TABLE guides ADD COLUMN screenshot_path TEXT")
        # ── sessions / frames 表（場次錄製功能）──
        existing_tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "sessions" not in existing_tables:
            conn.execute("""
                CREATE TABLE sessions (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_name    TEXT NOT NULL,
                    platform     TEXT,
                    started_at   TEXT NOT NULL,
                    ended_at     TEXT,
                    total_frames INTEGER DEFAULT 0,
                    dir_size_kb  INTEGER DEFAULT 0
                )
            """)
        # migration: 加 dir_size_kb
        existing_cols = (
            [r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()]
            if "sessions" in existing_tables
            else []
        )
        if "dir_size_kb" not in existing_cols and "sessions" in existing_tables:
            conn.execute("ALTER TABLE sessions ADD COLUMN dir_size_kb INTEGER DEFAULT 0")
            conn.commit()
        if "frames" not in existing_tables:
            conn.execute("""
                CREATE TABLE frames (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id  INTEGER NOT NULL,
                    seq         INTEGER NOT NULL,
                    ts          TEXT NOT NULL,
                    img_path    TEXT NOT NULL,
                    translation TEXT
                )
            """)
        conn.commit()
        conn.close()
        # 補算舊場次的 dir_size_kb
        self.root.after(500, self._backfill_session_sizes)
        # 建立 Tab4 讀取用的持久連線（唯讀模式，避免反覆 connect/close）
        self._db_conn = sqlite3.connect(self.DB_PATH, check_same_thread=False)
        self._db_conn.row_factory = sqlite3.Row

    def _backfill_session_sizes(self):

        try:
            conn = sqlite3.connect(self.DB_PATH)
            rows = conn.execute("SELECT id FROM sessions WHERE dir_size_kb=0 OR dir_size_kb IS NULL").fetchall()
            for (sid,) in rows:
                first = conn.execute("SELECT img_path FROM frames WHERE session_id=? LIMIT 1", (sid,)).fetchone()
                if first:
                    sess_dir = os.path.dirname(os.path.join(self.LOG_DIR, first[0]))
                    kb = _calc_dir_size_kb(sess_dir)
                    conn.execute("UPDATE sessions SET dir_size_kb=? WHERE id=?", (kb, sid))
            conn.commit()
            conn.close()
            if rows:
                log(f"[DB] 補算 {len(rows)} 筆場次大小完成")
        except Exception as e:
            log(f"[DB] 補算場次大小失敗: {e}")

    def _save_translation_log(self, segments, model, win_title, image_pil, target_window="", platform=""):

        try:
            # 從視窗標題擷取 ROM 名稱
            rom_name = win_title
            if " - " in win_title:
                rom_name = win_title.split(" - ", 1)[1]
            safe_name = re.sub(r'[\\/:*?"<>|]', "_", rom_name).strip()
            if not safe_name:
                safe_name = "unknown_rom"

            # ── 儲存截圖到 translation_logs/screenshots/遊戲名稱/ ──
            ss_dir = os.path.join(self.LOG_DIR, "screenshots", safe_name)
            os.makedirs(ss_dir, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            ss_filename = f"{ts}.jpg"
            ss_path = os.path.join(ss_dir, ss_filename)
            image_pil.save(ss_path, format="JPEG", quality=85)

            # 截圖相對路徑（相對於 translation_logs/）
            ss_rel = os.path.join("screenshots", safe_name, ss_filename)

            # ── 寫入 SQLite ──
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            full_segments = [
                {
                    "tw": s.get("tw", ""),
                    "x": s.get("x", 0.05),
                    "y": s.get("y", 0.1),
                    "w": s.get("w", 0.9),
                    "h": s.get("h", 0.08),
                }
                for s in segments
                if s.get("tw")
            ]
            lines_json = json.dumps(full_segments, ensure_ascii=False)

            conn = sqlite3.connect(self.DB_PATH)
            conn.execute(
                "INSERT INTO translations (rom_name, timestamp, model, lines, screenshot_path, target_window, platform) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (rom_name, timestamp, model, lines_json, ss_rel, target_window, platform),
            )
            conn.commit()
            count = conn.execute("SELECT COUNT(*) FROM translations WHERE rom_name = ?", (rom_name,)).fetchone()[0]
            conn.close()

            log(f"翻譯紀錄已儲存: {rom_name} (第 {count} 筆) 截圖: {ss_rel}")
            # 更新導覽狀態（存檔完成後才觸發，確保 DB 已寫入）
            self._nav_rom_name = rom_name
            self._nav_index = max(0, len(self._nav_ids) - 1)
            self.root.after(0, self._nav_reload)
        except Exception as e:
            log(f"儲存翻譯紀錄失敗: {e}")

    # ══════════════════════════════════════════
    # 翻譯結果視窗導覽
    # ══════════════════════════════════════════
    def _nav_reload(self):

        if not self._nav_rom_name:
            return
        try:
            conn = sqlite3.connect(self.DB_PATH)
            rows = conn.execute(
                "SELECT id FROM translations WHERE rom_name=? ORDER BY id ASC", (self._nav_rom_name,)
            ).fetchall()
            conn.close()
            self._nav_ids = [r[0] for r in rows]
        except Exception:
            self._nav_ids = []
        # 跳到最新一筆（清單末尾）
        self._nav_index = max(0, len(self._nav_ids) - 1)
        self._nav_update_bar()

    def _nav_update_bar(self):
        total = len(self._nav_ids)
        if total == 0:
            self._nav_label.config(text="")
            self._nav_prev_btn.config(state="disabled")
            self._nav_next_btn.config(state="disabled")
            return
        pos = self._nav_index + 1
        self._nav_label.config(text=f"{pos} / {total}")
        self._nav_prev_btn.config(state="normal" if self._nav_index > 0 else "disabled")
        self._nav_next_btn.config(state="normal" if self._nav_index < total - 1 else "disabled")

    def _nav_go(self, index: int):

        if index < 0 or index >= len(self._nav_ids):
            return
        db_id = self._nav_ids[index]
        try:
            conn = sqlite3.connect(self.DB_PATH)
            row = conn.execute("SELECT lines, screenshot_path FROM translations WHERE id=?", (db_id,)).fetchone()
            conn.close()
            if not row:
                return
            segments = []
            for i, item in enumerate(json.loads(row[0])):
                if isinstance(item, str):
                    segments.append({"tw": item, "x": 0.05, "y": round(i * 0.09 + 0.05, 4), "w": 0.9, "h": 0.08})
                else:
                    segments.append(item)
            ss_path = os.path.join(self.LOG_DIR, row[1]) if row[1] else None
            if ss_path and os.path.exists(ss_path):
                img = Image.open(ss_path).convert("RGB")
            else:
                # 無截圖：建立黑底佔位
                img = Image.new("RGB", (DISPLAY_WIDTH_SMALL, DISPLAY_INIT_HEIGHT), (0, 0, 0))
            self._nav_index = index
            self._nav_update_bar()
            self.render(segments, img, source="history")
        except Exception as e:
            log(f"[Nav] 載入歷史失敗: {e}")

    def _nav_prev(self):
        self._nav_go(self._nav_index - 1)

    def _nav_next(self):
        self._nav_go(self._nav_index + 1)

    # ══════════════════════════════════════════
    # 攻略視窗導覽
    # ══════════════════════════════════════════
    def _guide_nav_reload(self):

        if not self._guide_nav_rom_name:
            return
        try:
            conn = sqlite3.connect(self.DB_PATH)
            rows = conn.execute(
                "SELECT id FROM guides WHERE rom_name=? ORDER BY id ASC", (self._guide_nav_rom_name,)
            ).fetchall()
            conn.close()
            self._guide_nav_ids = [r[0] for r in rows]
        except Exception:
            self._guide_nav_ids = []
        self._guide_nav_index = max(0, len(self._guide_nav_ids) - 1)
        self._guide_nav_update_bar()

    def _guide_nav_update_bar(self):
        total = len(self._guide_nav_ids)
        if not (hasattr(self, "_guide_nav_label") and self._guide_nav_label.winfo_exists()):
            return
        if total == 0:
            self._guide_nav_label.config(text="")
            self._guide_nav_prev_btn.config(state="disabled")
            self._guide_nav_next_btn.config(state="disabled")
            return
        pos = self._guide_nav_index + 1
        self._guide_nav_label.config(text=f"{pos} / {total}")
        self._guide_nav_prev_btn.config(state="normal" if self._guide_nav_index > 0 else "disabled")
        self._guide_nav_next_btn.config(state="normal" if self._guide_nav_index < total - 1 else "disabled")

    def _guide_nav_go(self, index: int):

        if index < 0 or index >= len(self._guide_nav_ids):
            return
        db_id = self._guide_nav_ids[index]
        try:
            conn = sqlite3.connect(self.DB_PATH)
            row = conn.execute(
                "SELECT progress, guide_content, screenshot_path FROM guides WHERE id=?", (db_id,)
            ).fetchone()
            conn.close()
            if not row:
                return
            progress, guide_json, ss_rel = row
            guide_list = json.loads(guide_json) if guide_json else []
            if ss_rel:
                ss_path = os.path.join(self.LOG_DIR, ss_rel)
                try:
                    img = Image.open(ss_path).convert("RGB")
                except Exception:
                    img = Image.new("RGB", (DISPLAY_WIDTH_SMALL, DISPLAY_INIT_HEIGHT), (26, 26, 46))
            else:
                img = Image.new("RGB", (DISPLAY_WIDTH_SMALL, DISPLAY_INIT_HEIGHT), (26, 26, 46))
            self._guide_nav_index = index
            self._guide_nav_update_bar()
            self._render_guide(progress, guide_list, img)
        except Exception as e:
            log(f"[GuideNav] 載入歷史失敗: {e}")

    def _guide_nav_prev(self):
        self._guide_nav_go(self._guide_nav_index - 1)

    def _guide_nav_next(self):
        self._guide_nav_go(self._guide_nav_index + 1)

    # ══════════════════════════════════════════
    # 渲染結果
    # ══════════════════════════════════════════
    def render(self, segments, image_pil, source="capture"):
        log(f"render 被呼叫: source={source}, segments={len(segments) if segments else 0}")
        if not self.display.winfo_exists() or not segments:
            log(f"render 提前返回: display={self.display.winfo_exists()}, segments={bool(segments)}")
            return

        # 依原圖寬度決定目標顯示寬度
        _src_w = image_pil.width
        _target_w = _get_display_width(_src_w)

        if source == "file":
            orig_w, orig_h = image_pil.width, image_pil.height
            mode = self.winmode_var.get() if hasattr(self, "winmode_var") else "mesen"
            if mode == "corner":
                max_h = self.root.winfo_screenheight() // 2 - 30
                max_w = _target_w
            else:
                max_h = DISPLAY_INIT_HEIGHT
                max_w = _target_w
            scale = min(max_w / orig_w, max_h / orig_h)
            out_w = int(orig_w * scale)
            out_h = int(orig_h * scale)
            image_pil = image_pil.resize((out_w, out_h), Image.LANCZOS)
        elif source == "history":
            orig_w, orig_h = image_pil.width, image_pil.height
            scale = _target_w / orig_w
            out_w = int(orig_w * scale)
            out_h = int(orig_h * scale)
            image_pil = image_pil.resize((out_w, out_h), Image.LANCZOS)
        else:
            orig_w, orig_h = image_pil.width, image_pil.height
            scale_w = _target_w / orig_w
            max_h = self.root.winfo_screenheight() - 80
            scale_h = max_h / orig_h
            scale = min(scale_w, scale_h)
            out_w = int(orig_w * scale)
            out_h = int(orig_h * scale)
            image_pil = image_pil.resize((out_w, out_h), Image.LANCZOS)

        # ── 座標診斷 LOG（DEBUG_COORD=True 時輸出）──
        _all_sx = [float(s.get("x", 0)) for s in segments]
        _all_sy = [float(s.get("y", 0)) for s in segments]
        _group_px_x = max(_all_sx) > 1.0
        _group_px_y = max(_all_sy) > 1.0
        if DEBUG_COORD:
            log(f"[COORD] 原圖={orig_w}x{orig_h} 顯示={out_w}x{out_h} scale={scale:.3f} source={source}")
            _px_fix_count = 0
            for i, s in enumerate(segments):
                sx_raw = float(s.get("x", 0))
                sy_raw = float(s.get("y", 0))
                tw_preview = s.get("tw", "")[:12].replace("\n", " ")
                if _group_px_x or _group_px_y:
                    _px_fix_count += 1
                    sx_c = (sx_raw / orig_w) if _group_px_x else sx_raw
                    sy_c = (sy_raw / orig_h) if _group_px_y else sy_raw
                    if sx_c > 1.0: sx_c = sx_raw / max(_all_sx)
                    if sy_c > 1.0: sy_c = sy_raw / max(_all_sy)
                    sx_c = max(0.02, min(0.98, sx_c))
                    sy_c = max(0.02, min(0.98, sy_c))
                    tag_x = "⚠超出" if sx_raw > orig_w else ""
                    tag_y = "⚠超出" if sy_raw > orig_h else ""
                    log(f"[COORD] seg[{i}] 像素 x={sx_raw:.0f}{tag_x} y={sy_raw:.0f}{tag_y} → 修正後比例({sx_c:.3f},{sy_c:.3f}) → 畫面({int(sx_c*out_w)},{int(sy_c*out_h)}) | {tw_preview!r}")
                else:
                    log(f"[COORD] seg[{i}] 比例 x={sx_raw:.3f} y={sy_raw:.3f} → 畫面({int(sx_raw*out_w)},{int(sy_raw*out_h)}) | {tw_preview!r}")
            if _px_fix_count:
                log(f"[COORD] ⚠ 共 {_px_fix_count}/{len(segments)} 筆像素座標，x軸{'像素' if _group_px_x else '比例'} y軸{'像素' if _group_px_y else '比例'}")

        is_vertical = self.text_dir_var.get() == "vertical"
        if is_vertical:
            sorted_segs = sorted(segments, key=lambda s: (-float(s.get("x", 0)), float(s.get("y", 0))))
        else:
            sorted_segs = sorted(segments, key=lambda s: float(s.get("y", 0)))
        if self.config.get("text_direction") != self.text_dir_var.get():
            self.config["text_direction"] = self.text_dir_var.get()
            save_config(self.config)

        # 收集非空譯文及其座標
        items = []

        # ── 座標預處理：x/y 軸分開處理，各自獨立修正 ──
        # 先收集原始值
        raw_coords = []
        for s in sorted_segs:
            tw = s.get("tw", "").replace("\n", " ").replace("\r", "").strip()
            if tw:
                raw_coords.append((tw, float(s.get("x", 0.05)), float(s.get("y", 0.1))))

        if raw_coords:
            all_sx = [c[1] for c in raw_coords]
            all_sy = [c[2] for c in raw_coords]
            max_sx = max(all_sx)
            max_sy = max(all_sy)

            # 判斷整組 x/y 是否為像素座標：任一值 > 1.0 即整組視為像素
            group_is_px_x = max_sx > 1.0
            group_is_px_y = max_sy > 1.0

            for tw, sx, sy in raw_coords:
                # X 軸：像素 → 除以原圖寬，超出範圍夾邊
                if group_is_px_x:
                    sx = sx / orig_w
                sx = max(0.02, min(0.98, sx))

                # Y 軸：像素 → 若最大值超出原圖高，代表模型用了更大座標系（如螢幕高度）
                # 用 max_sy 做歸一化以保留組內相對位置；否則用 orig_h
                if group_is_px_y:
                    if max_sy > orig_h:
                        sy = sy / max_sy
                    else:
                        sy = sy / orig_h
                sy = max(0.02, min(0.98, sy))

                items.append((tw, sx, sy))
        if not items:
            return

        # ── 方向E：render 前合併相近 segment（防疊字預處理）──
        # x_thresh=0.03：同欄判斷；y_thresh=0.04：同行判斷（對話框多行間距通常 >0.05）
        raw_dicts = [{"tw": tw, "x": sx, "y": sy, "w": 0.1, "h": 0.05} for tw, sx, sy in items]
        merged = _merge_segments(raw_dicts, x_thresh=0.03, y_thresh=0.04)
        items = [(m["tw"].replace("\n", " "), m["x"], m["y"]) for m in merged]

        items.sort(key=lambda t: t[2])  # 依 sy 升序：y 小的（選單）先於 y 大的（對話框）

        # ── 角色名稱 y 座標修正：若短文字無標點且 y 比下一段小很多，貼近下一段上方 ──
        if len(items) >= 2:
            _punct = set("，。！？、：；…""''「」『』【】〔〕《》〈〉·～─—,.!?:;\"'()[]{}·~-")
            _corrected = list(items)
            for i in range(len(_corrected) - 1):
                tw_i, sx_i, sy_i = _corrected[i]
                tw_next, sx_next, sy_next = _corrected[i + 1]
                is_short = len(tw_i.replace(" ", "")) <= 10
                has_no_punct = not any(c in _punct for c in tw_i)
                y_gap = sy_next - sy_i
                # y 差距 > 0.15 且判斷為角色名稱
                # 排除：當前 y 在上半部（<0.4）且下一段在下半部（>0.5），兩者跨越畫面中線，屬於不同區域不修正
                crosses_midline = sy_i < 0.4 and sy_next > 0.5
                if is_short and has_no_punct and y_gap > 0.15 and not crosses_midline:
                    # 將角色名稱 y 調整到下一段 y 減去一個估算行高（字級/out_h）
                    approx_line_h = OVERLAY_FONT_SIZE_MAX_DEFAULT / out_h
                    new_sy = max(0.02, sy_next - approx_line_h * 1.5)
                    if DEBUG_COORD:
                        log(f"[COORD] 角色名稱 y 修正: {tw_i!r} {sy_i:.3f}→{new_sy:.3f} (next_y={sy_next:.3f})")
                    _corrected[i] = (tw_i, sx_i, new_sy)
            items = _corrected
        tgt_lang = getattr(self, "tgt_lang_var", None)
        tgt_lang_str = tgt_lang.get() if tgt_lang else "Traditional Chinese(正體中文)"
        font_size = OVERLAY_FONT_SIZE_MAX_DEFAULT
        min_font_size = 9  # 方向A：允許縮小至 9px 作為疊字輔助

        while font_size >= min_font_size:
            font = _get_font_for_lang(tgt_lang_str, font_size)
            if font is None:
                font = ImageFont.load_default()
                break

            line_h = font_size + 4
            usable_w = out_w - PADDING * 2
            y_limit = out_h - PADDING

            sim_col_next_y = {}
            sim_ok = True
            for tw, sx, sy in items:
                col = int(sx * 8) if not is_vertical else 0
                col_next = sim_col_next_y.get(col, PADDING)
                draw_x = PADDING if is_vertical else max(PADDING, int(sx * out_w))
                text_w = out_w - draw_x - PADDING
                if text_w < 30:
                    draw_x = PADDING
                    text_w = usable_w
                avg_cw = font_size * 0.55
                cpl = max(1, int(text_w / avg_cw))
                nlines = max(1, -(-len(tw) // cpl))
                block_h = nlines * line_h + 2

                raw_y = int(sy * out_h)
                # 同欄內：若 raw_y 在 col_next 的 2 倍行高以內，視為連續行往下推
                # 否則視為新區塊，直接使用 raw_y（避免跨對話框的段落互相干擾）
                if raw_y >= col_next + line_h * 2:
                    target_y = raw_y
                elif raw_y >= col_next:
                    target_y = raw_y
                else:
                    target_y = col_next

                if target_y + block_h <= y_limit:
                    sim_col_next_y[col] = target_y + block_h
                else:
                    sim_col_next_y[col] = col_next + block_h
                    if sim_col_next_y[col] > out_h:
                        sim_ok = False
                        break

            if sim_ok:
                break
            font_size -= 1

        # ── 底圖：原圖 + 30% 不透明度 ──
        bg_rgba = image_pil.convert("RGBA")
        black_bg = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 255))
        blended = Image.blend(black_bg, bg_rgba, alpha=0.30)
        out_img = blended.convert("RGB")
        draw = ImageDraw.Draw(out_img)

        # ── 繪製譯文 ──
        line_h = font_size + 4
        y_limit = out_h - PADDING
        col_next_y = {}

        for tw, sx, sy in items:
            draw_x = PADDING if is_vertical else max(PADDING, int(sx * out_w))
            col = 0 if is_vertical else int(sx * 8)
            col_next = col_next_y.get(col, PADDING)

            raw_y = int(sy * out_h)
            # 同欄內：若 raw_y 在 col_next 的 2 倍行高以內，視為連續行往下推
            # 否則視為新區塊，直接使用 raw_y（避免跨對話框的段落互相干擾）
            # 額外：若 raw_y 已超過 col_next 足夠多，代表是新的 UI 區塊，重置防疊
            if raw_y >= col_next + line_h * 2:
                draw_y = raw_y  # 新區塊，直接使用 AI 給的 y
            elif raw_y >= col_next:
                draw_y = raw_y  # 有空間，直接用 raw_y
            else:
                draw_y = col_next  # 真正的疊字才往下推

            text_w = out_w - draw_x - PADDING
            if text_w < 30:
                draw_x = PADDING
            avg_cw = font_size * 0.55
            cpl = max(1, int((out_w - draw_x - PADDING) / avg_cw)) if avg_cw > 0 else 1
            nlines = max(1, -(-len(tw) // cpl))
            block_h = nlines * (font_size + 4) + 2

            if draw_y + block_h > y_limit:
                draw_y = max(PADDING, y_limit - block_h)

            draw_wrapped_text_safe(draw, tw, draw_x + 1, draw_y + 1, font, out_w, out_h, (0, 0, 0))
            draw_wrapped_text_safe(draw, tw, draw_x, draw_y, font, out_w, out_h, "white")
            if DEBUG_COORD:
                log(f"[COORD] 繪製 ({draw_x},{draw_y}) norm_x={sx:.3f} norm_y={sy:.3f} raw_y={int(sy*out_h)} final_y={draw_y} | {tw[:12]!r}")
            col_next_y[col] = draw_y + block_h

        if source == "capture":
            self.display.geometry(f"{out_w}x{out_h}")
        else:
            self.display.geometry(f"{out_w}x{out_h}")

        self.tk_img = ImageTk.PhotoImage(out_img)
        self.canvas_label.config(image=self.tk_img)
        self._ensure_display()
        log(f"render 完成: {out_w}x{out_h}, 字級={font_size}, 段數={len(items)}")


# ==========================================
# Splash 視窗
# ==========================================
class SplashScreen:
    """啟動載入畫面（Toplevel，主視窗建完後自動關閉）"""

    def __init__(self, root):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)          # 無標題列
        self.win._lf_no_theme = True             # 標記：不受主題套用影響
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#1a1a2e")

        # ── 定位：置中於主視窗預計出現的位置 ──
        w, h = 420, 220
        main_w, main_h = 580, 900
        # 讀取上次儲存的主視窗座標（與 __init__ 邏輯一致）
        try:
            with open(KEY_FILE, "r", encoding="utf-8") as _f:
                _cfg = json.load(_f)
            mx = _cfg.get("main_win_x", None)
            my = _cfg.get("main_win_y", None)
        except Exception:
            mx, my = None, None
        if mx is None or my is None:
            # 無記錄：fallback 置中螢幕
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            mx, my = 0, 0
            main_w = sw
            main_h = sh
        x = mx + (main_w - w) // 2
        y = my + (main_h - h) // 2
        self.win.geometry(f"{w}x{h}+{x}+{y}")

        # ── 內容 ──
        tk.Label(
            self.win, text="LangForge", bg="#1a1a2e", fg="#50c8ff",
            font=("Arial", 28, "bold")
        ).pack(pady=(28, 2))

        tk.Label(
            self.win, text=ABOUT_VERSION, bg="#1a1a2e", fg="#aaaaaa",
            font=("Arial", 11)
        ).pack()

        tk.Frame(self.win, bg="#50c8ff", height=1).pack(fill="x", padx=30, pady=(14, 10))

        self._msg_var = tk.StringVar(value="初始化中..." if CURRENT_LANG != "en" else "Initializing...")
        tk.Label(
            self.win, textvariable=self._msg_var, bg="#1a1a2e", fg="#cccccc",
            font=("Arial", 10)
        ).pack()

        tk.Label(
            self.win, text="© 2026 GoOnSoft / Toya Kyo", bg="#1a1a2e", fg="#555566",
            font=("Arial", 8)
        ).pack(side="bottom", pady=10)

        self.win.update()

    def update_text(self, msg: str):
        """更新進度文字並強制重繪"""
        if self.win.winfo_exists():
            self._msg_var.set(msg)
            self.win.update()

    def close(self):
        if self.win.winfo_exists():
            self.win.destroy()


# ==========================================
# 啟動入口
# ==========================================
if __name__ == "__main__":
    # 設定 Per-Monitor DPI Aware，讓 Tkinter 直接用實體像素座標
    # 避免 Windows DPI 虛擬化造成 geometry() 座標不穩定
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    root = tk.Tk()
    root.withdraw()  # 先隱藏，避免未設定位置就閃現
    root.update_idletasks()  # 讓 DPI 設定生效後再建立 UI
    
    splash = SplashScreen(root)
    app = LangForgeApp(root, splash=splash)

    # 確保 splash 完全關閉後再顯示主視窗
    root.after(100, root.deiconify)  # ← 延遲 100ms 後顯示

    root.mainloop()