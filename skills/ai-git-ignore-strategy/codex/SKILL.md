---
name: ai-git-ignore-strategy
description: 建立、檢核並修正 Codex 工作中的 Git 追蹤規則，包含 .gitignore、.gitattributes、AI agent folders、本機 Codex skills、runtime logs、line-ending noise、file mode drift 與 commit-before-push hygiene。當使用者要求「檢核 gitignore」「整理 repo」「commit 前審查」「清理 AI 追蹤紀錄」「行尾 CRLF 問題」「0 byte diff」「file mode 漂移」或類似 Git hygiene 任務時觸發。
---

# AI 工作區 Git 管控最佳實務 for Codex

當使用者用各類代理型 AI 工具（Antigravity、Claude Code、Codex、Cursor、Gemini⋯⋯）進行本地開發時，AI 系統會在專案根目錄產生隱藏的本地狀態與對話紀錄資料夾（如 `.codex/`, `.claude/`, `.agent/`, `.gemini/` 等）。

這些資料夾會隨時間迅速膨脹，若不小心推上 Git 將導致：

1. **Repository Bloat**：專案體積變大，Clone/Pull 變慢。
2. **Merge Conflicts**：團隊成員各自的 AI 紀錄檔互相衝突。
3. **Security Risks**：可能暴露對話中貼過的敏感資訊或測試密碼。

---

## 🤖 給 Codex 的核心指示

> **重要原則：不要粗暴地把所有「看起來像 AI 產物」的檔案一律排除。**
> 必須先讀取檔案內容、理解用途，向開發者說明並確認後才行動。

當使用者明確要求 Codex 檢查或修正 `.gitignore`、`.gitattributes`、repo 乾淨度、AI 工作區、本機 skills、runtime logs、行尾漂移、file mode drift 或 commit 前 hygiene 時，**嚴格**按以下流程執行：

### Codex 操作規則

- 優先用 `rg` / `rg --files` 搜尋；不可用時再 fallback。
- 對彼此獨立的讀取動作使用 `multi_tool_use.parallel`，例如 `git status`、`git diff`、`Get-Content`、`rg`、目錄列示。
- 在目前可寫 workspace 內手動編輯檔案時使用 `apply_patch`。
- 如果目標 repo root、`.git` 目錄或已安裝的 skill folder 位於 sandbox 外，使用 `functions.shell_command` 並加上 `sandbox_permissions: "require_escalated"` 與清楚的 justification。
- 如果重要指令因 sandbox 或 network restriction 失敗，使用 escalation 重跑同一指令，不要繞過審批流程。
- 不要使用 `git add .`，除非整個 worktree 已審查且使用者明確同意。預設只 stage 精準路徑。
- 不要 revert 與本任務無關的使用者變更。遇到 dirty tree 時，先區分本任務變更、runtime 變更與其他使用者變更。
- 只有使用者在當前任務明確要求 push 時才 push。
- 在 Windows + SSHFS 專案中，mode-only diff 先視為環境雜訊，直到確認不是內容變更。

Codex user skills 通常位於 Windows 的 `$env:USERPROFILE\.codex\skills\<skill-name>\SKILL.md`，或 Unix-like 系統的 `~/.codex/skills/<skill-name>/SKILL.md`。專案內的 `.codex/skills/` 只有在確認包含 project-owned custom skills 時才應追蹤。

### 第一階段：診斷 (Diagnose First)

修改 ignore 規則前，先讀取 repo 規則與 Git 狀態：

```powershell
Get-Content .gitignore -ErrorAction SilentlyContinue
Get-Content .gitattributes -ErrorAction SilentlyContinue
git status --short
git ls-files | Select-Object -First 100
git ls-files --others --ignored --exclude-standard | Select-Object -First 50
git diff --stat
git diff --summary
git log --oneline -10
```

> 💡 第 5 行 (`--others --ignored`) 是反向驗證的關鍵 — 看「規則實際攔下了什麼」。若看到本該追蹤的檔案被擋（例如 seed json 被 `*.json` 誤殺），就是規則太粗暴的訊號。

對可疑的 ignored path，確認是哪條規則生效：

```powershell
git check-ignore -v <path>
```

如果 `git status` 顯示大量 modified，但 `git diff --stat` 顯示 `0 insertions, 0 deletions`，執行：

