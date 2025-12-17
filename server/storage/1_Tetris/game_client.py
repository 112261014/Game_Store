import socket
import argparse
import sys
import pygame
import random
import threading
import queue

# --- 設定常數 ---
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
BLOCK_SIZE = 30
GRID_WIDTH = 10
GRID_HEIGHT = 20
SIDE_PANEL_WIDTH = 120

# 顏色定義 (R, G, B)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)

# 方塊形狀定義 (I, J, L, O, S, T, Z)
SHAPES = [
    [[1, 1, 1, 1]], # I
    [[1, 0, 0], [1, 1, 1]], # J
    [[0, 0, 1], [1, 1, 1]], # L
    [[1, 1], [1, 1]], # O
    [[0, 1, 1], [1, 1, 0]], # S
    [[0, 1, 0], [1, 1, 1]], # T
    [[1, 1, 0], [0, 1, 1]]  # Z
]

SHAPE_COLORS = [CYAN, BLUE, ORANGE, YELLOW, GREEN, MAGENTA, RED]

# --- 網路處理 ---
class NetworkManager:
    def __init__(self, host, port, event_queue):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        self.event_queue = event_queue
        self.connected = False
        self.seed = None

    def connect(self):
        try:
            self.socket.connect((self.host, self.port))
            self.connected = True
            # 啟動接收執行緒
            threading.Thread(target=self.receive_loop, daemon=True).start()
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def receive_loop(self):
        buffer = ""
        while self.connected:
            try:
                data = self.socket.recv(1024).decode()
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    msg, buffer = buffer.split("\n", 1)
                    self.handle_message(msg)
            except:
                break
        self.connected = False

    def handle_message(self, msg):
        if msg.startswith("SEED:"):
            # 收到種子碼，放入佇列通知主執行緒
            seed_val = int(msg.split(":")[1])
            self.event_queue.put(("SEED", seed_val))
        elif msg.startswith("GARBAGE:"):
            # 收到垃圾行攻擊
            lines = int(msg.split(":")[1])
            self.event_queue.put(("GARBAGE", lines))

    def send_attack(self, lines):
        if self.connected:
            try:
                self.socket.sendall(f"ATTACK:{lines}\n".encode())
            except:
                self.connected = False

    def send_gameover(self):
        if self.connected:
            try:
                self.socket.sendall(b"GAMEOVER\n")
            except:
                self.connected = False

# --- 遊戲邏輯 ---
class TetrisGame:
    def __init__(self):
        self.grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.current_piece = None
        self.current_x = 0
        self.current_y = 0
        self.current_color = None
        self.bag = []
        self.score = 0
        self.game_over = False
        self.rng = random.Random() # 獨立的隨機產生器實例

    def init_rng(self, seed):
        print(f"Initializing RNG with seed: {seed}")
        self.rng.seed(seed)
        self.new_piece()

    def get_7_bag_piece(self):
        if not self.bag:
            self.bag = list(range(len(SHAPES)))
            self.rng.shuffle(self.bag) # 使用同步的 RNG 洗牌
        shape_idx = self.bag.pop()
        return SHAPES[shape_idx], SHAPE_COLORS[shape_idx]

    def new_piece(self):
        self.current_piece, self.current_color = self.get_7_bag_piece()
        self.current_x = GRID_WIDTH // 2 - len(self.current_piece[0]) // 2
        self.current_y = 0
        
        if self.check_collision(self.current_piece, self.current_x, self.current_y):
            self.game_over = True

    def check_collision(self, shape, offset_x, offset_y):
        for cy, row in enumerate(shape):
            for cx, cell in enumerate(row):
                if cell:
                    try:
                        if (offset_x + cx < 0 or 
                            offset_x + cx >= GRID_WIDTH or 
                            offset_y + cy >= GRID_HEIGHT or
                            (offset_y + cy >= 0 and self.grid[offset_y + cy][offset_x + cx])):
                            return True
                    except IndexError:
                        return True
        return False

    def rotate_piece(self):
        # 簡單旋轉 (矩陣轉置 + 反轉列)
        new_shape = [list(row) for row in zip(*self.current_piece[::-1])]
        if not self.check_collision(new_shape, self.current_x, self.current_y):
            self.current_piece = new_shape

    def lock_piece(self):
        for cy, row in enumerate(self.current_piece):
            for cx, cell in enumerate(row):
                if cell:
                    if self.current_y + cy >= 0:
                        self.grid[self.current_y + cy][self.current_x + cx] = self.current_color
        
        cleared_lines = self.clear_lines()
        self.new_piece()
        return cleared_lines

    def clear_lines(self):
        lines_to_clear = []
        for y, row in enumerate(self.grid):
            if all(cell != 0 for cell in row):
                lines_to_clear.append(y)
        
        for y in lines_to_clear:
            del self.grid[y]
            self.grid.insert(0, [0 for _ in range(GRID_WIDTH)])
            self.score += 100
        
        return len(lines_to_clear)

    def add_garbage(self, lines):
        # 接收攻擊：底部增加灰色垃圾行，頂部移除
        for _ in range(lines):
            del self.grid[0]
            garbage_row = [GRAY if i != self.rng.randint(0, GRID_WIDTH-1) else 0 for i in range(GRID_WIDTH)]
            self.grid.append(garbage_row)

