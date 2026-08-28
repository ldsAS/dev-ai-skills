# 路徑主張帳本 (Claims Ledger)

本 skill 對外部工具行為所做的每一條路徑主張，及其依據、取證時間與狀態。
狀態定義與維護規則見 [`README.md`](./README.md)。

**最後更新**：2026-08-28（Issue #10 判定為尾斜線語彙假陽性 —— 新增 C-96：目錄尾斜線等價與上下文取用改採實際 match span）

| 狀態 | 數量 |
| :--- | ---: |
| 已驗證 | 69 |
| 結構性 | 4 |
| 移出範圍 | 3 |
| 被取代 | 1 |
| **總計** | **77** |

---

## Claude Code

| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-01 | `.claude/*` | 擋直接子項，讓下方白名單得以生效 | 結構性 | — | — | 結構性 |
| C-02 | `.claude/settings.json` | 團隊共用設定（權限、hooks），應提交 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-03 | `.claude/settings.local.json` | 個人本機設定，應排除。📌 官方 settings 頁改版後會抽出**裸 token** `settings.local.json`（無目錄前綴），那是本條的**語彙別名**，不是新路徑，**不需新增規則或主張** | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-04 | `.claude/commands/`、`.claude/agents/` | 團隊共用，應提交 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-05 | `.claude/rules/` | 團隊共用分檔規則，應提交 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-06 | `.claude/skills/` | 需逐案確認（CLI 安裝 vs 自撰） | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-07 | `~/.claude/projects/` | 對話紀錄與 memory 在家目錄，不在專案內 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-08 | `.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json` | 外掛／市集清單檔，官方定位為「Sharing with teammates, distributing to community」。**若本 repo 本身就是 plugin 或 marketplace，必須提交**。現行規則不擋（正確），已補進 🟢 清單 | 官方文件 | 2026-07-30 | — | 已驗證 |
| C-09 | `.claude/workflows/`、`.claude/worktrees/` | **兩者相反**。`workflows/` 有 user-scope（`~/.claude/workflows/`）與 project-scope 兩層，屬團隊共用 → **已放行**。`worktrees/` 是 git worktree 實體工作目錄，且官方修過「repository-committed symlink at `.claude/worktrees` 可在 repo 外建檔」的逃逸問題 → **已 explicit 排除** | 官方 CHANGELOG | 2026-07-30 | — | 已驗證 |
| C-83 | `.claude/launch.json` | Claude Code 的**開發伺服器啟動設定**：以具名 configuration 記錄啟動指令（`runtimeExecutable`／`runtimeArgs`／`port`），供工具直接跑起專案。**範本預設不放行（白名單為註解狀態）** —— 可能寫入個人絕對路徑，且「要不要公開建置方式」屬專案決定。地位等同 `.vscode/launch.json`，而本 skill 早已將後者列為團隊共用可保留 —— 先前**漏了 Claude Code 的對應檔**，被 `.claude/*` 靜默擋下。Claude Code 的個人層檔案一律走 `.local.json` 後綴（見 C-03），此檔無該後綴。⚠️ 殘留風險：launch.json 可能寫入個人絕對路徑，提交前應確認為相對路徑。**發現經過**：比對 PM-tools-Dashboard-docker 的實際運作情況時，在該專案發現此檔存在、內容為三組專案級啟動設定（Docker Compose／Flask／Gunicorn），但被 `.claude/*` 擋下且未追蹤 | 工具文件（launch 設定格式）＋實地觀察 | 2026-08-07 | — | 已驗證 |
| C-90 | `~/.claude/sessions/`、`~/.claude/backups/` | **家目錄的執行期狀態與設定備份，不寫入專案** → 五版範本**無需新增任何規則**。官方 CHANGELOG：「Fixed headless sessions not cleaning up stale entries in `~/.claude/sessions` left by sessions that exited uncleanly」；官方 settings 頁：「`~/.claude.json` can't be parsed. Claude Code copies the broken file to `~/.claude/backups/.claude.json.corrupted.<timestamp>`」。⚠️ **2026-08-26 更正措辭**：初版寫「實查比文件更廣」，**那是錯的** —— 完整描述其實存在，只是在**當時未納入監控**的官方 `.claude` 目錄頁：「`backups/` — Earlier versions of `~/.claude.json`, copied when Claude Code rewrites the file. **Claude Code keeps the five newest**, plus a copy of any version it couldn't parse」，與本機實查的 5 個 `.claude.json.backup.<epoch_ms>` 完全吻合。受監控的 settings 頁只描述損毀複本那一種情境。**正確的教訓不是「官方文件不完整」，而是「我們的監控來源不完整」** —— 見文末〈監控來源缺口〉。`~/.claude/sessions/` 為 per-process 狀態檔（`<pid>.json`、`<pid>.<hash>.key`），**與 C-07 的 `~/.claude/projects/`（對話紀錄與 memory）不是同一回事**，勿互相套用 | 官方 CHANGELOG＋官方 settings 頁＋本機實查 | 2026-08-26 | 2.1.246 | 已驗證 |
| C-91 | `~/.claude/plugins/known_marketplaces.json` | 家目錄的**已知外掛市集註冊表**，供 `claude plugin install <name>` 解析市集名稱；位於家目錄 → **無需專案規則**。官方 CHANGELOG：「Fixed `claude plugin install <name>` exiting silently (or hanging in a terminal) instead of reporting an error when `~/.claude/plugins/known_marketplaces.json` is empty or corrupted」。⚠️ **本條最大的誤讀風險是與另兩條混淆，三者位置與用途皆不同**：① 本條＝**使用者層**註冊表；② `.claude-plugin/marketplace.json`（C-08）＝**專案層**，當本 repo 自己就是 marketplace 時必須提交；③ `.agents/plugins/marketplace.json`（C-14）＝**Codex 專案層**團隊共用市集。本機 `~/.claude/plugins/` 尚未建立（未安裝任何外掛） | 官方 CHANGELOG（修復說明中的附帶提及，非路徑規格）＋本機實查 | 2026-08-26 | 2.1.246 | 已驗證 |
| C-92 | `~/.claude/skills/synced/`、`.claude/skills/synced/` | **`synced` 是保留名稱，不只是家目錄路徑。** 官方 skills 頁：「The folder name `synced` is **reserved in the enterprise, personal, and project skills locations**, in any capitalization. Claude Code downloads the skills you enable on claude.ai into `~/.claude/skills/synced/` when `CLAUDE_CODE_SYNC_SKILLS` is set in non-interactive mode, and **skips a skill you author at that name**」。→ 兩層意義：① 下載內容落在**家目錄**，不進專案，**無需新增規則**；② **專案層 `.claude/skills/synced/` 也是保留名**，自撰技能取此名會被工具**靜默略過** —— 本 skill 建議 scoped allowlist 時（`!.claude/skills/<project-skill>/`），`synced` 是**不可用的名稱**。現行範本以 `.claude/skills/*` 擋下，行為已正確（專案層不該出現此目錄），故**範本無需異動** | 官方文件 skills 頁 | 2026-08-26 | 2.1.246 | 已驗證 |
| C-53 | `.claude/skills/verify/SKILL.md` | `/verify` 把可用的建置指令自動寫入 repo root（monorepo 則寫入被動到的套件目錄），官方定位「so later runs and **other agents** follow the same steps」＝設計上要共享 → **已放行**。屬「自動產生但意圖共享」的第三類，補足了原本 CLI 安裝／自撰的二分法 | 官方文件（**由排程監控於 2026-07-30 自動偵測**） | 2026-07-30 | — | 已驗證 |
| C-61 | `.mcp.json` | Claude Code 的**專案層 MCP server 設定**，官方層級表列於 Project 欄（User 為 `~/.claude.json`）＝團隊共用 → **應提交**。位於 repo 根目錄而非 `.claude/` 底下，現行規則不擋（正確），已補進 🟢 清單。⚠️ 與 Antigravity 的 `.agents/mcp_config.json`（C-58）**檔名與位置皆不同**，不可互相類比 | 官方文件 `settings.md` 層級表 | 2026-08-03 | — | 已驗證 |
| C-62 | `.claude`（路徑本身作為 symlink） | 官方修復紀錄：「Fixed workflow saves and scheduled-task writes following a symlink at `.claude`, which could redirect writes outside the project」。**比 C-09 的 `.claude/worktrees` 範圍更廣** —— 是 `.claude` 這個路徑本身。已修復但舊版仍受影響：**不要提交 `.claude` 或 `.claude/worktrees` 的 symlink** | 官方 CHANGELOG | 2026-08-03 | — | 已驗證 |

