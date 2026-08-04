# 交接包：移除舊路徑後的載入實查 — 2026-08-04

**要問的工具**：Codex、GitHub Copilot（各一題）、Antigravity（一題，可選）
**性質**：(c) 類漂移 —— 官方文件與實機行為是否相符
**為什麼要問**：我們剛剛**主動移除了兩條安裝路徑**，依據是官方文件。
若文件說法與實機不符，技能會**無聲消失**，沒有任何錯誤訊息。

> 📌 回答時**請附上你的工具版本號**。沒有版本號的回報無法證偽
> （日後文件與紀錄不符時，分不清是文件寫錯、當時版本較舊、還是後來改掉了），
> 依本專案規則一律視為「未驗證」。
>
> 📌 **請以實機查核為準**，不要用「其他工具是這樣所以我大概也是」的類比推論。
> 若你查不到、或只能推測，請直接說「查不到」—— 那也是有價值的答案。

---

## 背景（你沒有這個專案的上下文，以下自帶）

有一個開源 repo `dev-ai-skills`，維護一個名為 `ai-git-ignore-strategy` 的技能，
提供五種工具變體（antigravity／claude／codex／generic／vscode）。

它原本用安裝器把技能複製到**六條**使用者層路徑。2026-08-04 收斂為**四條**：

| 路徑 | 現在 | 變體 |
| :--- | :--- | :--- |
| `~/.claude/skills/` | ✅ 保留 | claude |
| `~/.gemini/config/skills/` | ✅ 保留 | antigravity |
| `~/.gemini/antigravity/skills/` | ✅ 保留 | antigravity |
| `~/.agents/skills/` | ✅ 保留 | generic |
| `~/.codex/skills/` | ❌ **複本已刪除** | （原為 codex） |
| `~/.copilot/skills/` | ❌ **複本已刪除，目錄也移除** | （原為 vscode） |

刪除的依據是官方文件：

- Codex 官方 skills scope 表列的 USER 路徑是 `$HOME/.agents/skills`，
  `.codex/skills` 在該表**出現 0 次**
- Copilot 官方 agent-skills 頁把 `~/.copilot/skills/`、`~/.claude/skills/`、
  `~/.agents/skills/` 三者並列為 Personal skills 位置

也就是說：**我們相信 `~/.agents/skills/` 這一份就足以讓你們兩個都讀到。**
這個假設如果錯了，技能就從你的環境消失了。

---

## 3-1　給 Codex 的問題

**Q1. 你現在載入得到 `ai-git-ignore-strategy` 這個技能嗎？如果有，是從哪個路徑載入的？**

請實際查核，不要只看文件。可參考的做法：列出目前可用的 skills、
或列出你實際掃描的 skill 路徑與各路徑下的內容。

回報請包含：

- 你的版本號
- 有沒有載入到這個技能
- **實際的載入路徑**（絕對路徑）
- `~/.codex/skills/` 目前的內容（該目錄應該還在，因為底下有你的內建 `.system/`，
  但我們裝的 `ai-git-ignore-strategy` 已被刪除）—— 這個路徑你到底會不會掃？

---

## 3-2　給 GitHub Copilot (VS Code) 的問題

**Q1. 你現在載入得到 `ai-git-ignore-strategy` 這個技能嗎？如果有，是從哪個路徑載入的？**

背景補充：`~/.copilot/skills/` 這個**目錄已經整個被移除**（不只是刪掉裡面的技能）。
我們預期你改從 `~/.agents/skills/` 讀到同一個技能（generic 變體）。

回報請包含：

- 你的 VS Code 版本與 Copilot Chat 擴充版本
- 有沒有載入到這個技能
- **實際的載入路徑**（絕對路徑）
- 你實際掃描哪幾條使用者層 skill 路徑

> 附帶一問：先前查證顯示你會同時讀 `~/.copilot/skills/`、`~/.claude/skills/`、
> `~/.agents/skills/`。刪除前你應該會看到**三份同名**的 `ai-git-ignore-strategy`。
> 現在應該只剩一份（`~/.claude/skills/` 的 claude 變體與 `~/.agents/skills/` 的
> generic 變體）—— 實際上你看到幾份？同名時你怎麼處理？

---

## 3-3　給 Antigravity 的問題（可選，與上面無關）

這題與路徑移除無關，是帳本裡**最後一條依據不足的白名單**。

**Q1. `{workspace}/.agents/agents/{agent_name}/agent.json` 這個檔案，實際內容長什麼樣？**

已知（來自 agy 1.0.13 二進位內的字串）：

- 存在明確路徑模板 `{workspace}/.agents/agents/{agent_name}/agent.json`
- 有全域對應 `{appDataDir}/agents/{agent_name}/agent.json`
- 有 `writing agent.json`／`marshaling agent.json` 字串

**但沒有人看過真實檔案。** 本 skill 目前把 `.agents/agents/` 列為**應提交**（白名單放行），
理由是它看起來像使用者發起的角色宣告，而非執行期狀態。

請實際建立一個 workspace 層級的自訂 agent，然後：

- 貼出產生的 `agent.json` **完整內容**（敏感值可遮蔽，但請保留欄位名稱與結構）
- 告訴我們該目錄下**還有沒有別的檔案**
- 你的版本號

**判斷重點**：內容是「角色宣告」（名稱、說明、工具權限、提示詞 —— 適合提交、
團隊共用）還是「執行期狀態」（session id、時間戳、對話內容、快取 —— 不該提交）？

> ⚠️ 如果你**沒有實際建立過**這個檔案，請直接說「沒有實機資料」。
> 不要根據其他工具（例如 Claude Code 的 `.claude/agents/`）的作法來推測 ——
> 本專案先前已有多次因類比推論而登記錯誤主張的紀錄。

---

## 回填方式

答案存成 `rounds/2026-08-04-<tool>.reply.md`，維護者會逐條複驗後更新
[`CLAIMS.md`](../CLAIMS.md)。**回報不會被照單全收** —— 先前輪次中有數項經複驗後未採信，
也有一項推翻了維護者自己的錯誤主張。兩種結果都算成功。
