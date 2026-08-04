# dev-ai-skills

> 集中管理跨 AI 代理工具（Antigravity、Claude Code、GitHub Copilot、Codex⋯⋯）的 **Skills** 技能庫。
>
> 每個 skill 依工具提供專用版本：`antigravity/`（Gemini / Antigravity 專用）、`claude/`（Claude Code 專用）、`vscode/`（GitHub Copilot / VS Code 專用）、`codex/`（Codex 專用）、`generic/`（工具無關的通用版本，供其他 AI 工具 fallback）。

---

## 📦 目前提供的技能

| 技能 | 用途 | 版本狀態 |
| :--- | :--- | :---: |
| [`ai-git-ignore-strategy`](./skills/ai-git-ignore-strategy/) | Git 追蹤審查與 `.gitignore` / `.gitattributes` 最佳實務 | Antigravity / Claude / VS Code / Codex / Generic |

---

## 🚀 快速安裝

### Linux / macOS

```bash
git clone https://github.com/ldsAS/dev-ai-skills.git
cd dev-ai-skills

# 一鍵：自動偵測所有已安裝的 AI 工具並鋪上對應版本
./install.sh

# 只裝某一個工具的版本
./install.sh claude        # 只裝 Claude 版到 ~/.claude/skills/
./install.sh antigravity   # 只裝 Antigravity 版到 ~/.gemini/config/skills/ (2.0) 與/或 ~/.gemini/antigravity/skills/ (1.x)
./install.sh codex         # 裝到 ~/.agents/skills/（Codex 官方 USER 路徑，generic 版）
./install.sh vscode        # 強制裝 vscode 版到 ~/.copilot/skills/
./install.sh generic       # 只裝 generic 版（鋪到所有偵測到的 AI 工具，作為 fallback）

# 專案層：只寫 <repo>/.agents/skills/ 單一份
./install.sh --project                     # 當前目錄
./install.sh --project /path/to/repo
```

### Windows (PowerShell)

```powershell
git clone https://github.com/ldsAS/dev-ai-skills.git
cd dev-ai-skills

# 一鍵自動偵測
# 💡 若遇到 Execution Policy 權限報錯，請改用：powershell -ExecutionPolicy Bypass -File .\install.ps1
.\install.ps1

# 指定工具
.\install.ps1 claude
.\install.ps1 antigravity
.\install.ps1 codex
.\install.ps1 vscode       # 強制裝 vscode 版到 ~/.copilot/skills/
.\install.ps1 generic

# 專案層：只寫 <repo>\.agents\skills\ 單一份
.\install.ps1 project
.\install.ps1 project C:\path	oepo
```

---

## 📂 安裝邏輯

安裝器是 **Copy 模式**（不是 symlink）—— 更新 repo 後要重跑 `install.sh` / `install.ps1`，新版本才會鋪到各工具的 skills 目錄。

### 兩條原則

1. **一個工具一份。** 同名技能在多條路徑各放一份，之後只會各自過期、彼此不一致，
   而且不會有任何機制報錯。Codex 官方明載同名技能**不會合併**，多份等於多個候選。
2. **共用路徑放 generic 版。** `~/.agents/skills/` 同時被 Codex、Gemini CLI、Copilot 讀取，
   放任一工具的專屬變體，其他工具就會讀到寫著別人工具名的內容（C-79）。

### 全域安裝：路徑對照（唯一真相來源）

| AI 工具 | 讀取路徑 | 安裝器寫入 | 帳本 |
| :--- | :--- | :--- | :--- |
| Claude Code | `~/.claude/skills/` | ✅ `claude` 版 | C-06 |
| Antigravity CLI | `~/.gemini/config/skills/` | ✅ `antigravity` 版 | C-47 |
| Antigravity IDE | `~/.gemini/antigravity/skills/` | ✅ `antigravity` 版 | C-48 |
| Codex | `~/.agents/skills/` | ✅ `generic` 版 | C-12、C-64 |
| Gemini CLI | `~/.agents/skills/` | ↑ **同一份**，不另外裝 | C-22 |
| GitHub Copilot | `~/.agents/skills/` | ↑ **同一份**，不另外裝 | C-77 |

> Antigravity 的兩條全域路徑**都要寫** —— 它們是不同產品（IDE 與 CLI），不是新舊關係。
> 2026-07-30 曾誤判為新舊而改成 fallback，導致技能在 IDE 端失效（C-48）。

### 舊版相容路徑：不主動建立

