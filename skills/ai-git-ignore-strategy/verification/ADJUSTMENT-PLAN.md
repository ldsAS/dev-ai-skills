# 調整規劃：安裝範圍與機制邊界 — 2026-08-03

**背景**：四工具交叉檢視完成後，需要決定兩件事 ——
(1) 這個 skill 該裝全域還是專案層；(2) 它與其他既有機制有沒有功能重疊。

本文件先呈現**查核結果**，再給**分階段調整規劃**。尚未執行任何調整。

---

# 第一部分：功能重疊檢核

檢核對象：五個工具全域 skills 目錄的實際內容 ＋ Claude Code 的內建 skill／指令。

## A. 無重疊（確認可共存，不需處理）

| 機制 | 來源 | 為什麼不重疊 |
| :--- | :--- | :--- |
| `permissioned-github` | Antigravity builtin | 講的是**如何**與 GitHub 互動（`gh` CLI 用法、權限不足時如何請求授權），完全不涉及「什麼該提交」。實測 gitignore／commit 判斷關鍵字命中 **0 次** |
| `accidental-data-loss-prevention` | Gemini／Antigravity builtin | 針對**不可逆的破壞性操作**（`DROP TABLE`、`gcloud ... delete`、KMS 銷毀），與 git 追蹤無關 |
| `skill-repair`、GCP／BigQuery 系列 20 個 | Gemini builtin | 領域完全不同，關鍵字命中 0 |
| `simplify` | Claude Code | 針對已變更程式碼的品質重構，不判斷檔案該不該進 git |
| `review` | Claude Code | 審查 GitHub PR 的內容，非追蹤配置 |

**結論**：外部工具的 GitHub 機制與本 skill **職責不衝突**。
`permissioned-github` 管「能不能推」，本 skill 管「該不該推」，兩者互補。

## B. 真正的功能重疊（需要劃界）

### B-1　`security-review` ↔ 本 skill 的「機密檔案」判斷

| | `security-review` | 本 skill |
| :--- | :--- | :--- |
| 觸發 | 審查目前分支的待提交變更 | 檢核 gitignore／commit 前審查 |
| 手段 | 檢查**變更內容**是否有安全問題 | 讓機密檔案**根本不被追蹤** |
| 涵蓋 | `.env` 內容、硬編碼金鑰、注入風險⋯⋯ | `.env`、`*.pem`、`*.key`、`certs/`、`credentials.json` 的**追蹤狀態** |

**重疊處**：兩者都關心機密外洩。
**差異**：一個是「內容審查」（事後偵測），一個是「追蹤阻擋」（事前預防）。

**這是互補而非取代**，但目前兩份 skill 都沒說明彼此關係，實際使用時可能：

- 使用者以為跑過 `security-review` 就不必檢核 gitignore（漏掉未追蹤但即將被 `git add .` 的機密檔）
- 或反過來以為 gitignore 檢核過就不必做內容審查（漏掉**已提交檔案內**的硬編碼金鑰）

### B-2　觸發詞碰撞：「commit 前審查」

本 skill 的 `description` 含觸發詞「**commit 前審查**」。同一句話也會讓
`security-review`（審查待提交變更）與 `simplify`（審查已變更程式碼）成為候選。

三者都合理，但**使用者說「幫我 commit 前審查一下」時，AI 該挑哪一個並不明確**。

## C. 下游依賴（不是重疊，但相互影響）

以下機制都會**產生「應該提交」的檔案**，而該檔能不能被團隊共用，取決於本 skill 的白名單是否正確：

| 產生者 | 產物 | 帳本 | 若白名單錯了會怎樣 |
| :--- | :--- | :--- | :--- |
| `/verify`（`run` skill） | `.claude/skills/verify/SKILL.md` | C-53 | 團隊失去共用的建置指令紀錄 |
| `fewer-permission-prompts` | 專案 `.claude/settings.json` | C-02 | 團隊各自重複被權限提示打斷 |
| `update-config` | `settings.json`／hooks | C-02 | 同上 |
| `init` | `CLAUDE.md` | 🟢 應提交 | 團隊失去專案指令檔 |

**這是一個值得寫進 skill 的觀察**：本 skill 的白名單不只影響「repo 乾不乾淨」，
還直接決定**其他 AI 機制的產出能不能被團隊共用**。誤殺的代價比想像中大。

