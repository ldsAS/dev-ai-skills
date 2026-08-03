# 交接回覆：Claude Code 交叉檢視 — 2026-08-03

**交接包**：[`2026-08-03-cross-tool-review.md`](./2026-08-03-cross-tool-review.md)
**回報環境**：Claude Code（Opus 5）／Windows 11／本 repo 工作目錄

> ⚠️ **本份由 Claude Code 自答，等於自己檢視自己。** 為避免「自我回報把訓練知識
> 當成觀察結果」（Antigravity 前三輪的主要失效模式），下列每題都標明依據類型：
> **[實查]** 檔案系統／**[文件]** 官方文件原文／**[推論]** 由前二者推導。
> 標為 [推論] 者一律不當成已驗證。

---

## Q1　分類是否正確？特別是 `.claude/rules/` 與 `.claude/workflows/` 的兩層結構

**結論：相符**

**[文件]** `settings.md` 的層級對照表把三層講得很明確：

| 層級 | 位置 | 誰看得到 | 進 Git？ |
| :--- | :--- | :--- | :--- |
| User | `~/.claude/` | 你，跨所有專案 | No |
| **Project** | **`.claude/` in repository** | **All collaborators** | **Yes (committed to git)** |
| Local | `.claude/settings.local.json` | 只有你，只在此 repo | No (gitignored when Claude Code saves) |

官方直接寫明專案層 `.claude/` 是 **"Yes (committed to git)"**，本 skill 的白名單方向正確。

**[文件]** `.claude/rules/`：memory.md 說「The dialog protects you from files **other people
commit to a shared project**」，並把 `~/.claude/rules/` 列為 user-scope（「files you wrote
yourself, so they load without the dialog」）。→ 兩層結構成立，專案層屬團隊共用。

**[文件]** `.claude/workflows/`：CHANGELOG 有兩條分別佐證兩層 ——
「project-scope workflow saves now target the closest existing `.claude/workflows/`」
與「the workflow save dialog showing `~/.claude/workflows/` … for **user-scope** saves」。

**[實查]** 本機 `~/.claude/` 目前無 `rules/`、`workflows/`、`worktrees/` 三個目錄
（尚未使用過該功能才不存在，不影響上述結論）。

**信心：高**

---

## Q2　還有哪些「自動產生但意圖共享」的檔案？

**結論：僅能確認 `/verify` 一項，其餘無法確認**

**[文件]** `.claude/skills/verify/SKILL.md` —— 官方 skills.md：「it writes what worked to
`.claude/skills/verify/SKILL.md` at the repo root … so later runs and **other agents**
follow the same steps」。這一項成立，已是 C-53。

**[實查]** 本專案 `.claude/` 目前只有 `settings.local.json`，`git ls-files .claude` 為空 ——
沒有其他自動產生物可供觀察。

**無法確認的部分**：CHANGELOG 提到「workflow saves 與 **scheduled-task writes**」會受
`.claude` symlink 影響，暗示排程任務也會寫入某處，但**我無法從文件或本機確定它寫在
專案層還是家目錄**（本機 `~/.claude/tasks/` 存在，專案層無對應物）。

依交接包的共通要求，**沒有樣本就說無法確認** —— 此項不列入帳本，留待實際使用排程功能後再查。

**信心：中**（確認的一項高；未確認的部分明確標示）

---

## Q3　`.claude/worktrees/` 的 symlink 風險是否仍存在？

**結論：已修復，但排除規則仍應保留；且發現第二個更廣的 symlink 問題**

**[文件]** CHANGELOG 共有兩條相關修復：

```text
1. Fixed worktree creation following a repository-committed symlink at .claude/worktrees,
   which could create files outside the repository
2. Fixed workflow saves and scheduled-task writes following a symlink at .claude,
   which could redirect writes outside the project
```

第 1 條是本 skill 已知的（C-09）。**第 2 條是新的，而且範圍更廣** ——
問題不只在 `.claude/worktrees`，而是**`.claude` 這個路徑本身**若是 symlink，
workflow 儲存與排程任務的寫入都可能被導向專案之外。

兩條都已由官方修復，**但**：

- 修復只在新版生效，舊版仍受影響
- `.claude/worktrees/` 本來就是 git worktree 的實體工作目錄，屬執行期產物，
  無論有無此漏洞都該排除
- 「不要提交 `.claude` 或 `.claude/worktrees` 這兩個路徑的 symlink」這個建議
  對舊版使用者仍有價值

→ 現行排除規則維持，並把第 2 條補進範本註解（新增 C-62）。

**信心：高**（依據為官方 CHANGELOG 原文）

---

## Q4　除上列之外，還有什麼會被寫進專案 `.claude/`？

**結論：`.claude/` 之內無新發現；但發現一條專案層路徑不在 `.claude/` 底下**

**[文件]** `settings.md` 的層級對照表列出五類設定的專案層位置：

| 類別 | User | **Project** | Local |
| :--- | :--- | :--- | :--- |
| Settings | `~/.claude/settings.json` | `.claude/settings.json` | `.claude/settings.local.json` |
| Subagents | `~/.claude/agents/` | `.claude/agents/` | None |
| **MCP servers** | `~/.claude.json` | **`.mcp.json`** | `~/.claude.json`（per-project） |
| Plugins | `~/.claude/settings.json` | `.claude/settings.json` | `.claude/settings.local.json` |
| CLAUDE.md | `~/.claude/CLAUDE.md` | `CLAUDE.md` 或 `.claude/CLAUDE.md` | `CLAUDE.local.md` |

**新發現**：MCP servers 的專案層設定是 **`.mcp.json`（在 repo 根目錄，不在 `.claude/` 底下）**，
屬 Project 層＝團隊共用。本 skill **完全未提及**這個檔案。

現行範本不會擋到它（沒有任何規則匹配 `.mcp.json`），所以行為已經正確，
但應補進「🟢 應該提交」清單並登記為主張（新增 C-61）。

> 對照：Antigravity 的對應物是 `.agents/mcp_config.json`（C-58），
> 兩者都是專案層 MCP 定義，但**檔名與位置完全不同**，不可互相類比。

**[實查]** 家目錄 `~/.claude/` 有 `backups`、`ide`、`session-env`、`sessions`、
`shell-snapshots`、`tasks`、`telemetry`、`projects` 等目錄與 `policy-limits.json`、
`remote-settings.json` 兩個檔案 —— **全部在家目錄，不寫入專案**，對本 skill 無影響。

**[實查]** 本專案 `.claude/` 只有 `settings.local.json`，且 `git ls-files .claude` 為空
—— 現行規則運作正確。

**信心：高**

---

## 本輪帳本異動

| 帳本 | 異動 |
| :--- | :--- |
| C-02～C-09、C-53 | 全部維持，官方文件層級表再次佐證 |
| **C-61** | **新增** —— `.mcp.json`：Claude Code 專案層 MCP 設定，團隊共用應提交 |
| **C-62** | **新增** —— `.claude` 路徑本身的 symlink 風險（比 C-09 的 worktrees 更廣） |

範本規則**無需變動**（`.mcp.json` 本就不被擋），僅補註解與 🟢 清單。

---

## 附註：關於安裝範圍

檢視過程中確認 `install.sh` / `install.ps1` 的**五個目標全部是全域路徑**，
無任何專案層安裝選項。詳見維護者另行提出的範圍討論。
