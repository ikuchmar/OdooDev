#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Точка входа. Запускает Tk-приложение Context Docs Viewer.
"""

import sys
import tkinter as tk
from ui_app import App

def main():
    initial = sys.argv[1] if len(sys.argv) > 1 else ""
    root = tk.Tk()
    app = App(root, initial_query=initial)
    root.mainloop()

if __name__ == "__main__":
    main()
