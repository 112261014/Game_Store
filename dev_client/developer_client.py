import socket
import json
import sys
import os
import time
import zipfile
import shutil

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from common.util import send_json, recv_json, load_system_config, send_file

# ================= 全域變數 =================
config = load_system_config()
SERVER_IP = config.get("HOST", "127.0.0.1")
SERVER_PORT = config.get("DEV_PORT", 8889)

client_socket = None
curr_page = "Home"
user_id = ""

GAMES_DIR = os.path.join(os.path.dirname(__file__), 'games')

# ================= 輔助函式 =================
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_input(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        sys.exit(0)

def connect_server():
    global client_socket
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((SERVER_IP, SERVER_PORT))
        return True
    except Exception as e:
        print(f"無法連線至 Dev Server ({SERVER_IP}:{SERVER_PORT}): {e}")
        return False

def zip_game_folder(folder_path, output_path):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.pyc') or file == '.DS_Store' or '__pycache__' in root:
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)

# ================= 登入頁面 =================

def LoginPage():
    global user_id
    while True:
        clear_screen()
        print("=== Developer Console (Login) ===")
        print("1. 登入 (Login)")
        print("2. 註冊 (Register)")
        print("3. 離開 (Exit)")
        
        choice = get_input("> ")
        if choice == '3': sys.exit(0)
        
        if choice == '1':
            u = get_input("帳號: ")
            p = get_input("密碼: ")
            send_json(client_socket, {"cmd": "auth_login", "username": u, "password": p})
            resp = recv_json(client_socket)
            if resp and resp.get("status") == "ok":
                user_id = u
                print(f"登入成功！")
                time.sleep(1)
                return 
            else:
                print(f"登入失敗: {resp.get('reason') if resp else 'Server Error'}")
                input("按 Enter 重試...")
                
        elif choice == '2':
            u = get_input("設定帳號: ")
            p = get_input("設定密碼: ")
            send_json(client_socket, {"cmd": "auth_register", "username": u, "password": p})
            resp = recv_json(client_socket)
            if resp and resp.get("status") == "ok":
                print("註冊成功！請進行登入。")
            else:
                print(f"註冊失敗: {resp.get('reason') if resp else 'Server Error'}")
            input("按 Enter 繼續...")

# ================= 頁面邏輯 =================

def Home():
    global curr_page
    clear_screen()
    print(f"=== Developer Console ({user_id}) ===")
    print("1. 本地遊戲列表 (準備上架) - List Local")
    print("2. 遠端管理 (更新/下架) - List Remote")
    print("3. 離開")
    
    choice = get_input("選擇 > ")
    if choice == '1': curr_page = "ListLocal"
    elif choice == '2': curr_page = "ListRemote"
    elif choice == '3': sys.exit(0)

def ListLocal():
    global curr_page
    clear_screen()
    print("=== 本地開發中遊戲 (games/) ===")
    
    if not os.path.exists(GAMES_DIR):
        os.makedirs(GAMES_DIR)
        
    local_games = [d for d in os.listdir(GAMES_DIR) if os.path.isdir(os.path.join(GAMES_DIR, d))]
    
    if not local_games:
        print("沒有找到遊戲專案。請先執行 create_game_template.py 建立。")
        input("按 Enter 返回...")
        curr_page = "Home"
        return

    for idx, g in enumerate(local_games):
        print(f"{idx+1}. {g}")
        
    print("-" * 20)
    print("輸入編號進行上架 (Upload)，'b' 返回")
    
    choice = get_input("選擇 > ")
    if choice == 'b':
        curr_page = "Home"
        return
        
    if choice.isdigit() and 1 <= int(choice) <= len(local_games):
        game_folder = local_games[int(choice)-1]
        process_upload(game_folder)
    else:
        print("無效輸入")
        time.sleep(1)

