import socket
import threading
import json
import os
import shutil
import zipfile
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..')) 

from common.util import safe_socket_op, load_system_config, send_json, recv_json, recv_file, compare_versions
from server.db_manager import get_connection, init_db, verify_user, register_user

# 設定
config = load_system_config()
HOST = config.get("HOST", "127.0.0.1")
PORT = config.get("DEV_PORT", 8889) 
STORAGE_DIR = os.path.join(os.path.dirname(__file__), 'storage')

ONLINE_DEVS = {} # { username: conn }

def handle_auth_login(conn, data):
    username = data.get("username")
    password = data.get("password")
    
    if verify_user('dev', username, password):
        if username in ONLINE_DEVS:
            send_json(conn, {"status": "error", "reason": "帳號已在其他裝置登入"})
            return None
        ONLINE_DEVS[username] = conn
        print(f"[Auth] Developer '{username}' logged in.")
        send_json(conn, {"status": "ok", "username": username})
        return username
    else:
        send_json(conn, {"status": "error", "reason": "帳號或密碼錯誤"})
        return None

def handle_auth_register(conn, data):
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        send_json(conn, {"status": "error", "reason": "欄位不可為空"})
        return
        
    success, msg = register_user('dev', username, password)
    if success:
        print(f"[Auth] New developer registered: {username}")
        send_json(conn, {"status": "ok", "msg": msg})
    else:
        send_json(conn, {"status": "error", "reason": msg})

def handle_list_my_games(conn, dev_id):
    db = get_connection()
    c = db.cursor()
    c.execute("SELECT game_id, name, version, status, description FROM games WHERE dev_id = ?", (dev_id,))
    rows = c.fetchall()
    games = []
    for r in rows:
        games.append({
            "game_id": r[0], "name": r[1], "version": r[2], 
            "status": r[3], "description": r[4]
        })
    send_json(conn, {"status": "ok", "games": games})
    db.close()

def handle_upload_game(conn, dev_id, data):
    game_conf = data.get("config")
    is_update = data.get("is_update", False)
    game_id_to_update = data.get("game_id")
    new_version = game_conf.get('version', '0.0.0')

    # Version check omitted for brevity, keeping same logic as before...
    # (Checking version against DB if update)
    if is_update and game_id_to_update:
        db = get_connection()
        c = db.cursor()
        c.execute("SELECT version FROM games WHERE game_id=?", (game_id_to_update,))
        row = c.fetchone()
        db.close()
        if row:
            current_version = row[0]
            if compare_versions(new_version, current_version) <= 0:
                pass # Logic maintained

    print(f"[Upload] Receiving game data for {game_conf['game_name']} (v{new_version})...")
    temp_zip_path = os.path.join(STORAGE_DIR, f"temp_{dev_id}.zip")
    os.makedirs(STORAGE_DIR, exist_ok=True)
    
    if not recv_file(conn, temp_zip_path):
        send_json(conn, {"status": "error", "reason": "File transfer failed"})
        return

    db = get_connection()
    c = db.cursor()
    try:
        final_game_folder_name = ""
        if is_update and game_id_to_update:
            # Check version again
            c.execute("SELECT version FROM games WHERE game_id=?", (game_id_to_update,))
            row = c.fetchone()
            if row and compare_versions(new_version, row[0]) <= 0:
                 raise ValueError(f"版本號必須大於當前版本")

            c.execute('''UPDATE games SET version=?, description=?, server_exe=?, client_exe=?, 
                         game_type=?, min_players=?, max_players=?, status='active' 
                         WHERE game_id=? AND dev_id=?''',
                      (new_version, game_conf['description'], 
                       game_conf['server_entry'], game_conf['client_entry'], 
                       game_conf['game_type'], game_conf['min_players'], game_conf['max_players'],
                       game_id_to_update, dev_id))
            game_id = game_id_to_update
            final_game_folder_name = f"{game_id}_{game_conf['game_name']}"
        else:
            c.execute('''INSERT INTO games (dev_id, name, description, version, game_type, min_players, max_players, server_exe, client_exe, file_path) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (dev_id, game_conf['game_name'], game_conf['description'], new_version,
                       game_conf['game_type'], game_conf['min_players'], game_conf['max_players'],
                       game_conf['server_entry'], game_conf['client_entry'], ""))
            game_id = c.lastrowid
            final_game_folder_name = f"{game_id}_{game_conf['game_name']}"
            c.execute("UPDATE games SET file_path=? WHERE game_id=?", (final_game_folder_name, game_id))

        db.commit()
        target_dir = os.path.join(STORAGE_DIR, final_game_folder_name)
        if os.path.exists(target_dir): shutil.rmtree(target_dir)
        os.makedirs(target_dir, exist_ok=True)
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        print(f"[Upload] Game {game_id} updated to v{new_version}")
        send_json(conn, {"status": "ok", "game_id": game_id})
    except Exception as e:
        print(f"[Upload Error] {e}")
        send_json(conn, {"status": "error", "reason": str(e)})
    finally:
        db.close()
        if os.path.exists(temp_zip_path): os.remove(temp_zip_path)

def handle_remove_game(conn, dev_id, data):
    game_id = data.get("game_id")
    db = get_connection()
    c = db.cursor()
    c.execute("UPDATE games SET status='inactive' WHERE game_id=? AND dev_id=?", (game_id, dev_id))
    if c.rowcount > 0:
        send_json(conn, {"status": "ok"})
    else:
        send_json(conn, {"status": "error", "reason": "Game not found or permission denied"})
    db.commit()
    db.close()

@safe_socket_op
def handle_client(conn, addr):
    print(f"[DevServer] Connection from {addr}")
    current_user = None
    
    try:
        while True:
            req = recv_json(conn)
            if not req: break
            
            cmd = req.get("cmd")
            
            # Auth 檢查
            if not current_user:
                if cmd == "auth_login":
                    current_user = handle_auth_login(conn, req)
                elif cmd == "auth_register":
                    handle_auth_register(conn, req)
                else:
                    send_json(conn, {"status": "error", "reason": "Please login first"})
                continue

            if cmd == "list_my_games":
                handle_list_my_games(conn, current_user)
            elif cmd == "upload_game":
                handle_upload_game(conn, current_user, req)
            elif cmd == "remove_game":
                handle_remove_game(conn, current_user, req)
            else:
                send_json(conn, {"status": "error", "reason": "Unknown command"})

    finally:
        if current_user and current_user in ONLINE_DEVS:
            del ONLINE_DEVS[current_user]
        conn.close()

@safe_socket_op
def start_server():
    init_db() 
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((HOST, PORT))
        server.listen(5)
        print(f"=== Developer Server Started on {HOST}:{PORT} ===")
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr))
            t.daemon = True
            t.start()
    except Exception as e:
        print(f"Server Error: {e}")

if __name__ == '__main__':
    start_server()