# 跨工具交叉檢視 — 2026-08-03

**目的**：本輪對 skill 與監控機制做了大幅調整，請四個工具**各自檢視與自己相關的路徑主張**，
確認與該工具的實際行為相符。

**用法**：第三部分依工具分節，每節都自帶背景，可**單獨整份複製**貼給對應的工具。
回覆請存成 `2026-08-03-<tool>.reply.md`。

---

# 第一部分：本輪異動總覽

## A. 兩項先前的錯誤判定（重要）

### A-1　「Antigravity 沒有公開文件站」是錯的

先前只測了索引頁 `antigravity.google/docs`、拿到 345 bytes 的 stub 就下結論，
**沒有跟著頁面連結往下追**。實際有 **80+ 頁**文件，位於 `/docs/<section>` 之下。

後果：6 條 Antigravity 路徑主張被誤標為「監控盲區」，白白靠人工交接維持了一輪。

### A-2　C-48 判斷錯誤，且造成實際回歸

官方 `/docs/ide/skills` 與 `/docs/skills` 兩頁文字幾乎相同，只差一行：

| 產品 | 工作區 skills | **全域 skills** |
| :--- | :--- | :--- |
| Antigravity **IDE** | `<workspace-root>/.agents/skills/` | `~/.gemini/antigravity/skills/` |
| Antigravity **CLI** | `<workspace-root>/.agents/skills/` | `~/.gemini/config/skills/` |

兩條全域路徑**並存**，分屬不同產品，不是新舊關係。

先前的標記技能實驗把探針只放進 `~/.gemini/antigravity/skills/`，子代理回報看不到，
據此判定該路徑已死 —— 但那個子代理跑在 **CLI 情境**，實驗只證明「CLI 不讀這條」，
卻被推論成「沒人讀」。**結論的適用範圍超出了實驗涵蓋的產品。**

接著又據此把 `install.sh` / `install.ps1` 改成 fallback，於是在同時安裝 IDE 與 CLI 的
機器上，技能不再寫入 IDE 全域路徑 —— **等於在 IDE 端失效**。已還原雙路徑寫入。

> ⚠️ 若你的環境同時有 Antigravity IDE 與 CLI，請重跑一次安裝器補回 IDE 端。

### A-3　版本號之謎解開

```text
Antigravity 2.0 ┬ Antigravity CLI（agy，自身版本 1.x，文件導覽列標 v1.1.9）
                ├ Antigravity IDE
                └ Antigravity SDK
```

changelog 發行表的 `2.4.3` 是**套件版本**，`agy --version` 的 `1.0.13` 是 **CLI 元件版本**。
兩個都是真的，先前判定「查無 2.0 版本字串、該標籤無依據」有誤。

## B. 範圍調整

| 項目 | 調整 |
| :--- | :--- |
| **Cursor** | **移出維護範圍**（維護者未使用）。五版範本移除 3 條規則、監控來源移除、帳本 C-30～C-32 保留但標為「移出範圍」並排除於比對與涵蓋率外 |
| **Gemini CLI** | 降為參考層。倉庫未封存、未改名、npm 未 deprecated，仍是獨立產品；但官方有 `/docs/cli/gcli-migration` 說明如何遷移至 Antigravity CLI |
| **VS Code Copilot** | **從 0 提升為主線**。此前它是唯一「有變體、但 0 監控來源、0 帳本主張」的工具 |

## C. 新發現的誤殺與遺漏

| 帳本 | 路徑 | 問題 | 依據 |
| :--- | :--- | :--- | :--- |
| C-57 | `.agents/rules/`、`.agent/rules/` | 被 `.agents/*` 誤殺 → **已放行** | 官方：「Workspace rules live in the `.agents/rules` folder of your workspace or git root」；另載仍向後相容 `.agent/rules` |
| C-58 | `.agents/mcp_config.json` | 被誤殺 → **已放行** | 官方：「Workspace servers: `.agents/mcp_config.json`」 |
| C-72 | `*.instructions.md` | skill 完全未涵蓋 → **已登記** | Copilot 四種自訂檔型別之一 |
| C-73 | `*.agent.md` | skill 完全未涵蓋 → **已登記** | 同上 |