另外 `fewer-permission-prompts` 寫入專案 `settings.json` 這件事，正好是 C-53 建立的
**第三類「自動產生但意圖共享」**的又一個實例 —— 可作為該分類的補充例證。

---

# 第二部分：全域 vs 專案的結論

## ⚠️ 本節於 2026-08-04 更正

初版把 `ui-ux-pro-max` 歸為「該放全域」，並把 PM Dashboard 的版本漂移歸因於
「專案層安裝」。**兩點都錯**，維護者指正後重查上游 README 確認：

1. 上游標 **Recommended** 的正是**專案層**（`cd <project>` → `uipro init --ai <tool>`），
   全域只是次要選項。維護者的實際用法一直也是專案層。
2. 版本漂移的成因**不是專案層安裝，而是逐工具安裝**。

## 上游其實提供 2×2 安裝矩陣

| | 專案層 | 全域 |
| :--- | :--- | :--- |
| **逐工具** | `uipro init --ai claude` ← **Recommended** | `--ai claude --global` → `~/.claude/skills/` |
| **跨工具單一** | `--ai universal` → `.agents/skills/` | `--ai universal --global` → `~/.agents/skills/` |
| 全部 | `--ai all` | — |

另有 `uipro update` / `uipro update --global` 可刷新既有安裝。

## 修正後的因果：真正的軸線是「複製份數」

PM Dashboard 的三版本並存：

```text
.agent/skills/ui-ux-pro-max/SKILL.md    bf780c3091e4   10651 bytes
.codex/skills/ui-ux-pro-max/SKILL.md    b4f16d368d4c   10612 bytes  ┐ 相同
.gemini/skills/ui-ux-pro-max/SKILL.md   b4f16d368d4c   10612 bytes  ┘
.agents/skills/ui-ux-pro-max/SKILL.md   07b87b8998b5   14105 bytes  ┐ 相同
.claude/skills/ui-ux-pro-max/SKILL.md   07b87b8998b5   14105 bytes  ┘
```

成因是用了 `--ai claude`＋`--ai antigravity`＋⋯（或 `--ai all`）逐工具安裝。
若改用 `--ai universal`，只會有 `.agents/skills/` **一份**，不會漂移。

**所以「全域 vs 專案」與「逐工具 vs 單一路徑」是兩條獨立的軸，初版把它們混為一談。**

| 軸 | 選項 | 影響 |
| :--- | :--- | :--- |
| 範圍 | 全域／專案層 | 影響「要不要隨 repo 傳承」「版本能不能被釘住」 |
| **份數** | 逐工具／跨工具單一 | **影響版本漂移風險** —— 這才是 PM Dashboard 問題的根因 |

## 專案層的正當理由（初版低估了）

- 團隊要**釘住版本**，確保所有成員用同一版審查流程
- 技能內容需依專案調整（例如某專案的設計系統規格）
- 上游本來就把它當 Recommended，代表這是設計者預期的主要用法

## 全域的正當理由

- 跨專案通用、不隨 repo 傳承的工具
- 不必在每個新專案重跑安裝

## 對本 skill 的結論（修正版）

**兩者皆可，取決於團隊要不要釘版本。** 但無論選哪個，
**都應該優先用單一跨工具路徑 `.agents/skills/`（專案層）或 `~/.agents/skills/`（全域）**，
而不是逐工具複製 —— 這是漂移的真正解方。

依本輪帳本已驗證的事實：`.agents/skills/` 由 Codex（C-13）、Gemini CLI（C-22）、
Copilot（C-77）、Antigravity 共同讀取，是名副其實的跨工具標準路徑。

## 🔴 連帶發現：我們自己的安裝器也在複製

以帳本對照現行六個全域目標：

| 目標 | 誰讀 | 必要性 |
| :--- | :--- | :--- |
| `~/.agents/skills` | Codex（C-64）、Gemini CLI（C-22）、Copilot（C-77） | ✅ 必要 |
| `~/.claude/skills` | Claude Code | ✅ 必要 |
| `~/.gemini/config/skills` | Antigravity CLI（C-47） | ✅ 必要 |
| `~/.gemini/antigravity/skills` | Antigravity IDE（C-48） | ✅ 必要 |
| `~/.codex/skills` | 無官方依據（C-12：官方 scope 表 0 次） | ⚠️ **冗餘** |
| `~/.copilot/skills` | Copilot 亦讀 `~/.agents/skills`（C-77） | ⚠️ **冗餘** |

