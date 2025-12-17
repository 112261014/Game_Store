import socket
import argparse
import threading

# 遊戲設定
BOARD_SIZE = 10
EMPTY = '.'
BLACK = 'X'
WHITE = 'O'
DELIMITER = "<EOF>"

class GomokuGame:
    def __init__(self):
        self.board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.turn = BLACK
        self.players = {}
        self.sockets = []
        self.game_over = False

    def broadcast(self, message, prefix="VIEW"):
        """發送訊息給所有玩家，並加上分隔符號"""
        for s in self.sockets:
            try:
                s.sendall(f"{prefix}:{message}{DELIMITER}".encode())
            except:
                pass

    def send_to(self, socket, message, prefix="VIEW"):
        """發送訊息給特定玩家，並加上分隔符號"""
        try:
            socket.sendall(f"{prefix}:{message}{DELIMITER}".encode())
        except:
            pass

    def get_board_str(self):
        header = "   " + " ".join([str(i) for i in range(BOARD_SIZE)]) + "\n"
        board_str = header
        for r in range(BOARD_SIZE):
            board_str += f"{r:2} " + " ".join(self.board[r]) + "\n"
        return board_str

    def check_win(self, r, c, piece):
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            count = 1
            for i in range(1, 5):
                nr, nc = r + dr * i, c + dc * i
                if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and self.board[nr][nc] == piece:
                    count += 1
                else: break
            for i in range(1, 5):
                nr, nc = r - dr * i, c - dc * i
                if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and self.board[nr][nc] == piece:
                    count += 1
                else: break
            if count >= 5: return True
        return False

    def handle_move(self, player_socket, move_str):
        if self.game_over: return False
        try:
            r, c = map(int, move_str.split(' '))
        except ValueError:
            self.send_to(player_socket, "Invalid format. Use \"row col\" (e.g., 5,5)")
            return False

        if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE):
            self.send_to(player_socket, "Out of bounds!")
            return False
        if self.board[r][c] != EMPTY:
            self.send_to(player_socket, "Position taken!")
            return False

        piece = self.players[player_socket]
        if piece != self.turn:
            self.send_to(player_socket, "Not your turn!")
            return False

        self.board[r][c] = piece
        if self.check_win(r, c, piece):
            self.broadcast(self.get_board_str())
            self.broadcast(f"Player {piece} WINS!", prefix="OVER")
            self.game_over = True
            return True

        self.turn = WHITE if self.turn == BLACK else BLACK
        return True

def handle_client(conn, addr, game):
    print(f"[GameServer] Player connected: {addr}")
    try:
        while not game.game_over:
            data = conn.recv(1024)
            if not data: break
            
            # 可能會有黏包，這裡簡單處理（假設最後一個是最新指令），
            # 配合 Client 的 Buffer 機制，Server 這裡讀取到的通常是單次指令
            # 但若要嚴謹 Server 讀取也需要 buffer，不過 Server 目前只讀取短字串所以較少出錯
            msg = data.decode().strip()
            
            # === 修正重點 ===
            if game.handle_move(conn, msg):
                # 如果移動成功，更新全場狀態（換人、顯示棋盤）
                update_game_state(game)
            else:
                # 如果移動失敗（格式錯誤、已被佔用等），且是該玩家的回合
                # Server 必須補發一個 INPUT 指令，讓 Client 解鎖鍵盤再次輸入
                if game.players[conn] == game.turn:
                    game.send_to(conn, "Try again:", prefix="INPUT")
            
    except ConnectionResetError:
        print(f"Player {addr} disconnected.")
    finally:
        conn.close()

def update_game_state(game):
    if game.game_over: return

    game.broadcast(game.get_board_str())
    
    current_player_socket = None
    other_player_socket = None

    for s, color in game.players.items():
        if color == game.turn:
            current_player_socket = s
        else:
            other_player_socket = s
    
    if current_player_socket:
        game.send_to(current_player_socket, f"Your Turn ({game.turn}). Enter \"row col\":", prefix="INPUT")
    if other_player_socket:
        game.send_to(other_player_socket, f"Waiting for {game.turn}...", prefix="VIEW")

def run_game_server(host, port):
    print(f"[GameServer] Starting Gomoku on {host}:{port}...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(2)
    
    game = GomokuGame()
    print("[GameServer] Waiting for players...")

    conn1, addr1 = server.accept()
    game.sockets.append(conn1)
    game.players[conn1] = BLACK
    conn1.sendall(f"VIEW:Connected. You are BLACK (X). Waiting for opponent...\n{DELIMITER}".encode())

    conn2, addr2 = server.accept()
    game.sockets.append(conn2)
    game.players[conn2] = WHITE
    conn2.sendall(f"VIEW:Connected. You are WHITE (O).\n{DELIMITER}".encode())

    print("[GameServer] Game Start!")
    
    t1 = threading.Thread(target=handle_client, args=(conn1, addr1, game))
    t2 = threading.Thread(target=handle_client, args=(conn2, addr2, game))
    t1.start()
    t2.start()

    update_game_state(game)

    t1.join()
    t2.join()
    server.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start Gomoku Server')
    parser.add_argument('--host', type=str, default='127.0.0.1')
    parser.add_argument('--port', type=int, default=9000)
    args = parser.parse_args()
    
    run_game_server(args.host, args.port)