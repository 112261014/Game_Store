import socket
import argparse
import threading
import json
import time
import random
import uuid

# --- 遊戲設定 ---
WIDTH, HEIGHT = 800, 600
PLAYER_SIZE = 30
BULLET_SIZE = 5
SPEED = 3
BULLET_SPEED = 7
RELOAD_TIME = 0.5  # 秒

# 全域旗標，用來控制伺服器是否繼續運行
server_running = True

# --- 遊戲狀態管理 ---
class GameState:
    def __init__(self):
        self.players = {}  # {player_id: {x, y, dir, color, score, hp}}
        self.bullets = []  # [{x, y, dx, dy, owner_id}]
        self.walls = self.generate_symmetric_map()
        self.lock = threading.Lock()

    def generate_symmetric_map(self):
        """生成簡單的中心對稱地圖 (X軸與Y軸對稱)"""
        walls = []
        # 基本邊界牆
        walls.append({'x': 0, 'y': 0, 'w': WIDTH, 'h': 10}) # 上
        walls.append({'x': 0, 'y': HEIGHT-10, 'w': WIDTH, 'h': 10}) # 下
        walls.append({'x': 0, 'y': 0, 'w': 10, 'h': HEIGHT}) # 左
        walls.append({'x': WIDTH-10, 'y': 0, 'w': 10, 'h': HEIGHT}) # 右

        # 左上角的障礙物定義 (x, y, w, h)
        obstacles = [
            (100, 100, 50, 200),
            (250, 50, 200, 50),
            (150, 400, 50, 50),
        ]

        # 鏡像生成
        final_walls = []
        for rect in walls:
            final_walls.append(rect)

        for (x, y, w, h) in obstacles:
            # 左上
            final_walls.append({'x': x, 'y': y, 'w': w, 'h': h})
            # 右上 (X 鏡像)
            final_walls.append({'x': WIDTH - x - w, 'y': y, 'w': w, 'h': h})
            # 左下 (Y 鏡像)
            final_walls.append({'x': x, 'y': HEIGHT - y - h, 'w': w, 'h': h})
            # 右下 (XY 鏡像)
            final_walls.append({'x': WIDTH - x - w, 'y': HEIGHT - y - h, 'w': w, 'h': h})
        
        # 中心掩體
        final_walls.append({'x': WIDTH//2 - 50, 'y': HEIGHT//2 - 50, 'w': 100, 'h': 100})
        
        return final_walls

    def check_collision(self, rect):
        """檢查一個矩形是否與任何牆壁相撞"""
        rx, ry, rw, rh = rect['x'], rect['y'], rect['w'], rect['h']
        for w in self.walls:
            if (rx < w['x'] + w['w'] and rx + rw > w['x'] and
                ry < w['y'] + w['h'] and ry + rh > w['y']):
                return True
        return False

    def get_safe_spawn_pos(self):
        """尋找一個不與牆壁重疊的安全生成點"""
        while True:
            # 留一點邊距，避免剛好貼在邊界
            x = random.randint(50, WIDTH - 50 - PLAYER_SIZE)
            y = random.randint(50, HEIGHT - 50 - PLAYER_SIZE)
            rect = {'x': x, 'y': y, 'w': PLAYER_SIZE, 'h': PLAYER_SIZE}
            
            # 如果沒有撞到牆壁，就回傳這個座標
            if not self.check_collision(rect):
                return x, y

    def add_player(self, player_id):
        with self.lock:
            # 使用安全生成函數
            x, y = self.get_safe_spawn_pos()
            self.players[player_id] = {
                'x': x, 'y': y,
                'dir': 'UP',
                'hp': 3,
                'score': 0,
                'last_shot': 0
            }

    def remove_player(self, player_id):
        with self.lock:
            if player_id in self.players:
                del self.players[player_id]

    def check_player_hit(self, bullet_rect, owner_id):
        """檢查子彈是否擊中玩家"""
        bx, by, bw, bh = bullet_rect['x'], bullet_rect['y'], bullet_rect['w'], bullet_rect['h']
        hit_pid = None
        
        for pid, p in self.players.items():
            if pid == owner_id: continue # 不打自己
            if (bx < p['x'] + PLAYER_SIZE and bx + bw > p['x'] and
                by < p['y'] + PLAYER_SIZE and by + bh > p['y']):
                p['hp'] -= 1
                if p['hp'] <= 0:
                    # 重生邏輯：使用安全生成函數
                    p['hp'] = 3
                    new_x, new_y = self.get_safe_spawn_pos()
                    p['x'] = new_x
                    p['y'] = new_y
                hit_pid = pid
                break
        return hit_pid

    def update(self):
        with self.lock:
            # 更新子彈
            for b in self.bullets[:]:
                b['x'] += b['dx']
                b['y'] += b['dy']
                
                b_rect = {'x': b['x'], 'y': b['y'], 'w': BULLET_SIZE, 'h': BULLET_SIZE}
                
                # 子彈撞牆
                if self.check_collision(b_rect) or \
                   b['x'] < 0 or b['x'] > WIDTH or b['y'] < 0 or b['y'] > HEIGHT:
                    self.bullets.remove(b)
                    continue
                
                # 子彈撞人
                hit_pid = self.check_player_hit(b_rect, b['owner_id'])
                if hit_pid:
                    self.bullets.remove(b)
                    # 增加分數
                    if b['owner_id'] in self.players:
                        self.players[b['owner_id']]['score'] += 1

    def handle_input(self, player_id, data):
        with self.lock:
            if player_id not in self.players: return
            p = self.players[player_id]
            cmd = data.get('cmd')
            
            new_x, new_y = p['x'], p['y']
            
            if cmd == 'MOVE':
                direction = data.get('dir')
                p['dir'] = direction
                if direction == 'UP': new_y -= SPEED
                elif direction == 'DOWN': new_y += SPEED
                elif direction == 'LEFT': new_x -= SPEED
                elif direction == 'RIGHT': new_x += SPEED
                
                # 碰撞檢測
                if not self.check_collision({'x': new_x, 'y': new_y, 'w': PLAYER_SIZE, 'h': PLAYER_SIZE}):
                    p['x'], p['y'] = new_x, new_y

            elif cmd == 'SHOOT':
                now = time.time()
                if now - p['last_shot'] > RELOAD_TIME:
                    p['last_shot'] = now
                    dx, dy = 0, 0
                    if p['dir'] == 'UP': dy = -BULLET_SPEED
                    elif p['dir'] == 'DOWN': dy = BULLET_SPEED
                    elif p['dir'] == 'LEFT': dx = -BULLET_SPEED
                    elif p['dir'] == 'RIGHT': dx = BULLET_SPEED
                    
                    # 子彈從坦克中心發射
                    self.bullets.append({
                        'x': p['x'] + PLAYER_SIZE//2 - BULLET_SIZE//2,
                        'y': p['y'] + PLAYER_SIZE//2 - BULLET_SIZE//2,
                        'dx': dx, 'dy': dy,
                        'owner_id': player_id
                    })

    def get_snapshot(self):
        with self.lock:
            return {
                'players': self.players,
                'bullets': self.bullets,
                'walls': self.walls
            }

game_state = GameState()

# 更新 handle_client 以接收 clients 列表，以便在斷線時移除
def handle_client(conn, addr, clients):
    player_id = str(uuid.uuid4())[:8]
    print(f"[GameServer] Player {player_id} connected from {addr}")
    game_state.add_player(player_id)
    
    # 傳送 ID 給客戶端
    try:
        conn.sendall((json.dumps({"type": "INIT", "id": player_id}) + "\n").encode())

        buffer = ""
        while True:
            data = conn.recv(1024).decode()
            if not data: break
            
            buffer += data
            while "\n" in buffer:
                msg, buffer = buffer.split("\n", 1)
                try:
                    cmd_data = json.loads(msg)
                    game_state.handle_input(player_id, cmd_data)
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        print(f"Error with client {player_id}: {e}")
    finally:
        print(f"[GameServer] Player {player_id} disconnected")
        game_state.remove_player(player_id)
        # 從連線列表中移除自己
        if conn in clients:
            clients.remove(conn)
        conn.close()

def broadcast_state(clients):
    global server_running
    while server_running:
        time.sleep(0.016) # ~60 FPS
        game_state.update()
        snapshot = game_state.get_snapshot()
        msg = (json.dumps({"type": "UPDATE", "data": snapshot}) + "\n").encode()
        
        # 複製一份列表進行遍歷，避免迭代時被修改
        for c in clients[:]:
            try:
                c.sendall(msg)
            except:
                if c in clients:
                    clients.remove(c)

def run_game_server(host, port):
    global server_running
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    
    # 設定 Socket 超時，讓 accept 不會永久卡住，以便檢查關機條件
    server.settimeout(1.0)
    
    print(f"[GameServer] Running on {host}:{port}")
    
    clients = []
    ever_connected = False # 紀錄是否曾經有玩家連接過
    
    # 啟動廣播執行緒
    threading.Thread(target=broadcast_state, args=(clients,), daemon=True).start()

    try:
        while server_running:
            try:
                conn, addr = server.accept()
                clients.append(conn)
                ever_connected = True # 有人連進來了，標記為 True
                # 將 clients 列表傳給執行緒，讓它在結束時能將自己移除
                threading.Thread(target=handle_client, args=(conn, addr, clients), daemon=True).start()
            except socket.timeout:
                # 沒人連線，繼續迴圈檢查其他條件
                pass
            
            # 自動關機檢查：如果曾經有人連過，且現在沒人了
            if ever_connected and len(clients) == 0:
                print("[GameServer] All players disconnected. Shutting down server...")
                server_running = False
                break
                
    except KeyboardInterrupt:
        print("Server stopping...")
    finally:
        server_running = False
        server.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, default='127.0.0.1')
    parser.add_argument('--port', type=int, default=9000)
    args = parser.parse_args()
    run_game_server(args.host, args.port)