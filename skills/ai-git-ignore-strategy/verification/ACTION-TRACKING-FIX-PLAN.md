# 自動追蹤機制修正計畫 — 2026-08-14

**狀態**：待執行

**範圍**：`check_updates.py`、定期 GitHub Actions、提醒政策、監控說明與離線回歸測試。

**整合依據**：[`rounds/2026-08-14-claude.plan-review.md`](./rounds/2026-08-14-claude.plan-review.md)、
[`rounds/2026-08-14-claude.plan-review-r2.md`](./rounds/2026-08-14-claude.plan-review-r2.md)
與後續 Codex 對雙 signal、recovery 測試範圍及提醒噪音的複驗。

**本文件只記錄修正計畫，尚未實作任何程式或 workflow 異動。**

## 目錄

1. [背景與已確認問題](#一背景與已確認問題)
2. [修正目標](#二修正目標)
3. [不在本輪處理的範圍](#三不在本輪處理的範圍)
4. [設計決定](#四設計決定)
5. [分階段實作](#五分階段實作)
6. [預計異動檔案](#六預計異動檔案)
7. [測試矩陣](#七測試矩陣)
8. [端對端驗收](#八端對端驗收)
9. [既有 Issue 處理](#九既有-issue-處理)
10. [提交與發布策略](#十提交與發布策略)

---

## 一、背景與已確認問題

2026-08-14 以 GitHub 執行紀錄、Issue、baseline 提交與本機 dry-run 交叉檢核後，
確認自動追蹤主流程能取得官方來源、偵測 token 變化、建立／更新 Issue，並推送
`scripts/last_checked.json`。但仍有以下問題。

### 核心提醒原則：提醒機制風險，不提醒日常波動

自動追蹤的目的不是建立 AI 工具更新動態，而是找出**可能改變本 skill 路徑判斷、
追蹤決定或官方依據**的訊號，提醒維護者複驗。

會建立或更新 Issue 的情況限於：

- 官方來源中的路徑 token 新增或消失；
- 版本跨越明確設定的低頻門檻；
- 來源抓取或檢查程式失敗，導致本次無法可靠判定。

下列情況不得單獨建立 Issue：

- patch 更新；
- 預設採 major 門檻之工具的 minor 更新（包含 `0.x`）；
- 官方頁面一般文字調整，但路徑 token 沒有變化；
- baseline 只有完整版本字串或其他非機制 metadata 改變。

token 變化本身仍只是候選證據，不會自動修改 CLAIMS 或五個 `SKILL.md`。

### P0-1　檢查失敗仍顯示綠燈

2026-08-10 的 run 因 npm HTTP 429 產生 `[SIGNAL: CHECK_FAILED]` 並建立 Issue #8，
但 workflow conclusion 仍為 `success`。

原因是 workflow 只把 `failure=true` 寫入 step output，通知完成後沒有讓 job 回傳非 0。
這與 workflow 內「檢查腳本失敗不能亮綠燈」的宣稱不一致。

### P0-2　恢復後的失敗 Issue 不會自動結案

Issue #8 對應暫時性的 npm 429。後續多次執行已恢復成功，但 Issue 仍保持開啟，
容易讓維護者誤以為來源持續失效。

### P0-3　異動與失敗同時出現時，失敗 Issue 收不到更新

現行 workflow 在 `updates == true` 時優先選擇「工具路徑與機制異動」標題；即使同一份
報告也有 `failure == true`，仍不會建立或更新「檢查失敗」Issue。這會讓既有失敗 Issue
看似停滯，但來源其實仍在失敗。

### P1-1　非告警版本變化仍製造 baseline commit

`check_updates.py` 會把每次取得的完整版本號寫入 payload；即使只是被歸類為
「版本參考（非告警項）」的 patch 變化，也會觸發 `[SIGNAL: BASELINE_CHANGED]`。

例如 `93232f5` 只更新 Claude Code `2.1.226 → 2.1.227`，仍產生一個 bot commit。
這與「patch bump 不造成日常噪音」的設計目標不一致。

### P1-2　Antigravity 的告警理由與盲區說明已過期

腳本、skill 根目錄 README 與 verification README 仍宣稱 Antigravity 沒有公開文件站，
且監控盲區集中在 `.agents/*`。目前已納入多個 Antigravity 官方文件來源；實際兩個盲區是：

- `~/.gemini/tmp`（C-24）
- `User/workspaceStorage`（C-78）

### P1-3　新增 token 的報告語氣過度確定

token 抽取器只能確認官方頁面出現新的路徑字串，不能單靠字串判定它是：

- 工具自動產物；
- 可提交的專案設定；
- 使用者自訂命令；
- 文件中的示範路徑。

目前 Issue #7 的 `subagent-statusline.sh`、`post_tool_use.py` 即可能是文件範例，
不應直接描述成與 `.gitignore` 規則「直接相關」的正式機制。

### P1-4　major 告警的實機複驗提示與門檻 override 錯誤耦合

`check_updates.py` 目前以「工具名稱是否存在於 `ALERT_LEVEL`」決定是否印出實機交接提示。
移除 Antigravity minor 例外後，`ALERT_LEVEL` 會成為空的 override map；Antigravity major
雖仍會進入 `version_alerts`，提示條件卻恆為 false，與測試矩陣不一致。

版本門檻與提示是兩個責任：前者由 `ALERT_LEVEL.get(tool, "major")` 決定，後者應依
實際告警 tuple 的 `level == "major"` 決定，不得再以 override map 的 membership 代替。

### P2-1　官方 Actions runtime 已出現淘汰警告

兩份 workflow 目前使用 `actions/checkout@v4`、`actions/setup-python@v5`。
實際 run 已出現 Node 20 淘汰並由 runner 強制改用 Node 24 的警告。

### P2-2　排程延遲說明低估實際情況

註解寫「常延後 30–60 分鐘」，近期執行曾延後約 2–3 小時。這不是排程故障，
但文件應反映 GitHub schedule 可能延後數小時。

---

## 二、修正目標

1. 任何 `[SIGNAL: CHECK_FAILED]` 都要在通知完成後讓 workflow 明確標紅。
2. 異動與失敗同時出現時，兩類 Issue 都要收到本次報告。
3. 後續健康執行要留下恢復紀錄，並關閉所有同標題的過期失敗 Issue。
4. 非告警版本變化不得單獨修改 baseline、產生 bot commit 或開 Issue。
5. token 或明確設定的版本門檻變化仍要可靠告警並只提交一次 baseline。
6. 報告把新增路徑定位為「候選變動」，要求人工分類後才能回填 CLAIMS。
7. 文件中的來源、盲區與版本告警理由必須和實際程式一致。
8. 以不連網的 fixture 測試鎖住 signal、通知選擇、recovery 與 baseline 邊界。
9. major 告警必須附上通用人工複驗提示；提示條件不得依賴 `ALERT_LEVEL` 是否有 override。

---

## 三、不在本輪處理的範圍

- 不修改五個變體的 `SKILL.md` 範本規則。
- 不因 Issue #7 的候選 token 自動新增或修改 `CLAIMS.md`。
- 不自動判定 `~/.claude/skills/synced/` 的最終性質；它需另行取證。
- 不把使用者自訂 `.sh`／`.py` 範例直接加入 ignore 或 allowlist。
- 不改變「官方路徑 token 是主要訊號、版本號是輔助訊號」的總體架構。
- 不把 Codex、Gemini CLI、Antigravity 等工具的每次 minor 更新自動升格為 Issue 告警。
- 不在 push／pull_request workflow 中執行會連網、開 Issue 或推 baseline 的正式監控。
- 不加入事件匯流排、資料庫、額外套件或長期 validation mode；本輪只允許一個小型、
  純標準函式庫的 CI policy helper。

---

## 四、設計決定

### D1　依 signal 分別通知，最後才讓 job 失敗

`CHECK_FAILED` 不應在檢查 step 立即中止整個 job，否則 Issue 通知與必要的 baseline
處理可能被跳過。`UPDATE_DETECTED` 與 `CHECK_FAILED` 是兩個獨立狀態，不得用
`if/else` 只選其中一種標題。

| updates | failure | Issue 動作 | 最終狀態 |
| :---: | :---: | :--- | :---: |
| false | false | 不建立異動 Issue；執行 failure recovery | 綠燈 |
| true | false | 更新異動 Issue；同時執行 failure recovery | 綠燈 |
| false | true | 更新失敗 Issue | 紅燈 |
| true | true | **兩類 Issue 都更新** | 紅燈 |

流程固定為：

```text
執行檢查 → 解析 signal → 分別更新對應 Issue → 處理有意義的 baseline → 最後標紅
```

workflow 最後新增一個 failure gate：

```yaml
- name: Fail workflow when checks failed
  if: always() && steps.check.outputs.failure == 'true'
  run: exit 1
```

### D2　健康執行負責關閉失敗 Issue

當 `failure != true` 時，不論 `updates` 是 true 或 false，都尋找標題完全相同且仍開啟的
失敗 Issue：

1. 取得**所有**符合標題的 open issue number，不只 `.[0]`。
2. 逐張留言，註明恢復時間與本次 run URL。
3. 逐張關閉。
4. 沒有既有 Issue 時不做任何寫入。

更新異動 Issue 不自動關閉，仍由維護者在完成主張與技能複驗後處理。

### D3　區分 payload 差異與有意義的 baseline 差異

完整版本變動不再等同 baseline 必須提交。定義：

```text
meaningful_baseline_change =
    schema migration
    OR 首次納入來源
    OR token 新增／消失
    OR 版本跨越告警門檻
```

只有 `meaningful_baseline_change` 且新舊 payload 不同時才：

- 寫回 `scripts/last_checked.json`；
- 印出 `[SIGNAL: BASELINE_CHANGED]`；
- 允許 workflow 建立 bot commit。

只有非告警版本變化時，可在當次 report 列為參考，但不寫檔、不產生 commit。

依本計畫讓一般工具與 Antigravity 都採預設 major 門檻後，截至 2026-08-14 的歷史 schema 2 資料顯示，
這項調整約能消除：

- 所有觸及 baseline 的 commit：`7/19 ≈ 37%`；
- 真正的 bot baseline commit：`7/12 ≈ 58%`。

原先保留 Antigravity minor 例外時的結果是 `4/19`、`4/12`。改採 major 後，另外排除
`192fb49`、`2ab228d`、`2c28d35` 三次只有 Antigravity minor 版本變化的 commit，合計改為 7。
2026-08-12 的 minor 跨越同時有來源／token 變化，本來就屬有意義 baseline，因此不列入
可消除數量。Claude review 的 `3/19`、`3/12` 則是以「Codex `0.x` minor 升格為告警」為
前提；本計畫依維護者的降噪要求不採用該升格，因此 `c65d516` 仍屬可消除的非告警版本 commit。

因此預期能明顯降低純版本造成的 baseline 噪音，但 token、來源或 major 變化仍會形成
有意義的週期性 commit。非告警版本不寫回後，版本差異會表示「自上次**有意義 baseline**
以來」的累積值；例如可能顯示
`2.1.226 → 2.1.231`，而不是日對日差異。報告需明示這個語意。

### D4　版本號只作低頻輔助，不把一般 minor 升格為告警

Claude 複審確認 schema 2 歷史中共有 3 次 `0.x` minor 轉移，若全部升格，只有 1 次會
新增獨立告警週期；短期看似不吵，但樣本期很短，不能據此把所有快速迭代工具的 minor
更新永久當成機制風險。

本輪保留既有的明確門檻模型：

- 預設為 major：只比較第一段；`0.146 → 0.147`、`0.54 → 0.55`、`2.8 → 2.9` 都是參考資訊，
  **不產生 `UPDATE_DETECTED`**。
- `0.x → 1.x` 或 `1.x → 2.x` 才是預設 major 告警。
- 只有工具被 `ALERT_LEVEL` 明確設為 minor 時，minor 轉移才告警。
- patch 一律只是參考資訊，不告警。

換言之，現行 `version_key('0.146.2', 'major') == '0'` 是刻意的降噪政策，不再視為 bug。

### D5　Antigravity 改採 major 告警，明示降噪與靈敏度取捨

Antigravity 已有公開文件監控，不能再以「沒有公開文件站」作為保留 minor 門檻的理由。
實際歷史在 2026-08-04 至 2026-08-13 的 9 天內出現 4 次 minor 跨越，平均約 3 天一次；
其中 2026-08-12 同時有來源／token 變化，本來就會告警，其餘 3 次則是版本單獨造成的通知週期。
這個頻率不符合「只提醒可能影響 skill 機制的低頻訊號」目標，因此本輪移除唯一既有的
tool-specific minor 例外，讓 Antigravity 與其他工具一樣只在 major 跨越時觸發版本告警。

這是有意識地以較低靈敏度換取較低噪音，不代表 minor 更新沒有資訊價值，也不代表語意盲區
已被消除。現有 8 個來源與 18 條受覆蓋主張能偵測路徑 token 增減，但不能單獨證明路徑用途、
內容結構或實機行為未變；沒有 token 變化的 minor 語意改動，可能要等 major 告警或人工複驗
才會被發現。若日後需要補強，另案設計低頻、以時間為基礎的實機複驗，不把每次版本更新
重新當成提醒。本輪也不加入 cooldown、計數器或額外狀態檔。

版本門檻與人工複驗提示必須解耦。`ALERT_LEVEL` 只保存偏離預設 major 的門檻 override；
是否顯示提示則依 `version_alerts` 中的實際 `level` 判斷。任何 major 告警都附上通用的
人工複驗說明，但不因此建立額外 Issue；未來若重新加入 minor override，也不會因工具名稱
存在於 map 就誤套 major 專用提示。

### D6　新增 token 一律是候選訊號

報告用語改為：

> 偵測到官方來源中的候選路徑變動。請先判定它是正式機制、使用者自訂路徑、
> 文件範例或無關字串，再決定是否更新 CLAIMS 與五個 SKILL.md。

不在本輪加入容易誤殺的通用副檔名過濾；先保留訊號，再靠人工取證分類。

### D7　只抽出一個可測試的 CI policy helper

P0 的決策不能只留在 YAML／shell，再靠一次性手動驗收。新增一個小型 Python helper
（暫名 `scripts/monitor_ci_policy.py`），只使用標準函式庫，集中下列純決策：

- 從 report 與腳本 exit code 解析 `updates`／`failure`／`baseline`；
- 依 signal 決定要更新的 Issue 類型，包含雙 signal 時回傳兩類；
- 從 open issue JSON 選出**所有**同標題 recovery targets；
- 判定 workflow 最終是否必須失敗。

helper 不呼叫 `gh`、不寫 baseline、不關 Issue，也不建立通用 state machine；GitHub 副作用仍由
workflow 執行。測試以 `importlib.util.spec_from_file_location()` 載入，避免新增 package 或
污染 `sys.path`。

### D8　validation mode 必須隔離且驗完移除

受控 failure／recovery 驗收使用獨立的 validation Issue 標題，硬性禁止 baseline commit／push，
也不得碰正式異動或失敗 Issue。完整驗收完成後移除 validation input 與分支，不留下長期入口。

### D9　不改變 skill 本體；既有長度問題另案處理

本輪不修改五個 `SKILL.md`、CLAIMS、安裝器或專案 `git-tracking/MASTER.md`，也不讓監控結果
自動回寫 skill。因此不會改變使用者實際觸發 skill 時的流程、工具權限或追蹤判準。

目前五個變體約 681–766 行，已是既有的 context 成本；沒有「超過 100 行就失效」的硬性
門檻，但較長內容確實可能降低指示被穩定定位的效率。這份自動追蹤修正不再增加其行數。
若日後實際運作出現漏讀／漏步驟，再另案依 progressive disclosure 把詳細範本與背景移到
reference；不要把 skill 拆分與 CI 修正混成同一輪。

---

## 五、分階段實作

### 階段 1　修正 workflow 狀態與恢復流程

1. 新增 `monitor_ci_policy.py`，讓 signal、Issue 類型、recovery target 與 failure gate
   的判定可離線測試。
2. `check-updates.yml` 呼叫 helper 取得 outputs，不在 YAML 重寫第二份判定邏輯。
3. `updates` 與 `failure` 各自觸發對應通知；兩者同時成立時兩類 Issue 都更新。
4. 新增健康執行時的 recovery step，處理所有完全相同標題的開啟中失敗 Issue。
5. 在所有通知與 baseline step 之後新增 failure gate。
6. 確認通知失敗、baseline push 失敗仍會自然讓 job 失敗。

### 階段 2　重構 baseline 寫回條件

1. 將「取得的新版本」與「版本是否跨告警門檻」分開計算。
2. 建立 `meaningful_baseline_change`。
3. 只有非告警版本變化（patch 或預設 major 下未跨 major 的 minor）時，不呼叫 baseline 寫檔。
4. bootstrap、token 異動、有效版本告警仍寫回完整新 payload。
5. `--dry-run` 在所有情況下維持零寫入。

### 階段 3　修正版本政策與報告文字

1. 保留 `version_key()` 的 major／minor 明確門檻，不把一般 minor 自動升格。
2. 在程式與 README 說明版本號是低頻輔助訊號，不是更新通知來源。
3. 移除 Antigravity minor 例外、改採 major，並記錄降噪與語意盲區之間的取捨。
4. 將實機複驗提示由 `ALERT_LEVEL` membership 改為實際 `level == "major"`，並改成通用文案。
5. 把「直接相關」改為「候選路徑變動」。
6. 將真正的盲區改為 C-24／C-78。
7. 同步 skill 根目錄 README 與 verification README，避免程式與文件再次漂移。

### 階段 4　升級 workflow runtime

1. `actions/checkout` 升級至實作當下官方 Node 24 相容版本（目前查核為 v7）。
2. `actions/setup-python` 同步升級（目前查核為 v7）。
3. `check-updates.yml` 與 `verify-template.yml` 使用相同 major。
4. 將排程延遲說明改為「可能延後數十分鐘至數小時」。

### 階段 5　新增離線回歸測試

1. 以 Python 標準函式庫 `unittest`／`unittest.mock` 建立 fixture 測試。
2. mock `fetch()`、版本來源與暫存 baseline，測試不得連外。
3. 以 report、exit code 與 open issue JSON fixture 測試 CI policy helper。
4. 測試 helper 的雙 signal、零／一／多張 recovery issue 與最終 gate。
5. 測試空的 `ALERT_LEVEL` 下，minor 不告警，Antigravity 與一般工具的 major 告警都包含
   通用人工複驗提示。
6. 以 `importlib.util.spec_from_file_location()` 載入 scripts，不新增 `__init__.py` 或改
   `sys.path`。
7. 新增只讀、無 GitHub write 權限的測試 workflow。
8. push／PR 只跑離線測試，不執行正式監控、Issue 寫入或 baseline push。

### 階段 6　受控端對端驗收

1. 暫時加入明確的 validation mode；它使用獨立 Issue 標題且禁止 baseline push。
2. 以一次受控 failure 模式驗證通知後 workflow 確實標紅。
3. 再以 validation recovery 驗證留言與關閉所有同標題測試 Issue。
4. 確認正式異動／失敗 Issue 與 `scripts/last_checked.json` 全程未受影響。
5. 移除 validation input 與分支後再形成最終提交內容。
6. 實際 Issue 狀態變更與 workflow dispatch 須在執行前取得維護者授權。

---

## 六、預計異動檔案

| 檔案 | 預計異動 |
| :--- | :--- |
| `.github/workflows/check-updates.yml` | helper 串接、雙 signal 通知、failure gate、recovery、runtime 升級與排程說明；validation 分支驗完移除 |
| `.github/workflows/verify-template.yml` | runtime 升級；必要時保留原職責不混入正式監控 |
| `scripts/check_updates.py` | meaningful baseline、低頻版本政策說明、major 提示解耦、候選路徑措辭、正確盲區理由 |
| `scripts/monitor_ci_policy.py` | 新增；純 signal／Issue／recovery／gate 判定，不含 GitHub 寫入 |
| `scripts/last_checked.json` | 只在 schema 或有意義 baseline 變化時更新 |
| `skills/ai-git-ignore-strategy/README.md` | 移除「Antigravity 無公開文件站」的過期說明，改述目前來源與告警取捨 |
| `skills/ai-git-ignore-strategy/verification/README.md` | 同步來源、版本門檻與盲區說明 |
| `tests/test_check_updates.py` | 新增離線 fixture 回歸測試 |
| `tests/test_monitor_ci_policy.py` | 新增 CI policy fixture 測試 |
| `.github/workflows/verify-monitor.yml` | 建議新增；只跑離線監控測試，權限 `contents: read` |

五個變體的 `SKILL.md` 與 `verification/CLAIMS.md` 預設不在本輪異動清單。

---

## 七、測試矩陣

| 案例 | 輸入 | 預期 signal／結果 |
| :--- | :--- | :--- |
| 無異動 | token、版本 key 均相同 | 無 signal、baseline 不寫入 |
| patch-only | `2.1.229 → 2.1.230` | 可列參考；無 `UPDATE_DETECTED`、無 `BASELINE_CHANGED` |
| 1.x major 變化 | `2.x → 3.x` | `UPDATE_DETECTED`＋`BASELINE_CHANGED`＋通用人工複驗提示 |
| 預設 major 的 0.x minor | Codex `0.146 → 0.147` | 可列參考；無 `UPDATE_DETECTED`、無 `BASELINE_CHANGED` |
| 0.x 跨 1.0 | `0.99 → 1.0` | `UPDATE_DETECTED`＋`BASELINE_CHANGED` |
| Antigravity minor | `2.8 → 2.9` | 可列參考；無 `UPDATE_DETECTED`、無 `BASELINE_CHANGED` |
| Antigravity major | `2.x → 3.x` | `UPDATE_DETECTED`＋`BASELINE_CHANGED`＋通用人工複驗提示 |
| token 新增 | 官方來源多一個 token | 候選變動＋`UPDATE_DETECTED`＋`BASELINE_CHANGED` |
| token 消失 | 已知 token 消失 | 受影響 CLAIM＋`UPDATE_DETECTED`＋`BASELINE_CHANGED` |
| 新來源 bootstrap | baseline 無該來源 | 建立來源 baseline，不把首次內容誤報為異動 |
| 部分來源失敗 | 一個 fetch 失敗 | 保留舊來源、`CHECK_FAILED`、最終 workflow 紅燈 |
| 腳本例外 | main 未預期例外 | report 含 traceback、`CHECK_FAILED`、exit 非 0 |
| 雙 signal | 同時有 token 異動與來源失敗 | 異動、失敗兩類 Issue 都更新；最終紅燈 |
| dry-run | 任一變化＋`--dry-run` | 報告照常，檔案不寫入 |
| coverage | 現有帳本 | 45 條涵蓋／2 條盲區（除非本輪另有經核准的 CLAIM 變動） |
| recovery＋異動 | 前次 failure、此次健康但有更新 | 更新異動 Issue；同時關閉所有失敗 Issue；workflow 綠燈 |
| recovery 多張 | 有兩張同標題 open failure Issue | 兩張都留言並關閉，不只處理第一張 |
| validation 隔離 | 受控 failure／recovery | 只碰 validation Issue；無 baseline diff；驗完移除入口 |

---

## 八、端對端驗收

本機先依序執行：

```text
python -m py_compile scripts/check_updates.py scripts/monitor_ci_policy.py
python -m unittest discover -s tests -p "test_*.py"
python scripts/check_updates.py --coverage
python scripts/check_updates.py --dry-run
python scripts/verify_gitignore_template.py
git diff --check
git diff --summary
git ls-files --eol
```

驗收標準：

- 五版 `.gitignore` 邊界案例維持各 47 條全過。
- coverage 沒有無理由改變。
- patch-only 測試不產生 baseline diff。
- 一般 minor（包含 Antigravity）不開 Issue、不產生 baseline diff；major 跨越仍告警。
- major 告警皆包含通用人工複驗提示，且提示條件不依賴 `ALERT_LEVEL` membership。
- failure fixture 不能得到綠燈。
- 雙 signal 必須同時選出兩類通知，且 recovery 能處理所有同標題 open issue。
- workflow YAML 可被 GitHub 接受，內嵌 shell 無語法錯誤。
- 只出現預期內容 diff，沒有 CRLF／LF 或 file mode 雜訊。
- 受控 GitHub 測試完成隔離的 failure → recovery，且未碰正式 Issue 或 baseline。

---

## 九、既有 Issue 處理

### Issue #7　工具路徑與機制異動

保持開啟，逐項分類：

| 候選 token | 初步分類 | 下一步 |
| :--- | :--- | :--- |
| `~/.claude/skills/synced/` | 真實的使用者層同步機制候選 | 查官方定位、產生條件與是否影響本技能的全域安裝建議 |
| `~/.claude/subagent-statusline.sh` | 使用者自訂命令／文件範例候選 | 不直接新增 CLAIM；先確認是否有工具自動建立行為 |
| `~/.codex/hooks/post_tool_use.py` | hooks 範例路徑候選 | 不直接新增 CLAIM；先分離 hooks 機制與範例腳本名稱 |

完成取證後才決定是否新增 CLAIM、更新技能或只在 Issue 記錄「無需處理」。

### Issue #8　檢查失敗

先保留到 recovery 機制完成。受控驗收使用獨立 validation Issue，不拿 #8 當測試資料；
正式修正發布後，第一個健康 production run 應自動在 #8 留言並關閉。發布前不先人工關閉，
發布後則以 #8 的實際狀態確認 production recovery 生效。

---

## 十、提交與發布策略

建議拆為三個 commit：

1. `fix(ci): 讓監控失敗正確標紅並處理恢復`
2. `fix(monitor): 降低版本基準線噪音並修正告警語意`
3. `test(docs): 補監控回歸測試與同步驗證文件`

提交前只暫存明確檔案，不使用 `git add .`。每個 commit 都檢查：

```text
git status --short
git diff --cached --check
git diff --cached --summary
```

完成本機測試後先回報維護者；只有取得明確的 push 授權才推送 GitHub。
實際 workflow dispatch、Issue 留言或關閉也在執行前再次確認授權。
