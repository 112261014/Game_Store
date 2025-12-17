import socket
import json
import sys
import os
import time

# 引入共用工具
from common.util import send_json, recv_json, load_system_config

# ================= 全域變數 =================
config = load_system_config()

curr_page = "Home"

def Home():
    #選擇list local or list remote

def ListLocal():
    #從dev_client/games/列出所有資料夾名稱，選擇一個upload，注意這裡要檢查上傳格式：
    #格式例如，要有game_server.py以及game_client.py，
    # 為了lobby可以指定--host --port，game_server.py main argument要包括--host --port，或是要在config列出lobby可以修改的位置
    # config必須包括：遊戲名稱, 版本號, 簡短介紹或描述, 遊戲類型（CLI / GUI / 人數上限等）, game_server.py以及game_client.py得實際啟動檔名稱
    # dev_server要將remote存檔在./server/storage，同時將必要資訊存入./server/db

def ListRemote():
    #列出該創作者的所有remote作品，選擇後可以update or remove，注意update 選擇local file同樣要檢查格式
    #remove後要讓lobby端可以擋住已下載的player

def start():
    global curr_page

    #先登入開發者帳號

    while True:
        if curr_page == "Home":
            Home()
        elif curr_page == "ListLocal":
            ListLocal()
        elif curr_page == "ListRemote":
            ListRemote()


if __name__ == '__main__':
    start()