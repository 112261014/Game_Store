#!/bin/bash

# 定義顏色，讓輸出更美觀
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${CYAN}=== Game Store Platform 自動化安裝腳本 ===${NC}"

# 1. 檢查 Python 是否安裝
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo -e "${YELLOW}錯誤: 找不到 python3 或 python 指令，請先安裝 Python。${NC}"
    exit 1
fi

echo -e "${GREEN}使用 Python: $($PYTHON_CMD --version)${NC}"

# 2. 建立虛擬環境 (venv)
VENV_DIR="venv"
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}虛擬環境 ($VENV_DIR) 已存在，跳過建立步驟。${NC}"
else
    echo -e "${CYAN}正在建立虛擬環境...${NC}"
    $PYTHON_CMD -m venv $VENV_DIR
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}虛擬環境建立成功！${NC}"
    else
        echo -e "${YELLOW}虛擬環境建立失敗，請檢查 python venv 模組。${NC}"
        exit 1
    fi
fi

# 3. 啟用虛擬環境並安裝依賴
echo -e "${CYAN}正在安裝相依套件 (requirements.txt)...${NC}"
source $VENV_DIR/bin/activate

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo -e "${YELLOW}找不到 requirements.txt，跳過套件安裝 (假設使用標準函式庫)。${NC}"
fi

# 4. 初始化資料庫
echo -e "${CYAN}正在初始化資料庫...${NC}"
python -m server.db_manager
if [ $? -eq 0 ]; then
    echo -e "${GREEN}資料庫初始化成功 (game_store.db)${NC}"
else
    echo -e "${YELLOW}資料庫初始化失敗。${NC}"
fi

# 5. 建立必要的資料夾
echo -e "${CYAN}正在檢查並建立目錄結構...${NC}"
mkdir -p server/storage
mkdir -p player_client/downloads
mkdir -p dev_client/games

echo -e "${GREEN}=== 安裝完成！ ===${NC}"
echo -e ""
echo -e "請依照以下步驟啟動系統 (建議開啟 4 個終端機視窗)："
echo -e ""
echo -e "1. ${YELLOW}啟動 Developer Server (後端)${NC}"
echo -e "   source venv/bin/activate && python -m server.dev_server"
echo -e ""
echo -e "2. ${YELLOW}啟動 Lobby Server (後端)${NC}"
echo -e "   source venv/bin/activate && python -m server.lobby_server"
echo -e ""
echo -e "3. ${YELLOW}啟動 Developer Client (開發者)${NC}"
echo -e "   source venv/bin/activate && python -m dev_client.developer_client"
echo -e ""
echo -e "4. ${YELLOW}啟動 Player Client (玩家)${NC}"
echo -e "   source venv/bin/activate && python -m player_client.lobby_client"
echo -e ""
echo -e "${CYAN}祝 Demo 順利！${NC}"