import socket
import argparse
import sys

DELIMITER = "<EOF>"

def run_game_client(host, port):
    print(f"[GameClient] Connecting to {host}:{port}...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        
        buffer = ""
        while True:
            # 接收資料
            data = s.recv(4096)
            if not data:
                break
            
            # 將收到的 bytes 轉為字串並加入緩衝區
            buffer += data.decode()
            
            # 處理緩衝區內所有的完整訊息
            while DELIMITER in buffer:
                # 切割第一條完整訊息
                message, buffer = buffer.split(DELIMITER, 1)
                
                # 處理這條訊息
                if ":" in message:
                    msg_type, content = message.split(":", 1)
                    
                    if msg_type == "VIEW":
                        print(content)
                    
                    elif msg_type == "INPUT":
                        # 使用迴圈確保輸入不為空
                        while True:
                            user_input = input(f"{content} ")
                            if user_input.strip():
                                break
                        
                        if user_input.lower() == 'quit':
                            s.close()
                            return
                        s.sendall(user_input.encode())
                    
                    elif msg_type == "OVER":
                        print("\n=== GAME OVER ===")
                        print(content)
                        s.close()
                        return
                else:
                    print(message)
            
    except ConnectionRefusedError:
        print("Failed to connect to game server.")
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        s.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start Gomoku Client')
    parser.add_argument('--host', type=str, default='127.0.0.1')
    parser.add_argument('--port', type=int, default=9000)
    args = parser.parse_args()
    
    run_game_client(args.host, args.port)