## D. 機制強化

| 項目 | 內容 |
| :--- | :--- |
| 範本邊界驗證 | 新增 `scripts/verify_gitignore_template.py` + CI（push 到 `skills/**` 觸發）。48 個案例實跑 `git check-ignore` |
| Antigravity 版本追蹤 | 自 changelog 發行表取版本；**次版號跳動即提醒重跑交接**（其他工具為主版號門檻） |
| TOKEN_RE 排序修正 | `*.agent.md` 原會被 DOT_NAMES 的 `agent` 先吃掉、只留 `.agent` |
| 涵蓋率排除規則 | 「移出範圍」的主張不再計入盲區，避免報表失真 |

## E. 數據對照

| 指標 | 本輪前 | 本輪後 |
| :--- | ---: | ---: |
| 監控來源 | 13 | **22** |
| 帳本主張 | 43 | **50** |
| 可自動偵測 | 21 | **34** |
| 監控盲區 | 8 | **2** |
| 範本邊界案例 | 0（無此機制） | **48** |

剩餘 2 個盲區皆合理無解：`~/.gemini/tmp`（Gemini CLI session，已降參考層）、
`~/.copilot/skills`（本專案安裝器自己的目標路徑，不會有官方文件提及）。

---

# 第二部分：四工具對照表

| 工具 | 對應模型 | 變體 | 監控來源 | 帳本主張 | 範本規則 | 版本告警門檻 |
| :--- | :--- | :---: | ---: | ---: | ---: | :--- |
| **Antigravity** | Gemini | `antigravity/` | 8 | 18（C-40～C-58） | `.agents` 13、`.agent` 4、`.antigravitycli` 1 | **次版號** |
| **Claude Code** | Claude | `claude/` | 4 | 10（C-01～C-09、C-53） | `.claude` 11 | 主版號 |
| **Codex** | ChatGPT | `codex/` | 3 | 8（C-10～C-17） | `.codex` 8 | 主版號 |
| **VS Code Copilot** | GitHub Copilot | `vscode/` | 3 | 5（C-70～C-74） | `.github/prompts` 等 | 無（不在 npm） |
| *generic（基準）* | — | `generic/` | — | — | 同上，不指名工具 | — |
| *Gemini CLI（參考）* | Gemini | 無 | 4 | 5（C-20～C-24） | `.gemini` 4 | 主版號 |
| *Cursor（已移出）* | — | 無 | 0 | 3（C-30～C-32，凍結） | 0 | — |

## 三層防護與觸發方式

| 層 | 防什麼 | 觸發 | 需要人在場 |
| :--- | :--- | :--- | :---: |
| `check-updates.yml` | 上游官方文件變了 | 排程，每日 UTC 01:15 | ❌ |
| `verify-template.yml` | 自己把規則改壞 | push 到 `skills/**` | ❌ |
| `verification/rounds/` | 文件與實機不符 | Antigravity 次版號跳動時自動提醒 | ✅ |

---

# 第三部分：給各工具的自我檢視清單

> 以下四節各自獨立，請整節複製給對應工具。

## 共通要求（每節都已內含，此處僅供維護者參考）

過去兩輪交接的教訓，四項要求都是有來由的：

1. **以實際觀察回答，不要用訓練知識推測。** 曾有回報把訓練知識當成觀察結果，
   導致兩條「已確認存在」的路徑實際上根本不存在。
2. **不要用「跟其他工具類似」作答。** 曾有回報在自己環境搜尋後一個樣本都沒找到，
   卻改以「類似 `.claude/agents/`」給出高信心結論。
3. **沒有樣本就說「無法確認」。** 這比猜測有用得多。
4. **必附版本號。** 缺版本號的回覆無法與官方文件的時間軸對照，一律記為未驗證。

---

## 3-1　給 Antigravity

