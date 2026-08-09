---
name: ai-git-ignore-strategy
description: 建立、檢核並修正 Codex 工作中的 Git 追蹤規則，包含 .gitignore、.gitattributes、AI agent folders、本機 Codex skills、runtime logs、line-ending noise、file mode drift 與 commit-before-push hygiene。當使用者要求「檢核 gitignore」「哪些檔案不該進 git」「commit 前確認會提交哪些檔案」「整理 repo 的 AI 產生物」「清理 AI 追蹤紀錄」「行尾 CRLF 問題」「0 byte diff」「file mode 漂移」或類似 Git hygiene 任務時觸發。本 skill 只判斷**檔案該不該被 git 追蹤**，不做程式碼安全稽核，也不做重構或簡化 —— 那兩類請交給對應的 skill。
---

# AI 工作區 Git 管控最佳實務 for Codex

當使用者用各類代理型 AI 工具（Antigravity、Claude Code、Codex、Gemini⋯⋯）進行本地開發時，AI 系統會在專案根目錄產生隱藏的本地狀態與對話紀錄資料夾（如 `.codex/`, `.claude/`, `.agent/`, `.gemini/` 等）。

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
- 如果目標 repo root、`.git` 目錄或已安裝的 skill folder 位於 sandbox 外，使用 `functions.exec_command` 並加上 `sandbox_permissions: "require_escalated"` 與清楚的 justification。
- 如果重要指令因 sandbox 或 network restriction 失敗，使用 escalation 重跑同一指令，不要繞過審批流程。
- 不要使用 `git add .`，除非整個 worktree 已審查且使用者明確同意。預設只 stage 精準路徑。
- 不要 revert 與本任務無關的使用者變更。遇到 dirty tree 時，先區分本任務變更、runtime 變更與其他使用者變更。
- 只有使用者在當前任務明確要求 push 時才 push。
- 在 Windows + SSHFS 專案中，mode-only diff 先視為環境雜訊，直到確認不是內容變更。

Codex user skills 通常位於 Windows 的 `$env:USERPROFILE\.codex\skills\<skill-name>\SKILL.md`，或 Unix-like 系統的 `~/.codex/skills/<skill-name>/SKILL.md`。專案內的 `.codex/skills/` 只有在確認包含 project-owned custom skills 時才應追蹤。

### 第一階段：診斷 (Diagnose First)

> 📒 **先看 `git-tracking/MASTER.md`**（若專案有的話）—— 那是這個專案先前的追蹤決定。
> 本階段的目標是找出「決定、路徑事實、`.gitignore` 實際行為」三者的不一致，
> 而不是從零重新判斷一遍。詳見下方〈專案追蹤決定表〉。

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

**跨平台訊號 fingerprint 檢查**：用 `rg --files` 或目錄列示偵測下列訊號，若**多個**同時命中代表此專案有跨平台部署需求，第三階段 Report 應主動提及「預防性 fileMode 提示」：

- 同一 repo 同時存在 `.sh` + `.ps1`（或 + `.bat` / `.cmd` / `.vbs`）
- 根目錄有 `Dockerfile` / `docker-compose.yml`
- `.gitattributes` 指定多種 `eol`（同時有 `eol=lf` 與 `eol=crlf`）
- `README.md` / `DEPLOY.md` 提及 VM、SSHFS、Linux VM、Tailscale、systemd
- 已存在的 `.gitattributes` 有 `binary` 標記混合多平台腳本

命中 0–1 項：純單一 OS 專案，跳過預防性提示；命中 2 項以上：在第三階段加入相應的 ⚠️ 建議微調項。

如果 Git 回報 `index file corrupt`，先暫停並說明必須修復 index 才能正常審查 status/diff，不要把它當成一般檔案變更問題。

### 第二階段：分類 (Classify Files)

除非使用者已要求直接執行且風險很低，否則修改規則前先建立簡潔報告，分成以下三類。

#### 🟢 應該提交 (Keep And Commit)

