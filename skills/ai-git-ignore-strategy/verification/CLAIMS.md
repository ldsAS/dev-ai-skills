# 路徑主張帳本 (Claims Ledger)

本 skill 對外部工具行為所做的每一條路徑主張，及其依據、取證時間與狀態。
狀態定義與維護規則見 [`README.md`](./README.md)。

**最後更新**：2026-07-30（Antigravity 第一輪交接結果已回填；新增排程自動偵測的 C-53）

| 狀態 | 數量 |
| :--- | ---: |
| 已驗證 | 24 |
| 待實查 | 9 |
| 有疑 | 2 |
| 結構性 | 5 |
| **總計** | **40** |

---

## Claude Code

| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-01 | `.claude/*` | 擋直接子項，讓下方白名單得以生效 | 結構性 | — | — | 結構性 |
| C-02 | `.claude/settings.json` | 團隊共用設定（權限、hooks），應提交 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-03 | `.claude/settings.local.json` | 個人本機設定，應排除 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-04 | `.claude/commands/`、`.claude/agents/` | 團隊共用，應提交 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-05 | `.claude/rules/` | 團隊共用分檔規則，應提交 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-06 | `.claude/skills/` | 需逐案確認（CLI 安裝 vs 自撰） | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-07 | `~/.claude/projects/` | 對話紀錄與 memory 在家目錄，不在專案內 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-08 | `.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json` | 存在於官方文件，但 skill 完全未提及；預設不被任何規則擋下 | 官方文件 | 2026-07-29 | — | 待實查 |
| C-09 | `.claude/workflows/`、`.claude/worktrees/` | 出現於 CHANGELOG，目前被 `.claude/*` 擋下；worktrees 應擋，workflows 是否團隊共用未知 | 官方文件 | 2026-07-29 | — | 待實查 |
| C-53 | `.claude/skills/verify/SKILL.md` | Claude Code 的 verify 技能會**自動寫入**此檔並註明「so later runs and other agents follow the same steps」＝設計上要共享；但目前被 `.claude/skills/*` 擋下。屬「自動產生但意圖共享」的第三類，現行 skill 的二分法（CLI 安裝 vs 自撰）未涵蓋 | 官方文件（**由排程監控於 2026-07-30 自動偵測**） | 2026-07-30 | — | 待實查 |

## Codex

| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-10 | `.codex/*` | 擋直接子項 | 結構性 | — | — | 結構性 |
| C-11 | `.codex/config.toml` | 專案層設定覆寫，官方明示放進 repo，應提交 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-12 | `.codex/skills/` | 需逐案確認 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-13 | `.agents/skills` | Codex 從 CWD 逐層往上掃到 repo root | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-14 | `.agents/plugins/marketplace.json` | 專案層外掛市集，官方定位為團隊共用，應提交 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-15 | `.agents/plugins/*` | 市集內外掛本體視為安裝產物，應排除 | 推論 | 2026-07-29 | — | 待實查 |
| C-16 | `.codex-plugin/plugin.json` | 出現於 changelog，skill 未提及 | 官方文件 | 2026-07-29 | — | 待實查 |
| C-17 | `.codex/` 專案目錄其餘內容 | 除 config.toml 外是否有 cache／session 需擋 | — | — | — | 待實查 |

## Gemini CLI

| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-20 | `.gemini/*` | 擋直接子項 | 結構性 | — | — | 結構性 |
| C-21 | `.gemini/settings.json` | Workspace 設定，與 `.claude/settings.json` 同性質，應提交 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-22 | `.agents/skills/` | 為 `.gemini/skills/` 的別名，且**優先權高於**後者 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-23 | `.geminiignore`、`.aiexclude` | Gemini CLI 的忽略檔，skill 完全未提及 | 官方文件 | 2026-07-29 | — | 待實查 |
| C-24 | `.gemini/` 專案目錄其餘內容 | 是否有 cache／session 需擋 | — | — | — | 待實查 |

## Cursor

| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-30 | `.cursor/*` | 擋直接子項 | 結構性 | — | — | 結構性 |
| C-31 | `.cursor/rules/` | 團隊規則，官方建議 commit | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-32 | `.cursor/rules/imported/` | 疑為自動匯入產物，但現行 `!.cursor/rules/` 整包放行，可能誤提交 | 官方文件 | 2026-07-29 | — | 待實查 |

## Antigravity

> ⚠️ Antigravity **沒有公開文件站**（`antigravity.google/docs` 為空 stub）。
> 目前唯一可穩定取得路徑資訊的來源是 `antigravity.google/changelog`。
> 本區多數項目只能靠實機交接確認。

| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-40 | `.agents/*` | 擋直接子項 | 結構性 | — | — | 結構性 |
| C-41 | `.agents/AGENTS.md` | ~~專案級自訂規則，應提交~~ → **不存在**；Antigravity 只讀根目錄的 `AGENTS.md` | 實機＋維護者複驗 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-42 | `.agents/settings.json` | ~~專案共用設定，應提交~~ → **不存在**；專案設定實存於 `~/.gemini/config/projects/<uuid>.json` | 實機＋官方 changelog（雙重佐證） | 2026-07-29 | 1.0.13 | 已驗證 |
| C-43 | `.agents/settings.local.json` | ~~個人本機設定~~ → **不存在**，係誤類比 Claude Code；規則已移除 | 實機＋維護者複驗 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-44 | `.agents/hooks.json` | 工作區層級 hooks **確實存在於設計中**；「屬團隊共用、與家目錄 hooks 合併且專案優先」之說法**依據循環且標的物未觀察到** | 官方 changelog（存在性）／回報未採信（歸類） | 2026-07-29 | 1.0.13 | 有疑 |
| C-45 | `.antigravitycli/` | 舊版工作區對應檔，現行版本不再產生；規則保留供舊專案 | 官方 changelog＋實機 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-46 | `.agent/` | 舊版佈局的專案工作區暫存，現行版本不再產生；規則保留供舊專案 | 實機＋維護者複驗 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-47 | `~/.gemini/config/skills/` | **現行**全域 skills 路徑；實查含工具自身的 `.datacloud_skills_manifest` 與 22 個內建技能 | 實機＋維護者複驗 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-48 | `~/.gemini/antigravity/skills/` | ~~1.x 全域路徑~~ → **舊版佈局，未證實會被讀取**：該目錄僅有本專案 `install.sh` 寫入的內容，無工具自身產物；`~/.gemini/config/.migrated`（2026-06-23）顯示已遷移，而本技能是遷移後才寫入 | 維護者複驗**推翻**回報結論 | 2026-07-29 | 1.0.13 | 有疑 |
| C-49 | Antigravity 對話紀錄位置 | 在家目錄 `~/.gemini/antigravity/conversations/`（實查 21 項）與 `~/.gemini/antigravity-cli/conversations/`（1 項），**不寫入專案** | 實機＋維護者複驗 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-50 | `AGENTS.md`（根目錄） | Antigravity 已支援讀取，與 `GEMINI.md` 並列 | 官方 changelog＋實機 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-51 | 技能觸發語法 | `@skill-name` **已不適用**；技能由 Agent 依任務自動掃描載入 | 實機（回報） | 2026-07-29 | 1.0.13 | 已驗證 |
| C-52 | 專案目錄自動產生物 | Antigravity **不在專案目錄產生任何 cache／log／session**，全部收於 `~/.gemini/` | 實機＋維護者複驗 | 2026-07-29 | 1.0.13 | 已驗證 |

> 📌 **版本標籤更正**：本 skill 原以「1.x／2.0」區分新舊路徑，但實查 `agy --version` 為 **1.0.13**，
> 且 `config.json`、`antigravity_state.pbtxt`、`settings.json` 中均查無任何 `2.0` 版本字串。
> 該標籤無可觀察依據，已改用「現行全域路徑／舊版佈局」並以 `~/.gemini/config/.migrated` 為分界證據。

## 跨工具

| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-60 | `.agents/` | **非 Antigravity 專屬**，是 Codex／Gemini CLI／Antigravity 共用的跨工具目錄 | 官方文件（三方交叉） | 2026-07-29 | — | 已驗證 |

---

## 依據摘錄

> 引述自各工具官方文件／changelog，取證日 2026-07-29。
> 機器可比對的 token 快照見 [`scripts/last_checked.json`](../../../scripts/last_checked.json)。

**C-05** `.claude/rules/` — [docs.claude.com/en/docs/claude-code/memory](https://docs.claude.com/en/docs/claude-code/memory)
> For larger projects, you can organize instructions into multiple files using the `.claude/rules/`
>
> The dialog protects you from files other people commit to a shared project.

**C-07** `~/.claude/projects/` — 同上
> Each project gets its own memory directory at `~/.claude/projects/<project>/memory/`

**C-11** `.codex/config.toml` — [developers.openai.com/codex/config-basic](https://developers.openai.com/codex/config-basic)
> To scope settings to a specific project or subfolder, add a `.codex/config.toml` file in your repo.

**C-13** `.agents/skills` — [developers.openai.com/codex/skills](https://developers.openai.com/codex/skills)
> For repositories, Codex scans `.agents/skills` in every directory from your current working directory up to the repository root.

**C-14** `.agents/plugins/marketplace.json` — [developers.openai.com/codex/changelog](https://developers.openai.com/codex/changelog)
> You can install plugins for just yourself with `~/.agents/plugins/marketplace.json` and `~/.codex/plugins/`, or for everyone on a project with `.agents/plugins/marketplace.json`

**C-21** `.gemini/settings.json` — [gemini-cli docs/cli/settings.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/settings.md)
> **Workspace settings**: `your-project/.gemini/settings.json` … Workspace settings override user settings.

**C-22** `.agents/skills/` — [gemini-cli docs/cli/skills.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/skills.md)
> Within the same tier (user or workspace), the `.agents/skills/` alias takes precedence over the `.gemini/skills/` directory.

**C-32** `.cursor/rules/imported/` — [cursor.com/docs/context/rules](https://cursor.com/docs/context/rules)
> `.cursor/rule/imported/<repoName>/dir/rule.mdc`

**C-44** `.agents/hooks.json` — [antigravity.google/changelog](https://antigravity.google/changelog)
> Fixed workspace-local hooks defined in `/.agents/hooks.json` not loading after trusting a folder

**C-45** `.antigravitycli/` — 同上
> Decoupled project discovery from local `.antigravitycli` workspace directories. The CLI now stores workspace-to-project mappings in a centralized `~/.gemini/antigravity-cli/cache/projects.json` file, eliminating repository clutter

**C-47** `~/.gemini/config/` — 同上
> Fixed the /agents panel's "Create New Agents" section displaying the wrong global configuration directory (`~/.gemini/antigravity-cli/` instead of `~/.gemini/config/`)

**C-50** `AGENTS.md` — 同上
> Added support for reading rules from `AGENTS.md` in addition to `GEMINI.md`

---

## 交接輪次紀錄

| 日期 | 工具 | 涵蓋項目 | 交接包 | 回覆 |
| :--- | :--- | :--- | :--- | :--- |
| 2026-07-29 | Antigravity 1.0.13 | C-41～C-49（新增 C-51、C-52） | [交接包](./rounds/2026-07-29-antigravity.md) | [回覆](./rounds/2026-07-29-antigravity.reply.md)　已回填；其中 C-44、C-48 經維護者複驗後**未採信**回報結論 |
