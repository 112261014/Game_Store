import socket
import json
import struct
import os
import functools

def safe_socket_op(func):
    """裝飾器：處理 Socket 連線與 JSON 解析錯誤"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ConnectionResetError, BrokenPipeError):
            print(f"[Network] 連線中斷: {func.__name__}")
            return None
        except json.JSONDecodeError:
            print(f"[Network] JSON 格式錯誤")
            return None
        except Exception as e:
            print(f"[Error] 未預期錯誤: {e}")
            return None
    return wrapper

def load_system_config():
    """讀取全域設定檔"""
    config_path = os.path.join(os.path.dirname(__file__), '../config/system_config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"system_config load error, using default")
        return {"HOST": "127.0.0.1", "PORT": 8888, "DEV_PORT": 8889}

def compare_versions(ver1, ver2):
    """
    比較版本號字串。
    回傳: 1 (ver1 > ver2), -1 (ver1 < ver2), 0 (相等)
    """
    def normalize(v):
        return [int(x) for x in v.split(".")]
    
    try:
        p1 = normalize(ver1)
        p2 = normalize(ver2)
    except ValueError:
        # 若格式錯誤，簡單比較字串
        return 1 if ver1 > ver2 else (-1 if ver1 < ver2 else 0)

    len_diff = len(p1) - len(p2)
    if len_diff > 0:
        p2.extend([0] * len_diff)
    elif len_diff < 0:
        p1.extend([0] * (-len_diff))

    if p1 > p2: return 1
    elif p1 < p2: return -1
    else: return 0

def send_json(sock, data):
    """傳送 JSON"""
    try:
        message = json.dumps(data) + '\n'
        sock.sendall(message.encode('utf-8'))
    except Exception as e:
        print(f"[Send Error] {e}")

def recv_json(sock):
    """接收 JSON (改為逐字元讀取，避免誤讀 Binary 資料)"""
    buffer = b""
    try:
        while True:
            b = sock.recv(1)
            if not b: return None
            buffer += b
            if b == b'\n':
                return json.loads(buffer.decode('utf-8'))
    except Exception as e:
        print(f"[Recv Error] {e}")
        return None

def send_file(sock, file_path):
    """傳送檔案 (先傳大小，再傳內容)"""
    try:
        file_size = os.path.getsize(file_path)
        sock.sendall(struct.pack('>Q', file_size))
        with open(file_path, 'rb') as f:
            while True:
                bytes_read = f.read(4096)
                if not bytes_read: break
                sock.sendall(bytes_read)
        return True
    except Exception as e:
        print(f"[Send File Error] {e}")
        return False

def recv_file(sock, save_path):
    """接收檔案"""
    try:
        raw_msglen = sock.recv(8)
        if not raw_msglen: return False
        file_size = struct.unpack('>Q', raw_msglen)[0]
        
        received_size = 0
        with open(save_path, 'wb') as f:
            while received_size < file_size:
                chunk_size = 4096 if (file_size - received_size) > 4096 else (file_size - received_size)
                chunk = sock.recv(chunk_size)
                if not chunk: break
                f.write(chunk)
                received_size += len(chunk)
        return True
    except Exception as e:
        print(f"[Recv File Error] {e}")
        return False