**我們正在做 PM Dashboard 同樣的事** —— 寫六份，其中兩份多餘。
兩者都不會出錯（多寫無害），但同樣有「更新時漏掉某份」的漂移風險。

---

# 第三部分：調整規劃

## 優先序說明

依「**修正錯誤 → 補足缺口 → 增加彈性**」排序。P0 是目前狀態與事實不符者。

## P0-1　把「技能性質判準」升格為獨立段落　✅ 已完成（2026-08-04）

**已做**：五版新增獨立小節「📦 技能庫 (Skills) 的性質判準」（三類來源對照表＋判斷關鍵），並以 PM Dashboard 的三份複本漂移當反例；⚠️ Ask 段的舊子項改為指向該節，避免同一判準寫兩處。

**現況**：判準藏在 ❓ 需確認段的子條目，容易被略過。
**調整**：升為獨立小節，並以 PM Dashboard 的三版本漂移當反例。
**理由**：這個 skill 誕生的原因，正好是它自己最好的教材。
**影響檔案**：五版 `SKILL.md`
**驗收**：五版同構；`verify_gitignore_template.py` 維持全過。

## P0-2　補上與 `security-review` 的邊界說明　✅ 已完成（2026-08-04）

**已做**：五版於 🔴 段末補上分工說明（事後偵測 vs 事前預防，兩者不可互相取代）。`security-review` 是 Claude Code 內建，故非 claude 版一律寫成「安全審查（如 Claude Code 的 `security-review`）」，不去斷言其他工具也有同名機制。claude／antigravity 版的「🔗 與其他技能協作」段改為指向該說明。

**現況**：兩份 skill 互不提及，使用者可能誤以為做過其一就夠。
**調整**：在本 skill 的「與其他技能協作」段落明確寫出分工 ——

> `security-review` 檢查**變更內容**有沒有安全問題（事後偵測）；
> 本 skill 讓機密檔案**根本不被追蹤**（事前預防）。
> 兩者互補，跑過其一不能取代另一。已提交檔案內的硬編碼金鑰只有前者抓得到；
> 未追蹤但即將被 `git add .` 掃進去的 `.env` 只有後者擋得住。

**影響檔案**：五版 `SKILL.md`（該段已存在，補寫即可）
**驗收**：五版同構。

## P0-3　補上「白名單影響其他機制產出」的說明　✅ 已完成（2026-08-04）

**已做**：五版於 🟢 段末補上對照表（產生者／產物／誤殺的後果），並點明關鍵風險 —— 白名單擋錯時**不會有任何錯誤訊息**，只會讓別人的機制無聲失效。

**現況**：skill 只講 repo 乾淨度，沒講誤殺會連帶影響什麼。
**調整**：在 🟢 應該提交段補一句，並列出第一部分 C 節的對照表。
**理由**：提高白名單正確性的權重，也讓審查者知道為什麼不能「一律擋掉比較安全」。
**影響檔案**：五版 `SKILL.md`

## P1-1　觸發詞去碰撞　✅ 已完成（2026-08-04）

**現況**：「commit 前審查」同時是 `security-review` 與 `simplify` 的合理觸發語。
**已做**：兩個泛用詞改成指向性說法，並在句末加一句明確的**領域切割**：

| 原 | 現 |
| :--- | :--- |
| 「整理 repo」 | 「整理 repo 的 AI 產生物」 |
| 「commit 前審查」 | 「commit 前確認會提交哪些檔案」 |
| （無） | 新增「哪些檔案不該進 git」 |
| （無） | 句末：「只判斷**檔案該不該被 git 追蹤**，不做程式碼安全稽核，也不做重構或簡化 —— 那兩類請交給對應的 skill」 |

**設計原則**：只**收窄自己**，不去動任何既有 skill 的設定 ——
維護者的要求是「不要影響到原本全域 AI 工具就配的 skill」，
因此去碰撞的作法是讓本 skill 不去搶別人的語意，而不是改別人的觸發詞。

**未做**：五工具實際挑選行為的實測。改動只縮小語意範圍、未擴大，
風險偏低，但**下次在各工具用到時仍請留意是否還挑得到**。

## P1-2　安裝器：先減少冗餘複製，再談專案層

初版把這項寫成「加 `--project` 模式」，經 2026-08-04 更正後拆為兩步。

### P1-2a　移除冗餘的全域目標（優先）　✅ 已完成（2026-08-04，commit af48460）

