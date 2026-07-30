# 交接回覆：Antigravity 第二輪 — 2026-07-30

**交接包**：[`2026-07-30-antigravity-round2.md`](./2026-07-30-antigravity-round2.md)
**回報環境**：Antigravity `1.0.13`／IDE + CLI／Windows 11

> 維護者在同機以 `agy.exe` 字串分析與檔案系統查核複驗。

| 題 | 帳本 | 回報結論 | 複驗後採用 |
| :--- | :--- | :--- | :--- |
| Q1 | C-48 | `~/.gemini/antigravity/skills/` 是死路徑 | ✅ **採用** — 方法正確 |
| Q2 | C-54 | `.agents/agents/` 應提交 | ⚠️ **結論相同但依據不採用**，改由二進位對稱設計獨立佐證（見文末） |
| 自由敘述 | — | 列出 4 條 `.agents/` 執行期路徑 | ❌ **全數不採用**（但直覺方向正確） |
| 自由敘述 | — | 建議的 `.gitignore` 寫法 | ❌ **不採用** — 有三處退步 |

---

## ✅ Q1 採用：這次的方法是對的

與第一輪不同，這次做了**真正的實驗**而非推論：

1. 只在待測路徑建立探針技能 `zz-probe-legacy-path`
2. 確認另一路徑沒有同名項目（對照組）
3. 以 `invoke_subagent` 開全新子代理，強制重新初始化並掃描技能目錄
4. 子代理回報可用技能中**沒有**探針，且明確指出 `ai-git-ignore-strategy` 載入自
   `C:\Users\LdsFi\.gemini\config\skills\ai-git-ignore-strategy\SKILL.md`
5. 清理探針目錄

第 4 步是關鍵——它不只給出否定結果，還**正面指認了實際載入路徑**，構成完整的證據。
維護者複驗確認探針已清乾淨（`~/.gemini/antigravity/skills/` 現僅餘 `ai-git-ignore-strategy`）。

**C-48 結案**：`~/.gemini/antigravity/skills/` 在 1.0.13 已不被掃描。

### 連帶修正安裝器

複驗時發現 `install.sh` / `install.ps1` 的偵測邏輯有實質缺陷：

```bash
[[ -d "$HOME/.gemini/antigravity" ]] && has_antigravity_v1=true   # 舊寫法
```

`~/.gemini/antigravity/` **是現行版本使用中的資料目錄**（`conversations/`、`brain/`、
`builtin/skills/` 都在裡面），拿它的存在判定為「1.x 舊版」是錯的。結果是**每個現代安裝
都會多寫一份技能到已證實沒人讀的目錄**。

已改為：遷移前佈局只在「沒有現行 `~/.gemini/config`」時才作為 fallback。
實測兩種情境皆符合預期：

```text
現代（config + antigravity 皆存在） → 只裝到 ~/.gemini/config/skills/
遷移前（僅 antigravity）           → fallback 到 ~/.gemini/antigravity/skills/
```

---

## ❌ Q2 不採用：用了明文禁止的推論方式

交接包最後一句寫著：

> 若你的環境中沒有任何 `.agents/agents/`，請直接說「無法確認」，
> **不要**依 `.claude/agents/` 的類比推論作答。

回報的依據 1 是「實地搜尋⋯⋯均未產生實體的 `agent.json`」（＝沒找到），
依據 2 則是「依據核心架構設計⋯⋯類似 `.claude/agents/`」——**正是被禁止的那條路**。
在零觀察樣本的情況下標記「信心：高」並給出「應提交」，不予採納。

**它的推論過程不予採納。** 不過同一結論後來由二進位分析獨立取得了依據——
見文末〈追加：C-54 由二進位對稱設計自行結案〉。答案碰巧對，不代表推論方式可接受。

---

## ❌ 自由敘述四條路徑：全部查無實據

回報列出四條「執行期敏感檔案」。每一條都帶著 `(或 ...)` 的括號替代寫法——這是猜測的特徵——
且沒有說明是執行什麼指令看到的。以 `agy.exe` 1.0.13 逐一比對：

| 回報宣稱 | 二進位出現次數 | 實際情形 |
| :--- | ---: | :--- |
| `.agents/workspaces/`（或 `workspace/`） | 0 | 查無 |
| `.agents/scratch/` | 0 | `scratch/` 真實存在，但位於 `{{ArtifactDirectoryPath}}/scratch/`，非 `.agents/` 底下 |
| `.agents/milestones.json`（或 `milestone.md`） | 0 | milestone 是真概念，但**不是這個檔名**（見下） |
| `.agents/logs/`（或 `.agents/tasks/`） | 0 | 任務日誌實際在 `~/.gemini/antigravity/brain/<uuid>/.system_generated/logs/` |

