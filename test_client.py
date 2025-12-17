curr_page = "Home"
viewing_game = ""
room_id = 0

def Home():
    #選單輸入list game, list room or create room，更新curr_page
    return

def Game_list():
    #跟lobby要求現在上架的遊戲列出，也可返回home，或調整viewing_game進入download_game

def Download_game():
    #跟lobby要求game info、評分，並詢問是否下載

def RoomList():
    #跟lobby要求在線房間編號，房間遊戲，以及房間內玩家，使用者可以選擇一個加入

def EnterRoom():
    #可以隨時退出，或等待遊戲開始，有新玩家要顯示資訊，如果房間遊戲還沒下載要強制退出
    #用房間的game_server的host, port加入遊戲

def CreateRoom():
    #列出本地遊戲，選擇一個遊戲後開房間，
    #跟lobby要求一個新房號以及一組game_server的host, port，等待使用者按下開始

def start():
    while True :
        if curr_page == "Home":
            Home()
        elif curr_page == "GameList":
            GameList()
        elif curr_page == "RoomList":
            RoomList()
        elif curr_page == "CreateRoom":
            CreateRoom()
        elif curr_page == "EnterRoom":
            EnterRoom()
        elif curr_page == "DownloadGame":
            DownloadGame()
            