**現況**：六個全域目標中有兩個沒有官方依據 ——
`~/.codex/skills`（官方 scope 表 0 次，見 C-12）與 `~/.copilot/skills`
（Copilot 亦讀 `~/.agents/skills`，見 C-77）。
**調整**：降為「僅在該目錄**已裝過本專案技能**時才續寫」的相容模式，不再主動建立。
> 📌 2026-08-04 修正判準：原本寫的是「目錄已存在」，但 `~/.codex/skills/` 底下有 Codex
> 內建的 `.system/`（C-82），該目錄永遠存在 —— 用目錄存在當判準會讓已刪除的舊複本復活。
**理由**：我們自己正在犯 PM Dashboard 的同型問題 —— 多份複製、更新時易漏。
**風險**：低。兩條路徑本來就有 `~/.agents/skills` 覆蓋。
**驗收**：假 HOME 四情境各測一次（只有 `.system`／已有我方舊複本／空的相容目錄／顯式 codex 模式），並於本機實跑確認刪除後重跑不會復活。

### P1-2b　`--project` 模式　✅ 已完成（2026-08-04）

**已做**：`./install.sh --project [dir]`／`.\install.ps1 project [dir]`，
只寫 `<repo>/.agents/skills/` **單一路徑、單一份複製** —— 即上游 `uipro init --ai universal`
的作法，不是新發明。裝的是 **generic** 變體（共用路徑不能放工具專屬版，見 C-79）。

安裝後會印出兩件必須手動做的事：

1. **`.gitignore` 放行規則** —— 不放行的話本 skill 會把自己藏起來（被自己的 `.agents/skills/*` 擋掉）
2. **AGENTS.md 的使用時機宣告** —— 專案層技能不該只靠觸發詞被撞到。
   這是維護者在 `ui-ux-pro-max` 上實際採用的作法：在 `AGENTS.md` 寫明
   「會動到 X 時要用這個專案 skill」，比依賴 `description` 可靠。

**驗收結果**：

| 檢查 | 結果 |
| :--- | :--- |
| 假專案安裝（bash／PowerShell） | 兩版輸出一致；PS 解析 0 errors、BOM 與 CRLF 保持 |
| 未加放行 → 應被擋 | ✅ 命中 `.agents/skills/*` |
| 加了安裝器印的兩行 → 應放行 | ✅ 命中 `!.agents/skills/ai-git-ignore-strategy/**` |
| 放行沒開太大 | ✅ 第三方技能與 `.agents/ORIGINAL_REQUEST.md` 仍被擋 |
| `git add -A --dry-run` | 只加入 skill 本體與 `.gitignore` |
| 無任何全域工具時 `--project` 仍可用 | ✅ exit 0（專案層安裝不經工具偵測） |

## P2-1　重跑安裝器同步版本

**現況**：Codex 回報本機已安裝的版本停在 7/08，SHA256 與 repo 不同；
其餘工具的全域副本亦未隨本輪大量修正更新。
**調整**：待 P0／P1 定案後統一重跑 `install.sh`。
**理由**：先改完再裝，避免裝兩次。

---

## 不建議做的事

| 提議 | 為何不做 |
| :--- | :--- |
| ~~把 skill 改成只裝專案層~~ | **此列於 2026-08-04 撤回** —— 原理由（會造成 N 份複製）已證實歸因錯誤：漂移來自逐工具安裝，與專案層無關。專案層是上游 Recommended 的作法，若團隊要釘版本則完全合理 |
| 把專案專屬判斷寫進 skill | 判斷屬於專案的 `.gitignore`／`DEPLOY.md`，寫進 skill 會讓通用方法被單一專案綁架 |
| 移除 `permissioned-github` 等既有機制 | 職責不重疊，互補共存 |

---

## 待決事項

1. ~~P1-1 改觸發詞的風險是否可接受~~ → 2026-08-04 維護者同意，已完成
2. ~~P1-2a 移除兩個冗餘全域目標~~ → 已完成
3. ~~P1-2b `--project` 模式是否需要~~ → 已完成
4. ~~P0-1／P0-2／P0-3~~ → 2026-08-04 已完成
5. **P2-1 尚未執行** —— 全域副本仍停在 2026-07-08／09 的版本。
   本輪（含觸發詞修改）要生效必須重跑安裝器；重跑會覆寫全域副本，
   請維護者確認時機
