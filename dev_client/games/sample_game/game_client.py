import socket
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
