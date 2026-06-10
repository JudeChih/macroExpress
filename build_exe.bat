@echo off
chcp 65001 >nul
title 打包 全自動按鍵 -^> 單一 exe
cd /d "%~dp0"

echo ============================================
echo   全自動多開按鍵觸發器  一鍵打包為 .exe
echo ============================================
echo.

REM --- 確認 Python 是否存在 ---
where python >nul 2>nul
if errorlevel 1 (
    echo [錯誤] 找不到 Python，請先安裝 Python 3 並勾選 "Add to PATH"。
    pause
    exit /b 1
)

echo [1/3] 安裝/更新依賴套件 (pyinstaller, pynput)...
python -m pip install --upgrade pip >nul
python -m pip install pyinstaller pynput
echo.

echo [2/3] 開始打包 (--onefile --noconsole)...
REM --noconsole：執行時不顯示命令提示字元視窗
REM --onefile  ：打包成單一 exe 檔案
REM hidden-import：確保 pynput 的 Windows 依賴正確打包
python -m PyInstaller --noconfirm --clean --onefile --noconsole ^
    --name "全自動按鍵" ^
    --hidden-import pynput.keyboard._win32 ^
    --hidden-import pynput.mouse._win32 ^
    macro_clicker.py

if errorlevel 1 (
    echo.
    echo [錯誤] 打包失敗，請往上捲動查看錯誤訊息。
    pause
    exit /b 1
)

echo.
echo [3/3] 打包完成！
echo   生成的執行檔： dist\全自動按鍵.exe
echo   可直接複製到其他 Windows 電腦執行（不需安裝 Python）。
echo   注意：settings.json 會自動生成在 exe 同目錄，用來記憶設定。
echo.
pause