- 專案原始碼：`.py`, `.html`, `.css`, `.js`, `.ts`, `.sh`, `.bat`, `.ps1`。
- 文件與維運資料：`README.md`, `DEPLOY.md`, `docs/`, `CHANGELOG.md`。
- 跨平台 repo policy：`.gitattributes`, `.editorconfig`, `.nvmrc`。
- 專案自動化參考：Windows Task Scheduler 匯出 XML、systemd service sample、Docker / CI config。
- 專案設計 source of truth：`design-system/MASTER.md`、有意義的 page override。
- 團隊 AI 指令與共享 AI 設定：`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.github/prompts/*.prompt.md`（Copilot 共享 prompt）, `.agents/plugins/marketplace.json`（Codex 團隊共用外掛市集）, `.claude/settings.json`（團隊權限／hooks）, `.claude/commands/`, `.geminiignore`、`.aiexclude`（AI 忽略規則，與 `.gitignore` 同性質）、`.claude-plugin/plugin.json`、`.codex-plugin/plugin.json`（本 repo 本身是外掛時的清單檔）、`.mcp.json`（Claude Code 專案層 MCP server 設定，官方層級表列為 Project 層）、`.claude/rules/`（團隊共用分檔規則）, `.codex/config.toml`（專案層設定覆寫）, `.gemini/settings.json`（Workspace 設定），或明確要共享的 project-specific skill files。
- 客製專案 skills：例如 `.codex/skills/<project-skill>/SKILL.md`，但必須先確認它不是本機安裝的第三方 skill。

- **本技能的專案決定表**：`git-tracking/MASTER.md` —— 記錄這個專案對各路徑的追蹤決定與刻意偏離之處。它是判斷依據而非個人設定，**必須提交**，否則下次執行只能從零重問一輪。

> **白名單錯了，代價不只是 repo 不乾淨。** 下列機制都會產生「應該提交」的檔案，
> 而它們能不能被團隊共用，完全取決於本 skill 的白名單是否正確：
>
> | 產生者 | 產物 | 誤殺的後果 |
> | :--- | :--- | :--- |
> | Claude Code 的 `/verify` | `.claude/skills/verify/SKILL.md` | 團隊失去共用的建置指令紀錄 |
> | 權限／設定調整機制 | 專案 `.claude/settings.json` | 團隊各自重複被權限提示打斷 |
> | 專案初始化機制 | `CLAUDE.md`／`AGENTS.md` | 團隊失去專案指令檔 |
>
> 所以**不能用「一律擋掉比較安全」的心態處理白名單**。擋錯的成本是別人的機制失效，
> 而且失效時**不會有任何錯誤訊息** —— 沒有人會發現，只會覺得那個功能「好像沒什麼用」。

#### 🔴 應該排除或取消追蹤 (Ignore Or Untrack)

- 本機 AI 工作區與 cache：`.agent/`（Antigravity 1.x）、`.antigravitycli/`（Antigravity CLI 舊版的工作區對應檔；新版已改集中到 `~/.gemini/antigravity-cli/cache/projects.json` 並淘汰此目錄，舊專案仍會殘留） 的工作區暫存、`.codex/`、`.gemini/` 的快取，但 confirmed project skills 例外。
  - ⚠️ 注意（最容易誤殺）：專案內 `.claude/`（`settings.json`, `commands/`, `skills/`）、`.github/prompts/*.prompt.md` 多半是刻意共享的設定與規則，屬於 🟢 或 ⚠️ 類；專案內 `.agents/` 的 `skills/`、`rules/` 也是刻意共享的設定，不要整包封殺（`.agents/AGENTS.md`、`.agents/settings.json` 曾列於此，2026-08-04 查證為**不存在的檔案**，規則與敘述均已移除；Antigravity 只讀**根目錄**的 `AGENTS.md`）；多數工具的對話紀錄存在使用者家目錄（如 `~/.claude/projects/`），不在專案內。 另外，`.agents/` 並非 Antigravity 專屬，而是**跨工具共用目錄** — Codex 會從當前工作目錄逐層往上掃 `.agents/skills`、Gemini CLI 以 `.agents/skills/` 作為 `.gemini/skills/` 的高優先別名、Antigravity 讀 `.agents/hooks.json`；只裝 Codex 的專案一樣會出現 `.agents/`，不要當成 Antigravity 殘留。　Antigravity 實查（1.0.13，2026-07-30）：對話紀錄位於 `~/.gemini/antigravity/conversations/` 等家目錄，**但專案內並非乾淨** — agent 會把使用者訊息**逐字**附加到 `.agents/ORIGINAL_REQUEST.md`（含 UTC 時間戳），屬本 skill 開頭所述的 Security Risks，必須排除。
- Runtime logs：`*.log`，通常會自動輪替或持續增長，沒有版本控制價值。
- 每次執行會覆寫的 runtime state：`last_run.txt`, `last_*.txt`。這些會讓 `git status` 長期保持 dirty。
- 機密：`.env`, `.env.*`，但保留 `!.env.example`；另排除 `*.pem`, `*.key`, `credentials.json`, `certs/`。
- 依賴與 build output：`venv/`, `.venv/`, `node_modules/`, `__pycache__/`, `dist/`, `build/`, `target/`。
- 大型 generated/binary artifacts，除非已確認要透過 Git LFS 或部署參考方式追蹤。

