---
name: ai-git-ignore-strategy
description: 建立並套用針對各式 AI 代理工具 (Claude Code, Antigravity, Cursor, Codex, Gemini 等) 的 .gitignore 最佳實務，防止專案庫被 AI 對話紀錄與暫存撐爆；同時正確保留設計藍圖、部署參考、備份資料檔與團隊 AI 指令檔。也負責跨平台（Linux VM ↔ Windows SSHFS）行尾正規化與 .gitattributes 設定。當使用者要求「檢核 gitignore」「整理 repo」「commit 前審查」「清理 AI 追蹤紀錄」「行尾 CRLF 問題」時觸發。
---

# AI 工作區 Git 管控最佳實務 (AI Git Ignore Strategy)

當使用者用各類代理型 AI 工具（Claude Code、Cursor、Antigravity、Gemini、Codex⋯⋯）進行本地開發時，AI 系統會在專案根目錄產生隱藏的本地狀態與對話紀錄資料夾（如 .claude/, .agent/, .gemini/ 等）。

這些資料夾會隨時間迅速膨脹，若不小心推上 Git 將導致：

1. **Repository Bloat**：專案體積變大，Clone/Pull 變慢。
2. **Merge Conflicts**：團隊成員各自的 AI 紀錄檔互相衝突。
3. **Security Risks**：可能暴露對話中貼過的敏感資訊或測試密碼。

---

## 🤖 給 AI 助手的核心指示

> **重要原則：不要粗暴地把所有「看起來像 AI 產物」的檔案一律排除。**
> 必須先讀取檔案內容、理解用途，向開發者說明並確認後才行動。

當使用者明確要求審查 Git 追蹤配置（檢核 .gitignore、整理 repo、commit 前審查等）時，**嚴格**按以下流程執行。請使用你當前 AI 工具提供的**讀檔工具**、**目錄列示工具**、**shell 執行工具**、**編輯工具**來完成各階段。

### 第一階段：診斷 (Diagnose)

1. **讀取 .gitignore**（以及 .gitattributes，如存在），確認目前規則。
2. **執行下列 Git 指令**取得當前狀態：
   - git status
   - git ls-files | head -100
   - git diff --stat
   - git log --oneline -10
3. 將未提交／已追蹤的檔案分類整理成表格，欄位包含：**檔案路徑、所在目錄、推測用途、是否已被追蹤、diff 大小**。

> 💡 **識別「假異動」**：如果 git diff --stat 顯示某檔案 0 insertions, 0 deletions 但又被標為 modified，通常是 CRLF/LF 行尾雜訊或 file mode 變動（755→644）。這類問題請交由**第五階段：跨平台行尾正規化**處理，不要當成內容變更。

### 第二階段：逐一審查 (Review)

對每個「看起來可能不需要提交」的檔案，**必須先讀取其內容**，然後依以下邏輯分類：

#### 🟢 應該提交 (Keep & Commit)

- **專案原始碼**：.py, .html, .css, .js, .ts, .sh, .bat, .ps1 等開發者撰寫的程式碼。
- **設計系統藍圖**：design-system/MASTER.md 等記錄專案色票、字型、元件規格的檔案。AI 依此量身定製視覺風格，刪除後 AI 無法維持一致性。
- **部署與維運文件**：DEPLOY.md, README.md, CHANGELOG.md, docs/。
- **排程與自動化設定參考**：task_info.xml（Windows Task Scheduler 匯出）、.service 檔備份、Dockerfile、docker-compose.yml、CI 設定檔。
- **資料備份檔**：若 .gitignore 已排除 *.json，則 .json.bak 可能是唯一透過 Git 傳承資料的管道 — **必須對照 DEPLOY.md 的「還原資料檔」清單確認是否有對應**。
- **專案級 AI 指令檔**：CLAUDE.md（根目錄）、.cursorrules、AGENTS.md 等團隊共用的 AI 規則檔。
- **跨平台設定**：.gitattributes、.editorconfig、.nvmrc。

#### 🔴 應該排除 (Ignore)

