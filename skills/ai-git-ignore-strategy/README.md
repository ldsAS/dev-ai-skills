# ai-git-ignore-strategy

針對各類 AI 代理工具 (Claude Code / Antigravity / GitHub Copilot / Codex / Cursor / Gemini) 建立 .gitignore 最佳實務的五階段審查流程，並延伸處理跨平台行尾（LF / CRLF）正規化。

## 適用情境

- 使用者說「檢核 gitignore」「整理 repo」「commit 前審查」
- 發現 .claude/ .gemini/ .agent/ 等 AI 工作資料夾被追蹤
- 專案庫突然變大、Clone 變慢
- git status 每次都出現幽靈異動（0 byte diff）
- .sh 腳本在 Linux 端噴 `\r: command not found`

## 五個版本差異

| 版本 | 對應工具 | 工具呼叫語法 |
| :--- | :--- | :--- |
| `antigravity/SKILL.md` | Google Antigravity | `view_file` / `list_dir` / `run_command` |
| `claude/SKILL.md` | Claude Code | `Read` / `Glob` / `Grep` / `Bash` / `Edit` |
| `vscode/SKILL.md` | GitHub Copilot (VS Code) | `read_file` / `list_dir` / `grep_search` / `run_in_terminal` / `replace_string_in_file` |
| `codex/SKILL.md` | Codex | `functions.shell_command` / `multi_tool_use.parallel` / `apply_patch` / sandbox escalation |
| `generic/SKILL.md` | 工具無關 | 描述為「讀檔工具」「shell 執行工具」等抽象名稱 |

四個繁中版本（Antigravity / Claude / VS Code / Generic）採共通的「五階段流程 + 三色分類 + 標準範本 + 救援指令」結構，依各工具的檔案讀取、shell 執行、編輯、權限提升與安裝位置做微調。Codex 版以英文撰寫並改用 `Diagnose / Classify / Execute / Rescue` 章節結構（搭配 `apply_patch`、`multi_tool_use.parallel`、sandbox escalation 等 Codex 特有規則），內容範圍對齊但不逐節平行。

## 安裝

從 repo 根目錄執行 `install.sh` 或 `install.ps1`，並傳入工具模式。此 repo 目前只有 `ai-git-ignore-strategy`，因此指定工具模式就會安裝這個 skill 的對應版本：

```bash
# Linux / macOS / WSL
./install.sh              # 自動偵測已安裝的 AI 工具
./install.sh claude       # 僅安裝 Claude 版
./install.sh antigravity  # 僅安裝 Antigravity 版
./install.sh codex        # 僅安裝 Codex 版
```

```powershell
# Windows
.\install.ps1
.\install.ps1 claude
.\install.ps1 codex
```

安裝完成後，於對應 AI 工具中喚起：

- **Claude Code**：在對話中輸入 `/ai-git-ignore-strategy` 或自然語言觸發（「幫我審查 gitignore」）
- **Antigravity**：skill 會在 YAML 描述的觸發字出現時自動載入
- **Codex**：放在 `~/.codex/skills/ai-git-ignore-strategy/SKILL.md` 後，由 YAML 描述中的 gitignore / repo hygiene 關鍵字自動觸發

## 維護者備註

修改此 skill 時，請同步更新工具專用版本（或至少更新 `generic/` 後再移植到各工具版本）。詳細規範見 repo 根目錄的 `CONTRIBUTING.md`。