## Codex

| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-10 | `.codex/*` | 擋直接子項 | 結構性 | — | — | 結構性 |
| C-11 | `.codex/config.toml` | 專案層設定覆寫，官方明示放進 repo，應提交 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-12 | `.codex/skills/` | ~~需逐案確認~~ → **不是官方 REPO 路徑**。官方 skills scope 表列的是 `$CWD/.agents/skills`、`$CWD/../.agents/skills`、`$REPO_ROOT/.agents/skills`（REPO）、`$HOME/.agents/skills`（USER）、`/etc/codex/skills`（ADMIN）—— `.codex/skills` 在該表**出現 0 次**。保留為舊版相容路徑，範本已加註；專案技能請優先用 `.agents/skills/` | 官方文件 build-skills | 2026-08-03 | — | 已驗證 |
| C-13 | `.agents/skills` | Codex 從 CWD 逐層往上掃到 repo root | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-14 | `.agents/plugins/marketplace.json` | 專案層外掛市集，官方定位為團隊共用，應提交 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-15 | `.agents/plugins/*` | 官方寫明專案層只放 `.agents/plugins/marketplace.json`，**外掛本體另存於 repo-local 目錄（如 `./plugins/`）**，不在 `.agents/plugins/` 底下。現行「放行 manifest、擋其餘」的三段式規則正確 | 官方 changelog | 2026-07-30 | — | 已驗證 |
| C-16 | `.codex-plugin/plugin.json` | 外掛必備清單檔（`Every plugin is a folder with a required .codex-plugin/plugin.json manifest`）。與 C-08 同性質，若本 repo 是外掛則必須提交。現行規則不擋（正確），已補進 🟢 清單 | 官方 changelog | 2026-07-30 | — | 已驗證 |
| C-17 | `.codex/hooks.json`、`.codex/hooks/`、`.codex/rules/` | **原規則誤殺三項**：三者都是官方列出的專案層設定層（未信任專案會跳過這些 layer），屬團隊共用 → **已放行**。⚠️ **2026-08-03 更正**：先前把 `.codex/rollout.jsonl` 列為專案層 session 紀錄並加了排除規則 —— **那是錯的**。該 token 取自官方 hooks 文件中傳給 hook 的**範例 payload**（`"transcript_path": "/workspace/.codex/rollout.jsonl"`），不是真實預設路徑。實際 rollout 位於 `$CODEX_HOME/sessions/YYYY/MM/DD/rollout-<ts>-<id>.jsonl`（`CODEX_HOME` 預設 `~/.codex`），本機實查一致。誤植規則已自五版移除 | 官方文件＋Codex 實機回覆＋本機實查 | 2026-08-03 | 0.146.0-alpha.9.2 | 已驗證 |
| C-93 | `~/.codex/hooks/post_tool_use.py` | **文件範例中的使用者自撰腳本路徑，不是工具產物。** 原文出自官方 hooks 頁的 `hooks.json` 範例：`{"type":"command","command":"python3 ~/.codex/hooks/post_tool_use.py","async":true,...}`。→ 它示範的是「使用者把自己寫的 hook 腳本放在家目錄」，Codex **不會自動建立此檔**；位於家目錄且非自動產物，**無需任何專案規則**。⚠️ 與 C-17 的 `.codex/rollout.jsonl` 屬**同一類陷阱**（自文件範例抽出的 token），差別在那次的 `/workspace/` 是虛構前綴而被誤判為真實路徑，本次已先讀上下文再分類 —— **token 是線索，不是結論** | 官方文件 hooks 頁（範例 payload，非路徑規格） | 2026-08-26 | — | 已驗證 |
| C-94 | `.antigravityignore` | 官方 changelog：「Fixed `@` file path completion showing files that were in your `.antigravityignore`」，只足以證實 Antigravity 會依此檔排除 `@` 檔案路徑補全的候選。**現行範本沒有阻擋此名稱；因位置與分享定位未定，本輪維持現狀、不新增規則，五版無需異動**。⚠️ **殘留未知，勿以類比補齊**：8 個 Antigravity 官方文件來源中**僅 changelog 一處提及**，該行是修復說明而非規格；**檔案位置（專案根目錄／家目錄）、是否團隊共用、與 `.geminiignore` 的關係皆未載明**，`/docs/cli/gcli-migration` 頁全文 0 次提及 ignore。本機亦尚未出現此檔。**發現經過**：2026-08-22 偵測到的 token 因抽取器漏列長名而被截短成 `.antigravity`（見 C-95），2026-08-26 修正後才還原成正確檔名並完成有限分類 | 官方 changelog（修復說明中的附帶提及，非路徑規格）＋8 來源全文檢索 | 2026-08-26 | 2.10.0 | 已驗證 |
| C-63 | Codex 官方文件站位置 | 文件已自 `developers.openai.com/codex/*` **搬遷至** `learn.chatgpt.com/docs/*`（舊網址仍 302 導向）。監控來源已改指正式網址並補上 `build-skills`、`hooks` 兩頁 | Codex 實機回覆＋重導向實測 | 2026-08-03 | — | 已驗證 |
| C-64 | `~/.agents/skills/` | Codex 官方 USER scope 路徑；亦為 Gemini CLI 與 Copilot 的使用者層技能位置，屬**跨工具共用**。本專案安裝器原本只寫 `~/.codex/skills`（該路徑實查僅有我方寫入的內容，屬 C-48 同型的循環證據），已補上此路徑 | 官方文件 build-skills | 2026-08-03 | — | 已驗證 |
| C-85 | Codex 的實際 skill root 清單 | **實機確認**：目前 task 登記的 root 為 `r0 = ~/.agents/skills`、`r1 = ~/.codex/skills/.system`，本技能自 `r0/ai-git-ignore-strategy/SKILL.md` 載入（實體目錄，非 symlink）。→ 2026-08-07 刪除 `~/.codex/skills/ai-git-ignore-strategy` 後**技能未消失**，該次移除安全。另確認 `.codex/skills` **父目錄未出現在 root 清單**，不應再視為現行 USER 安裝路徑（呼應 C-12；`.system/` 子目錄則確實在用，見 C-82）。⚠️ 回報者主動聲明：本輪未在 `~/.codex/skills/` 放探針技能，故**不宣稱**所有版本與啟動模式都無 legacy fallback —— 但對本次刪除的安全性，有實際載入成功可直接證明 | Codex 實機回覆＋官方 scope 表 | 2026-08-09 | Codex Desktop 26.803.5235.0／bundled runtime 0.147.0-alpha.6.5（task metadata 為 0.146.0-alpha.9.2） | 已驗證 |

## Gemini CLI

| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-20 | `.gemini/*` | 擋直接子項 | 結構性 | — | — | 結構性 |
| C-21 | `.gemini/settings.json` | Workspace 設定，與 `.claude/settings.json` 同性質，應提交 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-22 | `.agents/skills/` | 為 `.gemini/skills/` 的別名，且**優先權高於**後者 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-23 | `.geminiignore`、`.aiexclude` | AI 忽略規則檔，官方明示「similar to `.gitignore`」，與 `.gitignore` 同性質 → **應提交**。現行規則不擋（正確），已補進 🟢 清單 | 官方文件 | 2026-07-30 | — | 已驗證 |
| C-24 | `~/.gemini/tmp/`（session 實際位置） | Session 存於 **家目錄** `~/.gemini/tmp/<project_hash>/chats/`，不寫入專案。專案內 `.gemini/` 以 `settings.json`、`skills/` 等共享內容為主，無需額外 cache 排除規則 | 官方文件 | 2026-07-30 | — | 已驗證 |

## VS Code / GitHub Copilot

> 2026-08-03 建立。此前這個工具**完全沒有監控來源、也沒有任何主張** ——
> 但它是維護者實際使用的四個工具之一，且早有 `vscode/` 變體。

| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-70 | `copilot-instructions.md`（位於 `.github/`） | 專案指令檔，由 `/init` 產生；官方列為 always-on instructions（與 `AGENTS.md`、`CLAUDE.md` 並列）→ **應提交**。現行規則不擋（正確） | 官方文件 | 2026-08-03 | — | 已驗證 |
| C-71 | `.github/prompts`、`.prompt.md` | 共享 prompt files，官方：Workspace scope 的預設位置為 `.github/prompts` → **應提交**。現行規則不擋（正確） | 官方文件 | 2026-08-03 | — | 已驗證 |
| C-72 | `.instructions.md`（位於 `.github/instructions/`） | 針對特定語言／框架／資料夾的指令檔，官方列為四種自訂檔型別之一 → **應提交**。skill 原本完全未提及 | 官方文件 | 2026-08-03 | — | 已驗證 |
| C-73 | `.agent.md`（位於 `.github/agents/`） | 自訂 agent 定義檔，官方列為四種自訂檔型別之一 → **應提交**。skill 原本完全未提及 | 官方文件 | 2026-08-03 | — | 已驗證 |
| C-74 | `~/.copilot/skills/` | 使用者層技能安裝路徑（`install.sh` 的 vscode 目標），在家目錄不影響專案 | 官方文件 agent-skills 頁 | 2026-08-03 | — | 已驗證 |
| C-75 | `.github/skills/` | Copilot 專案層技能位置之一（官方另列 `.claude/skills/`、`.agents/skills/`）→ **應提交**。現行規則不擋（正確） | 官方文件 agent-skills 頁 | 2026-08-03 | — | 已驗證 |
| C-76 | `.github/hooks/*.json` | Copilot 工作區 hooks，官方列為 Workspace 預設位置 → **應提交**（與 `.github/workflows` 同性質）。⚠️ 內含可執行指令，提交前應審查 | 官方文件 hooks 頁 | 2026-08-03 | — | 已驗證 |
| C-77 | Copilot 跨工具讀取 `.claude/`、`.agents/` | 官方明載 Copilot 會讀 `.claude/skills/`、`.agents/skills/`、`~/.claude/skills/`、`~/.agents/skills/`，以及 Claude 格式的 `.claude/settings.json`、`.claude/settings.local.json`（hooks）。**`.claude/` 並非 Claude Code 專屬** —— 繼 C-60 的 `.agents/` 之後，`.claude/` 同樣是跨工具目錄。`.claude/skills/*` 的 scoped allowlist 因此同時影響 Copilot | 官方文件 agent-skills／hooks 頁 | 2026-08-03 | — | 已驗證 |
| C-84 | Copilot「Agent Host」的使用者層讀取位置 | 官方：「When Agent Host is enabled, the agent reads user-level customizations from harness-agnostic folders like `~/.copilot` (Copilot) and `~/.claude` (Claude), rather than from your VS Code profile user data.」→ **非預設**（"when enabled"），且**全屬家目錄，無專案層路徑** → **本 skill 無需新增任何 `.gitignore` 規則**。⚠️ 但影響安裝決策：本頁**未提及 `~/.agents`**（該路徑的依據來自 agent-skills 頁，見 C-77）。2026-08-07 我方已移除 `~/.copilot/skills` 的複本 —— 即使 Agent Host 情境下 `~/.agents/skills` 未被讀取，`~/.claude/skills` 仍留有本技能（claude 變體），故移除不致使技能消失。仍待 Copilot 實機確認實際載入來源（見 2026-08-04 交接包） | 官方文件 customization overview（**由排程監控於 2026-08-06 自動偵測**） | 2026-08-07 | — | 已驗證 |
| C-79 | 跨工具共用路徑 vs 逐工具變體 | `~/.agents/skills/` 由 Codex（C-64）、Gemini CLI（C-22）、Copilot（C-77）共同讀取；`~/.claude/skills/` 由 Claude Code **與 Copilot** 共同讀取（C-77）。本 skill 提供逐工具變體，**放進共用路徑會讓其他工具讀到不屬於自己的工具名**。Codex 官方文件明載同名技能不合併。⚠️ **2026-08-09 更正依據**：原記「實查本機：Copilot 同時看得到兩份同名技能」—— 那是**由「兩個目錄都存在」推論的，不是 catalog 觀察**，與 C-48、C-74 同型的循環證據。Copilot 實機回覆顯示：兩份同名實體複本（`~/.agents` generic ＋ `~/.claude` claude）在 active session 的 catalog 中**只出現一個項目**，來源為 `.agents`（見 C-86）。→ **結論不變，理由改為更強的版本**：同名時哪一份勝出**沒有已驗證的規則**，把工具專屬變體放進共用路徑等於擲骰子，故一律放 `generic` 變體（與上游 `uipro init --ai universal` 同解法） | 帳本交叉推導；原「本機實查」部分已由 C-86 更正 | 2026-08-09 | — | 已驗證 |
| C-86 | Copilot 的實際 skill catalog 來源 | **實機確認**：active agent host 注入的 skill catalog 直接列出 `C:\Users\LdsFi\.agents\skills\ai-git-ignore-strategy\SKILL.md`（generic 變體），不是來自工作區或 `.copilot/skills/`。→ 2026-08-07 移除 `~/.copilot/skills/` 後**技能未消失**，該次移除安全。⚠️ **重要且推翻我方原依據**：檔案系統有**兩份**同名實體技能（`~/.agents` generic ＋ `~/.claude` claude），但 catalog **只出現一個項目**，來源為 `.agents` —— C-79 原稱「Copilot 同時看得到兩份」是由目錄存在推論的，非 catalog 觀察，已更正。⚠️ 但**不可反向外推**：回報者明確指出「不能據此推論 Copilot 不掃 `~/.claude/skills/`，也不能推論 `.agents` 永遠優先」；官方文件列出三條 Personal 路徑（`~/.copilot`、`~/.agents`、`~/.claude`）卻**未定義同名 collision 的優先順序**，runtime log 亦無 discovery／dedup 事件。本輪未建立探針技能、未重載 VS Code 做破壞性實驗，故**同名優先權維持未驗證**。另更正一項措辭：`~/.copilot/` 父目錄仍存在（其下有 `ide/*.lock`），只有 `skills/` 子目錄被移除；`~/.copilot/skills/` 亦**非**無效或廢棄路徑，官方仍列為 Personal skill 位置 | Copilot 實機回覆（active agent host catalog）＋本機實查 | 2026-08-09 | VS Code 1.125.1／Copilot Chat 0.53.1（build 1） | 已驗證 |
| C-78 | `User/workspaceStorage/<workspace-id>/`、`User/globalStorage/github.copilot-chat/`（均相對於 VS Code user-data root） | VS Code Copilot Chat 的 session、transcript、debug log、editing state 與 tool-embeddings cache 寫入 **VS Code user data**，不是 repository。active session 實查確認 workspace storage 對應目前 repo、其下出現 `chatSessions/`、`chatEditingSessions/`、`GitHub.copilot-chat/transcripts/`、`GitHub.copilot-chat/debug-logs/`；同時 repo Git 狀態沒有新的 Copilot runtime 檔。**不應新增專案層 `.copilot/`、cache、log 或 session ignore 規則。** | [Windows 實機回覆](./rounds/2026-08-03-vscode-copilot.reply.md)＋已安裝 extension package | 2026-08-03 | VS Code 1.125.1／Copilot Chat 0.53.1 | 已驗證 |

