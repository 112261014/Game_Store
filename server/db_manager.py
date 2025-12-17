import sqlite3
import os
import sys

# 資料庫檔案路徑
DB_PATH = os.path.join(os.path.dirname(__file__), 'db', 'game_store.db')

def get_connection():
    """取得資料庫連線"""
    return sqlite3.connect(DB_PATH)

def init_db():
    """初始化資料庫：建立所需表格"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = get_connection()
    c = conn.cursor()
    
    # 建立 Games Table
    c.execute('''CREATE TABLE IF NOT EXISTS games (
        game_id INTEGER PRIMARY KEY AUTOINCREMENT,
        dev_id TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        version TEXT,
        game_type TEXT,
        min_players INTEGER,
        max_players INTEGER,
        server_exe TEXT,
        client_exe TEXT,
        file_path TEXT,
        status TEXT DEFAULT 'active'
    )''')
    
    # 建立 Reviews Table
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER,
        player_id TEXT,
        score INTEGER,
        comment TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # 建立 Play History Table
    c.execute('''CREATE TABLE IF NOT EXISTS play_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER,
        player_id TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- 新增：帳號管理 Tables ---
    # Developer 帳號表
    c.execute('''CREATE TABLE IF NOT EXISTS developers (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL
    )''')

    # Player 帳號表
    c.execute('''CREATE TABLE IF NOT EXISTS players (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL
    )''')
    
    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully.")

def reset_db():
    """重置資料庫"""
    print("[DB] Resetting database... (ALL DATA WILL BE LOST)")
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("DROP TABLE IF EXISTS games")
        c.execute("DROP TABLE IF EXISTS reviews")
        c.execute("DROP TABLE IF EXISTS play_history")
        c.execute("DROP TABLE IF EXISTS developers")
        c.execute("DROP TABLE IF EXISTS players")
        conn.commit()
        print("[DB] All tables dropped.")
    except Exception as e:
        print(f"[DB] Error dropping tables: {e}")
    finally:
        conn.close()
    init_db()

# --- Auth Helpers ---

def register_user(role, username, password):
    """
    註冊使用者
    role: 'dev' or 'player'
    回傳: (success: bool, message: str)
    """
    table = "developers" if role == 'dev' else "players"
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(f"INSERT INTO {table} (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True, "註冊成功"
    except sqlite3.IntegrityError:
        return False, "帳號已被使用"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def verify_user(role, username, password):
    """
    驗證使用者登入
    role: 'dev' or 'player'
    回傳: bool
    """
    table = "developers" if role == 'dev' else "players"
    conn = get_connection()
    c = conn.cursor()
    c.execute(f"SELECT password FROM {table} WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    
    if row and row[0] == password:
        return True
    return False

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'reset':
        reset_db()
    else:
        init_db()