```powershell
git diff --summary
git config --get core.fileMode
```

Windows + SSHFS 的 mode drift 可用暫時關閉 file mode tracking 的方式比對：

```powershell
git -c core.fileMode=false status --short
git -c core.fileMode=false diff --summary
```

如果 Git 回報 `index file corrupt`，先暫停並說明必須修復 index 才能正常審查 status/diff，不要把它當成一般檔案變更問題。

### 第二階段：分類 (Classify Files)

除非使用者已要求直接執行且風險很低，否則修改規則前先建立簡潔報告，分成以下三類。

#### 🟢 應該提交 (Keep And Commit)

- 專案原始碼：`.py`, `.html`, `.css`, `.js`, `.ts`, `.sh`, `.bat`, `.ps1`。
- 文件與維運資料：`README.md`, `DEPLOY.md`, `docs/`, `CHANGELOG.md`。
- 跨平台 repo policy：`.gitattributes`, `.editorconfig`, `.nvmrc`。
- 專案自動化參考：Windows Task Scheduler 匯出 XML、systemd service sample、Docker / CI config。
- 專案設計 source of truth：`design-system/MASTER.md`、有意義的 page override。
- 團隊 AI 指令：`AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.github/copilot-instructions.md`，或明確要共享的 project-specific skill files。
- 客製專案 skills：例如 `.codex/skills/<project-skill>/SKILL.md`，但必須先確認它不是本機安裝的第三方 skill。

#### 🔴 應該排除或取消追蹤 (Ignore Or Untrack)

- 本機 AI 工作區與 cache：`.agent/`, `.claude/`, `.codex/`, `.gemini/`, `.cursor/`, `.github/prompts/`，但 confirmed project skills 例外。
- Runtime logs：`*.log`，通常會自動輪替或持續增長，沒有版本控制價值。
- 每次執行會覆寫的 runtime state：`last_run.txt`, `last_*.txt`。這些會讓 `git status` 長期保持 dirty。
- 機密：`.env`, `.env.*`，但保留 `!.env.example`；另排除 `*.pem`, `*.key`, `credentials.json`, `certs/`。
- 依賴與 build output：`venv/`, `.venv/`, `node_modules/`, `__pycache__/`, `dist/`, `build/`, `target/`。
- 大型 generated/binary artifacts，除非已確認要透過 Git LFS 或部署參考方式追蹤。

如專案另有 `*.jsonl`、`*.pid`、`*.lock` 等 runtime 檔，先審查用途再加入，不要把特定專案的歷史檔名硬寫進通用 skill。

#### ⚠️ 需要跟開發者確認 (Ask Before Deciding)

- `.codex/skills/`, `.claude/skills/`, `.gemini/skills/`：是本機安裝的第三方 skill，還是 project-owned custom skill？
- `$env:USERPROFILE\.codex\skills\` / `~/.codex/skills/`：這是 user-level Codex skill installation，通常不要整包複製進專案 repo。
- `*.json`：runtime data，還是 `package.json`, `tsconfig.json`, `manifest.json` 這類 source/config？
- `*.json.bak`：可丟棄備份，還是 DEPLOY 文件提到的唯一可還原資料？
- `.vscode/`：個人設定，還是團隊共享的 `extensions.json` / `launch.json`？
- 大型 PDF、XML、export：部署參考，還是已過期的靜態快照？

### 第三階段：向開發者報告 (Report Shape)

在執行任何 `.gitignore` 修改前，使用這個格式回報：

```markdown
## Git 追蹤審查報告

### ✅ 建議提交
| Path | Reason |
| :--- | :--- |

### 🚫 建議排除或取消追蹤
| Path | Reason | Action |
| :--- | :--- | :--- |

### ⚠️ 建議微調（非緊急）
| 規則 / 檔案 | 現狀 | 建議 | 理由 |
| :--- | :--- | :--- | :--- |
| `.env` 規則 | 單一 `.env` | 改為 `.env` + `.env.*` + `!.env.example` 三件套 | 防止未來 `.env.production` 等變體被誤推 |
| `*.json` blanket 規則 | 單行無註解 | 加註解說明意圖、列出已知敏感檔 | 避免日後被縮限為 `data/*.json` 時意外解放 |
| `secrets.json` | 已被 `*.json` 涵蓋 | 額外 explicit 列名一次 | 廣域規則若日後縮減，敏感檔仍有 explicit 保護 |

