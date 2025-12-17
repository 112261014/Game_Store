# Game Store Platform Demo

## 快速啟動

1. **執行安裝腳本** (只需執行一次)：
   ```bash
   chmod +x setup.sh
   ./setup.sh
   
2. **啟動服務**：
   請開啟 4 個終端機視窗，分別執行以下指令 (確保已在專案根目錄)：

   * **視窗 1: Developer Server** (負責上架管理)
       ```bash
       source venv/bin/activate
       python -m server.dev_server
       
   * **視窗 2: Lobby Server** (負責大廳與遊戲配對)
       ```bash
       source venv/bin/activate
       python -m server.lobby_server
       
   * **視窗 3: Developer Client** (開發者工具：建立範本、上架遊戲)
       ```bash
       source venv/bin/activate
       python -m dev_client.developer_client
       
   * **視窗 4: Player Client** (玩家大廳：瀏覽、下載、遊玩)
       ```bash
       source venv/bin/activate
       python -m player_client.lobby_client
       
## 系統架構
* **Server**: 包含 DB (SQLite), Storage (遊戲檔案), 兩個 Server Process。
* **Developer**: 透過 Dev Client 登入、打包遊戲並上傳。
* **Player**: 透過 Lobby Client 登入、下載遊戲、開房、自動啟動遊戲。

這樣一來，助教只需要拿到您的程式碼包，執行 `./setup.sh` 就能搞定一切環境設定與初始化，並清楚知道如何啟動各個組件。祝您 Demo 順利！