def process_upload(folder_name, is_update=False, game_id=None):
    full_path = os.path.join(GAMES_DIR, folder_name)
    config_path = os.path.join(full_path, "config.json")
    
    if not os.path.exists(config_path):
        print(f"錯誤：找不到 config.json 於 {folder_name}")
        input("按 Enter 繼續...")
        return
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            game_config = json.load(f)
        req_fields = ["game_name", "version", "server_entry", "client_entry"]
        for field in req_fields:
            if field not in game_config:
                print(f"Config 缺少必要欄位: {field}")
                input("按 Enter 繼續...")
                return
    except json.JSONDecodeError:
        print("Config 格式錯誤 (非有效 JSON)")
        input("按 Enter 繼續...")
        return

    print(f"正在打包遊戲 '{folder_name}' ...")
    zip_filename = "temp_upload.zip"
    zip_game_folder(full_path, zip_filename)
    
    print("正在上傳中...")
    req = {
        "cmd": "upload_game",
        "config": game_config,
        "is_update": is_update,
        "game_id": game_id
    }
    send_json(client_socket, req)
    
    if send_file(client_socket, zip_filename):
        resp = recv_json(client_socket)
        if resp and resp.get("status") == "ok":
            print(f"上架/更新成功！ Game ID: {resp.get('game_id')}")
        else:
            print(f"失敗: {resp.get('reason')}")
    else:
        print("檔案傳輸失敗")
        
    if os.path.exists(zip_filename):
        os.remove(zip_filename)
    input("按 Enter 繼續...")
    global curr_page
    curr_page = "Home"

def ListRemote():
    global curr_page
    clear_screen()
    print("=== 遠端已上架遊戲 ===")
    send_json(client_socket, {"cmd": "list_my_games"})
    resp = recv_json(client_socket)
    if not resp or resp.get("status") != "ok":
        print("無法取得列表")
        curr_page = "Home"
        return
    games = resp.get("games", [])
    if not games: print("你還沒有上架任何遊戲。")
    for idx, g in enumerate(games):
        status_str = " (已下架)" if g['status'] == 'inactive' else ""
        print(f"{idx+1}. [{g['game_id']}] {g['name']} v{g['version']}{status_str}")
    print("-" * 20)
    print("輸入編號管理遊戲，'b' 返回")
    choice = get_input("選擇 > ")
    if choice == 'b':
        curr_page = "Home"
        return
    if choice.isdigit() and 1 <= int(choice) <= len(games):
        target_game = games[int(choice)-1]
        manage_remote_game(target_game)
    else:
        print("無效輸入")
        time.sleep(1)

def manage_remote_game(game_info):
    clear_screen()
    print(f"正在管理: {game_info['name']} (ID: {game_info['game_id']})")
    print("1. 更新遊戲 (上傳本地新版本)")
    print("2. 下架遊戲 (Remove)")
    print("3. 返回")
    choice = get_input("選擇 > ")
    if choice == '1':
        print("請輸入本地對應的資料夾名稱 (位於 games/ 下):")
        folder = get_input("> ")
        full_path = os.path.join(GAMES_DIR, folder)
        if os.path.exists(full_path) and os.path.isdir(full_path):
            process_upload(folder, is_update=True, game_id=game_info['game_id'])
        else:
            print("找不到該資料夾。")
            input("按 Enter...")
    elif choice == '2':
        confirm = get_input("確定要下架嗎? (y/n): ")
        if confirm.lower() == 'y':
            send_json(client_socket, {"cmd": "remove_game", "game_id": game_info['game_id']})
            resp = recv_json(client_socket)
            if resp.get("status") == "ok": print("下架成功。")
            else: print(f"下架失敗: {resp.get('reason')}")
            input("按 Enter...")

def start():
    global user_id
    global curr_page
    if not connect_server(): return
    
    # 登入
    LoginPage()

    while True:
        try:
            if curr_page == "Home": Home()
            elif curr_page == "ListLocal": ListLocal()
            elif curr_page == "ListRemote": ListRemote()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            input("Recovering...")
            curr_page = "Home"

    client_socket.close()

if __name__ == '__main__':
    start()