如專案另有 `*.jsonl`、`*.pid`、`*.lock` 等 runtime 檔，先審查用途再加入，不要把特定專案的歷史檔名硬寫進通用 skill。

> **與安全審查機制的分工**：安全審查（如 Claude Code 的 `security-review`）檢查**變更內容**
> 有沒有安全問題 —— 屬**事後偵測**；本 skill 讓機密檔案**根本不被追蹤** —— 屬**事前預防**。
> 兩者互補，跑過其一不能取代另一：
>
> - 已提交檔案裡的硬編碼金鑰，**只有安全審查抓得到**
> - 尚未追蹤、但下一個 `git add .` 就會被掃進去的 `.env`，**只有本 skill 擋得住**

#### ⚠️ 需要跟開發者確認 (Ask Before Deciding)

- `.codex/skills/`, `.claude/skills/`, `.agents/skills/`（跨工具：Codex／Gemini CLI／Antigravity 共用）, `.agent/skills/`（1.x）, `.gemini/skills/`：是本機安裝的第三方 skill、project-owned custom skill，還是**工具自動記錄但官方定位為要共享的**？第三類例如 Claude Code 的 `/verify` 會把可用的建置指令寫進 `.claude/skills/verify/SKILL.md`，官方說明為「so later runs and other agents follow the same steps」—— 這類**應該提交**。
  → 完整判準見下方「技能庫 (Skills) 的性質判準」——**先問技能是怎麼來的，不要憑目錄名決定**。
- **Antigravity 工作區 agent 定義**：`.agents/agents/<name>/agent.json`（由 agy 1.0.13 二進位內的路徑模板 `{workspace}/.agents/agents/{agent_name}/agent.json` 證實）。agy 1.0.13 二進位顯示 agents 與 skills 有**完全對稱**的 workspace／global 建立路徑函式，且執行期狀態另有去處，性質看似角色宣告。但**尚無人目視過實體檔案** —— **範本預設不放行**，確認內容是角色宣告而非執行狀態後，再把 `# !.agents/agents/` 的註解拿掉。　**2026-08-09 補充**：欄位結構已由 agy 二進位的 protobuf 定義佐證 —— `name`／`displayName`／`description`／`hidden`／`customAgentSpec{customAgent{systemPromptSections, toolNames}}`，全屬靜態角色宣告，無 session／時間戳等執行期欄位（C-87）。**但仍維持不放行**：無人目視過實體檔案、該目錄下是否還有其他檔案未確認、且實際 key 命名（`custom_agent_spec` 或 `customAgentSpec`）未定。
- **Claude Code 開發伺服器啟動設定**：`.claude/launch.json`（C-83）。內容是具名的啟動指令（`runtimeExecutable`／`runtimeArgs`／`port`），性質等同 `.vscode/launch.json`。**範本預設不放行** —— 它可能寫入個人絕對路徑，而且「要不要公開建置方式」是專案決定。確認過內容是相對路徑後，把範本裡 `# !.claude/launch.json` 的註解拿掉即可。
- `$env:USERPROFILE\.codex\skills\` / `~/.codex/skills/`：這是 user-level Codex skill installation，通常不要整包複製進專案 repo。
- `*.json`：runtime data，還是 `package.json`, `tsconfig.json`, `manifest.json` 這類 source/config？
- `*.json.bak`：可丟棄備份，還是 DEPLOY 文件提到的唯一可還原資料？
- `.vscode/`：個人設定，還是團隊共享的 `extensions.json` / `launch.json`？
- 大型 PDF、XML、export：部署參考，還是已過期的靜態快照？

#### 📦 技能庫 (Skills) 的性質判準

`.claude/skills/`、`.agents/skills/`、`.gemini/skills/` 這類目錄**不能一律提交，也不能一律排除**。
判準是「這個技能是怎麼來的」：

| 來源 | 處置 | 理由 |
| :--- | :--- | :--- |
| CLI 工具安裝的第三方技能（如 `uipro init`） | **不提交**，在 `DEPLOY.md` 記錄安裝指令 | 提交等於把上游的複本釘進 repo，上游更新後就開始漂移 |
| 開發者自行撰寫的客製技能 | **提交** | 是專案的一部分，沒有別的傳承管道 |
| 工具自動產生、但官方定位為要共享的 | **提交** | 例：`/verify` 寫入 `.claude/skills/verify/SKILL.md`，官方說明「so later runs and other agents follow the same steps」 |

**判斷關鍵**：官方文件有沒有講明「讓後續執行或其他 agent 沿用」。
有 → 屬第三類，應提交；沒有 → 回到前兩類，問開發者。

> 🔍 **這個 skill 的誕生原因，就是它自己最好的反例。**
> 維護者在 PM Dashboard 專案使用 `ui-ux-pro-max` 時，是**逐工具各裝一次**的
> （`--ai claude` ＋ `--ai antigravity` ＋⋯⋯），於是同一個技能在專案裡留下**六份**複本：
> `.agent/skills/`、`.agents/skills/`、`.claude/skills/`、`.codex/skills/`、
> `.gemini/skills/`、`.github/prompts/` 各一份。
>
> 2026-08-07 實查證實**已經漂移**：`.agent/` 的 `SKILL.md` 是 `bf780c30`（2026-04-26），
> `.agents/` 的是 `07b87b89`（2026-07-07），內容不同 ——
> 而**沒有任何機制會為此報錯**，本機執行時哪一份生效也不確定。
> 上游其實提供 `--ai universal`，只寫一份到 `.agents/skills/`。
>
> 教訓是：**技能的「份數」比它裝在全域還是專案更關鍵。**
> 審查時看到多份同名技能，那是訊號，不是巧合 —— 先問「為什麼有這麼多份」，再問「要不要提交」。

**必問開發者**：「這個技能是透過 CLI 安裝的、您自己寫的，還是工具自動記錄的？」

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
| 跨平台 fileMode 提示 | DEPLOY.md 無記錄 | 補上 `git config core.fileMode false` 段落 | 第一階段 fingerprint 命中跨平台訊號（Dockerfile + .sh + .ps1 共存） |
| 根目錄散落 runtime 檔 | `last_*.txt`、`*.log` 等散在根目錄 | 方案 A：就地 ignore（本 skill 可直接執行）／方案 B：集中到 `data/` 等目錄（屬架構重構，**超出本 skill 範圍**，僅提出由開發者決定） | 方案 B 牽動程式路徑、排程與部署，須另行評估 |

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
git check-ignore -v .env.production       # 應該被擋：輸出命中的 ignore 規則
git check-ignore -v .env.example          # 應該放行：輸出 `!` 開頭的白名單規則
git check-ignore -v secrets.json          # 應該被擋：輸出命中的 ignore 規則
```

