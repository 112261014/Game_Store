import socket
import json
import sys
import os
import time
import zipfile
import subprocess
import threading
import stat

sys.path.append(os.path.join(os.path.dirname(__file__), '..')) 

from common.util import send_json, recv_json, load_system_config, recv_file

# ================= 全域變數 =================
config = load_system_config()
SERVER_IP = config.get("HOST", "127.0.0.1")
SERVER_PORT = config.get("LOBBY_PORT", 8888)

client_socket = None
user_name = ""
curr_page = "Home"
current_room_id = None
is_host = False
download_base_path = os.path.join(os.path.dirname(__file__), "downloads")

# ================= 輔助 =================
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
        print(f"無法連線至 Server: {e}")
        return False

def get_local_game_version(game_id, game_name):
    folder_name = f"{game_id}_{game_name}"
    save_dir = os.path.join(download_base_path, user_name, folder_name)
    config_path = os.path.join(save_dir, "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("version", "0.0.0")
        except: pass
    return None

def set_read_only(path):
    for root, dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            os.chmod(file_path, stat.S_IREAD | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

# ================= 登入頁面 =================

def LoginPage():
    global user_name
    while True:
        clear_screen()
        print("=== 歡迎來到 Game Center (Player) ===")
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
                user_name = u
                print(f"登入成功！歡迎 {user_name}")
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

# ================= 頁面功能 =================

def Home():
    global curr_page
    clear_screen()
    print(f"=== Game Center (Player: {user_name}) ===")
    print("1. 瀏覽遊戲 (Game List) - 下載/評分")
    print("2. 瀏覽房間 (Room List)")
    print("3. 建立房間 (Create Room)")
    print("4. 離開 (Exit)")
    
    choice = get_input("> ")
    if choice == '1': curr_page = "GameList"
    elif choice == '2': curr_page = "RoomList"
    elif choice == '3': curr_page = "CreateRoom"
    elif choice == '4': sys.exit(0)

def GameList():
    global curr_page
    clear_screen()
    print("=== 遊戲列表 ===")
    send_json(client_socket, {"cmd": "list_games"})
    resp = recv_json(client_socket)
    if not resp or resp.get("status") != "ok":
        print("列表取得失敗")
        time.sleep(1)
        curr_page = "Home"
        return
    games = resp.get("games", [])
    for i, g in enumerate(games):
        print(f"{i+1}. {g['name']} (v{g['version']})")
    print("-" * 20)
    print("輸入編號查看詳情 (下載/評分)，'b' 返回")
    choice = get_input("> ")
    if choice == 'b':
        curr_page = "Home"
        return
    if choice.isdigit() and 1 <= int(choice) <= len(games):
        target = games[int(choice)-1]
        show_game_detail(target)
    else:
        print("無效輸入")
        time.sleep(1)

def show_game_detail(game_info):
    clear_screen()
    print(f"正在取得 {game_info['name']} 詳細資料...")
    send_json(client_socket, {"cmd": "get_game_detail", "game_id": game_info['id']})
    resp = recv_json(client_socket)
    if not resp or resp.get("status") != "ok":
        print("無法取得詳細資料")
        time.sleep(1)
        return
    d = resp.get("detail", {})
    print(f"=== {d['name']} (v{d['version']}) ===")
    print(f"作者: {d['dev_id']}")
    print(f"類型: {d['type']}")
    print(f"人數: {d['min_players']} - {d['max_players']} 人")
    print(f"評分: {d['avg_score']} ⭐ ({d['review_count']} 人評論)")
    print(f"簡介: {d['description']}")
    print("\n--- 最新評論 ---")
    comments = d.get("comments", [])
    if not comments: print("(暫無評論)")
    else:
        for c in comments: print(f"[{c['score']}⭐] {c['user']}: {c['comment']}")
    print("-" * 20)
    print("1. 下載 / 更新遊戲")
    print("2. 給予評分 (需玩過)")
    print("3. 返回列表")
    act = get_input("> ")
    if act == '1': process_download(d)
    elif act == '2': process_rate(d)
    else: return

def process_rate(detail):
    print(f"\n=== 評分: {detail['name']} ===")
    while True:
        score_str = get_input("請輸入分數 (1-5): ")
        if score_str.isdigit() and 1 <= int(score_str) <= 5:
            score = int(score_str)
            break
        print("輸入錯誤")
    comment = get_input("請輸入短評 (選填): ")
    req = {"cmd": "rate_game", "game_id": detail['id'], "player_name": user_name, "score": score, "comment": comment}
    send_json(client_socket, req)
    resp = recv_json(client_socket)
    if resp and resp.get("status") == "ok": print("✅ 評分成功！")
    else: print(f"❌ 評分失敗: {resp.get('reason') if resp else 'Unknown'}")
    input("按 Enter 繼續...")

def process_download(detail):
    game_id = detail['id']
    game_name = detail['name']
    server_ver = detail['version']
    local_ver = get_local_game_version(game_id, game_name)
    if local_ver:
        if local_ver == server_ver:
            print(f"⚠️ 遊戲已是最新版 (v{local_ver})，是否重新下載？ (y/n)")
            if get_input("> ").lower() != 'y': return
        else:
            print(f"發現新版本 (Local: {local_ver} -> Server: {server_ver})")
    folder_name = f"{game_id}_{game_name}"
    save_dir = os.path.join(download_base_path, user_name, folder_name)
    print(f"正在請求下載 {game_name} ...")
    send_json(client_socket, {"cmd": "download_game", "game_id": game_id})
    resp = recv_json(client_socket)
    if not resp or resp.get("status") != "ok":
        print(f"下載請求失敗: {resp.get('reason') if resp else 'Unknown'}")
        time.sleep(2)
        return
    temp_zip = "temp_game.zip"
    if recv_file(client_socket, temp_zip):
        print("檔案接收成功，正在安裝...")
        if os.path.exists(save_dir):
            for root, dirs, files in os.walk(save_dir):
                for f in files: os.chmod(os.path.join(root, f), stat.S_IWRITE)
            import shutil
            shutil.rmtree(save_dir)
        os.makedirs(save_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(temp_zip, 'r') as zf: zf.extractall(save_dir)
            set_read_only(save_dir)
            print(f"✅ 安裝完成 (唯讀)！位置: {save_dir}")
        except Exception as e: print(f"解壓縮/設定權限失敗: {e}")
        finally: 
            if os.path.exists(temp_zip): os.remove(temp_zip)
    else: print("檔案傳輸中斷")
    input("按 Enter 繼續...")

def RoomList():
    global curr_page, current_room_id, is_host
    clear_screen()
    print("=== 房間列表 ===")
    send_json(client_socket, {"cmd": "list_rooms"})
    resp = recv_json(client_socket)
    if resp is None:
        print("無法取得房間列表")
        time.sleep(1)
        curr_page = "Home"
        return
    rooms = resp.get("rooms", [])
    rooms_map = {} 
    if not rooms: print("目前沒有房間。")
    else:
        for idx, r in enumerate(rooms):
            print(f"{idx+1}. ID:{r['room_id']} | {r['game_name']} (v{r.get('version','?')}) | Host:{r['host']} ({r['players']})")
            rooms_map[str(idx+1)] = r
    print("-" * 20)
    print("輸入序號 (例如 1) 或 房間 ID 加入，'b' 返回")
    choice = get_input("> ")
    if choice == 'b':
        curr_page = "Home"
        return
    target_room = rooms_map.get(choice)
    if not target_room:
        for r in rooms:
            if str(r['room_id']) == choice:
                target_room = r
                break
    if target_room:
        room_id = target_room['room_id']
        game_name = target_room['game_name']
        local_ver = None
        user_dir = os.path.join(download_base_path, user_name)
        if os.path.exists(user_dir):
            for d in os.listdir(user_dir):
                if game_name in d: 
                    conf_path = os.path.join(user_dir, d, "config.json")
                    if os.path.exists(conf_path):
                        with open(conf_path,'r') as f:
                            c = json.load(f)
                            if c.get("game_name") == game_name:
                                local_ver = c.get("version")
                                break
        if not local_ver:
             print("❌ 找不到本地遊戲檔案，請先下載！")
             time.sleep(1)
             return
        send_json(client_socket, {"cmd": "join_room", "room_id": room_id, "player_name": user_name, "version": local_ver})
        resp = recv_json(client_socket)
        if resp and resp.get("status") == "ok":
            print("加入成功！")
            current_room_id = room_id
            is_host = False
            EnterRoom(resp.get("game_name"))
        else:
            print(f"加入失敗: {resp.get('reason') if resp else 'Error'}")
            time.sleep(2)
    else:
        print("無效輸入")
        time.sleep(1)

def CreateRoom():
    global curr_page, current_room_id, is_host
    clear_screen()
    print("=== 建立房間 ===")
    send_json(client_socket, {"cmd": "list_games"})
    resp = recv_json(client_socket)
    if resp is None: return
    games = resp.get("games", [])
    for i, g in enumerate(games):
        print(f"{i+1}. {g['name']} (v{g['version']})")
    print("選擇遊戲開房，'b' 返回")
    choice = get_input("> ")
    if choice == 'b':
        curr_page = "Home"
        return
    if choice.isdigit() and 1 <= int(choice) <= len(games):
        game = games[int(choice)-1]
        local_ver = get_local_game_version(game['id'], game['name'])
        if not local_ver:
            print("❌ 你尚未下載此遊戲，無法開房！")
            time.sleep(1)
            return
        send_json(client_socket, {"cmd": "create_room", "game_id": game['id'], "player_name": user_name, "version": local_ver})
        resp = recv_json(client_socket)
        if resp and resp.get("status") == "ok":
            current_room_id = resp['room_id']
            is_host = True
            print(f"房間建立成功 ID: {current_room_id}")
            EnterRoom(game['name'])
        else:
            print(f"建立失敗: {resp.get('reason') if resp else 'Unknown'}")
            time.sleep(3)

def EnterRoom(game_name_display):
    global curr_page
    print(f"\n--- 進入等待室 ({game_name_display}) ---")
    if is_host: print("你是房主。當人齊了請按 's' 開始遊戲，'q' 離開")
    else: print("等待房主開始遊戲... (按 Ctrl+C 輸入 'q' 離開)")
    room_loop()

def room_loop():
    global curr_page
    client_socket.settimeout(0.1)
    while True:
        try:
            try:
                chunk = client_socket.recv(4096).decode('utf-8')
                if chunk and '\n' in chunk:
                    msgs = chunk.strip().split('\n')
                    for m in msgs:
                        try: handle_room_message(json.loads(m))
                        except: pass
            except socket.timeout: pass
            except Exception as e:
                print(f"連線異常: {e}")
                curr_page = "Home"
                break
        except KeyboardInterrupt:
            if is_host:
                cmd = input("\n(s: Start, q: Quit): ").strip().lower()
                if cmd == 's':
                    send_json(client_socket, {"cmd": "start_game", "room_id": current_room_id})
                    print("已發送開始請求...")
                elif cmd == 'q':
                    send_json(client_socket, {"cmd": "leave_room", "room_id": current_room_id})
                    recv_json(client_socket) 
                    curr_page = "Home"
                    return
            else:
                cmd = input("\n(q: Quit): ").strip().lower()
                if cmd == 'q':
                    send_json(client_socket, {"cmd": "leave_room", "room_id": current_room_id})
                    recv_json(client_socket)
                    print("離開房間...")
                    curr_page = "Home"
                    return

def handle_room_message(msg):
    cmd = msg.get("cmd")
    if cmd == "room_update":
        print(f"\n[Room] 目前玩家: {msg['players']} ({msg['curr_count']}/{msg['max_count']})")
        if is_host: print("(按 Ctrl+C 輸入 's' 開始遊戲)")
    elif cmd == "game_started":
        print("\n---遊戲開始！啟動 Game Client---")
        # FIX: 使用 server 傳來的 game_id 與 game_name 來啟動正確遊戲
        launch_game(msg['game_server_ip'], msg['game_server_port'], msg['game_id'], msg['game_name'])
    elif cmd == "error":
        print(f"\n[Error] {msg.get('reason')}")

def launch_game(ip, port, game_id, game_name):
    """
    啟動遊戲
    修正：不再遍歷目錄，而是根據 game_id 和 game_name 直接定位資料夾
    """
    global curr_page
    
    # 組合出正確的資料夾名稱
    folder_name = f"{game_id}_{game_name}"
    target_dir = os.path.join(download_base_path, user_name, folder_name)
    
    target_script = None
    
    if os.path.exists(target_dir) and os.path.isdir(target_dir):
        conf_path = os.path.join(target_dir, "config.json")
        if os.path.exists(conf_path):
            try:
                with open(conf_path, 'r', encoding='utf-8') as f:
                    c = json.load(f)
                    script_name = c.get("client_entry", "game_client.py")
                    script_path = os.path.join(target_dir, script_name)
                    if os.path.exists(script_path):
                        target_script = script_path
            except Exception as e:
                print(f"讀取遊戲 Config 錯誤: {e}")
    
    if target_script:
        print(f"Executing: {target_script} --host {ip} --port {port}")
        client_socket.settimeout(None)
        try: 
            subprocess.run([sys.executable, target_script, "--host", ip, "--port", str(port)])
        except Exception as e: print(f"遊戲執行錯誤: {e}")
        finally: client_socket.settimeout(0.1)
    else:
        print(f"錯誤：找不到遊戲啟動檔。請確認已下載遊戲 {game_name} (ID: {game_id})")
        # 這裡不拋出 GameFinished，讓使用者留在房間內看錯誤訊息? 
        # 或者直接返回房間等待下一場
        # 我們選擇直接返回房間 Loop
        pass

    print("遊戲結束，返回房間。")
    if is_host: print("(房主按 Ctrl+C 輸入 's' 再來一場，或輸入 'q' 離開)")
    else: print("等待房主開始下一場... (按 Ctrl+C 輸入 'q' 離開)")
    return

def start():
    global curr_page
    if not connect_server(): return
    LoginPage()
    try:
        while True:
            try:
                if curr_page == "Home": Home()
                elif curr_page == "GameList": GameList()
                elif curr_page == "RoomList": RoomList()
                elif curr_page == "CreateRoom": CreateRoom()
            except Exception as e:
                if str(e) == "GameFinished":
                    curr_page = "Home"
                    continue
                print(f"Client Error: {e}")
                break
    finally:
        if client_socket and current_room_id:
            try: send_json(client_socket, {"cmd": "leave_room", "room_id": current_room_id})
            except: pass
        if client_socket:
            client_socket.close()

if __name__ == '__main__':
    start()