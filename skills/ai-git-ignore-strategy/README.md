# ai-git-ignore-strategy

針對各類 AI 代理工具 (Claude Code / Antigravity / GitHub Copilot / Codex / Gemini) 建立 .gitignore 最佳實務的五階段審查流程，並延伸處理跨平台行尾（LF / CRLF）正規化。

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
| `codex/SKILL.md` | Codex | `functions.exec_command` / `multi_tool_use.parallel` / `apply_patch` / sandbox escalation |
| `generic/SKILL.md` | 工具無關 | 描述為「讀檔工具」「shell 執行工具」等抽象名稱 |

五版內容結構一致（五階段流程 + 三色分類 + 標準範本 + 救援指令），並依各工具的檔案讀取、shell 執行、編輯、權限提升與安裝位置做微調。Codex 版額外納入 `apply_patch`、`multi_tool_use.parallel`、sandbox escalation 等 Codex 特有操作規則，並全程使用 PowerShell 範例（Windows + SSHFS 友善）。

## 單一 MASTER.md 架構

本技能的 `git-tracking/MASTER.md` 比照 [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) 的 `design-system/MASTER.md`，作為專案層的單一真相來源。五個工具版本只調整操作方式，不得分叉專案追蹤決策。

所有工具都必須讀取同一份 `<repo>/git-tracking/MASTER.md`；需要更新且已取得修改授權時，也只能寫入該檔。不得建立 `MASTER.codex.md`、`MASTER.claude.md` 或其他工具專屬副本。這項硬規則也直接寫在每個版本的 `SKILL.md`，README 在此僅說明設計理由。

## 安裝

從 repo 根目錄執行 `install.sh` 或 `install.ps1`，並傳入工具模式。`claude`／`antigravity`／`vscode` 會安裝各自版本；`codex` 會把 `generic/` 安裝到 Codex、Gemini CLI、Copilot 共用的 `~/.agents/skills/`，避免在同一共用路徑放入 Codex 專屬工具語法。

```bash
# Linux / macOS / WSL
./install.sh              # 自動偵測已安裝的 AI 工具
./install.sh claude       # 僅安裝 Claude 版
./install.sh antigravity  # 僅安裝 Antigravity 版（→ 偵測到的 CLI 與 IDE 兩條全域路徑）
./install.sh codex        # 僅安裝 Codex 版
./install.sh vscode       # 僅安裝 VS Code Copilot 版（~/.copilot/skills/）
```

```powershell
# Windows (若遇到 Execution Policy 權限報錯，請改用：powershell -ExecutionPolicy Bypass -File .\install.ps1 <參數>)
.\install.ps1
.\install.ps1 claude
.\install.ps1 codex
```

安裝完成後，於對應 AI 工具中喚起：

- **Claude Code**：在對話中輸入 `/ai-git-ignore-strategy`，或自然語言觸發（「幫我檢核 gitignore」「哪些檔案不該進 git」）
- **Antigravity**：skill 會在 YAML 描述的觸發字出現時自動載入
- **Codex**：安裝器寫入官方 USER 路徑 `~/.agents/skills/ai-git-ignore-strategy/SKILL.md`（**不是** `~/.codex/skills/`，該路徑未見於官方 skills scope 表，見 C-12），由 YAML 描述中的關鍵字自動觸發。2026-08-09 Codex 實機確認載入來源即為此路徑（C-85）
- **GitHub Copilot (VS Code)**、**Gemini CLI**：同樣讀 `~/.agents/skills/`，共用上面那一份，不另外安裝

> 📌 完整的路徑對照表（含每條路徑的帳本編號）見 repo 根目錄 `README.md` 的「安裝邏輯」一節 —— 那裡是唯一真相來源。

## 維護者備註

修改此 skill 時，請同步更新工具專用版本（或至少更新 `generic/` 後再移植到各工具版本）。詳細規範見 repo 根目錄的 `CONTRIBUTING.md`。

全域安裝必須是**最後一次 source 修改之後**的步驟：先完成五版與帳本修改、跑完驗證，再執行 `install.ps1` auto 模式或 `update-skills.bat`。如果安裝後又改了任何 variant，就必須重跑安裝並比對來源與全域 `SKILL.md` 的 SHA256；「曾經安裝成功」不代表目前仍同步。

### 路徑主張的依據

本 skill 的規則建立在一組「哪個工具會在哪裡產生什麼檔案」的路徑事實上，這些事實會隨工具改版而變。

- 每條主張的依據、取證日與狀態記錄於 [`verification/CLAIMS.md`](./verification/) — **改動任何路徑規則前請先查閱**
- 官方文件（包含 Antigravity 文件站）的路徑 token 異動由 [`check-updates.yml`](../../.github/workflows/check-updates.yml) 每日偵測；token 只作候選訊號，需人工分類後才更新帳本或規則
- 版本號只作低頻輔助：目前各工具皆只在 major 跨越時告警，patch／minor 不因版本本身開 issue 或寫回 baseline
- 文件語意與實機行為的盲區走人工交接流程，見 `verification/README.md`；不把每次工具更新當成交接提醒

`verification/` 不會被 `install.sh` 安裝到使用者環境（安裝器只複製 `<variant>/` 底下的內容）。