- **AI 對話紀錄與快取**：.agent/, .claude/, .codex/, .gemini/, .cursor/, .github/prompts/ 底下非 skills 的 session logs、快取、索引檔。
  - ⚠️ 注意：.claude/skills/、.gemini/skills/ 是客製技能可能要保留（見「需確認」類）；.claude/ 底下的其他資料夾（projects/, sessions/, telemetry/, shell-snapshots/）才是純暫存。
- **自動執行日誌**：*.log（無限增長、無版本控制意義）。
- **Runtime 狀態檔**：像 last_run.txt, last_scan.txt, last_download.txt 這類「每次執行就覆寫」的狀態檔。它們會讓 git status 永遠滿江紅。
- **二進位大型檔案**：PDF、圖片、影片、字型檔。Git 不擅長處理 binary，會永久佔用歷史空間。可考慮用 Git LFS 或改放 Notion/Drive 連結。
- **機密檔案**：.env, *.pem, *.key, certs/, credentials.json。
- **虛擬環境 / 依賴**：venv/, node_modules/, __pycache__/, .venv/, target/, dist/, build/。
- **編輯器本地設定**：.DS_Store, Thumbs.db, .idea/, .vscode/settings.json（團隊共用的 .vscode/extensions.json、launch.json 可保留）。

#### ⚠️ 需要跟開發者確認 (Ask)

- **AI 技能庫 (Skills)**：各 AI 工具的 skills/ 目錄。
  - 透過 CLI 工具安裝的（如 uipro init --ai ...）→ **不需要** Git 傳承，在 DEPLOY.md 記錄安裝指令即可。
  - 開發者自行撰寫的客製技能 → **應該提交**。
  - **必問開發者**：「這個技能是透過 CLI 安裝的，還是您自己寫的？」
