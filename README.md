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
| GitHub Copilot (VS Code) | 無單一固定目錄；依專案放在 `.github/copilot-instructions.md` 或 prompts 目錄 | ❌（需手動部署） |

> 💡 如果某 AI 工具**沒有**對應版本（例如一個 skill 只寫了 generic 版），安裝器會自動把 generic 版鋪給該工具作為 fallback。
>
> ⚠️ **VS Code Copilot 不支援自動安裝**：Copilot 沒有像 `~/.claude/skills/` 這種使用者層級的單一 skills 目錄，安裝器不處理 `vscode/` 變體。若要使用 vscode 版內容，請手動把 `skills/<skill-name>/vscode/SKILL.md` 的內容貼進專案的 `.github/copilot-instructions.md`，或專案約定的 prompts 目錄。

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
