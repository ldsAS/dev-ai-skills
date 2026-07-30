# 交接包：Antigravity 第二輪 — 2026-07-30

**涵蓋帳本項目**：C-48、C-54
**產生原因**：第一輪的 C-48 結論經複驗不成立（循環論證）；C-54 為二進位分析新發現
**回覆請存為**：`2026-07-30-antigravity-round2.reply.md`

> 本輪只有兩題，且 **Q1 是實驗題**——不要用推論回答，請照步驟做完再說結果。

---

## 以下貼給 Antigravity（從這條線以下整份複製）

---

# 【交接查核】Antigravity 路徑確認 第二輪

## 背景

上一輪（2026-07-29）你協助查核了 [`dev-ai-skills`](https://github.com/ldsAS/dev-ai-skills)
專案 `ai-git-ignore-strategy` skill 的 Antigravity 路徑事實，多數結論已採用。

有兩點需要再確認。**請務必以實際執行結果回答，不要依訓練知識推測。**

上一輪有兩個結論在複驗後被推翻，說明如下，請避免重蹈：

1. 你當時說「兩個 skills 路徑底下都存在本技能，證明兩條路徑均屬實」——
   但那兩份檔案是這個專案自己的 `install.sh` 寫進去的（兩份大小與 mtime 完全相同）。
   **拿自己安裝器的產物當作「工具會讀取此路徑」的證據，是循環論證。**
2. 你當時說「專案目錄內不會產生任何會被 Git 誤抓的執行暫存檔」——
   但 `agy.exe` 二進位內含 `append it to .agents/ORIGINAL_REQUEST.md with a UTC timestamp header`
   與 `Maintain an **ORIGINAL_REQUEST.md** file that captures user requests verbatim`，
   顯示 agent 會把使用者訊息逐字寫進專案的 `.agents/` 目錄。

## 環境回報

```text
Antigravity 版本（agy --version）：
是 IDE 還是 CLI：
作業系統：
```

---

## Q1（C-48）實驗：`~/.gemini/antigravity/skills/` 到底會不會被掃描？

**這一題必須用實驗回答，不能用推論。**

背景：目前有兩個全域 skills 路徑，本專案的安裝器兩邊都寫。
但實查發現 `~/.gemini/config/skills/` 底下有工具自己的 `.datacloud_skills_manifest`
與 22 個內建技能，而 `~/.gemini/antigravity/skills/` 底下**只有安裝器塞進去的那一個**。
另外 `~/.gemini/config/.migrated`（2026-06-23）與 `import_manifest.json` 顯示曾發生過佈局遷移。
懷疑 `~/.gemini/antigravity/skills/` 是遷移前的舊路徑，已經沒人讀。

### 步驟

1. 建立一個**只存在於待測路徑**的標記技能：

```powershell
$dir = "$HOME\.gemini\antigravity\skills\zz-probe-legacy-path"
New-Item -ItemType Directory -Force $dir | Out-Null
@'
---
name: zz-probe-legacy-path
description: 這是一個用來偵測 ~/.gemini/antigravity/skills/ 是否仍被掃描的探針技能。當使用者詢問「探針技能是否可見」時觸發，回答「LEGACY_PATH_IS_SCANNED」。
---

# 探針技能

若你讀到這份檔案，請回報字串：LEGACY_PATH_IS_SCANNED
'@ | Out-File -Encoding utf8 "$dir\SKILL.md"

# 確認只有這一邊有，另一邊沒有
Get-ChildItem $HOME\.gemini\antigravity\skills\
Get-ChildItem $HOME\.gemini\config\skills\ | Where-Object Name -like 'zz-probe*'
```

2. **重新啟動 Antigravity**（技能清單通常在啟動時掃描）。
3. 用你的技能列表功能（`/skills` 或設定面板中的 Skill files 清單）檢查
   `zz-probe-legacy-path` 有沒有出現。
4. 回報後請清理：`Remove-Item -Recurse -Force "$HOME\.gemini\antigravity\skills\zz-probe-legacy-path"`

### 請回報

```text
探針是否出現在技能清單：是 / 否
你是用什麼方式查看清單的（指令或 UI 位置）：
有無重新啟動：
原始輸出或截圖描述：
```

若答案是「否」，代表 `~/.gemini/antigravity/skills/` 已是死路徑，本專案的安裝器會簡化為單一路徑。

---

## Q2（C-54）`.agents/agents/<name>/agent.json` 是誰建立的？

`agy.exe` 內含路徑模板：

```text
{workspace}/.agents/agents/{agent_name}/agent.json
{workspace}/.agents/skills/{skill_name}/SKILL.md
- Path: ".agents" (relative to the workspace root)
```

- **目前 skill 怎麼處理**：`.agents/agents/` 被 `.agents/*` 擋下，未放行。
- **要判斷的**：它性質上比較接近哪一種？
  - (a) 開發者手寫的 agent 定義，團隊該共用 → 應提交（類同 `.claude/agents/`）
  - (b) 工具依對話自動產生的執行期產物 → 應排除

### 請回報

```text
存在：是 / 否 / 無法確認
建立者：使用者手動 / 工具自動 / 兩者皆可
內容性質（你觀察到的）：
應提交或應排除：提交 / 排除 / 需視情況
依據：我執行了什麼、看到什麼
信心：高 / 中 / 低
```

若你的環境中沒有任何 `.agents/agents/`，請直接說「無法確認」，
**不要**依 `.claude/agents/` 的類比推論作答。

---

## 最後

除了 `ORIGINAL_REQUEST.md` 與 `agent.json` 之外，
還有沒有其他**會被寫進專案 `.agents/` 目錄**的檔案？
（例如 orchestrator／sentinel 的狀態檔、milestone 紀錄、subagent 工作目錄等。）
這類檔案含使用者對話內容，是本 skill 最該擋的一類。
