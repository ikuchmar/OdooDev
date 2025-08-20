# -*- coding: utf-8 -*-
"""
app_main.py — точка входа.
Запускает графический интерфейс из tools/ui_app.py
"""

from tools.ui_app import App_UI

def main():
    app = App_UI()
    app.mainloop()

if __name__ == "__main__":
    main()