## Cursor（已移出維護範圍）

> 🚫 **2026-08-03 移出**：維護者未使用 Cursor，為降低維護負擔已自五版範本移除
> `.cursor/*` 相關規則、自監控來源移除 `cursor.com/docs`。
> 下列三條**保留作為歷史紀錄**（帳本原則：不刪除，只改狀態）。
> 若日後要重新納入，規則與依據可直接由此還原。

| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-30 | `.cursor/*` | 擋直接子項 | 結構性 | — | — | 移出範圍 |
| C-31 | `.cursor/rules/` | 團隊規則，官方建議 commit | 官方文件 | 2026-07-29 | — | 移出範圍 |
| C-32 | `.cursor/rules/imported/` | Cursor 會自其他 repo pull and sync 規則並放到 `.cursor/rules/imported/<repoName>`，屬可重新取得的鏡像 | 官方文件 | 2026-07-29 | — | 移出範圍 |

## Antigravity

> ✅ **2026-08-03 更正**：Antigravity **有完整的官方文件站**（80+ 頁），
> 涵蓋 `/docs/skills`、`/docs/subagents`、`/docs/hooks`、`/docs/rules-workflows`、
> `/docs/plugins`、`/docs/cli/*`、`/docs/ide/*` 等。
>
> ⚠️ 先前判定「沒有公開文件站」**是錯的** —— 當時只測了索引頁 `antigravity.google/docs`
> 拿到 345 bytes 的 stub 就下結論，沒有跟著頁面連結往下追。實際文件在 `/docs/<section>` 之下。
>
> 產品家族為 **Antigravity 2.0**（套件版本）下轄 **Antigravity CLI**（`agy`，自身版本 1.x）、
> **Antigravity IDE**、**Antigravity SDK**；官方另有 `/docs/cli/gcli-migration`
> 說明如何自 Gemini CLI 遷移過來。這解釋了先前 `2.4.3` 與 `agy --version 1.0.13` 的差異 ——
> 兩個都是真的版本號，分屬套件與 CLI 元件。
>
> 已於 2026-08-03 納入 7 個官方文件來源，本區原本 6 條監控盲區**全數消除**。

| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-40 | `.agents/*` | 擋直接子項 | 結構性 | — | — | 結構性 |
| C-41 | `.agents/AGENTS.md` | ~~專案級設定，應提交~~ → **不存在**；Antigravity 只讀根目錄的 `AGENTS.md`。**2026-08-04 白名單規則已自五版移除**：agy 1.0.13 二進位中 `{workspace}/.agents/` 的路徑模板完整清單只有 `skills`、`agents`、`ORIGINAL_REQUEST.md` 三條，本條不在內；本機五個實際專案的 `.agents/` 亦 0 次出現。原先保留為「防禦性白名單」，但為不存在的路徑留規則會讓讀者誤以為該路徑有效 —— 同 `.codex/rollout.jsonl` 的處置 | 實機＋維護者複驗 | 2026-08-04 | 1.0.13 | 已驗證 |
| C-42 | `.agents/settings.json` | ~~專案級設定，應提交~~ → **不存在**；專案設定實存於 `~/.gemini/config/projects/<uuid>.json`。**2026-08-04 白名單規則已自五版移除**：agy 1.0.13 二進位中 `{workspace}/.agents/` 的路徑模板完整清單只有 `skills`、`agents`、`ORIGINAL_REQUEST.md` 三條，本條不在內；本機五個實際專案的 `.agents/` 亦 0 次出現。原先保留為「防禦性白名單」，但為不存在的路徑留規則會讓讀者誤以為該路徑有效 —— 同 `.codex/rollout.jsonl` 的處置 | 實機＋官方 changelog（雙重佐證） | 2026-08-04 | 1.0.13 | 已驗證 |
| C-43 | `.agents/settings.local.json` | ~~個人本機設定~~ → **不存在**，係誤類比 Claude Code；規則已移除 | 實機＋維護者複驗 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-44 | `.agents/hooks.json` | 工作區層級 hooks；**會合併多個 hooks.json 檔**（二進位字串 `loaded %d named hooks from %d hooks.json file(s)` 為複數）。信任狀態以工作區絕對路徑為 key 存於家目錄 `~/.gemini/trusted_hooks.json` —— 此設計意味 hooks 定義可來自他人 commit 的 repo，故**屬可共享檔**；是否提交屬專案決策，非待驗事實 | 二進位字串分析＋`trusted_hooks.json` 結構 | 2026-07-30 | 1.0.13 | 已驗證 |
| C-45 | `.antigravitycli/` | 舊版工作區對應檔，現行版本不再產生；規則保留供舊專案 | 官方 changelog＋實機 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-46 | `.agent/` | 舊版佈局的專案工作區暫存，現行版本不再產生；規則保留供舊專案 | 實機＋維護者複驗 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-47 | `~/.gemini/config/skills/` | **Antigravity CLI** 的全域 skills 路徑（官方 `/docs/skills`）；實查含工具自身的 `.datacloud_skills_manifest` 與 22 個內建技能。與 C-48 的 IDE 路徑並存 | 官方文件＋實機 | 2026-08-03 | 2.x | 已驗證 |
| C-48 | `~/.gemini/antigravity/skills/` | ~~死路徑，已不掃描~~ → **是 Antigravity IDE 的全域 skills 路徑，仍然有效**。官方 `/docs/ide/skills` 與 `/docs/skills` 兩頁文字幾乎相同，只差一行：IDE 用 `~/.gemini/antigravity/skills/`、CLI 用 `~/.gemini/config/skills/`，**兩者並存而非新舊關係**。2026-07-30 的探針實驗是在子代理（CLI 情境）跑的，只證明「CLI 不讀這條」，卻被推論成「沒人讀」—— **實驗範圍比結論窄**。安裝器已還原雙路徑寫入 | 官方文件 `/docs/ide/skills` | 2026-08-03 | 2.x | 已驗證 |
| C-49 | Antigravity 對話紀錄位置 | 在家目錄 `~/.gemini/antigravity/conversations/`（實查 21 項）與 `~/.gemini/antigravity-cli/conversations/`（1 項），**不寫入專案** | 實機＋維護者複驗 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-50 | `AGENTS.md`（根目錄） | Antigravity 已支援讀取，與 `GEMINI.md` 並列 | 官方 changelog＋實機 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-51 | 技能觸發語法 | `@skill-name` **已不適用**；技能由 Agent 依任務自動掃描載入 | 實機（回報） | 2026-07-29 | 1.0.13 | 已驗證 |
| C-52 | 專案目錄自動產生物 | ~~不在專案目錄產生任何 cache／log~~ → **回報有誤**：對話紀錄確實在家目錄，但 agent 會寫入 `.agents/ORIGINAL_REQUEST.md`（見 C-55） | 二進位字串分析**推翻**回報結論 | 2026-07-30 | 1.0.13 | 已驗證 |
| C-54 | `.agents/agents/<name>/agent.json` | 工作區層級自訂子代理定義。**2026-08-07 起範本預設不放行（白名單改為註解狀態）** —— 路徑事實明確，但「該不該提交」的依據是內容推測而非官方明文，故交由開發者確認後啟用。依據為二進位中的**明確路徑模板**：`{workspace}/.agents/agents/{agent_name}/agent.json`（另有全域對應 `{appDataDir}/agents/{agent_name}/agent.json`）—— 不是類比、也不只是架構對稱。`writing agent.json`／`marshaling agent.json` 顯示為使用者發起的持久化宣告，執行期狀態另有去處（C-56 與家目錄 `brain/`）。**殘留未知**：實體檔案內容尚無人目視，且本機五個實際專案的 `.agents/` 皆未出現 `agents/`（工具支援但使用者未用過）。**2026-08-09 Antigravity 回覆後仍維持註解狀態**：欄位結構已由二進位 protobuf 定義佐證為純角色宣告（C-87），但依 2026-08-07 確立的門檻，白名單要「啟用」需**官方明文定位為團隊共用**；欄位性質證明的是內容，不是官方的分享定位，且 (a) 無人目視實體檔案、(b) 「目錄下還有沒有其他檔案」仍未回答、(c) 實際 key 命名未定。為單一條目破例會讓該門檻失效 | 二進位字串分析（明確路徑模板） | 2026-08-04 | 1.0.13 | 已驗證 |
| C-55 | `.agents/ORIGINAL_REQUEST.md` | agent 會把使用者訊息**逐字**附加至此檔（含 UTC 時間戳），亦有 `.agents/<agent_folder>/ORIGINAL_REQUEST.md` 變體。**屬敏感內容，必須排除** | 二進位字串分析 | 2026-07-30 | 1.0.13 | 已驗證 |
| C-56 | `.agents/<type>_<milestone>[_<N>][_gen<N>]/` | 子代理在**專案內**建立的工作目錄命名規則（二進位字串），內含 `ORIGINAL_REQUEST.md` 等記錄。已被 `.agents/*` 完整涵蓋 | 二進位字串分析 | 2026-07-30 | 1.0.13 | 已驗證 |
| C-80 | Antigravity 的 worktree 處理 | 2.5.0 changelog 提到「environment selector 記住上次使用的 worktree」「側欄可依 worktree 排序」，但二進位中 worktree 相關字串全是 git 操作（`gitdir:`、`rev-parse`、`worktree list`、`repo root`），查無 `.agents/worktree*` 或 `~/.gemini/*/worktree*`。→ **Antigravity 讀取標準 git worktree，不自建工具管理的 worktree 目錄**，與 Claude Code 的 `.claude/worktrees/`（C-09）不同，**本 skill 無需為其新增規則** | 官方 changelog＋二進位字串分析 | 2026-08-04 | 2.5.0 | 已驗證 |
| C-87 | `.agents/agents/<name>/agent.json` 的欄位結構 | Antigravity 回覆**誠實聲明無實機資料**（agy 1.0.13 為 headless，該檔通常由桌面端 GUI「Create New Agent」建立或人工編寫），並提供一份社群 schema。**維護者以二進位獨立複驗，結果比回覆自身的依據更強**：`customAgentSpec`(7)、`systemPromptSections`(2)、`toolNames`(4)、`customAgent`(15) 皆存在，且是 **protobuf 訊息定義**而非零星字串 —— 例：`protobuf:"bytes,2,opt,name=custom_agent_spec,json=customAgentSpec,proto3"`。欄位集合為 `name`／`displayName`／`description`／`hidden`／`customAgentSpec{customAgent{systemPromptSections, toolNames}}`，**全屬靜態角色宣告**，無 session／時間戳／對話等執行期欄位。→ 支持「性質適合提交」。⚠️ **仍不足以啟用白名單**（見 C-54）：(1) **無人目視過實體檔案**；(2) 交接包 Q3「目錄下還有沒有其他檔案」回覆自陳「無法由系統生成結果斷定」＝**未回答**；(3) **新發現的未決點** —— Go 結構標籤是 `json:"custom_agent_spec,omitempty"`，以 `encoding/json` 封送會輸出 **snake_case**，`customAgentSpec` 只是 protobuf JSON 名。回覆給的 camelCase schema 可能取自 protobuf JSON 形式而非磁碟實際內容，**實際 key 命名未定**。另：二進位有 `creating agent directory`、`writing agent.json`、`marshaling agent.json` 與 9 處 `AgentsCreatePath`，顯示寫入機制存在，但查無對應的使用者層子命令字串 | Antigravity 回覆（社群 schema，自陳無實機）＋維護者二進位複驗（protobuf 定義） | 2026-08-09 | agy 1.0.13 | 已驗證 |
| C-81 | `.agent/skills/<name>/` | 舊佈局的專案技能目錄。**官方向後相容只明載 `.agent/rules`**（見 C-57），**未提及 skills**；現行 agy 1.0.13 二進位對 `.agent/` 0 命中。本條規則的真實依據是**實地觀察**：`PM-tools-Dashboard-docker` 存在 `.agent/skills/ui-ux-pro-max/`，由第三方安裝器（`uipro init --ai antigravity`）寫入，非 Antigravity 自身產生。⚠️ 依此，規則的正當性是「使用者刻意放的技能應提交」，**不是**「工具會讀這個路徑」—— 後者無依據，勿據以推論。範本已加註，無此目錄的專案可整組刪除 | 實地觀察（第三方安裝器產物）＋二進位反證 | 2026-08-04 | 1.0.13 | 已驗證 |
| C-82 | `~/.codex/skills/.system/` | Codex **內建系統技能**的存放處（含 `.codex-system-skills.marker`，底下有 `imagegen`、`skill-creator`、`review-agent` 等）。意義：`~/.codex/skills/` 這個目錄**永遠存在**，不論使用者有沒有裝過第三方技能。⚠️ 因此安裝器判斷「舊版相容路徑要不要續寫」時，**不能用「目錄是否存在」當判準** —— 否則使用者手動刪掉的舊複本會在下次安裝時復活。判準已改為「該目錄裡是否已有本專案裝過的技能」 | 本機實查 | 2026-08-04 | 0.146.0-alpha.9.2 | 已驗證 |
| C-57 | `.agents/rules/`、`.agent/rules/` | 工作區規則資料夾，官方：「Workspace rules live in the `.agents/rules` folder of your workspace or git root」，性質同 `.claude/rules/` → **應提交（已放行）**。官方另載「now defaults to `.agents/rules`, but still maintains backward support for `.agent/rules`」，故舊佈局一併放行 | 官方文件 `/docs/rules-workflows` | 2026-08-03 | 2.x | 已驗證 |
| C-58 | `.agents/mcp_config.json` | 工作區層級 MCP server 定義，官方：「Workspace servers: `.agents/mcp_config.json`」（全域版為 `~/.gemini/config/mcp_config.json`）→ **應提交（已放行）**。原被 `.agents/*` 誤殺 | 官方文件 `/docs/cli/gcli-migration` | 2026-08-03 | 2.x | 已驗證 |
| C-59 | `~/.gemini/config/sidecars/`、`~/.gemini/config/plugins/<name>/sidecars/` | Sidecar 設定檔為 **`sidecar.json`（單數）**，官方明載只有這兩個位置、**都在家目錄**；專案層無此概念 → 本 skill **無需新增規則**。2026-08-03 回報曾稱專案 `.agents/` 下可能有 `sidecars.json`，經查二進位與官方文件皆無，不予採納 | 官方文件 `/docs/sidecars` | 2026-08-03 | 2.x | 已驗證 |

