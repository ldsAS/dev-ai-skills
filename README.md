# dev-ai-skills

> 集中管理跨 AI 代理工具（Antigravity、Claude Code、GitHub Copilot、Codex、Cursor⋯⋯）的 **Skills** 技能庫。
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
./install.sh antigravity   # 只裝 Antigravity 版到 ~/.gemini/antigravity/skills/
./install.sh codex         # 只裝 Codex 版到 ~/.codex/skills/
./install.sh generic       # 只裝 generic 版（鋪到所有偵測到的 AI 工具，作為 fallback）
```

### Windows (PowerShell)

```powershell
git clone https://github.com/ldsAS/dev-ai-skills.git
cd dev-ai-skills

# 一鍵自動偵測
.\install.ps1

# 指定工具
.\install.ps1 claude
.\install.ps1 antigravity
.\install.ps1 codex
.\install.ps1 vscode       # 只裝 VS Code Copilot 版到 ~/.copilot/skills/
.\install.ps1 generic
```

---

## 📂 安裝邏輯

安裝器是 **Copy 模式**（不是 symlink） — 更新 repo 後需要重跑 `install.sh` / `install.ps1` 才會把新版本鋪到 AI 工具的 skills 目錄。

| AI 工具 | Skills 目標目錄 | 自動安裝 |
| :--- | :--- | :---: |
| Claude Code | `~/.claude/skills/<skill-name>/` | ✅ |
| Antigravity | `~/.gemini/antigravity/skills/<skill-name>/` | ✅ |
| Codex | `~/.codex/skills/<skill-name>/` | ✅ |
| GitHub Copilot (VS Code) | `~/.copilot/skills/<skill-name>/`（原生掃描路徑）| ✅ `vscode` 模式 |

> 💡 如果某 AI 工具**沒有**對應版本（例如一個 skill 只寫了 generic 版），安裝器會自動把 generic 版鋪給該工具作為 fallback。
>
> ℹ️ **VS Code Copilot 掃描邏輯**：Copilot 原生會掃描 `~/.copilot/skills/`、`~/.agents/skills/`、`~/.claude/skills/` 三個個人層級路徑。使用 `install.ps1 vscode`（或 `auto`）會將 vscode 版裝到 `~/.copilot/skills/`，確保 Claude Code 的 `~/.claude/skills/` 保持 Claude 版，兩者互不干擾。

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
