# 文件端查證：Codex 與 Copilot — 2026-08-03

**交接包**：[`2026-08-03-cross-tool-review.md`](./2026-08-03-cross-tool-review.md) 第 3-3、3-4 節
**執行者**：Claude Code（維護者側）

> 這兩個工具無法由我扮演作答，但**多數問題官方文件就查得到**。
> 本文件先把文件端能定案的做掉，把交給工具本身的問題縮到最小。
> 未能由文件定案者一律標為「**待工具確認**」，不猜測。

---

## Codex

| 題 | 結論 | 依據 |
| :--- | :--- | :--- |
| Q1 專案層 config／hooks／rules 是否都在 `.codex/` 下 | ✅ **確認** | 官方 config-reference：「Untrusted projects skip project-scoped `.codex/` layers, including project-local **config, hooks, and rules**」；hooks 指南列出 `<repo>/.codex/hooks.json`、`.codex/hooks/*.py`；rules 指南列出 `rules/` 資料夾與 `.rules` 副檔名 |
| Q3 `.agents/skills` 掃描規則 | ✅ **確認** | 官方：「Codex scans `.agents/skills` in every directory from your current working directory up to the repository root」 |
| Q4 外掛本體位置 | ✅ **確認** | 官方：「for everyone on a project with `.agents/plugins/marketplace.json` and **a repo-local plugin directory such as `./plugins/`**」 |
| Q2 `.codex/` 還有什麼自動產生物 | ⚠️ **部分** | 已知 `.codex/rollout.jsonl`（session 執行期紀錄，C-17 已涵蓋）。**其餘待工具確認** |

**待 Codex 確認**：專案層 `.codex/` 除 `config.toml`、`hooks.json`、`hooks/`、`rules/`、
`rollout.jsonl` 之外，是否還有 cache、索引、session 等自動產生物。

---

## VS Code / GitHub Copilot

### Q1　四種自訂檔是否完整 → ❌ **不完整，實際有六類**

官方 customization 頁列出擴充支援四種檔案（`SKILL.md`／`*.agent.md`／
`*.instructions.md`／`*.prompt.md`），但另一段把自訂型別講得更全：

> This applies to all customization types: always-on instructions
> (`copilot-instructions.md`, `AGENTS.md`, `CLAUDE.md`), file-based instructions,
> prompt files, custom agents, **agent skills, and hooks**.

→ 交接包原本列的五類漏了 **skills** 與 **hooks**。

### Q2　各類自訂檔的存放位置 → ✅ **官方直接給了目錄結構**

```text
my-monorepo/                      # repo root (has .git folder)
├── .github/
│   ├── copilot-instructions.md
│   ├── instructions/
│   │   └── style.instructions.md
│   ├── prompts/
│   │   └── review.prompt.md
│   └── agents/
│       └── reviewer.agent.md
```

另兩類的位置在各自的專門頁：

| 類別 | Workspace | User |
| :--- | :--- | :--- |
| Skills | **`.github/skills/`**、`.claude/skills/`、`.agents/skills/` | `~/.copilot/skills/`、`~/.claude/skills/`、`~/.agents/skills/` |
| Hooks | **`.github/hooks/*.json`**、`.claude/settings.json`、`.claude/settings.local.json` | `~/.copilot/hooks`、`~/.claude/settings.json` |

### 🔴 重大發現：Copilot 是 `.claude/` 與 `.agents/` 的**跨工具消費者**

官方明載 Copilot 會讀取：

- `.claude/skills/`、`.agents/skills/`（專案層技能）
- `~/.claude/skills/`、`~/.agents/skills/`（使用者層技能）
- **`.claude/settings.json`、`.claude/settings.local.json`**（Claude 格式的 hooks）

意義有二：

1. 本 skill 原本把 `.claude/` 視為 Claude Code 專屬 —— **不成立**。
   繼 C-60 確認 `.agents/` 是跨工具目錄之後，`.claude/` 同樣是跨工具的。
2. `.claude/skills/*` 的 scoped allowlist（擋第三方、放行自撰）**同時影響 Copilot**，
   不只影響 Claude Code。這讓那條規則的重要性提高。

### Q3　Copilot 是否在專案產生 cache／log → ✅ **實機確認**

skills 與 hooks 兩頁**均未提及**專案層的 cache 或 log。唯一出現的 `.log`
是官方範例中「**使用者自行設定**的 hook 把稽核日誌寫到 `.github/hooks/audit.log`」——
那是使用者行為，不是工具自動產生。

文件沒提到不等於不存在；因此已由 VS Code 1.125.1／Copilot Chat 0.53.1 的 active
agent session 實查補足。session、transcript、debug log 與 editing state 實際落在
`<VS Code user-data>/User/workspaceStorage/<workspace-id>/`，global cache 落在同一份
user data 的 `globalStorage/`，不是 repository。同期 `git status` 未出現新的 Copilot
runtime 檔。詳見 [VS Code 實機回覆](./2026-08-03-vscode-copilot.reply.md)。

### Q4　`~/.copilot/skills/` 是否正確 → ✅ **確認（依據升級）**

官方 skills 頁把 `~/.copilot/skills/` 明列為 Personal skills 位置。

> 📌 此前 C-74 的依據是「本專案安裝器寫過這個路徑」—— 那是**循環證據**
> （與先前 C-48 犯的錯同型）。現已改為官方文件佐證。

---

## 本輪帳本異動

| 帳本 | 異動 |
| :--- | :--- |
| C-72、C-73 | 補上具體位置：`.github/instructions/`、`.github/agents/` |
| C-74 | 依據由「實機（安裝器）」升級為「官方文件」 |
| **C-75** | 新增 —— `.github/skills/`：Copilot 專案層技能 |
| **C-76** | 新增 —— `.github/hooks/*.json`：Copilot 工作區 hooks（含可執行指令） |
| **C-77** | 新增 —— Copilot 跨工具讀取 `.claude/`、`.agents/` |
| **C-78** | 新增 —— Copilot runtime session／log／cache 位於 VS Code user data，非 repository；不需新增 project `.gitignore` 規則 |
| C-17 | 維持；Codex Q2 的其餘部分列為待工具確認 |

## 監控補強

`TOKEN_RE` 原本只涵蓋 `.github/prompts`，其餘 `.github/` 子目錄與 `~/.copilot/*`
**都抓不到**。已擴充為 `prompts|skills|hooks|instructions|agents`，並把 `copilot`
加入 dot-name 清單。

## 仍需交給工具本身的問題

| 工具 | 問題 |
| :--- | :--- |
| Codex | 專案層 `.codex/` 除已知五項外，還有什麼自動產生物？ |

Copilot Q3 已由 [VS Code 實機回覆](./2026-08-03-vscode-copilot.reply.md) 定案；其餘問題已由官方文件定案，無需再問。
