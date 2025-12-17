import socket
import threading
import json
import time
import sys
import os
import subprocess
import shutil

sys.path.append(os.path.join(os.path.dirname(__file__), '..')) 

from common.util import safe_socket_op, load_system_config, send_json, recv_json, send_file, compare_versions
from server.db_manager import get_connection, verify_user, register_user

# ================= 設定區 =================
config = load_system_config()
HOST = config.get("HOST", "127.0.0.1")
PORT = config.get("LOBBY_PORT", 8888)
STORAGE_DIR = os.path.join(os.path.dirname(__file__), 'storage')

# ================= 全域變數 =================
CLIENTS = {}   
ROOMS = {}      
ACTIVE_GAMES = {} 
ONLINE_PLAYERS = {} 

FREE_PORTS = list(range(9000, 9100))
USED_PORTS = set()
LOCK = threading.RLock()

def get_free_port():
    with LOCK:
        if not FREE_PORTS: return None
        port = FREE_PORTS.pop(0)
        USED_PORTS.add(port)
        return port

def release_port(port):
    with LOCK:
        if port in USED_PORTS:
            USED_PORTS.remove(port)
            FREE_PORTS.append(port)
            FREE_PORTS.sort()

# ================= 資料庫輔助 =================
def get_game_info(game_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT game_id, name, version, description, game_type, min_players, max_players, file_path, status, dev_id FROM games WHERE game_id=?", (game_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "game_id": row[0], "name": row[1], "version": row[2], 
            "description": row[3], "type": row[4], "min_players": row[5], 
            "max_players": row[6], "file_path": row[7], "status": row[8],
            "dev_id": row[9]
        }
    return None

def get_game_file_path(game_id):
    info = get_game_info(game_id)
    if info:
        folder_name = info['file_path']
        full_path = os.path.join(STORAGE_DIR, folder_name)
        return full_path
    return None

def record_play_history(game_id, player_names):
    if not player_names: return
    conn = get_connection()
    c = conn.cursor()
    try:
        data = [(game_id, pname) for pname in player_names]
        c.executemany("INSERT INTO play_history (game_id, player_id) VALUES (?, ?)", data)
        conn.commit()
    except Exception as e:
        print(f"[History Error] {e}")
    finally:
        conn.close()

# ================= Auth 邏輯 =================

def handle_auth_login(conn, data):
    username = data.get("username")
    password = data.get("password")
    if verify_user('player', username, password):
        with LOCK:
            if username in ONLINE_PLAYERS:
                send_json(conn, {"status": "error", "reason": "帳號已在其他裝置登入"})
                return None
            ONLINE_PLAYERS[username] = conn
        print(f"[Auth] Player '{username}' logged in.")
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
    success, msg = register_user('player', username, password)
    if success:
        print(f"[Auth] New player registered: {username}")
        send_json(conn, {"status": "ok", "msg": msg})
    else:
        send_json(conn, {"status": "error", "reason": msg})

# ================= 遊戲邏輯 =================

def handle_list_games(conn):
    db = get_connection()
    c = db.cursor()
    c.execute("SELECT game_id, name, version, description, min_players, max_players FROM games WHERE status='active'")
    rows = c.fetchall()
    db.close()
    games = []
    for r in rows:
        games.append({
            "id": r[0], "name": r[1], "version": r[2], 
            "info": r[3], "min": r[4], "max": r[5]
        })
    send_json(conn, {"status": "ok", "games": games})

def handle_get_game_detail(conn, data):
    game_id = data.get("game_id")
    info = get_game_info(game_id)
    if not info:
        send_json(conn, {"status": "error", "reason": "Game not found"})
        return
    db = get_connection()
    c = db.cursor()
    c.execute("SELECT AVG(score), COUNT(*) FROM reviews WHERE game_id=?", (game_id,))
    row = c.fetchone()
    avg_score = row[0] if row[0] is not None else 0.0
    review_count = row[1]
    c.execute("SELECT player_id, score, comment, timestamp FROM reviews WHERE game_id=? ORDER BY timestamp DESC LIMIT 5", (game_id,))
    rows = c.fetchall()
    comments = []
    for r in rows:
        comments.append({"user": r[0], "score": r[1], "comment": r[2], "date": r[3]})
    db.close()
    detail = {
        "id": info['game_id'], "name": info['name'], "version": info['version'],
        "description": info['description'], "dev_id": info['dev_id'], "type": info['type'],
        "min_players": info['min_players'], "max_players": info['max_players'],
        "avg_score": round(avg_score, 1), "review_count": review_count, "comments": comments
    }
    send_json(conn, {"status": "ok", "detail": detail})

