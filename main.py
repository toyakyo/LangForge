"""
LangForge 應用執行入口
版本：V1.0.1-beta.5
執行命令：python main.py
"""

import sys
import ctypes
from pathlib import Path

# 確保可以導入 langforge 模組
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))


def setup_dpi_awareness():
    """設定 Windows DPI 識別（Tkinter 必需）"""
    try:
        if sys.platform == "win32":
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception as e:
        print(f"警告：DPI 設定失敗：{e}")


def main():
    """應用主入口"""
    try:
        # DPI 設定
        setup_dpi_awareness()
        
        # 導入並啟動應用
        from langforge.core.langforge import LangForgeApp
        import tkinter as tk
        
        root = tk.Tk()
        app = LangForgeApp(root)
        root.mainloop()
    
    except ImportError as e:
        print(f"❌ 導入錯誤：{e}")
        print("請確認 langforge/core/langforge.py 是否存在")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 發生錯誤：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
