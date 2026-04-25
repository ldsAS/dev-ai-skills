# ai-git-ignore-strategy

針對各類 AI 代理工具 (Claude Code / Antigravity / Cursor / Codex / Gemini) 建立 .gitignore 最佳實務的四階段審查流程，並延伸處理跨平台行尾（LF / CRLF）正規化。

## 適用情境

- 使用者說「檢核 gitignore」「整理 repo」「commit 前審查」
- 發現 .claude/ .gemini/ .agent/ 等 AI 工作資料夾被追蹤
- 專案庫突然變大、Clone 變慢
- git status 每次都出現幽靈異動（0 byte diff）
- .sh 腳本在 Linux 端噴 `\r: command not found`

## 四個版本差異

| 版本 | 對應工具 | 工具呼叫語法 |
| :--- | :--- | :--- |
| `antigravity/SKILL.md` | Google Antigravity | `view_file` / `list_dir` / `run_command` |
| `claude/SKILL.md` | Claude Code | `Read` / `Glob` / `Grep` / `Bash` / `Edit` |
| `vscode/SKILL.md` | GitHub Copilot (VS Code) | `read_file` / `list_dir` / `grep_search` / `run_in_terminal` / `replace_string_in_file` |
| `generic/SKILL.md` | 工具無關 | 描述為「讀檔工具」「shell 執行工具」等抽象名稱 |

四版內容結構一致（五階段流程 + 標準範本 + 救援指令），僅在工具名稱、呼叫語法、YAML frontmatter 觸發描述上做微調。

## 安裝

從 repo 根目錄執行 `install.sh` 或 `install.ps1`，並傳入 skill 名稱：

```bash
# Linux / macOS / WSL
./install.sh ai-git-ignore-strategy          # 自動偵測已安裝的 AI 工具
./install.sh ai-git-ignore-strategy claude   # 僅安裝 Claude 版
./install.sh ai-git-ignore-strategy antigravity
```

```powershell
# Windows
.\install.ps1 ai-git-ignore-strategy
.\install.ps1 ai-git-ignore-strategy claude
```

安裝完成後，於對應 AI 工具中喚起：

- **Claude Code**：在對話中輸入 `/ai-git-ignore-strategy` 或自然語言觸發（「幫我審查 gitignore」）
- **Antigravity**：skill 會在 YAML 描述的觸發字出現時自動載入

## 維護者備註

修改此 skill 時，請同步更新三個版本（或至少更新 `generic/` 並重新同步到另外兩個）。詳細規範見 repo 根目錄的 `CONTRIBUTING.md`。