```text
【交叉檢視】Antigravity 路徑主張 — 2026-08-03

我維護開源專案 dev-ai-skills 的 ai-git-ignore-strategy skill，
它會指導 AI 判斷哪些檔案該進 Git。以下是目前登記的 Antigravity 路徑主張，
請以你實際環境確認是否相符。

先回報：Antigravity 版本（agy --version 與產品版本）、IDE 還是 CLT、作業系統。

【應該提交（範本已放行）】
  .agents/skills/<自撰技能>/      工作區技能
  .agents/agents/<name>/agent.json 工作區自訂子代理定義
  .agents/rules/                  工作區規則（舊佈局 .agent/rules/ 亦放行）
  .agents/mcp_config.json         工作區 MCP server 定義
  .agents/plugins/marketplace.json 團隊共用外掛市集
  AGENTS.md、GEMINI.md（根目錄）   專案級規則檔

【應該排除（範本已擋）】
  .agents/ORIGINAL_REQUEST.md              逐字記錄使用者訊息（敏感）
  .agents/<type>_<milestone>[_N][_genN]/   子代理工作目錄
  .agents/settings.local.json / .agent/ / .antigravitycli/
  .agents/hooks.json                       ← 目前以註解形式擋著，見下方 Q3

【已知不存在（範本保留防禦性白名單）】
  .agents/AGENTS.md、.agents/settings.json
  （2026-07-29 實查不存在；專案設定實際在 ~/.gemini/config/projects/<uuid>.json）

【全域路徑】
  IDE → ~/.gemini/antigravity/skills/     CLI → ~/.gemini/config/skills/

請確認：
Q1 上列「應該提交」六項，在你的環境是否都存在且屬團隊共用？有無遺漏？
Q2 上列「應該排除」是否有任何一項其實該提交？
Q3 .agents/hooks.json 該不該提交？（內含可執行指令，需權衡）
Q4 兩條全域 skills 路徑（IDE / CLI）的分工是否正確？
Q5 除上列之外，還有什麼會被寫進專案 .agents/ 的檔案？

回覆格式（逐題）：
  結論：相符 / 不符 / 無法確認
  依據：我執行了什麼、看到什麼
  信心：高 / 中 / 低

請以實際觀察回答，不要用訓練知識推測；沒有樣本請直接說「無法確認」。
```

---

## 3-2　給 Claude Code

```text
【交叉檢視】Claude Code 路徑主張 — 2026-08-03

我維護開源專案 dev-ai-skills 的 ai-git-ignore-strategy skill。
以下是目前登記的 Claude Code 路徑主張，請確認是否與實際行為相符。

先回報：Claude Code 版本、作業系統。

【應該提交（範本已放行）】
  .claude/settings.json      團隊共用設定（權限、hooks）
  .claude/commands/          團隊共用 slash commands
  .claude/agents/            團隊共用 subagents
  .claude/rules/             團隊共用分檔規則
  .claude/workflows/         專案層 workflow
  .claude/skills/verify/     /verify 自動寫入，官方定位為要共享
  .claude-plugin/plugin.json、marketplace.json（本 repo 本身是外掛時）

【應該排除（範本已擋）】
  .claude/settings.local.json  個人本機設定
  .claude/skills/<第三方>/     本機安裝的技能（自撰的則應提交）
  .claude/worktrees/           git worktree 實體目錄

【對話紀錄】~/.claude/projects/ 等家目錄，不寫入專案

請確認：
Q1 上列分類是否正確？特別是 .claude/rules/ 與 .claude/workflows/
   是否確實有 user-scope 與 project-scope 兩層、且 project-scope 屬團隊共用？
Q2 .claude/skills/verify/SKILL.md 由 /verify 自動寫入，官方說明是
   「so later runs and other agents follow the same steps」。
   這類「自動產生但意圖共享」的檔案，還有哪些？
Q3 .claude/worktrees/ 官方曾修過「repository-committed symlink 可在 repo 外建檔」，
   這個風險是否仍存在？提交該路徑的 symlink 是否仍應避免？
Q4 除上列之外，還有什麼會被寫進專案 .claude/ 的檔案？

回覆格式（逐題）：結論 / 依據 / 信心。
請以實際觀察或官方文件回答，不要憑推測。
```