> 📌 **版本編號說明**（2026-08-03 更正）：Antigravity 有**兩套版本號** ——
> 產品版本走 2.x（changelog 的發行表：`2.4.3 July 28, 2026`、`2.3.1`、`2.3.0`⋯，最新 2.4.3），
> 而 `agy --version` 回傳的 `1.0.13` 是 CLI 執行檔自身的版號。
>
> ⚠️ 先前（2026-07-30）曾據 `agy --version` 與本機設定檔查無 `2.0` 字串，判定「1.x／2.0」標籤
> 無可觀察依據 —— **該判定有誤**。當時只查了本機檔案與二進位，卻沒查**已在監控清單中的
> changelog**，那裡就有正式的版本表。產品確實有 2.x 世代，回報自稱「2.0」並非杜撰。
>
> 路徑標籤仍維持「現行全域佈局／遷移前佈局」，但理由與版本無關：
> `~/.gemini/config/.migrated` 是可直接觀察的分界證據，比版本號更貼近實際行為（C-47、C-48）。
>
> 此版本號現已納入自動監控：**次版號跳動即告警**，作為重跑實機交接的觸發訊號。

## 跨工具

| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-60 | `.agents/` | **非 Antigravity 專屬**，是 Codex／Gemini CLI／Antigravity 共用的跨工具目錄 | 官方文件（三方交叉） | 2026-07-29 | — | 已驗證 |
| C-95 | 抽取器的長名與右側邊界（**非路徑主張**，故不列入監控涵蓋率） | `TOKEN_RE` 的 alternation 取**最先命中者**。2026-08-22～08-26 期間 `.antigravityignore` 因長名漏列而被存成 `.antigravity`，baseline 保存的不是官方原文檔名。第一輪已補入長名與**排序不變式**，但那只能保護清單內已知名稱；Codex 第二次複驗仍可重現 `.agentsfoo` → `.agents`、`.antigravityignore.bak` → `.antigravityignore` 等錯誤。→ dot-name 分支已補**右側邊界**：直接連接字元、連字號，或 `.` 後再接檔名字元時不得命中；單獨句尾 `.` 仍可由後處理清除。此邊界也揭露 baseline 中 5 個既有假 token：`./.codex` 來自 `./.codex-log`，4 個 `.copilot` 為完整家目錄路徑或 HTML class 的前綴殘留；已取原文上下文確認後精準移除。回歸測試同時覆蓋正向完整檔名、合法嵌套路徑、已知長名順序與 6 個未知長名負向案例 | 程式碼實測＋官方來源上下文＋回歸測試 | 2026-08-26 | — | 已驗證 |
| C-96 | 比較語彙與上下文取用（**非路徑主張**，故不列入監控涵蓋率） | **① 目錄尾斜線不構成路徑機制異動。** 2026-08-28 Issue #10 把 `.claude/skills`、`~/.claude/skills` 報成新增，實查官方 skills 頁後確認兩者各只有**一處**命中，都出自新增的指令範例「`claude plugin validate .claude/skills` for project skills or `claude plugin validate ~/.claude/skills` for personal skills」，是既有 `.claude/skills/`、`~/.claude/skills/` 的**尾斜線別名**，不是新儲存位置 → 告警比較改以 `token.rstrip("/\\")` 為鍵，**baseline 仍保存原文拼法**。C-06／C-53／C-62／C-92 均未被推翻，五版 SKILL.md 零異動。⚠️ **刻意接受的靈敏度損失（比照 D5 的取捨聲明）**：等價之後，**文件把某路徑從檔案改寫成目錄（或反之）將永遠不會告警** —— 實測 `.codexignore` → `.codexignore/` 完全無聲。判斷依據是散文中的斜線本來就不是可靠證據，且該情境機率極低；但這是**損失，不是沒有損失**。反斜線與正斜線**不**等價（`~\.claude\` vs `~/.claude/` 仍告警），目前無來源使用 Windows 表示法。另注意上游同頁常同時使用兩種拼法（全帳本 11 個 key 有雙拼法，皆為文件用語習慣），故上游日後若只留一種拼法，舊拼法會**永久留在 baseline** —— 不誤報，屬可接受殘留。**② 上下文必須取自實際 match span。** 原 `context_for()` 用 `text.find(token)`，短 token 會先命中較長路徑的子字串：Issue #10 為 `.claude/skills` 附上的竟是 `.claude/skills/deploy/SKILL.md` 那段「Custom commands have been merged into skills」，**錯的上下文會直接導向錯的分類決定**（D6 的第一步就出錯）。→ 改為走 `iter_token_matches()` 比對完整 token 後取 match span。依 C-89 驗證斷言有效：停用尾斜線等價 → 3 個測試轉紅且精確重現 Issue #10 假警報原文；還原 `find()` 實作 → 上下文測試轉紅 | 官方 skills 頁實查＋回歸測試（26 項）＋遠端 E2E run | 2026-08-28 | claude-code 2.1.250 | 已驗證 |
| C-88 | CI 斷言的寫法（**非路徑主張**，故不列入監控涵蓋率） | **原結論只修正 `! cmd` 與 `-v`，仍漏掉 index 行為。** 顯式 `check()` 雖避免 `set -e` 靜默通過，但普通 `git check-ignore -q` 預設不回報已追蹤檔案；GitHub Actions checkout 後，應放行檔即使白名單被刪除仍可能回傳 1，被錯判為正常。 | bash 手冊＋端對端實測 | 2026-08-09 | — | 被取代→C-89 |
| C-89 | CI ignore-policy 斷言（**非路徑主張**，故不列入監控涵蓋率） | 判定 `.gitignore` 規則行為必須使用 `git check-ignore --no-index -q -- <path>`，將 exit 0／1／其他錯誤分別處理為 ignored／allowed／command error；不得靠 `!` 反轉。`allowed` 與 `tracked` 是不同維度，如需確認納入版控，另以 `git ls-files --error-unmatch -- <path>` 斷言。2026-08-11 以 PM-tools-Dashboard-docker 四個實際已追蹤的放行檔重驗：普通模式全回傳 1，`--no-index` 才能在移除白名單時看見 ignore 規則。已同步五版與範本驗證器。 | `git check-ignore -h`（`--no-index: ignore index when checking`）＋實際 index 重驗 | 2026-08-11 | Git 2.x | 已驗證 |

---

## 依據摘錄

> 引述自各工具官方文件／changelog，取證日 2026-07-29。
> 機器可比對的 token 快照見 [`scripts/last_checked.json`](../../../scripts/last_checked.json)。