> ⚠️ **判讀規則**：`-v` 模式下「有輸出」**不等於**「被擋」——輸出的規則若以 `!` 開頭代表**放行**（`-v` 對負向規則也會輸出，且 exit code 同樣是 0）。要用 exit code 判斷時，改用不帶 `-v` 的 `git check-ignore -q <path>`：exit 0 = 被擋、exit 1 = 放行。

若 `.env.example` 命中的不是 `!` 開頭的規則、或 `secrets.json` 完全沒被擋，回到步驟 1 修正規則。**驗證沒過就不要進步驟 4**。

4. **補文件前先 grep**：若需要在文件中記錄「clone 後第一次設定步驟」（包含但不限於：技能重新安裝、靜態快照→連結、跨平台 `core.fileMode false` 設定、`chmod +x` 救援等）：

```powershell
Select-String -Path "README.md","DEPLOY.md","CONTRIBUTING.md" -Pattern "core.fileMode|chmod \+x" -SimpleMatch:$false 2>$null
```

   - **已存在** → 直接告知開發者位置（例如「DEPLOY.md 第 X 節已涵蓋」），跳過寫入
   - **不存在** → 詢問開發者要寫到哪份文件再補上；若兩份都沒有，建議寫到 `README.md` 的 Setup 段落
   - **動態資料目錄搬移**：若本次調整（或近期重構）曾搬移 runtime 資料目錄，額外確認 `DEPLOY.md` 已記錄部署安全順序「**停服務 → 拉代碼 → 搬舊資料 → 啟動服務**」— 服務運行中搬移動態檔案會引發排程與去重失效（真實事故教訓）

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

**Renormalize 修不到的「工作樹殘留」**：`git add --renormalize .` 只修**入庫側**（index）；工作樹的實體檔案不會被動。Git 只在 checkout 的瞬間套用 `eol=` 轉換，所以在規則導入**之前**就存在於工作樹、內容又與 index 一致的檔案，永遠不會被自動重寫 — `.gitattributes` 寫著 `*.bat eol=crlf`，硬碟上卻仍是 LF，而且 `git status` 完全乾淨。實際後果（真實案例）：LF 的 `.bat` 含中文時，cmd/CP950 會把中文尾位元組與 LF 配對吞掉，行黏合、指令腰斬（症狀如 `'pull' 不是內部或外部命令`）。

