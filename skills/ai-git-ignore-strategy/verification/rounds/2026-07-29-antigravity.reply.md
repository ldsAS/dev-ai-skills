# 交接回覆：Antigravity — 2026-07-29

**交接包**：[`2026-07-29-antigravity.md`](./2026-07-29-antigravity.md)
**回報環境**：Antigravity `1.0.13`（`agy --version`）／IDE + CLI 皆安裝／Windows 11／
`C:\Users\LdsFi\Desktop\BonHub Project\dev-ai-skills`

> 本輪回覆由維護者在**同一台機器**上獨立複驗（Claude Code，2026-07-29～30）。
> 下方「複驗」段落記錄哪些獲得證實、哪些**未被採信**。

---

## 回報摘要

| 題 | 帳本 | 回報結論 | 回報信心 | 複驗後採用 |
| :--- | :--- | :--- | :--- | :--- |
| Q1 | C-41 | `.agents/AGENTS.md` 不存在 | 高 | ✅ 採用 |
| Q2 | C-42 | `.agents/settings.json` 不存在；專案設定在 `~/.gemini/config/projects/<uuid>.json` | 高 | ✅ 採用 |
| Q3 | C-43 | `.agents/settings.local.json` 不存在，係誤類比 Claude Code | 高 | ✅ 採用 |
| Q4 | C-44 | `.agents/hooks.json` 屬團隊共用，與家目錄 hooks 合併、專案優先 | 高 | ⚠️ **不採用**（見下） |
| Q5 | C-45 | `.antigravitycli/` 現行版本不再產生 | 高 | ✅ 採用 |
| Q6 | C-46 | `.agent/` 現行版本不再產生 | 高 | ✅ 採用 |
| Q7 | C-47/48 | 兩條全域 skills 路徑「均屬實」 | 高 | ⚠️ **部分不採用**（見下） |
| Q8 | C-49 | 對話紀錄在家目錄，專案內不產生 | 高 | ✅ 採用（並強化） |
| Q9 | — | `@skill-name` 已不適用，技能自動載入 | 高 | ✅ 採用 |

---

## 維護者複驗

### 獲得證實

在同機執行的獨立查核與回報一致：

```text
.agents/                    存在但為空目錄（0 個項目），建立於 2026-07-07 20:14
agy --version               1.0.13
~/.gemini/antigravity/      最後寫入 2026-07-30 10:03  ← 使用中
~/.gemini/antigravity-cli/  最後寫入 2026-06-27 15:05  ← 已閒置
conversations 項目數        antigravity/ 21 項；antigravity-cli/ 1 項
專案目錄                    無 .agent/、無 .antigravitycli/、無任何 cache/log
```

`.agents/` 這個空目錄的建立時間正是 2026-07-07——即上一輪查核（commit `2ae5a55`）當天。
它是**當時被建立後留下的空殼**，本身不構成任何工具會使用該路徑的證據。

### ⚠️ Q7 部分不採用：`~/.gemini/antigravity/skills/` 的證據是循環的

回報說「在兩個路徑底下都確實存在本技能目錄 `ai-git-ignore-strategy`，證明此兩條路徑均屬實」。

**這個推論不成立**——那兩份檔案是本專案自己的 `install.sh` 在 2026-07-09 20:36 寫進去的
（兩份 `SKILL.md` 大小與 mtime 完全相同，皆為 27560 bytes / 2026-07-08 20:15）。
拿自己安裝器的產物當作「工具會讀取此路徑」的證據，是循環論證。

實際的目錄內容差異才是關鍵：

```text
~/.gemini/config/skills/       23 個項目：.datacloud_skills_manifest + 22 個官方內建技能
                               （accidental-data-loss-prevention、bigquery-*、gcp-* 等，日期 2026-06-23）
                               + 我們安裝的 ai-git-ignore-strategy
~/.gemini/antigravity/skills/  1 個項目：只有我們安裝的 ai-git-ignore-strategy
```

`~/.gemini/config/skills/` 有工具自己的 manifest 與內建技能，是**工具實際使用的目錄**；
`~/.gemini/antigravity/skills/` 除了我們塞進去的以外空無一物。