### ❓ 需要確認
| Path | Question |
| :--- | :--- |
```

> 💡 **四類差異**：
> - ✅ / 🚫：規則該怎麼定的明確判斷
> - ⚠️：現狀沒違規但**有更穩健的寫法**（防呆、註解、邊界條件）— 開發者可選擇套用、跳過或延後
> - ❓：需要 domain 知識才能判斷，等開發者回答

### 第四階段：執行 (Execute Safely)

分類已確認，或使用者已要求直接執行安全修正後：

1. 以最小變更修改 `.gitignore` 與 `.gitattributes`。
2. 對已被 Git 追蹤但現在要忽略的檔案，只從 index 移除、保留本機實體檔案：

```powershell
git rm --cached <path>
git rm --cached -r <dir>
```

3. **規則邊界驗證**（每改完一條規則必跑）：用 `git check-ignore -v` 對「應該被擋」與「應該放行」的檔案各跑一次，確認 glob 邊界沒寫錯：

```powershell
git check-ignore -v .env.production       # 應該被擋（顯示命中規則）
git check-ignore -v .env.example          # 應該放行（無輸出）
git check-ignore -v secrets.json          # 應該被擋（顯示命中規則）
```

若 `.env.example` 被誤擋、或 `secrets.json` 沒被擋，回到步驟 1 修正規則。**驗證沒過就不要進步驟 4**。

4. **補文件前先 grep**：若需要在文件中記錄「clone 後第一次設定步驟」（包含但不限於：技能重新安裝、靜態快照→連結、跨平台 `core.fileMode false` 設定、`chmod +x` 救援等）：

```powershell
Select-String -Path "README.md","DEPLOY.md","CONTRIBUTING.md" -Pattern "core.fileMode|chmod \+x" -SimpleMatch:$false 2>$null
```

   - **已存在** → 直接告知開發者位置（例如「DEPLOY.md 第 X 節已涵蓋」），跳過寫入
   - **不存在** → 詢問開發者要寫到哪份文件再補上；若兩份都沒有，建議寫到 `README.md` 的 Setup 段落

5. 只 stage 精準檔案：

```powershell
git add .gitignore .gitattributes DEPLOY.md
```

6. commit 前檢查 staged content：

```powershell
git status --short
git diff --cached --stat
git diff --cached --summary
git diff --cached --name-only
```

7. 依 concern 拆 commit：功能變更、ignore cleanup、line-ending normalization、mode cleanup 不要混在同一個 commit。

### 第五階段：跨平台環境雜訊正規化

#### 5a. 行尾正規化 (Line Endings)

Linux-deployed 專案預設使用 LF，Windows scripts 保留 CRLF：

```text
* text=auto eol=lf

*.bat  text eol=crlf
*.cmd  text eol=crlf
*.ps1  text eol=crlf
*.vbs  text eol=crlf

