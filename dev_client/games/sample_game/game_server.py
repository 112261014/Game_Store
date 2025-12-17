import socket
import argparse
import time
import threading

def run_game_server(host, port):
    print(f"[GameServer] Starting sample_game on {host}:{port}...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)
    
    print(f"[GameServer] Listening...")
    
    # 模擬遊戲邏輯
    try:
        while True:
            client, addr = server.accept()
            print(f"[GameServer] Player connected: {addr}")
            client.sendall(b"Welcome to sample_game! Game is running.\n")
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
