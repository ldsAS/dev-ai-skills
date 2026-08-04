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

## 實證：PM Dashboard 的現況

`ui-ux-pro-max` 依上游建議以 CLI 逐專案安裝（`cd <project>` → `uipro init --ai <tool>`），
結果在同一個專案內：

```text
.agent/skills/ui-ux-pro-max/SKILL.md    bf780c3091e4   10651 bytes
.codex/skills/ui-ux-pro-max/SKILL.md    b4f16d368d4c   10612 bytes  ┐ 相同
.gemini/skills/ui-ux-pro-max/SKILL.md   b4f16d368d4c   10612 bytes  ┘
.agents/skills/ui-ux-pro-max/SKILL.md   07b87b8998b5   14105 bytes  ┐ 相同
.claude/skills/ui-ux-pro-max/SKILL.md   07b87b8998b5   14105 bytes  ┘
```

**同一個技能、同一個專案、三個不同版本並存**，約 3.2 MB 重複內容。
這是複製式安裝的必然結果：更新時總會漏掉幾份。

而該專案的 `.gitignore` 用的正是本 skill 教的三段式 scoped allowlist：

```text
.claude/*
!.claude/skills/
.claude/skills/*
!.claude/skills/audit-import/      ← 只放行專案自撰的
!.claude/skills/audit-import/**
```

外來的 `ui-ux-pro-max` 一個檔都沒進 git；專案自撰的 `audit-import` 被正確提交。

## 由此得出的判準

真正的分野不是「全域 vs 專案」，而是**技能的性質**：

| 性質 | 例子 | 該放哪 | 理由 |
| :--- | :--- | :--- | :--- |
| 外來通用工具 | `ui-ux-pro-max`、**本 skill** | **全域** | 跨專案通用；裝專案層會複製 N 份並版本漂移 |
| 專案自撰 | `audit-import` | **專案層並提交** | 綁定該專案的資料與流程，團隊必須共用 |

**本 skill 自己早就寫了這個判準**（❓ 需確認段）：

> 透過 CLI 工具安裝的（如 `uipro init --ai claude`）→ **不需要** Git 傳承，
> 在 `DEPLOY.md` 記錄安裝指令即可
> 開發者自行撰寫的客製技能 → **應該提交**

按此判準，`ai-git-ignore-strategy` 屬前者 → **全域為正解**。

## 那「各專案情境不同」的顧慮怎麼辦

顧慮成立，但解法不是把 skill 搬進專案，而是**把方法與決定分開**：

| | 內容 | 存放位置 |
| :--- | :--- | :--- |
| **方法**（通用、不因專案而異） | 五階段審查流程、`git check-ignore` 邊界驗證、行尾與 fileMode 處理 | 全域 skill |
| **決定**（因專案而異） | 這個專案哪些檔案該提交、哪個 skill 要放行 | 該專案的 `.gitignore` ＋ `DEPLOY.md` |

PM Dashboard 已經是這個模式的實例：skill 提供方法，`.gitignore` 承載
「放行 `audit-import`、擋掉 `ui-ux-pro-max`」這個專案專屬的決定。
**判斷本來就不在 skill 裡。**

---

# 第三部分：調整規劃

## 優先序說明

依「**修正錯誤 → 補足缺口 → 增加彈性**」排序。P0 是目前狀態與事實不符者。

## P0-1　把「技能性質判準」升格為獨立段落

**現況**：判準藏在 ❓ 需確認段的子條目，容易被略過。
**調整**：升為獨立小節，並以 PM Dashboard 的三版本漂移當反例。
**理由**：這個 skill 誕生的原因，正好是它自己最好的教材。
**影響檔案**：五版 `SKILL.md`
**驗收**：五版同構；`verify_gitignore_template.py` 維持全過。

## P0-2　補上與 `security-review` 的邊界說明

**現況**：兩份 skill 互不提及，使用者可能誤以為做過其一就夠。
**調整**：在本 skill 的「與其他技能協作」段落明確寫出分工 ——

> `security-review` 檢查**變更內容**有沒有安全問題（事後偵測）；
> 本 skill 讓機密檔案**根本不被追蹤**（事前預防）。
> 兩者互補，跑過其一不能取代另一。已提交檔案內的硬編碼金鑰只有前者抓得到；
> 未追蹤但即將被 `git add .` 掃進去的 `.env` 只有後者擋得住。

**影響檔案**：五版 `SKILL.md`（該段已存在，補寫即可）
**驗收**：五版同構。

## P0-3　補上「白名單影響其他機制產出」的說明

**現況**：skill 只講 repo 乾淨度，沒講誤殺會連帶影響什麼。
**調整**：在 🟢 應該提交段補一句，並列出第一部分 C 節的對照表。
**理由**：提高白名單正確性的權重，也讓審查者知道為什麼不能「一律擋掉比較安全」。
**影響檔案**：五版 `SKILL.md`

## P1-1　觸發詞去碰撞

**現況**：「commit 前審查」同時是 `security-review` 與 `simplify` 的合理觸發語。
**調整**：把本 skill 的觸發詞改為指向性更明確的說法，例如
「commit 前**檢查追蹤配置**」「哪些檔案不該進 git」，並移除易碰撞的泛用詞。
**風險**：改 `description` 會影響 skill 被挑選的時機，**需要實測**。
**驗收**：五個工具各實測一次「幫我 commit 前審查」與
「幫我看哪些檔案不該進 git」，確認挑到預期的 skill。

## P1-2　安裝器加 `--project` 模式（可選）

**現況**：五個目標全部是全域，無專案層選項。
**調整**：新增 `--project` 模式，寫入 `./.agents/skills/`（**單一路徑**，
因為 Codex／Gemini CLI／Copilot／Antigravity 都讀這條，不必複製五份）。
**適用情境**：團隊要把審查流程的版本釘進 repo。
**注意**：裝進專案後需在該專案 `.gitignore` 用 scoped allowlist 放行自己 ——
這點要寫進安裝器的輸出提示，否則會被 skill 自己的規則擋掉。
**驗收**：假 HOME／假專案各測一次；放行規則以 `git check-ignore` 驗證。

## P2-1　重跑安裝器同步版本

**現況**：Codex 回報本機已安裝的版本停在 7/08，SHA256 與 repo 不同；
其餘工具的全域副本亦未隨本輪大量修正更新。
**調整**：待 P0／P1 定案後統一重跑 `install.sh`。
**理由**：先改完再裝，避免裝兩次。

---

## 不建議做的事

| 提議 | 為何不做 |
| :--- | :--- |
| 把 skill 改成只裝專案層 | PM Dashboard 已證實會造成 N 份複製與版本漂移 |
| 把專案專屬判斷寫進 skill | 判斷屬於專案的 `.gitignore`／`DEPLOY.md`，寫進 skill 會讓通用方法被單一專案綁架 |
| 移除 `permissioned-github` 等既有機制 | 職責不重疊，互補共存 |

---

## 待決事項

1. P1-1 改觸發詞的風險是否可接受（會影響 skill 挑選）
2. P1-2 的 `--project` 模式是否現在就做，或先只做 P0
