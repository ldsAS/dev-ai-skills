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