- **產生的設定檔**：如 design-system/pages/*.md。需確認是可重新產生的快取，或有手動調整過的客製設定。
- **大型 PDF / 文件快照**：是否是 Notion/雲端文件的靜態匯出？若是，**建議改以連結指向活文件**，避免靜態快照過時誤導。
- **用途不明的檔案**：任何無法從檔名或副檔名判斷用途的檔案，**一律先讀取內容再決定**。

### 第三階段：向開發者報告 (Report)

將審查結果整理成「✅ 建議提交 / 🚫 建議排除 / ❓ 需要您確認」三欄的表格，**在執行任何 .gitignore 修改之前**呈現給開發者確認。**等待開發者逐一確認後**，才進入第四階段。

### 第四階段：執行 (Execute)

根據開發者確認後的結果：

1. **修改 .gitignore**，加入要排除的規則。
2. 若有已被 Git 追蹤但現在要排除的檔案，執行：
   - git rm --cached <path>           # 移除追蹤但保留本機檔案
   - git rm --cached -r <dir>         # 目錄版
3. 若有需要透過 CLI 重新安裝的技能，在 DEPLOY.md 補上安裝步驟。
4. 若有靜態快照要改成連結（如 PDF → Notion），在 README.md 或 DEPLOY.md 新增參考連結區塊。
5. 選擇性加入暫存（**不要** git add . 以免誤加）：git add <specific-files>
6. 提交前**再次提醒開發者**檢視 git status，確認暫存區符合預期後才 commit。
7. **Commit 策略**：若同時有「內容變更」和「純格式正規化」（LF 轉換 / mode 變更），**拆成兩個 commit**，避免格式噪音淹沒真正的功能變更。
8. **Push 必須明確授權**：即使 commit 完成，也**必須等開發者同意**（「請 push」「好的 push」）才推遠端。

### 第五階段：跨平台行尾正規化（Line Endings）

開發環境常見「Linux VM + Windows SSHFS 掛載」或「Windows 開發但部署到 Linux」的組合。Git 預設會依 core.autocrlf 在 checkout/commit 時轉換行尾，造成：

- git status 每次都滿江紅（0 byte 幽靈異動）
- Merge conflict 發生在純行尾差異
- .sh 腳本在 Linux 端因為 CRLF 噴 \r: command not found

**檢測**：git diff --stat | grep ' | *0$' 找 0 byte 修改的檔案。若有多個 0 byte diff 的文字檔，就是行尾問題。

**解法**：在專案根目錄建立 .gitattributes：

```text
# 預設：文字檔一律 LF
* text=auto eol=lf

# Windows 專用腳本：保留 CRLF
*.bat  text eol=crlf
*.cmd  text eol=crlf
*.ps1  text eol=crlf
*.vbs  text eol=crlf

# Binary 明確標記
*.pdf  binary
*.png  binary
*.jpg  binary
*.jpeg binary
*.ico  binary
*.woff binary
*.woff2 binary
```

**套用**：建立 .gitattributes 後，執行 git add --renormalize . 把既有檔案以 LF 重新入庫，然後檢視 git status，最後 git commit -m "chore: 導入 .gitattributes 強制 LF"。

> ⚠️ **Renormalize 會造成大量 diff**：所有曾經以 CRLF 存在的檔案都會顯示「整檔重寫」。這是預期行為，不是 bug。**務必拆成獨立 commit**，與內容變更分開。

---

## 🎯 標準化 .gitignore 規則範本

```text
# 機密與環境
.env
.env.*
!.env.example
*.pem
*.key
credentials.json

# 依賴與虛擬環境
venv/
.venv/
node_modules/
__pycache__/
*.pyc
target/
dist/
build/

# 編輯器與作業系統雜訊
.DS_Store
Thumbs.db
.idea/

# AI Agent Workspaces & Logs
.agent/
.claude/
.codex/
.gemini/
.cursor/
.github/prompts/
*.log

# Runtime 狀態檔
last_run.txt
last_*.txt

# TLS (self-signed)
certs/

# 如有需要保留的 AI 共用指令檔，請取消註解
# !CLAUDE.md
# !.cursorrules
# !AGENTS.md
```

> ⚠️ **此範本僅為起點**。是否需要白名單 (!) 放行特定 skills 資料夾、是否需要排除 design-system/ 等，皆必須經過「逐一審查」流程後再決定。

---

## 🚑 終極救援指令 (Remediation)

如果 AI 資料夾**已經被推送到 GitHub**：

```bash
# 1. 從 Git 快取中移除（不會刪除本機實體檔案）
git rm -r --cached .agent .claude .codex .gemini .cursor .github/prompts 2>/dev/null
git rm --cached *.log 2>/dev/null

# 2. 確保 .gitignore 已包含正確的阻擋規則

# 3. 如果歷史已被大檔污染，考慮用 git-filter-repo 瘦身

# 4. 重新加入應該提交的檔案（不要用 git add . 以免誤加）
git add <specific-files>

# 5. 提交
git commit -m "chore: 清理 AI 追蹤紀錄並套用最佳化 gitignore 規則"
# 等開發者明確授權後才 push
```

---

## 📚 延伸知識

### .gitignore 常見語法

| 語法 | 含義 | 範例 |
| :--- | :--- | :--- |
| folder/ | 忽略整個資料夾 | .gemini/ |
| *.ext | 忽略特定副檔名 | *.log |
| folder/* | 忽略資料夾內容但保留資料夾本身 | .agent/* |
| !path | 白名單：從忽略規則中排除特定路徑 | !.agent/skills/ |
| **/pattern | 任意層級遞迴比對 | **/node_modules/ |

> 💡 **白名單注意事項**：! 語法只在母目錄使用 *（星號）時才有效。例如 .claude/ 會完全忽略整個資料夾，此時 !.claude/skills/ **無效**。必須改為 .claude/* 搭配 !.claude/skills/ 才能正確放行。

### .gitattributes 進階用法

| 語法 | 用途 |
| :--- | :--- |
| * text=auto eol=lf | 所有文字檔強制 LF |
| *.sh text eol=lf | shell 腳本必須 LF |
| *.ps1 text eol=crlf | Windows 腳本強制 CRLF |
| *.pdf binary | 標記為 binary |
| *.md diff=markdown | 用 markdown-aware 的 diff 演算法 |
