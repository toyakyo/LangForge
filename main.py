"""
LangForge V1.5.2
應用程式入口點
"""

import sys
import os
import importlib.util
import tkinter as tk
import ctypes

# 直接載入 langforge.py
LANGFORGE_PATH = os.path.join(os.path.dirname(__file__), 'langforge', 'core', 'langforge.py')
spec = importlib.util.spec_from_file_location("langforge_module", LANGFORGE_PATH)
lf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lf)

if __name__ == "__main__":
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
    splash = lf.SplashScreen(root)
    app = lf.LangForgeApp(root, splash=splash)
    
    # 啟動主迴圈
    root.mainloop()