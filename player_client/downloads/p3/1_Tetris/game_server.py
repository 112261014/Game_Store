import socket
import argparse
import threading
import random
import sys

# 全域變數
clients = []
GLOBAL_SEED = random.randint(0, 1000000)  # 伺服器啟動時生成的唯一種子

def broadcast(message, sender_socket=None):
    """將訊息廣播給所有其他客戶端"""
    for client in clients:
        if client != sender_socket:
            try:
                client.sendall(message)
            except:
                clients.remove(client)

def handle_client(client_socket, addr):
    print(f"[GameServer] Player {addr} connected.")
    
    # 1. 連線後立即發送種子碼，確保方塊序列一致
    try:
        seed_msg = f"SEED:{GLOBAL_SEED}\n"
        client_socket.sendall(seed_msg.encode())
    except Exception as e:
        print(f"[GameServer] Error sending seed to {addr}: {e}")
        return

    while True:
        try:
            data = client_socket.recv(1024)
            if not data:
                break
            
            msg = data.decode().strip()
            
            # 處理攻擊指令 (格式: ATTACK:行數)
            if msg.startswith("ATTACK:"):
                lines = msg.split(":")[1]
                print(f"[GameServer] Player {addr} sent {lines} garbage lines!")
                # 轉發給其他玩家
                broadcast(f"GARBAGE:{lines}\n".encode(), sender_socket=client_socket)
            
            # 處理玩家輸掉
            elif msg == "GAMEOVER":
                print(f"[GameServer] Player {addr} Game Over.")
                # 可以在此處通知其他人有人輸了 (選做)

        except ConnectionResetError:
            break
        except Exception as e:
            print(f"[GameServer] Error handling client {addr}: {e}")
            break

    print(f"[GameServer] Player {addr} disconnected.")
    if client_socket in clients:
        clients.remove(client_socket)
    client_socket.close()

def run_game_server(host, port):
    print(f"[GameServer] Starting Tetris Battle Server on {host}:{port}...")
    print(f"[GameServer] Generated Global Seed: {GLOBAL_SEED}")
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((host, port))
        server.listen(5)
        print(f"[GameServer] Listening for players...")
        
        while True:
            client, addr = server.accept()
            clients.append(client)
            thread = threading.Thread(target=handle_client, args=(client, addr))
            thread.daemon = True
            thread.start()
            
    except KeyboardInterrupt:
        print("\n[GameServer] Stopping server...")
    except Exception as e:
        print(f"[GameServer] Error: {e}")
    finally:
        server.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start Tetris Game Server')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host IP')
    parser.add_argument('--port', type=int, default=9000, help='Host Port')
    args = parser.parse_args()
    
    run_game_server(args.host, args.port)