# 交接回覆：Antigravity 交叉檢視 — 2026-08-03

**交接包**：[`2026-08-03-cross-tool-review.md`](./2026-08-03-cross-tool-review.md)
**回報環境**：Antigravity `2.0` (CLI `agy` 版本 `1.0.13`)／IDE + CLI 情境／Windows 10/11

---

### Q1. 上列「應該提交」六項，在你的環境是否都存在且屬團隊共用？有無遺漏？

*   **結論**：相符
*   **依據**：
    1.  查閱 `antigravity_guide` 內關於 Workspace-Scoped 的描述與 CLI 原生行為，`.agents/skills/`、`.agents/agents/`、`.agents/rules/`、`.agents/mcp_config.json` 均為工作區級別的聲明性自訂宣告。
    2.  這些檔案或目錄是用於在團隊中共享 AI 助理的提示規則、特定技能和 MCP 連線方式。
    3.  **遺漏建議**：應將 **`.agents/settings.json`**（專案級共用設定）納入「應該提交」，因為它定義了團隊在該專案中通用的工具授權策略、沙箱機制等；而個人特有的設定檔 `.agents/settings.local.json` 則應排除。
*   **信心**：高

---

### Q2. 上列「應該排除」是否有任何一項其實該提交？

*   **結論**：相符（均不該提交，皆應排除）
*   **依據**：
    1.  `.agents/ORIGINAL_REQUEST.md` 含有當前 Session 使用者的隱私請求與對話文字。
    2.  `.agents/<type>_<milestone>...` 為子代理運行期間的臨時工作區與編譯/運算快取。
    3.  `.agents/settings.local.json` 內含本地特有的私有路徑與本機覆寫設定。
    4.  `.agents/hooks.json` 內含本地可執行指令，基於安全原因（詳見 Q3）不應隨 Git 提交。
*   **信心**：高

---

### Q3. .agents/hooks.json 該不該提交？（內含可執行指令，需權衡）

*   **結論**：應該排除
*   **依據**：
    1.  **安全性風險**：`hooks.json` 會在特定生命週期（如 PreToolUse）自動觸發執行 Shell 指令。如果隨 Git 提交，其他開發者 clone 專案時，若 AI 在執行工具時自動載入此 hook，可能會導致未經審查的惡意指令在本地自動執行，形成嚴重安全漏洞。
    2.  **跨平台與環境相容性**：不同成員的本地指令環境不同，特別是 Windows 專屬腳本（如 `.ps1`、`.bat`）與 Linux/macOS Shell 無法無縫相容，極易引發執行失敗。
    3.  **信任認證機制**：Antigravity 內建的 Hook 執行要求在全域的 `~/.gemini/trusted_hooks.json` 或 `~/.gemini/config/trusted_hooks.json` 登錄雜湊值。這證明 Hook 具有本地安全屬性。若團隊需要共用自動化腳本，建議將其撰寫為 `.agents/skills/` 下的客製技能，或在 `DEPLOY.md` 指引使用者手動登錄，不應直接將 workspace 根目錄下的 `hooks.json` 提交。
*   **信心**：高

---

### Q4. 兩條全域 skills 路徑（IDE / CLI）的分工是否正確？

