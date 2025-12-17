import socket
import threading
import json
import functools
import traceback

# =================設定區=================
HOST = ''
PORT = 0
BUFFER_SIZE = 4096

#用util.load_system_config()從system_config讀入HOST PORT

# =================全域變數 (Global State)=================
# 用來儲存所有連線跟房間資訊
CLIENTS = {}  # 格式: { (ip, port): socket_obj }
ROOMS = {}    # 格式: { 'room_id': [socket_obj, ...] }

# 執行緒鎖 (因為我們有多個 Thread 會同時讀寫上面的全域變數)
LOCK = threading.Lock()

# =================裝飾器 (錯誤處理)=================
def safe_socket_op(func):
    """通用錯誤處理裝飾器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ConnectionResetError, BrokenPipeError):
            # 這是預期中的斷線，不用印太詳細的 Traceback
            return None
        except json.JSONDecodeError:
            print(f"[Data Error] 收到格式錯誤的 JSON")
            return None
        except Exception as e:
            print(f"[System Error] {func.__name__} 發生未預期錯誤: {e}")
            traceback.print_exc()
            return None
    return wrapper

@safe_socket_op
def send_json(conn, data):
    """傳送 JSON 給特定 socket"""
    message = json.dumps(data) + '\n'
    conn.sendall(message.encode('utf-8'))

def disconnect_client(conn, addr):
    #處理斷線

#從handle_client分派任務到這裡，寫出一一對應的函數解決需求，並給出API(json格式等）

#handle_start_game需要注意要強制更新、檢查是否已下架，可以給出db需求讓db端處理

@safe_socket_op
def handle_client(conn, addr):
    """讀入請求，包括：列出在線玩家、列出房間、列出遊戲、
    回傳某個遊戲的評論以及簡介、下載遊戲、開房間、加入房間、在房間開始某款遊戲"""

def start_server():
    

if __name__ == '__main__':
    start_server()