再加上兩項佐證：

- `~/.gemini/config/.migrated`（0 bytes，2026-06-23 12:16）——遷移完成標記
- `~/.gemini/config/import_manifest.json` 記錄 `"source": "antigravity"` 的匯入紀錄（2026-06-27）

**結論**：`~/.gemini/config/` 是遷移後的現行佈局，`~/.gemini/antigravity/skills/` 是遷移前的舊路徑，
且我們的技能是在遷移**之後**（7/09）才寫進去的——很可能寫進了一個沒人讀的位置。
C-48 因此**降級為「有疑」**，而非回報所稱的已證實。

### ⚠️ Q4 不採用：依據循環且標的不存在

回報稱 `.agents/hooks.json` 屬團隊共用、會與家目錄 hooks 合併且專案優先，信心標為「高」。
但：

1. 它自己也寫了「本機測試專案未配置 hooks，所以此處無此檔」——**標的物不存在，無從觀察**。
2. 它引用的唯一依據，是**交接包裡由我提供的那段 changelog 引文**。這是循環。
3. 「與全域 hooks 合併、專案優先」這項具體行為**沒有任何引用來源**，既非觀察也非文件。

該檔確實存在於設計中（changelog 有獨立佐證），但「團隊共用 vs 個人」與合併規則仍屬未驗證。
C-44 維持「有疑」，範本中的白名單維持註解狀態。

### 版本標籤問題

回報全文以「Antigravity 2.0」自稱，但 `agy --version` 回傳 **1.0.13**，
且我在 `config.json`、`antigravity_state.pbtxt`、`settings.json` 中都找不到任何 `2.0` 版本字串。

skill 原本以「1.x / 2.0」區分新舊路徑，這個標籤**沒有可觀察的依據**。
已改用可驗證的描述——「現行全域路徑」對「舊版佈局」，並以 `~/.gemini/config/.migrated` 作為分界證據。

---

## 額外收穫

回報主動指出（並經複驗證實）：

- **專案目錄內不產生任何 cache／log**。所有自動產生物（`agyhub_summaries_proto.pb`、
  `history.jsonl`、`cli.log`、`projects.json` 等）都收在 `~/.gemini/` 底下。
  對本 skill 而言這是重要的**否定結論**：Antigravity 不需要專案層的 cache 排除規則。
- 根目錄的 `AGENTS.md` / `GEMINI.md` 是 Antigravity 支援的專案級規則檔，應提交
  （本 skill 原本就已列入 🟢 應提交，此處為確認）。

---

## 本輪產生的 skill 異動

| 檔案 | 異動 |
| :--- | :--- |
| 五版 `SKILL.md` | 🟢 應提交清單移除 `.agents/AGENTS.md`、`.agents/settings.json` |
| 五版 `SKILL.md` | 範本移除 `.agents/settings.local.json`（仍被 `.agents/*` 涵蓋，邊界測試確認） |
| 五版 `SKILL.md` | 兩條 `!` 白名單改註記為「實查不存在，防禦性保留」 |
| 五版 `SKILL.md` | ⚠️ 註記補上 Antigravity 對話紀錄實際路徑與「專案內不產生 cache」 |
| `antigravity/SKILL.md` | 移除 `@ai-git-ignore-strategy` 觸發語法；改為自動載入 |
| `antigravity/SKILL.md` | 全域 skills 路徑標籤改為「現行／舊版佈局」並註記 C-48 |
| `CONTRIBUTING.md`、skill `README.md` | 同步上述兩項標籤與觸發語法 |

驗證：五版各 28 個邊界案例 `git check-ignore` 全數符合預期。

---

## 下一輪待辦

- C-44 `.agents/hooks.json`：需在**實際配置了 workspace hooks 的專案**上重問，
  並要求提供 `trusted_hooks.json` 與實際載入行為的觀察。
- C-48 `~/.gemini/antigravity/skills/`：需確認 Antigravity 是否真的掃描此路徑。
  若否，`install.sh` 的雙路徑寫入應簡化。
