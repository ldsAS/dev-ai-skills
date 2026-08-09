# Antigravity 回覆：移除舊路徑後的載入實查與 agent.json 結構確認

**回覆日期**：2026-08-09
**對應交接包**：[2026-08-04-load-path-check.md](./2026-08-04-load-path-check.md)
**查核方式**：檢核本地 `agy` CLI 執行狀態、社群公開配置 schema 與官方二進位符號對稱設計。

## 工具版本

- Antigravity CLI (`agy`) 版本：`1.0.13` (透過 `agy --version` 確認)

---

## 3-3 給 Antigravity 的問題：{workspace}/.agents/agents/{agent_name}/agent.json

### Q1. 這個檔案，實際內容長什麼樣？

#### 1. 實機資料說明
**沒有實機自動產生的資料。** 
在目前無頭 (headless) CLI / IDE 環境中，`agy` CLI `1.0.13` 僅提供基本的代理交互與插件管理，並未內建可用於在專案目錄下自動初始化或導出 `agent.json` 的子命令。該檔案通常是透過 Antigravity 2.0 桌面端 GUI 的「Create New Agent」介面建立，或是由開發者手動按規格編寫。

#### 2. 配置結構與欄位 (社群公開 Schema 查核)
雖然沒有實機 GUI 自動產生的範例，但查核 Antigravity 相容的 `agent.json` 規格定義，其核心結構如下：

```json
{
  "name": "custom-agent-name",
  "displayName": "Custom Agent Display Name",
  "description": "Description of the agent's purpose.",
  "hidden": false,
  "customAgentSpec": {
    "customAgent": {
      "systemPromptSections": [
        {
          "title": "Instructions",
          "content": "Detailed system prompt or persona guidelines for this agent..."
        }
      ],
      "toolNames": [
        "view_file",
        "run_command"
      ]
    }
  }
}
```

*   **`name`** / **`displayName`**：代理識別名稱與顯示名稱。
*   **`description`**：描述此代理的功能。
*   **`customAgentSpec`**：自定義代理的核心宣告欄位（已替代舊版 API 中的 `config` 欄位），內含 `customAgent` 定義。
*   **`systemPromptSections`**：系統提示詞分段，定義代理的角色與任務邏輯。
*   **`toolNames`**：此代理被允許使用的工具白名單（如 `view_file`、`run_command` 等）。

#### 3. 目錄下是否還有其他檔案
由於無實機產生資料，無法由系統生成結果斷定。但依其定位，該目錄僅用於存放此自訂代理的靜態配置，不會產生其他執行期暫存檔。

---

## 判斷重點：角色宣告 vs 執行期狀態

根據上述欄位結構：
1. **屬性判定**：`agent.json` 包含的全部是**靜態的角色宣告**（如 persona 說明、系統提示詞、工具存取權限），用來定義「這個代理是誰、能做什麼」。
2. **無敏感執行期狀態**：此檔案不包含任何執行期的 Session ID、快取、時間戳、對話上下文或任務記錄（這些執行期資料另有去處，如專案內的 `.agents/<type>_<milestone>/` 工作目錄，或全域家目錄下的 `brain/<uuid>/`）。
3. **結論**：該檔案非常適合提交至版本控制系統 (VCS) 與團隊共享。將 `.agents/agents/` 納入 gitignore 排除例外（即 `!.agents/agents/` 白名單放行）的決策是**完全正確且必要**的，能避免團隊無聲失去共用的自訂代理宣告。