| 路徑 | 為什麼降級 | 行為 |
| :--- | :--- | :--- |
| `~/.codex/skills/` | Codex 官方 skills scope 表**沒有這條**（C-12） | 只在**已經裝過本專案技能**時才續寫 |
| `~/.copilot/skills/` | Copilot 同樣讀 `~/.agents/skills/`（C-77） | 同上 |

> ⚠️ 判準是「**這個目錄裡已經有我們的技能**」，不是「目錄存在」。
> `~/.codex/skills/` 底下有 Codex 內建的 `.system/`，該目錄永遠存在 ——
> 若用「目錄存在」當判準，你手動刪掉的舊複本會在下次安裝時復活。

**想收掉舊複本**：直接刪掉那個技能資料夾就好，安裝器不會再把它裝回來。

### 專案層安裝

只寫 `<repo>/.agents/skills/` **單一路徑、單一份** —— 即上游 `uipro init --ai universal`
的作法，不逐工具各裝一次。適合團隊要把審查流程的版本釘進 repo 時使用。

裝完會提示兩件必須手動做的事：

1. 在專案 `.gitignore` 加 scoped allowlist 放行剛裝的技能（否則會被本 skill 自己的規則擋掉）
2. 在專案 `AGENTS.md` 寫明使用時機 —— 專案層技能不該只靠觸發詞被撞到

### 查自己現在裝了幾份

```powershell
"$env:USERPROFILE\.claude\skills","$env:USERPROFILE\.agents\skills","$env:USERPROFILE\.gemini\config\skills",
"$env:USERPROFILE\.geminintigravity\skills","$env:USERPROFILE\.codex\skills","$env:USERPROFILE\.copilot\skills" |
  ForEach-Object { if (Test-Path "$_i-git-ignore-strategy") { $_.Replace($env:USERPROFILE,'~') } }
```

```bash
for d in ~/.claude/skills ~/.agents/skills ~/.gemini/config/skills          ~/.gemini/antigravity/skills ~/.codex/skills ~/.copilot/skills; do
  [ -d "$d/ai-git-ignore-strategy" ] && echo "$d"
done
```

照上表，**正常情況應該是四條**：`~/.claude`、`~/.gemini/config`、`~/.gemini/antigravity`、`~/.agents`。
多出來的就是舊版相容路徑的殘留，可以直接刪。

> 💡 如果某 AI 工具**沒有**對應版本（例如一個 skill 只寫了 generic 版），安裝器會自動把 generic 版鋪給該工具作為 fallback。

---

## 🔄 更新已安裝的 skills

因為是 **Copy 模式**，**source repo 更新後不會自動同步到 AI 工具的 skills 目錄**。必須手動跑一次 `git pull` + 安裝器。

### Windows（推薦：雙擊 `update-skills.bat`）

```bat
:: 在檔案總管雙擊 update-skills.bat 即可（會 git pull + install.ps1 + pause 顯示結果）
```

或用 PowerShell 一行指令：

```powershell
cd "<你的 dev-ai-skills 路徑>"; git pull; .\install.ps1
```

### Linux / macOS

```bash
cd <你的 dev-ai-skills 路徑>
git pull && ./install.sh
```

> 💡 **指定單一工具更新**：在指令尾巴加參數即可（`claude` / `antigravity` / `codex` / `vscode` / `generic`）。例如 Windows 只更新 Claude 版：`.\install.ps1 claude`。

---

## 🤝 想新增 / 修改 Skill？

請閱讀 [CONTRIBUTING.md](./CONTRIBUTING.md)，裡面說明：

- 每個 skill 必須提供的目錄結構
- `SKILL.md` 的 frontmatter 規範
- 送 PR 前的自我檢查清單

---

## 📁 Repo 結構

```text
dev-ai-skills/
├── README.md               # 你正在讀的這份
├── CONTRIBUTING.md         # 新技能貢獻規範
├── LICENSE                 # MIT
├── install.sh              # Linux / macOS 安裝器
├── install.ps1             # Windows 安裝器
├── update-skills.bat       # Windows 一鍵更新啟動器（雙擊執行 git pull + install.ps1）
└── skills/
    ├── ai-git-ignore-strategy/
    │   ├── README.md
    │   ├── antigravity/SKILL.md
    │   ├── claude/SKILL.md
    │   ├── codex/SKILL.md
    │   ├── vscode/SKILL.md
    │   └── generic/SKILL.md
    └── (未來新增的 skill...)
```

---

## 📜 授權

[MIT License](./LICENSE)