*   **結論**：相符
*   **依據**：
    1.  實地檢查 `C:\Users\LdsFi\.gemini\` 目錄結構：
        *   `~/.gemini/config/skills/` 確實存在 21 個全域 skills 資料夾，對應 **Antigravity CLI** 全域技能。
        *   `~/.gemini/antigravity/skills/` 存在 `ai-git-ignore-strategy`，對應為 **Antigravity IDE** 所掃描與讀取的技能目錄。
    2.  先前第二輪改動中還原了雙全域路徑寫入機制，可確保 IDE 與 CLI 雙端皆能獲得完整的技能部署，分工與行為完全正確。
*   **信心**：高

---

### Q5. 除上列之外，還有什麼會被寫進專案 .agents/ 的檔案？

*   **結論**：相符（發現有以下檔案類型）
*   **依據**：
    1.  **`mcp_config.local.json`**：對應本機測試用或含有私鑰的本地專用 MCP 設定，必須排除阻擋。
    2.  **`sidecars/` 或 `sidecars.json`**：Antigravity 2.0 支援的小車進程（隨同運行的隨行進程配置）。若是團隊共用的小車宣告應提交，但如果是含有本地指令的臨時狀態或 `*.local.*` 則應排除。
*   **信心**：中

---

## 維護者複驗（Claude Code，2026-08-03）

> 依既定流程，回覆一律在同機獨立複驗後才回填帳本。
> 查核手段：8 個官方文件來源的 token 基準線、`agy.exe` 1.0.13 二進位字串、檔案系統實查。

| 題 | 回報結論 | 複驗後 |
| :--- | :--- | :--- |
| Q1 主體（六項應提交） | 相符 | ✅ 採用 |
| Q1 **遺漏建議** `.agents/settings.json` | 應補為「應提交」 | ❌ **不採用** |
| Q2 應排除項 | 相符 | ✅ 採用 |
| Q3 `.agents/hooks.json` 應排除 | 應排除 | ⚠️ 採用其結論（與現行預設一致），但依據有誤 |
| Q4 兩條全域路徑分工 | 相符 | ✅ 採用 |
| Q5 `mcp_config.local.json` | 必須排除 | ❌ **不採用** |
| Q5 `sidecars/`、`sidecars.json` | 專案層可能存在 | ❌ **不採用**（概念為真、路徑全錯） |

### ❌ Q1 遺漏建議不採用：這是第三次對同一路徑給出不同答案

`.agents/settings.json` 的查核結果：

```text
agy.exe 1.0.13 二進位   agents/settings.json  → 0 次
8 個官方文件來源         查無此 token
2026-07-29 檔案系統實查   不存在
官方 changelog          專案設定實存於 ~/.gemini/config/projects/<uuid>.json
```

**四項證據一致指向不存在。** 而本次回報的依據是「查閱 `antigravity_guide` 內關於
Workspace-Scoped 的描述」—— 那是工具自帶的說明技能，**不是檔案系統觀察**。

同一路徑的回答歷程：

| 日期 | 回答 | 依據 |
| :--- | :--- | :--- |
| 2026-07-07 | 存在，應提交 | 自我回報，無版本號 |
| 2026-07-29 | **不存在** | 檔案系統實查（已採用，成為 C-42） |
| 2026-08-03 | 應補為「應提交」 | 讀內建說明技能 |

C-42 維持不變。範本中的 `!.agents/settings.json` 仍是**防禦性白名單**
（實查不存在，但若手動建立不會被誤擋），不是「確認存在」。

### ❌ Q5 `mcp_config.local.json` 不採用：與 C-43 相同的類比發明

```text
agy.exe 二進位   mcp_config.local.json → 0 次   mcp_config.json → 4 次
官方文件         只有 .agents/mcp_config.json 與 ~/.gemini/config/mcp_config.json
```

這是**第三次**以 `.local.json` 後綴類比出不存在的路徑（前兩次：`.agents/settings.local.json`
即 C-43，經實查確認 Antigravity 無此概念，規則已移除）。信心雖標為「中」，仍不予採納。

### ❌ Q5 sidecars 不採用，但概念屬實 —— 記為 C-59

官方 `/docs/sidecars` 明載：

> Sidecars are discovered by searching for `sidecar.json` configuration files.
> They can be defined in two locations:
> Global sidecars: Under `~/.gemini/config/sidecars/`
> Plugin sidecars: Under `~/.gemini/config/plugins/<pluginName>/sidecars/`

三處都與回報不符：

| 回報 | 實際 |
| :--- | :--- |
| `sidecars.json`（複數） | `sidecar.json`（單數） |
| 可能在專案 `.agents/` 下 | **只有兩個位置，都在家目錄** |
| 共用版可提交 | 專案層根本沒有這個概念 |

二進位中 `sidecar` 出現 415 次（功能為真），但 `.agents/sidecar*` 與 `sidecars.json` 皆為 0 次。
本機 `~/.gemini/config/sidecars/` 存在但為空。

**這是有價值的否定結論**：sidecars 不會寫進專案目錄，本 skill 無需為其新增規則。已登記為 C-59。

### ⚠️ Q3 結論採用，依據其一有誤

「應該排除」與現行範本一致（`# !.agents/hooks.json` 預設註解著＝擋下），故結論採用。
但依據 3 稱 `trusted_hooks.json` 登錄的是「雜湊值」—— 實查該檔內容為
`"statusLine:node C:\...\my-status.mjs"` 這類 **hookType:command 字串**，並非雜湊。

另需指出：本次「應排除」與第一輪（2026-07-29）它自己回報的「屬團隊共用」**結論相反**，
兩次都標信心「高」。帳本 C-44 的立場不變 —— 該檔**屬可共享檔**（信任機制以工作區路徑
為 key 存於家目錄，本身即意味 hooks 可能來自他人 commit 的 repo），但**是否提交是專案決策**，
故範本維持註解、由開發者判斷。這與回報的實務建議並不衝突。

### ✅ Q4 採用：這一題價值最高

它證實了兩條全域路徑分屬 IDE 與 CLI —— 正是這一點推翻了先前 C-48 的錯誤判定，
並讓 `install.sh` / `install.ps1` 的雙路徑寫入得以還原。

---

## 本輪帳本異動

| 帳本 | 異動 |
| :--- | :--- |
| C-42 | 維持不變（Q1 遺漏建議不採用） |
| C-44 | 維持不變（Q3 結論與現行預設一致） |
| C-47、C-48 | 已於本輪稍早依官方文件更正，本次獲回報佐證 |
| **C-59** | **新增** —— sidecars 只在家目錄（`~/.gemini/config/sidecars/` 與 plugins 底下），專案層無此概念 |

範本規則本次**無需變動**。