```powershell
# 檢測：逐檔列出 index (i/)、工作樹 (w/)、attr 三方行尾，找 attr 與 w/ 不一致者
git ls-files --eol
# 例：i/lf  w/lf  attr/text eol=crlf  update-skills.bat   ← w/ 應為 crlf，中招

# 修復前先確認沒有內容變更；兩條 diff 都必須無輸出，否則不可刪檔
git diff -- update-skills.bat
git diff --cached -- update-skills.bat

# 修復：只對「內容乾淨但行尾殘留」的檔案刪除後重新 checkout，強制觸發行尾轉換（不會產生任何 diff）
Remove-Item update-skills.bat
git checkout -- update-skills.bat
```

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
# =========================================
# ⚠️ 白名單（! 開頭）預設啟用的門檻：**官方明文說它是團隊共用／要分享的**。
# 依據若是推論、內容觀察或跨工具類比，一律保持「註解狀態」並列入 ⚠️ 需確認 ——
# 路徑事實看得見（不會被靜默漏掉），但提交與否由你決定。
# 註解狀態的規則長這樣：# !.claude/launch.json
# =========================================
# ⚠️ .gitignore 的 # 只有在「行首」才算註解
# 寫成  !.claude/settings.json   # 團隊共用設定
# 會讓整條規則連同註解一起被當成檔名比對而完全失效 —
# 白名單看起來存在，實際上一條都沒生效。註解一律獨立成行。
# 每改完一條規則，務必用 git check-ignore 驗證邊界。
# =========================================
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
# .vscode/extensions.json 與 launch.json 若為團隊共用，應該提交（勿加進 ignore）