**C-05** `.claude/rules/` — [docs.claude.com/en/docs/claude-code/memory](https://docs.claude.com/en/docs/claude-code/memory)
> For larger projects, you can organize instructions into multiple files using the `.claude/rules/`
>
> The dialog protects you from files other people commit to a shared project.

**C-07** `~/.claude/projects/` — 同上
> Each project gets its own memory directory at `~/.claude/projects/<project>/memory/`

**C-11** `.codex/config.toml` — [developers.openai.com/codex/config-basic](https://developers.openai.com/codex/config-basic)
> To scope settings to a specific project or subfolder, add a `.codex/config.toml` file in your repo.

**C-13** `.agents/skills` — [developers.openai.com/codex/skills](https://developers.openai.com/codex/skills)
> For repositories, Codex scans `.agents/skills` in every directory from your current working directory up to the repository root.

**C-14** `.agents/plugins/marketplace.json` — [developers.openai.com/codex/changelog](https://developers.openai.com/codex/changelog)
> You can install plugins for just yourself with `~/.agents/plugins/marketplace.json` and `~/.codex/plugins/`, or for everyone on a project with `.agents/plugins/marketplace.json`

**C-21** `.gemini/settings.json` — [gemini-cli docs/cli/settings.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/settings.md)
> **Workspace settings**: `your-project/.gemini/settings.json` … Workspace settings override user settings.

**C-22** `.agents/skills/` — [gemini-cli docs/cli/skills.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/skills.md)
> Within the same tier (user or workspace), the `.agents/skills/` alias takes precedence over the `.gemini/skills/` directory.

**C-32** `.cursor/rules/imported/` — [cursor.com/docs/context/rules](https://cursor.com/docs/context/rules)
> `.cursor/rule/imported/<repoName>/dir/rule.mdc`
> Cursor will pull and sync the rule(s) into your project. Rules will be placed in `.cursor/rules/imported/<repoName>`

**C-08** — [docs.claude.com/en/docs/claude-code/plugins](https://docs.claude.com/en/docs/claude-code/plugins)
> **Plugins** (self-contained directories with skills, agents, hooks, or a `.claude-plugin/plugin.json` manifest) … Sharing with teammates, distributing to community, versioned releases, reusable across projects

**C-09** — [claude-code CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
> project-scope workflow saves now target the closest existing `.claude/workflows/`
>
> Fixed worktree creation following a repository-committed symlink at `.claude/worktrees`, which could create files outside the repository

**C-53** — [docs.claude.com/en/docs/claude-code/skills](https://docs.claude.com/en/docs/claude-code/skills)
> it writes what worked to `.claude/skills/verify/SKILL.md` at the repo root, or in the touched package directory in a monorepo, so later runs and other agents follow the same steps

**C-15／C-16** — [developers.openai.com/codex/changelog](https://developers.openai.com/codex/changelog)
> for everyone on a project with `.agents/plugins/marketplace.json` and a repo-local plugin directory such as `./plugins/`
>
> Every plugin is a folder with a required `.codex-plugin/plugin.json` manifest

**C-17** — [developers.openai.com/codex/hooks](https://developers.openai.com/codex/hooks)、[/rules](https://developers.openai.com/codex/rules)
> the four most useful locations are: `~/.codex/hooks.json` … `<repo>/.codex/…`
>
> Create a `.rules` file under a `rules/` folder next to an active config layer (for example, `~/.codex/rules/default.rules`)
>
> Untrusted projects skip project-scoped `.codex/` layers, including project-local config, hooks, and rules.

**C-23** — [gemini-cli docs/cli/gemini-ignore.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-ignore.md)
> Gemini CLI includes the ability to automatically ignore files, similar to `.gitignore` (used by Git) and `.aiexclude` (used by Gemini Code Assist).

**C-24** — [gemini-cli docs/cli/session-management.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/session-management.md)
> Sessions are stored in `~/.gemini/tmp/<project_hash>/chats/`

**C-44** `.agents/hooks.json` — [antigravity.google/changelog](https://antigravity.google/changelog)
> Fixed workspace-local hooks defined in `/.agents/hooks.json` not loading after trusting a folder

**C-45** `.antigravitycli/` — 同上
> Decoupled project discovery from local `.antigravitycli` workspace directories. The CLI now stores workspace-to-project mappings in a centralized `~/.gemini/antigravity-cli/cache/projects.json` file, eliminating repository clutter

**C-47** `~/.gemini/config/` — 同上
> Fixed the /agents panel's "Create New Agents" section displaying the wrong global configuration directory (`~/.gemini/antigravity-cli/` instead of `~/.gemini/config/`)

**C-50** `AGENTS.md` — 同上
> Added support for reading rules from `AGENTS.md` in addition to `GEMINI.md`

**C-44／C-54／C-55** — `agy.exe` 1.0.13 二進位字串（`%LOCALAPPDATA%\agy\bin\agy.exe`，152 MB）
> `{workspace}/.agents/skills/{skill_name}/SKILL.md`
> `{workspace}/.agents/agents/{agent_name}/agent.json`
> `- Path: ".agents" (relative to the workspace root)`
> `loaded %d named hooks from %d hooks.json file(s)`
> `Maintain an **ORIGINAL_REQUEST.md** file that captures user requests verbatim.`
> `append it to .agents/ORIGINAL_REQUEST.md with a UTC timestamp header`
> `append it to .agents/<your_folder>/ORIGINAL_REQUEST.md with a UTC timestamp header`

**C-54** — 同上，agents／skills 的建立路徑函式對稱（各 3 次出現）
> `{workspace}/.agents/agents/{agent_name}/agent.json`
> `{appDataDir}/agents/{agent_name}/agent.json`
> `store.(*Manager).GetAgentsCreatePath` ／ `store.(*Manager).GetGlobalAgentsCreatePath`
> `store.(*SkillsManager).GetSkillsCreatePath` ／ `GetGlobalSkillsCreatePath`
> `writing agent.json` ／ `marshaling agent.json`

**C-78** — [VS Code / GitHub Copilot 實機回覆](./rounds/2026-08-03-vscode-copilot.reply.md)
> 同一個 active Copilot agent session 的 workspace storage metadata 對應到目前 repository；
> session 內容、transcript、debug log 與 editing state 均存於 `<VS Code user-data>/User/workspaceStorage/<workspace-id>/`。
>
> global storage 另有 `github.copilot-chat/toolEmbeddingsCache.bin`；實查期間 repository 的 Git 狀態保持乾淨。

---

## 交接輪次紀錄

| 日期 | 工具 | 涵蓋項目 | 交接包 | 回覆 |
| :--- | :--- | :--- | :--- | :--- |
| 2026-07-29 | Antigravity 1.0.13 | C-41～C-49（新增 C-51、C-52） | [交接包](./rounds/2026-07-29-antigravity.md) | [回覆](./rounds/2026-07-29-antigravity.reply.md)　已回填；其中 C-44、C-48 經維護者複驗後**未採信**回報結論 |
| 2026-07-30 | Antigravity 1.0.13 | C-48、C-54（Q1 為實驗題） | [交接包](./rounds/2026-07-30-antigravity-round2.md) | [回覆](./rounds/2026-07-30-antigravity-round2.reply.md)　C-48 結案（實驗方法正確）；C-54 與自由敘述的 4 條路徑未採信，C-54 改由二進位對稱設計自行結案 |
| 2026-07-30 | 官方文件研究（無需交接） | C-08、C-09、C-15～C-17、C-23、C-24、C-32、C-53 | — | 九項全部由官方文件直接定案，未動用交接輪次 |
| 2026-08-04 | Codex、Copilot（＋Antigravity 可選） | 移除舊安裝路徑後的載入實查；C-54 實體檔案 | [交接包](./rounds/2026-08-04-load-path-check.md) | Codex [已實機回覆](./rounds/2026-08-04-codex.reply.md)（**全部採用**，新增 C-85：確認自 `~/.agents/skills/` 載入，移除舊複本後技能未消失；並抓出我方三處文件缺失，其中 `README.md` 的檢查指令含兩個 `0x07` 控制字元而**實際跑不出正確結果**）。Copilot [已實機回覆](./rounds/2026-08-04-vscode-copilot.reply.md)（**全部採用**，新增 C-86：同樣確認自 `~/.agents/skills/` 載入；並**推翻我方 C-79 的一項依據** —— 兩份同名實體複本在 catalog 中只出現一個項目，原稱「同時看得到兩份」是由目錄存在推論的循環證據）。Antigravity [已回覆](./rounds/2026-08-04-antigravity.reply.md)（**部分採用**，新增 C-87：誠實聲明無實機資料，所提社群 schema 經維護者以二進位 protobuf 定義獨立佐證成立；但「白名單完全正確且必要」的**強度不採用** —— 仍無人目視實體檔案、Q3 自陳無法斷定、且 key 命名 snake_case／camelCase 未定，故 `!.agents/agents/` **維持註解狀態**）。**本輪三工具全部回覆完畢** |
| 2026-08-26 | 排程偵測 → 維護者分類（無需交接） | Issue #7 累積的四批候選 token | [分類紀錄](./rounds/2026-08-26-claude.candidate-triage.md) | **全數歸檔為 C-90～C-93，五版 SKILL.md 零異動**（皆為家目錄路徑或文件範例）。三個發現：`synced` 是**專案層也適用的保留名稱**（C-92）；官方文件只描述 `backups/` 的損毀複本用途，實查發現實際是例行備份 —— **只憑 token 登記會把用途寫窄**（C-90）；`post_tool_use.py` 與 C-17 同屬「自文件範例抽出 token」的陷阱（C-93）。另核對 08-22 的 17 條「消失」為官方頁面改版，涵蓋率未降、無主張失去監控。Issue #7 曾據此結案 —— **但 Codex 複驗發現漏一項**：`.antigravityignore` 被抽取器**靜默截短**成 `.antigravity`（C-95），該候選從未以正確檔名出現在報告中。已補修已知長名不變式與未知長名右側邊界、補登 C-94／C-95、更正 C-90 措辭、同輪寫回 baseline，Issue #7 再次結案。詳見分類紀錄第八節 |
| 2026-08-28 | 排程偵測 → Codex 修正 → Claude 複驗 | Issue #10 的兩個候選 token | [複驗紀錄](./rounds/2026-08-28-claude.slash-alias-review.md) | **判定為假陽性，機制修正而非帳本修正 —— 五版 SKILL.md 與既有主張零異動。**兩個「新增」token 是既有目錄的尾斜線別名，實查官方頁確認各只有一處命中、都出自新增的 `claude plugin validate` 指令範例。Codex 一併抓到 `context_for()` 用 `text.find()` 會讓短 token 的上下文**指向較長路徑**（Issue #10 正是受害者）→ 新增 **C-96**。複驗獨立確認：兩 token 的精確命中位置、`.claude/commands/` 五版皆有白名單（C-04）故「commands 已併入 skills」不推翻任何主張、26 項測試、遠端 run 各步驟正確跳過、涵蓋率維持 50／2。**本輪是自動追蹤機制第一次走完「偵測 → 分類 → 修機制 → E2E 驗證 → 結案」的完整循環** |
| 2026-08-12 | Codex（實作修正）→ Claude 複驗 | Windows CP950 輸出、generic YAML fence | [Codex 交接](./rounds/2026-08-12-codex.reply.md) | [Claude 複驗](./rounds/2026-08-12-claude.review.md)　**兩項皆通過**。CP950 以「修正前必須崩潰」的雙向測試證實重現環境有效（`↔` U+2194 → `❌` U+274C 二次崩潰，與回報一致）；generic 兩段 YAML 與其餘四版逐字一致，C-89 的 `--no-index` 判定未被更動。**不需異動本帳本** —— 兩項均為實作與 Markdown 結構修正，未新增或推翻外部工具路徑事實 |
| 2026-08-07 | 比對 PM-tools-Dashboard-docker 實際運作 | 該專案 `.gitignore` 與現行範本的落差 | — | 發現 `.claude/launch.json` 被 `.claude/*` 靜默擋下 → 新增 **C-83**。另記該專案 `.gitignore` 自 2026-07-11 起未再更新，`.codex/`、`.gemini/` 的整包封殺已與 C-17、C-21 不符（目前該專案兩目錄為空，屬潛在而非現行誤殺） |
| 2026-08-04 | 維護者自查（縱向稽核） | 全範本每條規則的依據強度 | [稽核紀錄](./rounds/2026-08-04-speculation-audit.md) | 三條篩出：C-54 依據**被低估**（實為明確路徑模板，非對稱推論）；`.agent/skills/` 缺主張且規則寬於官方向後相容範圍 → 新增 C-81；`!.agents/AGENTS.md`／`!.agents/settings.json` 為**不存在的檔案**留白名單 → **已自五版移除**。另記三條假陽性係帳本路徑欄索引不足所致 |
| 2026-08-03 | **四工具交叉檢視** | 全部主線工具 | [交叉檢視文件](./rounds/2026-08-03-cross-tool-review.md) | Antigravity [已回覆](./rounds/2026-08-03-antigravity.reply.md)（6 項中 3 項複驗未採用，新增 C-59）；Claude Code [已自答](./rounds/2026-08-03-claude-code.reply.md)（新增 C-61、C-62）；Codex 與 Copilot 的文件端問題已由 [docs 查證](./rounds/2026-08-03-codex-copilot.docs.md) 定案（新增 C-75～C-77）；Copilot [已實機回覆](./rounds/2026-08-03-vscode-copilot.reply.md)（新增 C-78，無需新增 project `.gitignore` 規則）；Codex [已實機回覆](./rounds/2026-08-03-codex.reply.md)（**推翻我方 C-17 的 rollout 誤植**，新增 C-63、C-64）；四工具交叉檢視全部完成 |

---

## 監控來源缺口

**2026-08-26 發現。** `SOURCES` 目前納入 4 個 claude-code 來源（`settings`、`memory`、
`skills`、`changelog`），但官方另有一份**未納入監控**的 `.claude` 目錄參考頁：

```
https://docs.claude.com/en/docs/claude-code/claude-directory.md
```

該頁是 `~/.claude/` 的完整佈局說明。實測抽出的 token 中，**有 24 個是目前 baseline 沒有的**：

```
~/.claude/agent-memory/     ~/.claude/cache/changelog.md   ~/.claude/debug/
~/.claude/feedback-bundles/ ~/.claude/file-history/        ~/.claude/image-cache/
~/.claude/logs/             ~/.claude/output-styles/       ~/.claude/paste-cache/
~/.claude/plans/            ~/.claude/plugins/             ~/.claude/policy-limits.json
~/.claude/remote-settings.json  ~/.claude/session-env/     ~/.claude/stats-cache.json
~/.claude/statsig/          ~/.claude/todos/               ~/.claude/uploads/
~/.claude/usage-data/       （另有 4 條為文件中的相對路徑範例）
```

### 為什麼值得記

C-90 初版把「settings 頁只描述損毀複本」誤寫成「官方文件不完整」。實際上該頁
**完整描述了例行備份**（「keeps the five newest」），與本機實查的 5 個檔完全吻合 ——
**問題不在官方文件，在我們選的來源。**

24 條全屬家目錄，**不影響任何專案層 `.gitignore` 規則**，因此這不是誤殺風險；
但它意味著「盲區」的實際範圍比 `--coverage` 報的更大 ——
coverage 只能回答「已登記的主張有沒有來源涵蓋」，**回答不了「有沒有該登記卻沒登記的路徑」**。

### 附帶盲點：dot-name 直接接副檔名的檔名無法被表示（2026-08-26 補記）

`TOKEN_RE` 的 dot-name 分支要求名稱後接 `/` 才能向下延伸，因此 `~/.claude.json`
這種「dot-name 後直接接副檔名」的檔名**從來就無法以完整檔名抽出**
（`.mcp.json`、`settings.local.json` 是各自寫死的字面例外）。
C-95 的右側邊界補上後，此類檔名的行為從「**靜默截短**成 `~/.claude`」變成「**靜默不抽**」——
後者較安全（不會把錯的值存進 baseline），且在現行 26 個來源上實測新舊差異為 0。

與本缺口直接相扣：claude-directory 頁提及 `~/.claude.json` 共 **9 次**。
該頁若日後納入 `SOURCES`，這個檔名會完全不出現在報告與 baseline 中。
實質影響小（家目錄檔案，與 C-90 同類，專案範本本來就不需要規則），
但**決定納入該頁時需一併處理**，例如比照 `.mcp.json` 增列字面 token。

### 尚未處理

是否把該頁納入 `SOURCES` 屬**監控機制的調整**，與本輪的候選分類是不同性質的決定，
依 D9 的拆分原則**不在本輪一併處理**。納入時需注意：

- 新來源會走 bootstrap 路徑（測試矩陣已涵蓋：建立來源 baseline、不誤報為異動）
- 24 條新 token 需逐一分類，工作量與本輪相當
- `~/.claude.json` 需以字面 token 增列（見上方附帶盲點），否則該頁最常出現的檔名反而進不了 baseline