最後一條可由回報自身的系統訊息反證——它貼出的 log 路徑正是：

```text
file:///C:/Users/LdsFi/.gemini/antigravity/brain/ff178158-.../.system_generated/tasks/task-76.log
```

**在家目錄，不在專案。** 另查 artifacts 目錄亦在家目錄（`~/.gemini/antigravity-ide/html_artifacts`、
`~/.gemini/antigravity/brain/<uuid>/`）。

### 但方向是對的：真正的模式是 `.agents/<type>_<milestone>/`

二進位中確實有寫進專案 `.agents/` 的**子代理工作目錄**命名規則：

```text
.agents/<type>_<milestone>[_<N>][_gen<N>]/
- `<milestone>`: from your decomposition (e.g., `lexer`, `parser`)
```

配合先前查到的 `.agents/<your_folder>/ORIGINAL_REQUEST.md`，可知子代理會在專案內
建立以「類型＿里程碑」命名的工作目錄，並在其中記錄使用者訊息。
已登記為 **C-56**，現行 `.agents/*` 已完整涵蓋（邊界測試新增案例確認）。

---

## ❌ 不採用它建議的 `.gitignore` 寫法

回報建議：

```gitignore
.agents/*
!.agents/skills/
!.agents/agents/
!.agents/AGENTS.md
!.agents/settings.json
!.agents/hooks.json
```

三處退步：

1. `!.agents/skills/` 之後**沒有再用 `.agents/skills/*` 擋回**，會把本機安裝的第三方技能
   一起放行。現行範本刻意做了這層 scoped allowlist。
2. `!.agents/AGENTS.md`、`!.agents/settings.json` —— **它自己在第一輪已確認這兩者不存在**，
   這裡又建議放行，與自身前次結論矛盾。
3. `!.agents/hooks.json` 無條件放行，且未附安全提示。該檔內含可執行指令，
   而它在第一輪自己也提過需要信任機制。現行範本以註解形式保留、要求開發者確認後才放行。

---

## 本輪 skill 與 repo 異動

| 檔案 | 異動 |
| :--- | :--- |
| `install.sh`、`install.ps1` | 遷移前佈局改為 fallback（僅在無 `~/.gemini/config` 時啟用）；標籤去除無據的「2.0／1.x」 |
| `CONTRIBUTING.md`、skill `README.md` | 同步安裝路徑說明 |
| `verification/CLAIMS.md` | C-48、C-54 均結案；新增 C-56 |

`install.ps1` 已確認保留 UTF-8 BOM 與 CRLF，PowerShell 解析 0 錯誤。

---

## 追加：C-54 由二進位對稱設計自行結案（2026-07-30）

回報的「應提交」結論不採信（依據是被禁止的類比），但改查二進位後，**結論相同而依據不同**。

關鍵不是類比 Claude Code，而是 **agy 自己的對稱設計**：

```text
store.(*Manager).GetAgentsCreatePath        ／ GetGlobalAgentsCreatePath       （各 3 次）
store.(*SkillsManager).GetSkillsCreatePath  ／ GetGlobalSkillsCreatePath       （各 3 次）

{workspace}/.agents/agents/{agent_name}/agent.json
{appDataDir}/agents/{agent_name}/agent.json
```

工具為 agents 與 skills 建立了**完全平行的兩層（workspace／global）結構**。
既然 `.agents/skills/`（workspace 技能）本 skill 已放行，同一層級的
`.agents/agents/` 沒有理由擋下——那是工具自己認定的同類物。

另外兩項佐證：

- `writing agent.json`、`marshaling agent.json` —— 是使用者發起（`Create New Agents` UI）
  的持久化宣告，不是執行期日誌。
- 執行期狀態**另有去處**：專案內是 `.agents/<type>_<milestone>/`（C-56），
  家目錄是 `brain/<uuid>/`。`.agents/agents/` 不承擔那個角色。

**已放行 `!.agents/agents/`**，並在 ❓ 需確認保留一句：尚無人目視過實體檔案，
提交前請確認內容是角色宣告而非執行狀態。

風險權衡：若判斷錯誤而放行，會提交一些不該提交的檔案 —— 在 `git status` 看得見、
容易發現、易於回復；若判斷錯誤而擋下，團隊會**無聲地**失去共用子代理定義，
正是本 skill 最警告的「誤殺」失效模式。兩者不對稱，故採放行。

---

## Antigravity 部分至此全部結案

帳本 Antigravity 區 16 條全數定案（已驗證 15、結構性 1），無「待實查」與「有疑」殘留。
