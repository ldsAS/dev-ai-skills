# 交接包：Antigravity 路徑確認 — 2026-07-29

**涵蓋帳本項目**：C-41、C-42、C-43、C-44、C-45、C-46、C-48、C-49
**產生原因**：Antigravity 無公開文件站，這批路徑無法從官方文件查證
**回覆請存為**：`2026-07-29-antigravity.reply.md`

---

## 以下貼給 Antigravity（從這條線以下整份複製）

---

# 【交接查核】Antigravity 路徑確認

## 這是什麼

我維護一個開源專案 [`dev-ai-skills`](https://github.com/ldsAS/dev-ai-skills)，其中的
`ai-git-ignore-strategy` skill 會指導 AI 助理判斷：哪些 AI 工具產生的檔案該進 Git、哪些該擋。
你自己也是這個 skill 的使用者之一（`skills/ai-git-ignore-strategy/antigravity/SKILL.md`）。

這個 skill 的正確性取決於一組**路徑事實**。我已用自動化機制每日比對 Claude Code、Codex、
Gemini CLI、Cursor 的官方文件，但 **Antigravity 沒有公開文件站**
（`antigravity.google/docs` 是空 stub），唯一能穩定取得資訊的來源是
`antigravity.google/changelog`。以下項目因此無法從文件確認，需要你在實際環境查。

### 三件重要的事

1. **請以你實際看到的檔案系統狀態回答，不要用訓練知識推測。**
   這批問題中有兩項（`.agents/AGENTS.md`、`.agents/settings.json`）在 2026-07-07
   曾由 Antigravity 回報「確認存在」，但當時沒有留下檔案系統的實查證據，也沒記版本號，
   所以目前在帳本上是「有疑」而非「已驗證」。這次要的是 `ls` 的實際輸出。
2. **每題請標明信心程度**，並明確區分「我執行指令看到的」與「我推論的」。
3. **版本號是必填**。缺版本號的回覆無法與官方文件的時間軸對照，會被記為「未驗證」。

## 先回報環境

```text
Antigravity 版本（About / 說明 → 關於）：
是 IDE 還是 CLI（或兩者）：
作業系統：
測試用專案的絕對路徑：
```

## 請先執行這些指令

在一個**已經被 Antigravity 開啟並實際使用過**的專案根目錄執行：

```bash
# 專案層
ls -la .agents/ .agent/ .antigravitycli/ 2>/dev/null
find .agents .agent .antigravitycli -maxdepth 3 2>/dev/null

# 家目錄
ls -la ~/.gemini/
ls -la ~/.gemini/config/ ~/.gemini/antigravity/ ~/.gemini/antigravity-cli/ 2>/dev/null
```

PowerShell 環境請改用：

```powershell
Get-ChildItem -Force .agents, .agent, .antigravitycli -ErrorAction SilentlyContinue
Get-ChildItem -Force -Recurse -Depth 2 .agents -ErrorAction SilentlyContinue
Get-ChildItem -Force $HOME\.gemini
Get-ChildItem -Force $HOME\.gemini\config, $HOME\.gemini\antigravity, $HOME\.gemini\antigravity-cli -ErrorAction SilentlyContinue
```

**請把指令的原始輸出一併貼回來**，不要只給結論。

---

## 待確認項目

### Q1（C-41）`.agents/AGENTS.md` 是否真的存在？

- **目前 skill 怎麼寫**：列為「應該提交」的專案級 AI 規則檔，`.gitignore` 範本有
  `!.agents/AGENTS.md` 白名單放行。
- **官方文件怎麼說**：**查無依據**。2026-07-29 掃過 20 個官方來源（含 Codex、Gemini CLI、
  Cursor 文件與 Antigravity changelog）皆未出現此路徑。changelog 只提到
  Antigravity 支援讀取**根目錄**的 `AGENTS.md`（與 `GEMINI.md` 並列），沒提到 `.agents/` 底下的。
- **請確認**：`.agents/AGENTS.md` 這個檔案實際存在嗎？若存在，是誰建立的（工具自動產生
  還是使用者手動建立）？Antigravity 會讀它嗎？它跟根目錄的 `AGENTS.md` 是什麼關係？

### Q2（C-42）`.agents/settings.json` 是否真的存在？

- **目前 skill 怎麼寫**：列為「專案共用設定」，範本有 `!.agents/settings.json` 白名單放行。
- **官方文件怎麼說**：**查無依據**（同 Q1）。倒是 changelog 提到全域設定在
  `~/.gemini/antigravity-cli/settings.json`，專案設定在 `~/.gemini/config/projects/`
  ——都在**家目錄**，不在專案內。這與「專案內有 `.agents/settings.json`」的說法不一致。
- **請確認**：專案內的 `.agents/settings.json` 存在嗎？如果存在，它跟
  `~/.gemini/config/projects/` 底下的設定是什麼關係？哪個優先？

### Q3（C-43）`.agents/settings.local.json` 是否存在？

- **目前 skill 怎麼寫**：列為個人本機設定，範本明確排除。
- **官方文件怎麼說**：查無依據。這條規則可能是類比 Claude Code 的
  `.claude/settings.local.json` 而來，未必反映 Antigravity 實際行為。
- **請確認**：存在嗎？若不存在，這條規則就是空轉的死規則，我會移除。

### Q4（C-44）`.agents/hooks.json` 屬團隊共用還是個人？

- **目前 skill 怎麼寫**：範本裡以**註解形式**列出（`# !.agents/hooks.json`），預設**不放行**，
  等你確認後再決定。
- **官方文件怎麼說**：changelog 證實**確實存在**：
  > Fixed workspace-local hooks defined in `/.agents/hooks.json` not loading after trusting a folder

  另一則提到 `/hooks` 指令曾誤寫到 `~/.gemini/antigravity-cli/hooks.json`，
  正確位置應為共用的 `~/.gemini/config/hooks.json`。
- **請確認**：專案內的 `.agents/hooks.json` 是設計給**整個團隊共用**（該提交），
  還是**個人本機**（該排除）？它跟家目錄的 `hooks.json` 如何合併／覆寫？
  補充：hooks 內含可執行指令，若判定為團隊共用，提交前需要安全提醒。

### Q5（C-45）`.antigravitycli/` 你這版還會產生嗎？

- **目前 skill 怎麼寫**：已新增 `.antigravitycli/` 排除規則。
- **官方文件怎麼說**：changelog 說已淘汰：
  > Decoupled project discovery from local `.antigravitycli` workspace directories.
  > The CLI now stores workspace-to-project mappings in a centralized
  > `~/.gemini/antigravity-cli/cache/projects.json` file, eliminating repository clutter

- **請確認**：你目前的版本還會在專案內建立 `.antigravitycli/` 嗎？
  若不會，是從哪一版開始不會的？（舊專案可能仍有殘留，規則我會保留。）

### Q6（C-46）2.0 還會產生 `.agent/` 嗎？

- **目前 skill 怎麼寫**：`.agent/` 標為「Antigravity 1.x 專案工作區暫存」並排除。
- **官方文件怎麼說**：查無依據。
- **請確認**：你這版會不會建立 `.agent/`（單數）？如果只有 1.x 才有，這條規則是否還有保留價值？

### Q7（C-48）1.x 的全域 skills 路徑是 `~/.gemini/antigravity/skills/` 嗎？

- **目前 skill 怎麼寫**：本專案的 `install.sh` 與 `CONTRIBUTING.md` 都依賴兩條路徑：
  - `~/.gemini/config/skills/`（2.0 全域）
  - `~/.gemini/antigravity/skills/`（1.x 全域）
- **官方文件怎麼說**：2.0 的 `~/.gemini/config/` 已由 changelog **間接佐證**
  （某版曾誤顯示 `~/.gemini/antigravity-cli/` 而非正確的 `~/.gemini/config/`）。
  但 `~/.gemini/antigravity/skills/` **查無任何依據**。
- **請確認**：`~/.gemini/` 底下實際有哪些子目錄？skills 到底裝在哪？
  （這條若錯，本專案的安裝器就是把檔案放到錯的地方。）

### Q8（C-49）Antigravity 的對話紀錄存在哪？

- **目前 skill 怎麼寫**：只泛稱「多數工具的對話紀錄存在使用者家目錄」，
  沒有指出 Antigravity 的實際位置。
- **官方文件怎麼說**：changelog 提過 "SQLite conversation store"，但沒說路徑。
- **請確認**：對話紀錄／session 實際存在哪個路徑？**會不會寫進專案目錄**？
  （這是本 skill 最核心的關切——若會寫進專案，必須有規則擋下。）

### Q9 觸發語法

- **目前 skill 怎麼寫**：`skills/ai-git-ignore-strategy/README.md` 的維護者備註仍記載
  「`@ai-git-ignore-strategy` 觸發語法是否在 2.0 有效」待確認。
- **請確認**：在你這版，使用者要怎麼喚起一個已安裝的 skill？`@skill-name` 還有效嗎？

---

## 回填格式

請照下列格式逐題回覆：

```text
### Q1
存在：是 / 否 / 無法確認
實際路徑：
用途（你觀察到的）：
應提交或應排除：提交 / 排除 / 需視情況
依據：我執行了什麼指令、看到什麼輸出
信心：高 / 中 / 低
```

最後請補一段自由敘述：

> **有沒有我沒問到、但你認為這個 skill 應該涵蓋的 Antigravity 路徑？**
> 特別是任何會寫進**專案目錄**的自動產生檔案（cache、index、session、lock、log）。

---

## 附註：請留意輸出品質

過去曾發生 Antigravity 產出夾帶中英混雜的文字損壞（例如「多數工具 of 對話紀錄」）。
回覆前請自我檢查一次中文是否完整。
