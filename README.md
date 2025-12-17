# Game Store Platform Demo

## 快速啟動

1. **執行安裝腳本** (只需執行一次)：
   ```bash
   chmod +x setup.sh
   ./setup.sh
   
2. **啟動服務**：
   確認你的目錄在Game—Store/
   * **Developer Client** (開發者工具：建立範本、上架遊戲)
       ```bash
       source venv/bin/activate
       python -m dev_client.developer_client
       
   * **Player Client** (玩家大廳：瀏覽、下載、遊玩)
       ```bash
       source venv/bin/activate
       python -m player_client.lobby_client
       
## 系統架構
* **Server**: 包含 DB (SQLite), Storage (遊戲檔案), 兩個 Server Process。
* **Developer**: 透過 Dev Client 登入、打包遊戲並上傳。
* **Player**: 透過 Lobby Client 登入、下載遊戲、開房、自動啟動遊戲。