def handle_rate_game(conn, data):
    game_id = data.get("game_id")
    player_name = data.get("player_name")
    score = data.get("score")
    comment = data.get("comment", "")
    if not (1 <= score <= 5):
        send_json(conn, {"status": "error", "reason": "分數必須在 1-5 之間"})
        return
    db = get_connection()
    c = db.cursor()
    c.execute("SELECT COUNT(*) FROM play_history WHERE game_id=? AND player_id=?", (game_id, player_name))
    if c.fetchone()[0] == 0:
        db.close()
        send_json(conn, {"status": "error", "reason": "未玩過此遊戲，無法評分！"})
        return
    try:
        c.execute("INSERT INTO reviews (game_id, player_id, score, comment) VALUES (?, ?, ?, ?)", (game_id, player_name, score, comment))
        db.commit()
        send_json(conn, {"status": "ok"})
    except Exception as e:
        send_json(conn, {"status": "error", "reason": str(e)})
    finally:
        db.close()

def handle_download_game(conn, data):
    game_id = data.get("game_id")
    game_path = get_game_file_path(game_id)
    if not game_path or not os.path.exists(game_path):
        send_json(conn, {"status": "error", "reason": "Game files not found on server"})
        return
    print(f"[Download] Preparing download for Game {game_id}...")
    import zipfile
    temp_zip = f"temp_download_{game_id}.zip"
    try:
        with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(game_path):
                for file in files:
                    if file == "server_config.json" or file.endswith(".pyc"): continue
                    abs_file = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_file, game_path)
                    zf.write(abs_file, rel_path)
        send_json(conn, {"status": "ok", "game_id": game_id})
        send_file(conn, temp_zip)
    except Exception as e:
        send_json(conn, {"status": "error", "reason": str(e)})
    finally:
        if os.path.exists(temp_zip): os.remove(temp_zip)

def handle_create_room(conn, data, addr, current_user):
    game_id = data.get("game_id")
    player_name = current_user 
    client_version = data.get("version")
    
    game_info = get_game_info(game_id)
    if not game_info or game_info['status'] != 'active':
        send_json(conn, {"status": "error", "reason": "Game not available"})
        return
    server_version = game_info['version']
    if not client_version or compare_versions(client_version, server_version) < 0:
        send_json(conn, {"status": "error", "reason": f"版本過舊 (需 v{server_version})，請重新下載！"})
        return

    with LOCK:
        import random
        room_id = str(random.randint(100000, 999999))
        while room_id in ROOMS:
            room_id = str(random.randint(100000, 999999))
        ROOMS[room_id] = {
            "room_id": room_id, "game_id": game_id, "game_name": game_info['name'],
            "game_version": server_version, "game_path": game_info['file_path'],
            "host_conn": conn, "host_name": player_name,
            "players": [{"name": player_name, "conn": conn}],
            "status": "waiting", "min_players": game_info['min_players'], "max_players": game_info['max_players']
        }
    print(f"[Room] Created Room {room_id} for {game_info['name']}")
    send_json(conn, {"status": "ok", "room_id": room_id})

def handle_join_room(conn, data, current_user):
    room_id = data.get("room_id")
    player_name = current_user
    client_version = data.get("version")
    
    with LOCK:
        if room_id not in ROOMS:
            send_json(conn, {"status": "error", "reason": "Room not found"})
            return
        room = ROOMS[room_id]
        if room['status'] != 'waiting':
            send_json(conn, {"status": "error", "reason": "Game already started"})
            return
        if len(room['players']) >= room['max_players']:
            send_json(conn, {"status": "error", "reason": "Room is full"})
            return
        room_version = room.get('game_version', '0.0.0')
        if not client_version or client_version != room_version:
             send_json(conn, {"status": "error", "reason": f"版本不符 (房: v{room_version}, 你: v{client_version})，請檢查更新！"})
             return
        room['players'].append({"name": player_name, "conn": conn})
        
    send_json(conn, {"status": "ok", "room_id": room_id, "game_name": room['game_name'], "host_name": room['host_name']})
    broadcast_room_info(room)

def cleanup_room_if_needed(room_id):
    with LOCK:
        if room_id not in ROOMS: return
        room = ROOMS[room_id]
        host_present = any(p['conn'] == room['host_conn'] for p in room['players'])
        should_close = False
        if not host_present: should_close = True
        elif len(room['players']) == 0: should_close = True
            
        if should_close:
            if room_id in ACTIVE_GAMES:
                proc = ACTIVE_GAMES[room_id]
                try:
                    proc.terminate()
                    proc.wait(timeout=1)
                except: pass
                del ACTIVE_GAMES[room_id]
            if 'game_port' in room: release_port(room['game_port'])
            for p in room['players']:
                try: send_json(p['conn'], {"cmd": "error", "reason": "房主已離開，房間關閉。"})
                except: pass
            del ROOMS[room_id]
        else:
            broadcast_room_info(room)

