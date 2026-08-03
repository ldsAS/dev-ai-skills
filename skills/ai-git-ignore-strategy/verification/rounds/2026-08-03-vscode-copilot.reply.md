# VS Code / GitHub Copilot 實機回覆 — 2026-08-03

## 環境

| 項目 | 值 |
| :--- | :--- |
| 作業系統 | Windows |
| VS Code | 1.125.1 |
| GitHub Copilot Chat | 0.53.1（內建 `copilot-chat` 擴充） |
| 範圍 | 本機 VS Code 的標準 local Copilot agent session；不含使用者明確要求 agent 建檔的情況 |

> 本回覆只檢查檔案名稱、目錄結構與 session metadata；未轉錄任何對話內容。

## Q1　自訂檔類型

**結論：相符。**

文件端結論正確：除了 always-on instructions（`.github/copilot-instructions.md`、`AGENTS.md`、`CLAUDE.md`）外，Copilot 支援 file-based instructions、prompt files、custom agents、agent skills 與 hooks。這些都是刻意建立、可供團隊共享的 customization，不是執行期暫存。

**信心：高**（官方文件查證，見 [文件端查證](./2026-08-03-codex-copilot.docs.md)）。

## Q2　慣用的工作區位置

**結論：相符。**

預設工作區位置為：

- `.github/instructions/*.instructions.md`
- `.github/prompts/*.prompt.md`
- `.github/agents/*.agent.md`
- `.github/skills/<skill>/SKILL.md`
- `.github/hooks/*.json`

它們是專案規則、提示、skills 或 hooks，應先審查內容後依團隊需求提交；不可當成 Copilot 自動產生的 cache/session 而整包忽略。

**信心：高**（官方文件查證）。

## Q3　Copilot 是否在專案目錄自動產生 cache／log／session？

**結論：未觀察到；本次版本可確認為「不會自動寫入 repo」。**

執行中的 Copilot session 有下列直接證據：

1. VS Code 的 workspace storage metadata 將一個 workspace-storage ID 對應到目前的 repository；同一個 ID 下實際出現：
   - `chatSessions/<session-id>.jsonl`
   - `chatEditingSessions/<session-id>/`
   - `GitHub.copilot-chat/transcripts/<session-id>.jsonl`
   - `GitHub.copilot-chat/debug-logs/<session-id>/`
2. Copilot 的使用者層 global storage 另有 `github.copilot-chat/toolEmbeddingsCache.bin` 等快取；大 tool result 也會落在同一個 VS Code user-data 範圍的 session resources。
3. 這些路徑全部位於 `<VS Code user-data>/User/workspaceStorage/<workspace-id>/` 或 `<VS Code user-data>/User/globalStorage/`，**不在 repository 根目錄**。
4. 本 session 執行過程後，repository 的正常 Git 狀態仍乾淨；未出現新的 Copilot cache、log 或 session 檔。現有被忽略的 `.claude/` 與 Python bytecode 為既有、非 Copilot 本輪產物。
5. 已安裝的 Copilot Chat 擴充程式亦可找到 `transcripts`、`debug-logs` 與 `toolEmbeddingsCache` 的儲存實作字串，與上述實測目錄一致。

因此，**不應新增專案層 `.copilot/`、`.github/copilot-*` 或泛用 session/cache/log 的 `.gitignore` 規則**。這類規則沒有對應的自動產物，且容易誤殺真正應共享的 `.github/` customizations。

### 例外與邊界

下列情況會寫入專案，但不是 Copilot 自動的 runtime artifact：

- 使用者執行 `/init`、`/create-*`、匯出 chat，或要求 agent 建立／修改檔案。
- 使用者自行設定的 hook，例如將 audit log 寫到 `.github/hooks/audit.log`。
- 使用 worktree isolation 的 Copilot CLI session 可能建立 Git worktree；那是 Git 工作目錄管理，不是 cache/log/session 檔，應個案審查。

這是 VS Code 1.125.1／Copilot Chat 0.53.1 的 Windows 實查結論；升級主要版本或變更 agent host 後應重新驗證。

**信心：高**（同一個 active Copilot agent session 的 user-data 實測、repository Git 狀態與已安裝擴充程式交叉佐證）。

## Q4　`~/.copilot/skills/`

**結論：相符。**

此為 Personal skills 的使用者層位置，也是本專案 VS Code variant 的安裝目標；本次未觀察到它作為 project runtime session/cache/log 的儲存位置。

**信心：高**（官方 agent-skills 文件與實機目錄結構）。

## 回填建議

- 新增帳本 C-78，記錄 session/transcript/debug-log/cache 位於 VS Code user data、非 repository。
- 不修改 `.gitignore` 範本規則；維持 `.github/` 下 Copilot customizations 預設可追蹤的原則。

---

## 維護者複驗（Claude Code，2026-08-03）

**結論：四題全數採用。這是本輪三份回覆中品質最高的一份。**

### 獨立查核結果

在同機以 `%APPDATA%\Code\User` 為起點，比對 `workspace.json` 找出對應本 repo 的
workspace-storage ID，逐一確認回覆宣稱的目錄：

```text
workspaceStorage/f3cbbf8e2416b0245ed96c901a2ab432/
  chatSessions            存在 ✓
  chatEditingSessions     存在 ✓
  GitHub.copilot-chat/    存在 ✓ → debug-logs、transcripts
globalStorage/github.copilot-chat/   存在 ✓
專案根目錄                無任何 copilot／chatsession／transcript 檔 ✓
```

**全部相符。** 帳本 C-78 的內容與計數（56 → 57 條）亦經驗證一致，
`git check-ignore` 五版 49 個邊界案例維持全過。

### 這份回覆做對的三件事

1. **範圍寫死在版本上** —— 「VS Code 1.125.1／Copilot Chat 0.53.1 的 Windows 實查結論；
   升級主要版本後應重新驗證」。前幾輪的失效多半出在把單一觀察外推。
2. **敢下否定結論** —— 建議**不要**新增規則，並指出「不可當成 Copilot 自動產生的
   cache/session 而整包忽略 `.github/`」。提出「不必做什麼」比提出「該加什麼」更難，
   也更容易被誤當成敷衍。
3. **主動聲明查核邊界** —— 「只檢查檔案名稱、目錄結構與 session metadata；
   未轉錄任何對話內容」。檢視隱私路徑時這句話該是標配。

### 一處措辭需要精確化

對話摘要中稱驗證時建立的 `.venv` 是「**被忽略**、未追蹤」的本機環境。實際上：

```text
git check-ignore -v .venv              → 無規則命中（本 repo 的 .gitignore 沒有 venv 規則）
git check-ignore -v .venv/pyvenv.cfg   → .venv/.gitignore:1:*   ← Python 自建的內層 .gitignore
```

`git status` 之所以乾淨，是因為 **Python 的 `venv` 模組會在 `.venv/` 內自動產生一個
內容為 `*` 的 `.gitignore`**，不是本 repo 的規則擋下的。實務結果相同，但機制不同 ——
換成 `virtualenv` 或不寫該檔的舊版 Python 就不成立。

### 順帶修掉本 repo 的一個疏漏

上述查核暴露出：**本 skill 的範本明明列有 `venv/` 與 `.venv/`，本 repo 自己的
`.gitignore` 卻漏了**。已補上並註明理由（不要依賴工具剛好幫你擋）。
補上後 `.venv`、`venv/lib/x`、`.venv/Scripts/python.exe` 皆正確擋下，
且無任何已追蹤檔案受影響（0 筆）。

這是「自己的 repo 沒遵守自己的 skill」，屬於這輪交叉檢視的意外收穫。