# --- 主程式 ---
def run_game_client(host, port):
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Tetris Battle")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('Arial', 20)

    event_queue = queue.Queue()
    network = NetworkManager(host, port, event_queue)
    
    if not network.connect():
        print("無法連接到伺服器")
        return

    print("等待伺服器分配種子碼...")
    
    # 等待種子碼
    waiting = True
    seed = None
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
        
        try:
            msg_type, msg_val = event_queue.get_nowait()
            if msg_type == "SEED":
                seed = msg_val
                waiting = False
        except queue.Empty:
            pass
        
        screen.fill(BLACK)
        text = font.render("Connecting to Server...", True, WHITE)
        screen.blit(text, (50, SCREEN_HEIGHT // 2))
        pygame.display.flip()
        clock.tick(10)

    # 遊戲初始化
    game = TetrisGame()
    game.init_rng(seed) # 設定關鍵種子

    fall_time = 0
    fall_speed = 0.03
    running = True

    while running:
        fall_time += clock.get_rawtime()
        clock.tick(60)

        # 網路事件處理
        try:
            while True:
                msg_type, msg_val = event_queue.get_nowait()
                if msg_type == "GARBAGE":
                    game.add_garbage(msg_val)
        except queue.Empty:
            pass

        # 輸入處理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if not game.game_over:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        if not game.check_collision(game.current_piece, game.current_x - 1, game.current_y):
                            game.current_x -= 1
                    elif event.key == pygame.K_RIGHT:
                        if not game.check_collision(game.current_piece, game.current_x + 1, game.current_y):
                            game.current_x += 1
                    elif event.key == pygame.K_DOWN:
                        if not game.check_collision(game.current_piece, game.current_x, game.current_y + 1):
                            game.current_y += 1
                    elif event.key == pygame.K_UP:
                        game.rotate_piece()
                    elif event.key == pygame.K_SPACE:
                        # Hard drop: 移到底部
                        while not game.check_collision(game.current_piece, game.current_x, game.current_y + 1):
                            game.current_y += 1
                        
                        # --- 修改點：Hard Drop 後立即鎖定 ---
                        cleared = game.lock_piece()
                        fall_time = 0 # 重置下落時間，避免新方塊瞬間又掉一格
                        
                        # 立即處理攻擊邏輯
                        attack_lines = 0
                        if cleared == 2: attack_lines = 1
                        elif cleared == 3: attack_lines = 2
                        elif cleared == 4: attack_lines = 4
                        
                        if attack_lines > 0:
                            network.send_attack(attack_lines)
                            print(f"Attacked! Sent {attack_lines} lines.")

                        if game.game_over:
                            network.send_gameover()

        # 自動下落 (只有當遊戲沒結束且沒有在上方被 Hard Drop 鎖定重置時才執行)
        if not game.game_over:
            if fall_time / 1000 > fall_speed:
                fall_time = 0
                if not game.check_collision(game.current_piece, game.current_x, game.current_y + 1):
                    game.current_y += 1
                else:
                    # 這是自然落下觸底的鎖定
                    cleared = game.lock_piece()
                    
                    attack_lines = 0
                    if cleared == 2: attack_lines = 1
                    elif cleared == 3: attack_lines = 2
                    elif cleared == 4: attack_lines = 4
                    
                    if attack_lines > 0:
                        network.send_attack(attack_lines)
                        print(f"Attacked! Sent {attack_lines} lines.")

                    if game.game_over:
                        network.send_gameover()

        # 繪圖
        screen.fill(BLACK)

        # 畫格子
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                rect = pygame.Rect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                if game.grid[y][x]:
                    pygame.draw.rect(screen, game.grid[y][x], rect)
                pygame.draw.rect(screen, (40, 40, 40), rect, 1)

        # 畫當前落下物
        if game.current_piece and not game.game_over:
            for y, row in enumerate(game.current_piece):
                for x, cell in enumerate(row):
                    if cell:
                        rect = pygame.Rect((game.current_x + x) * BLOCK_SIZE, (game.current_y + y) * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                        pygame.draw.rect(screen, game.current_color, rect)
                        pygame.draw.rect(screen, WHITE, rect, 1)

        # 畫 UI
        score_text = font.render(f"Score: {game.score}", True, WHITE)
        screen.blit(score_text, (GRID_WIDTH * BLOCK_SIZE + 10, 20))
        
        if game.game_over:
            over_text = font.render("GAME OVER", True, RED)
            screen.blit(over_text, (GRID_WIDTH * BLOCK_SIZE + 10, 100))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start Tetris Game Client')
    parser.add_argument('--host', type=str, default='127.0.0.1')
    parser.add_argument('--port', type=int, default=9000)
    args = parser.parse_args()
    
    run_game_client(args.host, args.port)