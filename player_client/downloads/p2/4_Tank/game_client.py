import socket
import argparse
import threading
import json
import sys
import pygame

# --- 顏色定義 ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
RED = (200, 50, 50)
BLUE = (50, 50, 200)
GREEN = (50, 200, 50)
YELLOW = (200, 200, 50)

# --- 遊戲常數 ---
WIDTH, HEIGHT = 800, 600
PLAYER_SIZE = 30
BULLET_SIZE = 5

class GameClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_id = None
        self.running = True
        self.game_data = {'players': {}, 'bullets': [], 'walls': []}
        
        # Pygame 初始化
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Tank Battle Network")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 16)

    def connect(self):
        try:
            self.sock.connect((self.host, self.port))
            print(f"Connected to {self.host}:{self.port}")
            
            # 啟動接收執行緒
            threading.Thread(target=self.receive_data, daemon=True).start()
            return True
        except ConnectionRefusedError:
            print("Failed to connect to server.")
            return False

    def receive_data(self):
        buffer = ""
        while self.running:
            try:
                data = self.sock.recv(4096).decode()
                if not data:
                    print("Disconnected from server")
                    self.running = False
                    break
                
                buffer += data
                while "\n" in buffer:
                    msg, buffer = buffer.split("\n", 1)
                    try:
                        packet = json.loads(msg)
                        if packet['type'] == 'INIT':
                            self.my_id = packet['id']
                            print(f"My ID: {self.my_id}")
                        elif packet['type'] == 'UPDATE':
                            self.game_data = packet['data']
                    except json.JSONDecodeError:
                        pass
            except Exception as e:
                print(f"Network error: {e}")
                self.running = False
                break

    def send_command(self, cmd, direction=None):
        if not self.running: return
        payload = {'cmd': cmd}
        if direction:
            payload['dir'] = direction
        try:
            self.sock.sendall((json.dumps(payload) + "\n").encode())
        except:
            self.running = False

    def draw(self):
        self.screen.fill(BLACK)
        
        # 畫牆壁
        for w in self.game_data.get('walls', []):
            pygame.draw.rect(self.screen, GRAY, (w['x'], w['y'], w['w'], w['h']))
            
        # 畫坦克
        players = self.game_data.get('players', {})
        for pid, p in players.items():
            color = GREEN if pid == self.my_id else RED
            rect = (p['x'], p['y'], PLAYER_SIZE, PLAYER_SIZE)
            pygame.draw.rect(self.screen, color, rect)
            
            # 畫砲管指示方向
            center_x = p['x'] + PLAYER_SIZE // 2
            center_y = p['y'] + PLAYER_SIZE // 2
            end_x, end_y = center_x, center_y
            if p['dir'] == 'UP': end_y -= 20
            elif p['dir'] == 'DOWN': end_y += 20
            elif p['dir'] == 'LEFT': end_x -= 20
            elif p['dir'] == 'RIGHT': end_x += 20
            pygame.draw.line(self.screen, WHITE, (center_x, center_y), (end_x, end_y), 3)

            # 畫血量與分數
            info_text = f"HP:{p['hp']} S:{p['score']}"
            text_surf = self.font.render(info_text, True, WHITE)
            self.screen.blit(text_surf, (p['x'], p['y'] - 20))

        # 畫子彈
        for b in self.game_data.get('bullets', []):
            pygame.draw.rect(self.screen, YELLOW, (b['x'], b['y'], BULLET_SIZE, BULLET_SIZE))

        # UI 資訊
        if self.my_id:
            status = f"Connected | ID: {self.my_id}"
        else:
            status = "Connecting..."
        
        status_surf = self.font.render(status, True, WHITE)
        self.screen.blit(status_surf, (10, 10))

        pygame.display.flip()

    def run(self):
        if not self.connect():
            return

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.send_command('SHOOT')

            # 持續按鍵移動
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.send_command('MOVE', 'UP')
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.send_command('MOVE', 'DOWN')
            elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.send_command('MOVE', 'LEFT')
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.send_command('MOVE', 'RIGHT')

            self.draw()
            self.clock.tick(60)

        pygame.quit()
        self.sock.close()
        sys.exit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start Game Client')
    parser.add_argument('--host', type=str, default='127.0.0.1')
    parser.add_argument('--port', type=int, default=9000)
    args = parser.parse_args()
    
    client = GameClient(args.host, args.port)
    client.run()