"""
LangForge V1.0.1-beta.7
應用程式入口點
"""

import sys
import os

# 添加 langforge 模組到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # 從 langforge.core.langforge 導入所有必要的模組和類別
    import tkinter as tk
    import ctypes
    from langforge.core.langforge import (
        SplashScreen,
        LangForgeApp,
        CURRENT_LANG,
    )
    
    # 設定 Per-Monitor DPI Aware
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    
    # 建立主視窗
    root = tk.Tk()
    root.withdraw()  # 先隱藏
    root.update_idletasks()
    
    # 建立 Splash 和應用程式
    splash = SplashScreen(root)
    app = LangForgeApp(root, splash=splash)
    
    # 啟動主迴圈
    root.mainloop()