# AI Agent 工作區與快取
# 原則：擋「工具自動產生的暫存」，放行「刻意共享的設定 / 規則 / 技能」。
# 多數工具的對話紀錄存在使用者家目錄（如 ~/.claude/projects/），
# 專案內的 dot 資料夾反而以刻意共享的內容為主 — 不要整包封殺。
.claude/*
# 團隊共用設定（權限、hooks）
!.claude/settings.json
# 開發伺服器啟動設定：Claude Code 依此啟動專案（等同 .vscode/launch.json 的地位）。
# 內容是具名的執行指令（runtimeExecutable／runtimeArgs／port），屬專案層級；
# Claude Code 的個人檔一律走 .local.json 後綴，此檔沒有該後綴。
# ⚠️ 預設不啟用 —— 它可能寫入個人絕對路徑，且「要不要公開建置方式」是專案決定，不是路徑事實。
# 看過內容、確認是相對路徑後再取消註解（C-83）
# !.claude/launch.json
# 團隊共用 slash commands
!.claude/commands/
# 團隊共用 subagents
!.claude/agents/
# 團隊共用的分檔規則（官方定位為會被 commit 進共享專案的檔案）
!.claude/rules/
# 僅打開 skills 父目錄；實際 project skill 需用下方 scoped allowlist
!.claude/skills/
.claude/skills/*
# !.claude/skills/<project-skill>/
# !.claude/skills/<project-skill>/**
# /verify 會把可用的建置指令自動寫進此處，官方定位為「so later runs and other
# agents follow the same steps」＝設計上要共享。屬「自動產生但意圖共享」的第三類（C-53）
!.claude/skills/verify/
# 專案層 workflow；對應 user-scope 的 ~/.claude/workflows/，屬團隊共用（C-09）
!.claude/workflows/
# 個人本機設定：即使有上方白名單也 explicit 擋一次
.claude/settings.local.json
# git worktree 的實體工作目錄，執行期產物。官方修過兩條相關的 symlink 逃逸：
#   1. .claude/worktrees 的 committed symlink 可在 repo 外建檔（C-09）
#   2. .claude 這個路徑本身若是 symlink，workflow 儲存與排程任務的寫入
#      都可能被導向專案之外（C-62）—— 範圍比 1 更廣
# 兩者官方皆已修復，但舊版仍受影響：**不要提交 .claude 或 .claude/worktrees 的 symlink**
.claude/worktrees/
# Cursor 已於 2026-08-03 移出本 skill 的維護範圍（維護者未使用該工具）。
# 若你的專案有用 Cursor，需自行補上 .cursor/* 與 !.cursor/rules/ 規則。
# Antigravity 1.x 專案工作區暫存（現行 agy 1.0.13 二進位已 0 命中，保留供舊專案）
.agent/*
# 僅打開 skills 父目錄；實際 project skill 需用下方 scoped allowlist
# 官方僅明載 `.agent/rules` 向後相容，**未提及 skills**；現行 agy 1.0.13 二進位對
# `.agent/` 亦 0 命中。本組依據是實地觀察：舊專案存在第三方安裝器寫入的
# `.agent/skills/<name>/`（C-81）。專案若無此目錄，本組可整組刪除
!.agent/skills/
.agent/skills/*
# !.agent/skills/<project-skill>/
# !.agent/skills/<project-skill>/**
# 舊佈局的工作區規則；官方：「now defaults to .agents/rules, but still maintains
# backward support for .agent/rules」（C-57）
!.agent/rules/
# .agents/ 為跨工具共用目錄，非 Antigravity 專屬：
#   Codex       — 從 CWD 逐層往上掃 .agents/skills；.agents/plugins/marketplace.json 屬團隊共用
#   Gemini CLI  — .agents/skills/ 是 .gemini/skills/ 的別名，且優先權高於後者
#   Antigravity — .agents/hooks.json（工作區層級 hooks）
.agents/*
# 僅打開 skills 父目錄；實際 project skill 需用下方 scoped allowlist
!.agents/skills/
.agents/skills/*
# !.agents/skills/<project-skill>/
# !.agents/skills/<project-skill>/**
# 工作區規則。官方：「Workspace rules live in the .agents/rules folder of your
# workspace or git root」，性質同 .claude/rules/，屬團隊共用（C-57）
!.agents/rules/
# 工作區層級的 MCP server 定義。官方：「Workspace servers: .agents/mcp_config.json」
# （全域版在 ~/.gemini/config/mcp_config.json），屬團隊共用（C-58）
!.agents/mcp_config.json
# 必須先放行父目錄，否則下一行的 marketplace.json 白名單無效
# 專案層自訂子代理定義。agy 1.0.13 二進位有明確路徑模板
# {workspace}/.agents/agents/{agent_name}/agent.json，且執行期狀態另有去處
# （.agents/<type>_<milestone>/ 與家目錄 brain/）。
# ⚠️ 預設不啟用 —— 尚無人目視過實體檔案內容。確認是角色宣告而非執行狀態後再取消註解（C-54）
# !.agents/agents/
!.agents/plugins/
# 外掛本體多為安裝產物，不追蹤
.agents/plugins/*
# Codex 官方定位：「for everyone on a project」
!.agents/plugins/marketplace.json
# ⚠️ 此處原有 `!.agents/AGENTS.md`、`!.agents/settings.json` 兩條白名單，2026-08-04 移除。
# 移除理由：兩者皆為**不存在的檔案**。agy 1.0.13 二進位中 `{workspace}/.agents/` 的路徑
# 模板完整清單只有三條 —— `skills`、`agents`、`ORIGINAL_REQUEST.md`，兩者都不在內；
# 本機五個實際專案的 `.agents/` 亦 0 次出現。Antigravity 只讀**根目錄**的 `AGENTS.md`，
# 專案設定實存於 `~/.gemini/config/projects/<uuid>.json`。
# 為不存在的路徑留白名單會讓讀者誤以為該路徑有效 —— 請勿補回（C-41、C-42）
# agent 會把使用者訊息逐字寫入下列檔案（含 UTC 時間戳），可能含對話中貼過的敏感資訊。
# 已被上方 .agents/* 涵蓋，仍 explicit 列名一次 —— 廣域規則日後若被放寬仍有保護
.agents/ORIGINAL_REQUEST.md
.agents/**/ORIGINAL_REQUEST.md
# .agents/settings.local.json 已移除：實查確認 Antigravity 無此概念，
# 原規則是誤類比 Claude Code 而來（C-43）。該路徑仍被上方 .agents/* 涵蓋。
# 工作區層級 hooks：Antigravity 回報屬專案共用（與家目錄 hooks 合併、專案優先），
# 但實查環境中該檔不存在，此說法尚未直接驗證。內含可執行指令，確認後再放行（C-44）
# !.agents/hooks.json
# Antigravity CLI 舊版工作區對應檔（新版已淘汰，舊專案仍可能殘留）
.antigravitycli/
.codex/*
# 僅打開 skills 父目錄；實際 project skill 需用下方 scoped allowlist
# 專案層設定覆寫（官方：add a .codex/config.toml file in your repo）
!.codex/config.toml
# 專案層 lifecycle hooks 與其腳本；官方將 <repo>/.codex/hooks.json 列為
# 主要的 hooks 位置之一，屬團隊共用（C-17）
!.codex/hooks.json
!.codex/hooks/
# 沙箱指令規則（experimental）：控制哪些指令可在沙箱外執行，屬專案層政策（C-17）
!.codex/rules/
# ⚠️ .codex/skills 未見於官方 skills scope 表（REPO 為 .agents/skills、
# USER 為 $HOME/.agents/skills、ADMIN 為 /etc/codex/skills）。
# 保留為舊版相容路徑；專案技能請優先用上方的 .agents/skills/。見 C-12
!.codex/skills/
.codex/skills/*
# !.codex/skills/<project-skill>/
# !.codex/skills/<project-skill>/**
# ⚠️ 2026-08-03 移除誤植規則：先前依官方 hooks 文件中的一段 token 判定
# .codex/rollout.jsonl 是專案層 session 紀錄 —— 那其實是傳給 hook 的
# 範例 payload（"transcript_path": "/workspace/.codex/rollout.jsonl"），
# 不是真實預設路徑。實際 rollout 在 $CODEX_HOME/sessions/YYYY/MM/DD/
# （CODEX_HOME 預設 ~/.codex），不寫入專案。見 C-17。
.gemini/*
# 僅打開 skills 父目錄；實際 project skill 需用下方 scoped allowlist
# Workspace 設定，與 .claude/settings.json 同性質的專案層共用設定
!.gemini/settings.json
!.gemini/skills/
.gemini/skills/*
# !.gemini/skills/<project-skill>/
# !.gemini/skills/<project-skill>/**
# .github/prompts/ 是 VS Code Copilot 的團隊共享 prompt files (*.prompt.md)，
# 預設「應該提交」；確認內容為個人暫存時才取消下行註解：
# .github/prompts/

# 自動執行日誌（會自動輪替或持續增長，沒有版本控制價值）
*.log

# Runtime 狀態檔（每次執行會覆寫，不該放 Git）
last_*.txt
```

若 project-owned Codex skills 應該被追蹤，使用 allowlist，不要直接忽略整個 `.codex/`：

```gitignore
.codex/*
!.codex/skills/
.codex/skills/*
!.codex/skills/<project-skill>/
!.codex/skills/<project-skill>/**
```

> 💡 **白名單注意事項**：`!` 無法救回「位於已被忽略之**目錄**底下」的檔案，因為 Git 不會進入已忽略的資料夾。
> 例如：`.codex/` 會整包忽略資料夾，此時 `!.codex/skills/` **完全無效**；
> 必須使用 `.codex/*`（只擋直接子項）搭配 `!.codex/skills/` 才能正確放行。同理適用 `.claude/`、`.gemini/` 和其他需要部分追蹤的 AI agent folder。
> 若只想追蹤單一 project skill，還要先用 `.codex/skills/*` 重新擋住 skills 目錄內容，再用 `!.codex/skills/<project-skill>/` 與 `!.codex/skills/<project-skill>/**` 精準放行，避免把本機安裝的第三方 skills 一起提交。
> 檔案型規則不受此限：`*.json` 搭配 `!seed.json` 直接有效，不需要母目錄星號。

---

## 📒 專案追蹤決定表（`git-tracking/MASTER.md`）

上面的範本是**起點**，不是答案。每個專案會產生的檔案不同，「該不該提交」也常常
是專案自己的決定 —— 這份決定必須留在專案裡，否則每次執行都要重問一輪，
而刻意的偏離會被誤判成漂移。

作法比照 `ui-ux-pro-max` 的 `design-system/MASTER.md`：**技能是方法，決定留在專案**。

### 執行時做三方比對

```text
① git-tracking/MASTER.md  這個專案先前的決定
② 本技能目前的路徑事實    工具官方怎麼定位這條路徑（會隨工具改版更新）
③ git check-ignore        .gitignore 現在實際上擋不擋
```

**三者一致 → 不必報告。任兩者不一致 → 列進報告，但不要自動改。**

三種不一致各代表不同的事，處置也不同：

| 不一致 | 意思 | 該做什麼 |
| :--- | :--- | :--- |
| ① ≠ ③ | 決定過，但 `.gitignore` 沒照做（或後來被改掉） | 修 `.gitignore` |
| ② ≠ ③、① 沒記載 | 工具有這條路徑，本專案從沒決定過 | 問開發者，然後記進 ①（**最常見**） |
| ② 變了、① 有記載 | 工具改版，原決定的前提可能不成立 | 帶著新事實重問一次 |

> 沒有 ① 的專案，第一次執行時先建立它 —— 把現行 `.gitignore` 的既有決定補記進去，
> 而不是推倒重來。既有決定多半有理由，只是沒寫下來。

### 檔案格式

```markdown
# Git 追蹤決定表 (MASTER)

> **LOGIC**：本檔記錄「這個專案」對各路徑的追蹤決定，**優先於技能的預設範本**。
> 技能每次執行時做三方比對（本檔 ↔ 技能的路徑事實 ↔ `git check-ignore`），
> 只報告不一致處，不自動修改。

**專案**：<專案名>
**建立**：YYYY-MM-DD
**最後比對**：YYYY-MM-DD

## A. AI 工具路徑

| 路徑 | 決定 | 理由 | 決定日 |
| :--- | :--- | :--- | :--- |
| `.claude/skills/<自建技能>/` | 提交 | 自建團隊技能，需跨裝置同步 | 2026-07-11 |
| `.agent/skills/ui-ux-pro-max/` | 排除 | CLI 安裝，安裝指令記於 `DEPLOY.md` | 2026-07-11 |

## B. 本專案特有的產出物

| 路徑 | 決定 | 理由 | 決定日 |
| :--- | :--- | :--- | :--- |
| `data/*`（保留 `.gitkeep`） | 排除 | runtime 資料，非原始碼 | 2026-07-11 |

## C. 刻意偏離技能預設之處　⭐

| 路徑 | 技能預設 | 本專案 | 為什麼 |
| :--- | :--- | :--- | :--- |
| `.claude/settings.json` | 提交（團隊共用） | 排除 | 本專案不共用權限設定 |

## D. 尚未決定

| 路徑 | 卡在哪 |
| :--- | :--- |
| `.claude/launch.json` | 需先確認裡面沒有個人絕對路徑 |
```

**C 節是這份檔最重要的部分。** 沒有記錄的偏離，下次比對只會看到「和技能預設不一樣」，
於是重問一次；記下來之後，它就是一個有理由的決定，不再是待辦。

### 用 CI 鎖住決定 —— 以及一個會讓它靜默失效的寫法

決定表記錄「該怎樣」，CI 可以強制「真的就是這樣」：在 workflow 裡對關鍵路徑下斷言，
`.gitignore` 若被改到讓決定失效，CI 直接失敗。這是很值得做的一層防護。

**但斷言本身會靜默失效。** 直覺寫法是這樣：

```yaml
- shell: bash
  run: |
    ! git check-ignore -q .claude/launch.json     # ❌ 這行永遠不會讓 CI 失敗
```

GitHub Actions 的 `shell: bash` 等同 `bash -eo pipefail`，而 `set -e` 的例外明載
包含「**回傳值被 `!` 反轉時不中止**」。所以這條斷言不論結果如何都不會擋下 CI ——
決定失效了，綠燈照給。

**可用的寫法**：顯式比對，並一次列出所有不符項（只報第一條會讓人修一輪跑一輪）。

```yaml
- shell: bash
  run: |
    fail=0
    check() {  # $1=路徑  $2=預期（ignored / tracked）
      if git check-ignore -q "$1"; then actual=ignored; else actual=tracked; fi
      if [ "$actual" != "$2" ]; then
        echo "❌ $1：預期 $2，實際 $actual"
        fail=1
      fi
    }
    check .claude/launch.json          tracked
    check .claude/skills/thirdparty/   ignored
    exit $fail
```

> ⚠️ 這與稍早提過的 `git check-ignore -v` 退出碼問題是**同一個坑的兩種面貌**：
> `-v` 只要命中任何規則（**包含 `!` 開頭的放行規則**）就回傳 0；
> `! cmd` 則是反轉後的失敗不觸發 `set -e`。
> **判定擋或放行一律用不含 `-v` 的 `git check-ignore -q`，且不要靠 `!` 反轉。**

**驗收方式**：寫完斷言後，故意把某條決定改壞（例如刪掉一條 `!` 放行規則），
確認 CI 真的會紅。**沒被驗證過的斷言，跟沒有斷言一樣。**

### 這份檔要提交

它是專案的判斷依據，不是個人設定 —— 團隊成員與未來的你都需要它。
若專案用不到跨裝置協作，也至少讓下一次執行的 AI 讀得到。

---

## 救援指令 (Rescue Commands)

如果 AI workspace 或 runtime log 已被追蹤：

```powershell
# --ignore-unmatch 必加：沒加的話，只要清單中任何一個路徑不在 index，
# 整條指令會 fatal 中止、「一個檔案都不會移除」
# .agent / .agents / .codex / .gemini / .claude / .github/prompts
# 可能內含團隊共用內容（settings.json、rules/、skills/、*.prompt.md），不要整包移除。
# 先審查，再用精準路徑處理，例如 .claude/settings.local.json 或已確認的 runtime/cache 子目錄。
# 將 path/to/confirmed-ai-runtime-dir 替換成審查後確認的實際 runtime/cache 路徑。
git rm -r --cached --ignore-unmatch path/to/confirmed-ai-runtime-dir
git rm --cached --ignore-unmatch '*.log'   # 引號讓 git 對 pathspec 遞迴比對（PowerShell 本來就不展開裸 glob）
git add .gitignore .gitattributes
git diff --cached --stat
git diff --cached --summary
git commit -m "chore: 清理 AI 工作區與 runtime 追蹤紀錄"
```

如果機密或大檔已經 push 到歷史中，先說明風險並詢問，再使用 `git filter-repo` 等工具改寫歷史。