---

## 3-3　給 Codex

```text
【交叉檢視】Codex 路徑主張 — 2026-08-03

我維護開源專案 dev-ai-skills 的 ai-git-ignore-strategy skill。
以下是目前登記的 Codex 路徑主張，請確認是否與實際行為相符。

先回報：Codex 版本、作業系統。

【應該提交（範本已放行）】
  .codex/config.toml     專案層設定覆寫
  .codex/hooks.json      專案層 lifecycle hooks
  .codex/hooks/*.py      hook 腳本
  .codex/rules/*.rules   沙箱指令規則
  .agents/plugins/marketplace.json  團隊共用外掛市集
  .codex-plugin/plugin.json         外掛清單檔（本 repo 是外掛時）
  AGENTS.md（根目錄）

【應該排除（範本已擋）】
  .codex/rollout.jsonl   session 執行期紀錄
  .codex/skills/<第三方>/ 本機安裝的技能（自撰的則應提交）
  .agents/plugins/<外掛本體>/  外掛本體實際存於 repo-local 的 ./plugins/

請確認：
Q1 上列「應該提交」六項是否正確？官方文件提到未信任的專案會跳過
   「project-local config, hooks, and rules」，這三者是否都在 .codex/ 之下？
Q2 .codex/ 專案目錄除上列外，還有什麼會被自動產生（cache、session、索引等）？
Q3 .agents/skills 的掃描規則（從 CWD 逐層往上掃到 repo root）是否仍正確？
Q4 外掛本體的實際位置是否為 repo-local 的 ./plugins/？

回覆格式（逐題）：結論 / 依據 / 信心。
請以實際觀察或官方文件回答，不要憑推測。
```

---

## 3-4　給 VS Code / GitHub Copilot

```text
【交叉檢視】GitHub Copilot 路徑主張 — 2026-08-03

我維護開源專案 dev-ai-skills 的 ai-git-ignore-strategy skill。
這個工具的路徑主張是 2026-08-03 才首次建立的（此前完全沒有登記），
所以特別需要你確認完整性。

先回報：VS Code 版本、Copilot 擴充版本、作業系統。

【應該提交（範本不擋，預設會進 Git）】
  .github/copilot-instructions.md   專案指令檔（/init 產生）
  .github/prompts/*.prompt.md       共享 prompt files
  *.instructions.md                 針對語言／框架／資料夾的指令檔
  *.agent.md                        自訂 agent 定義檔
  AGENTS.md、CLAUDE.md              官方列為 always-on instructions

【使用者層（不影響專案）】
  ~/.copilot/skills/                本專案安裝器的 vscode 目標路徑

請確認：
Q1 上列五類自訂檔是否完整？官方文件列出的型別為
   SKILL.md / *.agent.md / *.instructions.md / *.prompt.md，是否還有其他？
Q2 *.instructions.md 與 *.agent.md 的**慣用存放位置**是哪裡？
   （.github/instructions/？.github/agents/？或任意位置？）
Q3 Copilot 是否會在專案目錄產生任何 cache、log、session 等執行期檔案？
   若有，路徑為何？這是本 skill 最該擋的一類。
Q4 ~/.copilot/skills/ 是否為正確的使用者層技能路徑？

回覆格式（逐題）：結論 / 依據 / 信心。
請以實際觀察或官方文件回答；Q3 若無法確認請直接說明，不要猜測。
```

---

# 回填流程

1. 各工具回覆存成 `2026-08-03-<tool>.reply.md`
2. **獨立複驗**後才回填帳本 —— 前兩輪共有四項回報經複驗後未採信
3. 帳本結論改變時**新增一列**並將舊列標為「被取代→C-XX」，不覆寫
4. 若改動範本規則，跑 `python scripts/verify_gitignore_template.py`（全綠才算數）
