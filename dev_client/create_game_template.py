import os
import json
import sys

def create_template():
    print("=== Create Game Template ===")
    game_name_input = input("Enter Game ID/Folder Name (e.g. my_snake): ").strip()
    if not game_name_input:
        print("Invalid name.")
        return

    base_dir = os.path.join("dev_client/games", game_name_input)
    os.makedirs(base_dir, exist_ok=True)
    
    # 1. 建立 config.json
    config_data = {
        "game_name": game_name_input,
        "version": "1.0.0",
        "description": "Short description here.",
        "game_type": "CLI",
        "min_players": 1,
        "max_players": 4,
        "server_entry": "game_server.py",
        "client_entry": "game_client.py"
    }
    
    with open(os.path.join(base_dir, "config.json"), "w", encoding='utf-8') as f:
        json.dump(config_data, f, indent=4)

    # 2. 建立 game_server.py 範本
    server_code = '''import socket
import argparse
import time
import threading

def run_game_server(host, port):
    print(f"[GameServer] Starting {game_name} on {host}:{port}...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)
    
    print(f"[GameServer] Listening...")
    
    # 模擬遊戲邏輯
    try:
        while True:
            client, addr = server.accept()
            print(f"[GameServer] Player connected: {addr}")
            client.sendall(b"Welcome to {game_name}! Game is running.\\n")
    except KeyboardInterrupt:
        print("Server stopping...")
    finally:
        server.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start Game Server')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host IP')
    parser.add_argument('--port', type=int, default=9000, help='Host Port')
    args = parser.parse_args()
    
    run_game_server(args.host, args.port)
'''.replace("{game_name}", game_name_input)

    with open(os.path.join(base_dir, "game_server.py"), "w", encoding='utf-8') as f:
        f.write(server_code)

    # 3. 建立 game_client.py 範本
    client_code = '''import socket
import argparse
import sys

def run_game_client(host, port):
    print(f"[GameClient] Connecting to {host}:{port}...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        
        # 接收歡迎訊息
        data = s.recv(1024)
        print("Server says:", data.decode())
        
        while True:
            msg = input("Enter command (or 'quit'): ")
            if msg == 'quit': break
            s.sendall(msg.encode())
            
    except ConnectionRefusedError:
        print("Failed to connect to game server.")
    finally:
        s.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start Game Client')
    parser.add_argument('--host', type=str, default='127.0.0.1')
    parser.add_argument('--port', type=int, default=9000)
    args = parser.parse_args()
    
    run_game_client(args.host, args.port)
'''
    with open(os.path.join(base_dir, "game_client.py"), "w", encoding='utf-8') as f:
        f.write(client_code)

    print(f"✅ Template created at {base_dir}/")
    print("Files: config.json, game_server.py, game_client.py")

if __name__ == '__main__':
    create_template()