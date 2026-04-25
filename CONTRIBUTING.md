# 貢獻指南 (Contributing)

感謝您願意為 `dev-ai-skills` 新增或改進技能！本文件說明每個 skill 必須遵守的結構、格式與自我檢核清單。

---

## 🏗 Skill 資料夾結構（必須）

每個 skill 都應提供工具專用版本與通用 fallback 的 `SKILL.md`：

```text
skills/<skill-name>/
├── README.md              # [必要] skill 簡介 + 各版本差異說明
├── antigravity/
│   └── SKILL.md           # [必要] Antigravity / Gemini 專用版（用 view_file, list_dir 等工具名）
├── claude/
│   └── SKILL.md           # [必要] Claude Code 專用版（用 Read, Edit, Bash, Glob 等工具名）
├── codex/
│   └── SKILL.md           # [必要] Codex 專用版（用 functions.shell_command, apply_patch 等工具名）
├── vscode/
│   └── SKILL.md           # [必要] GitHub Copilot / VS Code 專用版（用 read_file, run_in_terminal 等工具名）
└── generic/
    └── SKILL.md           # [必要] 工具無關版本（不指名工具，用「讀取檔案」「執行 git 指令」等通用描述）
```

**名稱規範**：`<skill-name>` 使用 **kebab-case**（小寫連字號），例如 `ai-git-ignore-strategy`、`pr-review-helper`。

---

## 📋 SKILL.md Frontmatter 規範

每個 `SKILL.md` 檔案開頭必須有下列 YAML frontmatter：

```markdown
---
name: skill-name-in-kebab-case
description: 一段清楚說明這個 skill 的用途與觸發時機的描述。越清楚越容易被 AI 正確使用 — 列出關鍵字（「當使用者說 X、Y、Z 時觸發」）會非常有幫助。
---

# Skill 內容從這裡開始...
```

| 欄位 | 必要 | 說明 |
| :--- | :---: | :--- |
| `name` | ✅ | 與資料夾名稱完全一致，kebab-case |
| `description` | ✅ | 觸發條件描述。長度 100-500 字中文為佳。列出關鍵字可大幅提高 AI 挑選準確率 |

> 💡 **各版本的 `description` 可以幾乎一樣**，但 body 內容會因工具差異而不同。

---

## 🔧 各版本的差異應該是什麼

| 版本 | 應該包含 | 不應包含 |
| :--- | :--- | :--- |
| `antigravity/SKILL.md` | Antigravity 特有的工具名（`view_file`, `list_dir`, `@skill-name` 觸發語法） | Claude 專屬工具名 |
| `claude/SKILL.md` | Claude Code 工具名（`Read`, `Edit`, `Bash`, `Glob`, `Grep`, `Write`）、`/skill-name` slash command | Antigravity 專屬工具名 |
| `codex/SKILL.md` | Codex 工具與規則（`functions.shell_command`, `multi_tool_use.parallel`, `apply_patch`, sandbox escalation, `~/.codex/skills/`） | Claude / Antigravity / VS Code 專屬工具名 |
| `vscode/SKILL.md` | GitHub Copilot / VS Code 工具名（`read_file`, `list_dir`, `grep_search`, `run_in_terminal`, `replace_string_in_file`） | Claude / Antigravity / Codex 專屬工具名 |
| `generic/SKILL.md` | 工具無關的描述（「讀取檔案內容」「列出目錄」「執行 git 指令」） | ❌ 任何具體工具名 |

---

## ✅ 送 PR 前的自我檢核清單

在開 Pull Request 之前，請確認：

- [ ] 各版本 `SKILL.md` 都有正確的 frontmatter（`name` + `description`）
- [ ] 各版本 `name` 欄位與資料夾名稱完全一致
- [ ] `antigravity/SKILL.md` 沒有出現 Claude 專屬工具名（如 `Read`, `Edit`, `Bash`）
- [ ] `claude/SKILL.md` 沒有出現 Antigravity 專屬工具名（如 `view_file`, `list_dir`）
- [ ] `codex/SKILL.md` 清楚記錄 Codex 的 `apply_patch`、`functions.shell_command`、sandbox escalation 與精準 staging 規則
- [ ] `vscode/SKILL.md` 沒有混入 Claude / Antigravity / Codex 專屬工具名
- [ ] `generic/SKILL.md` 沒有出現**任何**具體工具名
- [ ] 撰寫 `skills/<skill-name>/README.md` 說明各版本差異與使用時機
- [ ] 在 repo 根目錄的 [`README.md`](./README.md) 「目前提供的技能」表格中新增一行
- [ ] 本機跑過 `./install.sh` 驗證安裝器能正確鋪到所有目標目錄

---

## 🧪 本機測試

```bash
# 從乾淨狀態開始
rm -rf ~/.claude/skills/<your-skill-name>
rm -rf ~/.gemini/antigravity/skills/<your-skill-name>
rm -rf ~/.codex/skills/<your-skill-name>

# 執行安裝器
./install.sh

# 驗證結果
ls -la ~/.claude/skills/<your-skill-name>/
ls -la ~/.gemini/antigravity/skills/<your-skill-name>/
ls -la ~/.codex/skills/<your-skill-name>/

# 在實際 AI 工具中觸發，看是否能正確引用 skill
```

---

## 🎨 撰寫風格建議

- **優先用繁體中文**，術語與 CLI 指令保留原文
- **使用表格與標題結構**，避免單一大段落
- **給 AI 明確的 workflow**（第一階段 → 第二階段 → ...），而不是抽象原則
- **加入「❌ 不要這樣做」的反例**，比只寫「✅ 應該這樣做」有效
- **引用檔案路徑用 Linux 格式**（`/home/user/...`），即使在 Windows 上使用

---

## 📝 新增 Skill 的範例流程

```bash
# 1. 建立資料夾骨架
mkdir -p skills/my-new-skill/{antigravity,claude,codex,vscode,generic}

# 2. 撰寫各版本 SKILL.md（可以先寫 generic 版再往各工具 port）
$EDITOR skills/my-new-skill/generic/SKILL.md
$EDITOR skills/my-new-skill/claude/SKILL.md
$EDITOR skills/my-new-skill/antigravity/SKILL.md
$EDITOR skills/my-new-skill/codex/SKILL.md
$EDITOR skills/my-new-skill/vscode/SKILL.md

# 3. 撰寫 skill 的 README
$EDITOR skills/my-new-skill/README.md

# 4. 更新根 README 的技能清單表格
$EDITOR README.md

# 5. 本機測試安裝
./install.sh

# 6. commit + PR
git checkout -b add-my-new-skill
git add skills/my-new-skill README.md
git commit -m "feat: 新增 my-new-skill 技能"
git push -u origin add-my-new-skill
gh pr create
```

歡迎提 issue 討論新技能點子！