def handle_leave_room(conn, data):
    room_id = data.get("room_id")
    with LOCK:
        if room_id not in ROOMS: 
            send_json(conn, {"status": "ok"})
            return
        room = ROOMS[room_id]
        room['players'] = [p for p in room['players'] if p['conn'] != conn]
    send_json(conn, {"status": "ok"})
    cleanup_room_if_needed(room_id)

def broadcast_room_info(room):
    msg = {"cmd": "room_update", "players": [p['name'] for p in room['players']], "curr_count": len(room['players']), "max_count": room['max_players']}
    for p in room['players']:
        try: send_json(p['conn'], msg)
        except: pass

def handle_start_game(conn, data):
    room_id = data.get("room_id")
    with LOCK:
        if room_id not in ROOMS: return
        room = ROOMS[room_id]
        if room['host_conn'] != conn:
            send_json(conn, {"status": "error", "reason": "Only host can start game"})
            return
        if len(room['players']) < room['min_players']:
            send_json(conn, {"status": "error", "reason": "Not enough players"})
            return
        port = get_free_port()
        if not port:
            send_json(conn, {"status": "error", "reason": "No server ports available"})
            return
        room['game_port'] = port
        room['status'] = 'playing'

    record_play_history(room['game_id'], [p['name'] for p in room['players']])
    game_dir = os.path.join(STORAGE_DIR, room['game_path'])
    config_path = os.path.join(game_dir, "config.json")
    try:
        with open(config_path, 'r') as f:
            game_conf = json.load(f)
            server_script = game_conf.get("server_entry", "game_server.py")
        script_path = os.path.join(game_dir, server_script)
        cmd = [sys.executable, script_path, "--host", "0.0.0.0", "--port", str(port)]
        proc = subprocess.Popen(cmd, cwd=game_dir)
        ACTIVE_GAMES[room_id] = proc
        time.sleep(1)
        
        # FIX: 加入 game_id 與 game_name 讓 Client 知道要開哪個遊戲
        broadcast_msg = {
            "cmd": "game_started", 
            "game_server_ip": HOST, 
            "game_server_port": port,
            "game_id": room['game_id'],
            "game_name": room['game_name']
        }
        for p in room['players']:
            send_json(p['conn'], broadcast_msg)
    except Exception as e:
        print(f"[Game Launch Error] {e}")
        send_json(conn, {"status": "error", "reason": "Failed to launch game server"})
        release_port(port)
        with LOCK: room['status'] = 'waiting'

def handle_list_rooms(conn):
    with LOCK:
        rooms_list = []
        for rid, r in ROOMS.items():
            if r['status'] == 'waiting':
                rooms_list.append({
                    "room_id": rid, "game_name": r['game_name'], "version": r.get('game_version', 'unknown'),
                    "host": r['host_name'], "players": f"{len(r['players'])}/{r['max_players']}"
                })
    send_json(conn, {"status": "ok", "rooms": rooms_list})

@safe_socket_op
def handle_client(conn, addr):
    print(f"[Connect] {addr} connected")
    CLIENTS[addr] = conn
    current_user = None

    try:
        while True:
            req = recv_json(conn)
            if not req: break
            
            cmd = req.get("cmd")
            
            if not current_user:
                if cmd == "auth_login":
                    current_user = handle_auth_login(conn, req)
                elif cmd == "auth_register":
                    handle_auth_register(conn, req)
                else:
                    send_json(conn, {"status": "error", "reason": "Please login first"})
                continue
            
            if cmd == "list_games": handle_list_games(conn)
            elif cmd == "get_game_detail": handle_get_game_detail(conn, req)
            elif cmd == "rate_game": handle_rate_game(conn, req)
            elif cmd == "download_game": handle_download_game(conn, req)
            elif cmd == "create_room": handle_create_room(conn, req, addr, current_user)
            elif cmd == "list_rooms": handle_list_rooms(conn)
            elif cmd == "join_room": handle_join_room(conn, req, current_user)
            elif cmd == "start_game": handle_start_game(conn, req)
            elif cmd == "leave_room": handle_leave_room(conn, req)

    finally:
        print(f"[Disconnect] {addr} (User: {current_user})")
        with LOCK:
            if current_user and current_user in ONLINE_PLAYERS:
                del ONLINE_PLAYERS[current_user]
            for rid in list(ROOMS.keys()):
                room = ROOMS[rid]
                in_room = any(p['conn'] == conn for p in room['players'])
                if in_room:
                    room['players'] = [p for p in room['players'] if p['conn'] != conn]
                    cleanup_room_if_needed(rid)
        conn.close()
        if addr in CLIENTS: del CLIENTS[addr]

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((HOST, PORT))
        server.listen(10)
        print(f"=== Lobby Server Running on {HOST}:{PORT} ===")
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr))
            t.daemon = True
            t.start()
    except Exception as e:
        print(f"Server Error: {e}")
    finally:
        server.close()

if __name__ == '__main__':
    start_server()