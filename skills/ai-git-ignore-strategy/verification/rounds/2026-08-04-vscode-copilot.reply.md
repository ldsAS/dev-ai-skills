# VS Code / GitHub Copilot 回覆：移除舊路徑後的載入實查

**回覆日期**：2026-08-09  
**對應交接包**：[2026-08-04-load-path-check.md](./2026-08-04-load-path-check.md)  
**查核方式**：目前執行中的 VS Code Copilot agent 所收到的 skill catalog、使用者家目錄的實體目錄、內建 Copilot extension 文件，以及公開 VS Code 文件。未讀取或轉錄任何 chat 對話內容。

## 工具版本

| 項目 | 值 |
| :--- | :--- |
| 作業系統 | Windows |
| VS Code | 1.125.1 |
| GitHub Copilot Chat | 0.53.1（內建 `copilot-chat` extension，build 1） |

## Q1　現在載入得到 `ai-git-ignore-strategy` 嗎？

**結論：可以。這個正在執行的 Copilot agent 實際載入的是下列檔案：**

```text
C:\Users\LdsFi\.agents\skills\ai-git-ignore-strategy\SKILL.md
```

本回覆所在的 active agent host 注入的 skill catalog 直接列出了上述絕對路徑；它不是由本 repo 工作區、`.copilot/skills/` 或猜測的文件路徑載入。該實體檔存在，內容為 generic 變體的工具無關指示。

因此，`C:\Users\LdsFi\.copilot\skills\ai-git-ignore-strategy\` 被移除後，**本次 VS Code Copilot session 的技能沒有消失**；`~/.agents/skills/` 這一份足以供目前環境載入。

## 使用者層目錄盤點

| 路徑 | 實體狀態 | 此回合可得出的結論 |
| :--- | :--- | :--- |
| `C:\Users\LdsFi\.agents\skills\ai-git-ignore-strategy\` | 存在，含 `SKILL.md` | **已由 active runtime 實際載入** |
| `C:\Users\LdsFi\.claude\skills\ai-git-ignore-strategy\` | 存在，含 `SKILL.md` | Claude 變體的實體複本存在；不是本 session 列出的載入來源 |
| `C:\Users\LdsFi\.copilot\skills\` | 不存在 | 沒有 Copilot 專屬複本可供本回合載入 |
| `C:\Users\LdsFi\.copilot\` | 存在 | 只看到 `ide/` 下的 lock 檔；不能把「`skills/` 不存在」表述成整個 `.copilot/` 目錄已不存在 |

## Copilot 實際支援的使用者層 skill 路徑

VS Code 1.125.1 所附的 Copilot 0.53.1 內建 reference，以及本回合擷取的官方 Agent Skills 文件，都列出以下三條 Personal skill 位置：

```text
~/.copilot/skills/<name>/
~/.agents/skills/<name>/
~/.claude/skills/<name>/
```

這裡必須區分兩件事：

1. `~/.agents/skills/` 是本回合**有直接 runtime 證據**的實際載入來源。
2. 三條都是官方支援的位置；`~/.copilot/skills/` 並非無效或已廢棄的路徑。它目前只是沒有本技能的實體資料夾，因此本回合無法從執行期確認該路徑的載入行為。

## 同名技能的數量與處理

檔案系統中目前有 **兩份**同名實體技能：

```text
C:\Users\LdsFi\.agents\skills\ai-git-ignore-strategy\SKILL.md   (generic)
C:\Users\LdsFi\.claude\skills\ai-git-ignore-strategy\SKILL.md   (claude)
```

但是這個 active Copilot agent 的 catalog 只出現 **一個** `ai-git-ignore-strategy` 項目，且來源是 `~/.agents/skills/`。也就是說，對目前 session 可觀察到的行為是「只暴露一份、採用 `.agents` 來源」，沒有出現兩個可獨立選用的同名項目。

不過，這不能外推成「Copilot 不會掃 `~/.claude/skills/`」或「`.agents` 永遠有較高優先權」：官方文件列出了兩者，但沒有在可查到的內容中定義同名 collision 的優先順序；現有 runtime log 也沒有 skill-discovery／deduplication 事件。未建立暫時探針技能、未重載 VS Code 進行破壞性實驗，因此這一層的演算法維持**未驗證**。

## 全域與專案層的結論

對這個跨 repository 的 Git 追蹤稽核流程，預設採用全域 generic 版是合理的：

```text
~/.agents/skills/ai-git-ignore-strategy/
```

它在本次 VS Code Copilot runtime 已證實可用，也能避免額外建立第三份 `~/.copilot/skills/` 複本。保留 `~/.claude/skills/` 的 Claude 專用版，是讓 Claude Code 保有對應工具指令的獨立需求；Copilot 對同名根路徑的選擇規則則不應假設為穩定介面。

只有在下列情況才建議改用專案層 `<repo>/.agents/skills/ai-git-ignore-strategy/`：

- 團隊要把固定版本與 repository 一起審查、提交及傳承；
- 流程含有真正的專案專屬步驟；
- 所有協作者都必須自動取得同一套規則。

避免在同一個 Copilot 環境同時維護同名的全域與專案版本；目前沒有已驗證的 collision 優先順序。若專案確實需要不同流程，應改用清楚可區分的 skill 名稱，或明確停用其中一份。

對 `dev-ai-skills` 來源 repo 本身，canonical source 應繼續維持在：

```text
skills/ai-git-ignore-strategy/<variant>/SKILL.md
```

不需要在這個來源 repo 再建立一份同名 project copy。

## 回填判讀

| 問題 | 結果 | 信心 |
| :--- | :--- | :--- |
| 移除 `~/.copilot/skills/` 後本技能是否消失 | 否；目前從 `~/.agents/skills/` 實際載入 | 高 |
| `~/.agents/skills/` 是否可供目前 Copilot 使用 | 是 | 高 |
| `~/.copilot/skills/` 是否為無效／不支援路徑 | 否；官方仍列為 Personal skill 路徑 | 高 |
| Copilot 是否會掃三條使用者層路徑 | 官方文件列為支援；本回合僅 `.agents` 有 runtime 證據 | 文件：高；逐條 runtime：未驗證 |
| 同名技能的固定優先順序或 merge 規則 | 沒有可用的 runtime／文件證據 | 未驗證 |

依交接流程，本回覆只提供可複驗證據；是否據此調整 `CLAIMS.md`、安裝器註解或文件，交由維護者複驗後決定。
