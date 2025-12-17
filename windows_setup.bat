@echo off
REM 設定編碼為 UTF-8 以顯示中文
chcp 65001 > nul
setlocal

echo ==========================================
echo   Game Store Platform 自動化安裝腳本 (Windows)
echo ==========================================

REM 1. 檢查 Python 是否安裝
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 python 指令。
    echo 請確保已安裝 Python 並且勾選了 "Add Python to PATH"。
    pause
    exit /b
)

for /f "delims=" %%i in ('python --version') do set PYTHON_VER=%%i
echo [資訊] 使用 Python: %PYTHON_VER%

REM 2. 建立虛擬環境 (venv)
if exist "venv" (
    echo [資訊] 虛擬環境 (venv) 已存在，跳過建立步驟。
) else (
    echo [資訊] 正在建立虛擬環境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [錯誤] 虛擬環境建立失敗。
        pause
        exit /b
    )
    echo [成功] 虛擬環境建立完成。
)

REM 3. 啟用虛擬環境並安裝依賴
echo [資訊] 正在安裝相依套件 (requirements.txt)...
call venv\Scripts\activate.bat

if exist "requirements.txt" (
    pip install -r requirements.txt
) else (
    echo [警告] 找不到 requirements.txt，跳過套件安裝。
)

REM 4. 初始化資料庫
echo [資訊] 正在初始化資料庫...
python -m server.db_manager
if %errorlevel% neq 0 (
    echo [錯誤] 資料庫初始化失敗。
) else (
    echo [成功] 資料庫初始化成功 (game_store.db)
)

REM 5. 建立必要的資料夾
echo [資訊] 正在檢查並建立目錄結構...
if not exist "server\storage" mkdir "server\storage"
if not exist "player_client\downloads" mkdir "player_client\downloads"
if not exist "dev_client\games" mkdir "dev_client\games"

echo.
echo ==========================================
echo        安裝完成！ (Setup Complete)
echo ==========================================
echo.
echo 請依照以下步驟啟動系統 (建議開啟 4 個終端機視窗)：
echo 注意：每個視窗都需要先執行 `venv\Scripts\activate`
echo.
echo 1. 啟動 Developer Server (後端)
echo    venv\Scripts\activate ^& python -m server.dev_server
echo.
echo 2. 啟動 Lobby Server (後端)
echo    venv\Scripts\activate ^& python -m server.lobby_server
echo.
echo 3. 啟動 Developer Client (開發者)
echo    venv\Scripts\activate ^& python -m dev_client.developer_client
echo.
echo 4. 啟動 Player Client (玩家)
echo    venv\Scripts\activate ^& python -m player_client.lobby_client
echo.
echo 祝 Demo 順利！
pause