*.pdf          binary
*.png          binary
*.jpg          binary
*.jpeg         binary
*.ico          binary
*.woff         binary
*.woff2        binary
```

只在獨立 commit 套用 normalization：

```powershell
git add --renormalize .
git status --short
git diff --cached --stat
git commit -m "chore: 導入 .gitattributes 強制 LF，正規化既有文字檔行尾"
```

`git add --renormalize .` 可能造成大量 diff，這是預期行為；必須與功能變更拆開。

#### 5b. 檔案權限漂移 (File Mode Drift)

**症狀**：`git diff --stat` 每行顯示 `0 insertions, 0 deletions`、`git diff` 看不到任何 hunk，但 `git diff --summary` 出現大量 `mode change 100644 => 100755 <file>`。內容完全沒動，只有執行權限翻了。

**成因（最常見）**：Windows client 透過 **SSHFS** 掛載 Linux 目錄後，經 Windows 側的編輯器（VS Code、Notepad、任何 AI 工具）寫檔，SSHFS 的 `fmask`/`umask` 預設會把 Linux 側檔案翻成 `0755`。這是 mount 層行為，Git 本身沒做錯任何事。

**檢測**：

```powershell
git diff --summary | Select-String "mode change"   # 抓所有 mode 漂移
git config --get core.fileMode                       # 查目前設定（預設 true）
```

若 `.git/config` 因權限問題暫時無法寫入，可先用 `-c` 暫時診斷（不改 repo 設定）：

```powershell
git -c core.fileMode=false status --short
git -c core.fileMode=false diff --summary
```

**三種解法**（由重到輕，挑一個）：

1. **🥇 Repo 層關閉 mode 追蹤（首選，最乾淨）**

   ```powershell
   git config core.fileMode false
   ```

   只影響當前 repo，不是 global。關掉後 git 完全不追蹤 exec bit，SSHFS 怎麼翻都沒事。

   > ⚠️ **Trade-off**：`.sh` / shebang 腳本的 exec bit 不再由 Git 傳承。部署端（或新 clone）必須由 `DEPLOY.md` 明確記錄 `chmod +x <script>` 步驟，否則部署後會遇到 `Permission denied`。

2. **🥈 單檔 index 修正**

   ```powershell
   git update-index --chmod=-x <file>       # 從 index 取消 exec bit（保留 working tree 實體 mode）
   git update-index --chmod=+x <file>       # 加上 exec bit
   ```

   只改 git index 的記錄，不動 working tree。適合少量檔案、或想保留 mode 追蹤的情境。

3. **🥉 Working tree 批次修回（在 Linux VM 端執行）**

   ```bash
   find . -type f \( -name '*.py' -o -name '*.md' -o -name '*.html' -o -name '*.json' \) -exec chmod 644 {} \;
   chmod +x scripts/*.sh   # 該是執行檔的補回來
   ```

   治標不治本，下次 SSHFS 寫檔又會翻。通常只在前兩招都不方便時才用。

**SSHFS 源頭解法（進階）**：若能控制 mount 選項，`sshfs ... -o idmap=user,umask=022,fmask=133` 可以鎖 fmask=644。但 Windows 側多數情境（WinFsp / SSHFS-Win）改不動這個參數，直接走 `core.fileMode false` 最實際。

---

## 標準化 .gitignore 起點

這是起點，不可盲貼；依審查結果調整：

```gitignore
# 機密與環境
.env
.env.*
!.env.example
*.pem
*.key
credentials.json
certs/

# 敏感檔重複列名防呆（即使已被廣域規則涵蓋）
# 動機：廣域規則日後若被縮減（例如 *.json → data/*.json），
#       這些 explicit 規則仍會繼續保護敏感檔
# google_oauth_tokens.json     # OAuth refresh token
# secrets.json                 # 應用程式內嵌密鑰
# credentials.yaml             # 服務帳號憑證

# 依賴與虛擬環境
venv/
.venv/
node_modules/
__pycache__/
*.pyc
dist/
build/
target/

# 編輯器與作業系統雜訊
.DS_Store
Thumbs.db
.idea/
.vscode/settings.json

# AI Agent 工作區與快取
.agent/
.claude/
.codex/
.gemini/
.cursor/
.github/prompts/

# 自動執行日誌（會自動輪替或持續增長，沒有版本控制價值）
*.log

# Runtime 狀態檔（每次執行會覆寫，不該放 Git）
last_run.txt
last_*.txt
```

若 project-owned Codex skills 應該被追蹤，使用 allowlist，不要直接忽略整個 `.codex/`：

```gitignore
.codex/*
!.codex/skills/
!.codex/skills/<project-skill>/
!.codex/skills/<project-skill>/**
```

> 💡 **白名單注意事項**：`!` 白名單只有在母目錄使用 wildcard 形式時才會生效。
> 例如：`.codex/` 會整包忽略資料夾，此時 `!.codex/skills/` **完全無效**，因為 Git 不會進入已忽略的資料夾。
> 必須使用 `.codex/*` 搭配 `!.codex/skills/` 才能正確放行。同理適用 `.claude/`、`.gemini/` 和其他需要部分追蹤的 AI agent folder。

---

## 救援指令 (Rescue Commands)

如果 AI workspace 或 runtime log 已被追蹤：

```powershell
git rm -r --cached .agent .claude .codex .gemini .cursor .github/prompts
git rm --cached *.log
git add .gitignore .gitattributes
git diff --cached --stat
git diff --cached --summary
git commit -m "chore: 清理 AI 工作區與 runtime 追蹤紀錄"
```

如果機密或大檔已經 push 到歷史中，先說明風險並詢問，再使用 `git filter-repo` 等工具改寫歷史。
