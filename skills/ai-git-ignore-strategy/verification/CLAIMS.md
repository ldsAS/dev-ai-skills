# 路徑主張帳本 (Claims Ledger)

本 skill 對外部工具行為所做的每一條路徑主張，及其依據、取證時間與狀態。
狀態定義與維護規則見 [`README.md`](./README.md)。

**最後更新**：2026-07-30（**全部 43 條均已定案**，無待實查與有疑殘留）

| 狀態 | 數量 |
| :--- | ---: |
| 已驗證 | 38 |
| 待實查 | 0 |
| 有疑 | 0 |
| 結構性 | 5 |
| **總計** | **43** |

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
| C-08 | `.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json` | 外掛／市集清單檔，官方定位為「Sharing with teammates, distributing to community」。**若本 repo 本身就是 plugin 或 marketplace，必須提交**。現行規則不擋（正確），已補進 🟢 清單 | 官方文件 | 2026-07-30 | — | 已驗證 |
| C-09 | `.claude/workflows/`、`.claude/worktrees/` | **兩者相反**。`workflows/` 有 user-scope（`~/.claude/workflows/`）與 project-scope 兩層，屬團隊共用 → **已放行**。`worktrees/` 是 git worktree 實體工作目錄，且官方修過「repository-committed symlink at `.claude/worktrees` 可在 repo 外建檔」的逃逸問題 → **已 explicit 排除** | 官方 CHANGELOG | 2026-07-30 | — | 已驗證 |
| C-53 | `.claude/skills/verify/SKILL.md` | `/verify` 把可用的建置指令自動寫入 repo root（monorepo 則寫入被動到的套件目錄），官方定位「so later runs and **other agents** follow the same steps」＝設計上要共享 → **已放行**。屬「自動產生但意圖共享」的第三類，補足了原本 CLI 安裝／自撰的二分法 | 官方文件（**由排程監控於 2026-07-30 自動偵測**） | 2026-07-30 | — | 已驗證 |

## Codex

| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-10 | `.codex/*` | 擋直接子項 | 結構性 | — | — | 結構性 |
| C-11 | `.codex/config.toml` | 專案層設定覆寫，官方明示放進 repo，應提交 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-12 | `.codex/skills/` | 需逐案確認 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-13 | `.agents/skills` | Codex 從 CWD 逐層往上掃到 repo root | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-14 | `.agents/plugins/marketplace.json` | 專案層外掛市集，官方定位為團隊共用，應提交 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-15 | `.agents/plugins/*` | 官方寫明專案層只放 `.agents/plugins/marketplace.json`，**外掛本體另存於 repo-local 目錄（如 `./plugins/`）**，不在 `.agents/plugins/` 底下。現行「放行 manifest、擋其餘」的三段式規則正確 | 官方 changelog | 2026-07-30 | — | 已驗證 |
| C-16 | `.codex-plugin/plugin.json` | 外掛必備清單檔（`Every plugin is a folder with a required .codex-plugin/plugin.json manifest`）。與 C-08 同性質，若本 repo 是外掛則必須提交。現行規則不擋（正確），已補進 🟢 清單 | 官方 changelog | 2026-07-30 | — | 已驗證 |
| C-17 | `.codex/` 專案目錄其餘內容 | **原規則誤殺三項**：`.codex/hooks.json`、`.codex/hooks/*.py`、`.codex/rules/*.rules` 都是官方列出的專案層設定層（未信任專案會跳過這些 layer），屬團隊共用 → **已放行**。`.codex/rollout.jsonl` 為 session 執行期紀錄 → **已 explicit 排除** | 官方文件（hooks／rules 指南） | 2026-07-30 | — | 已驗證 |

## Gemini CLI

| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-20 | `.gemini/*` | 擋直接子項 | 結構性 | — | — | 結構性 |
| C-21 | `.gemini/settings.json` | Workspace 設定，與 `.claude/settings.json` 同性質，應提交 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-22 | `.agents/skills/` | 為 `.gemini/skills/` 的別名，且**優先權高於**後者 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-23 | `.geminiignore`、`.aiexclude` | AI 忽略規則檔，官方明示「similar to `.gitignore`」，與 `.gitignore` 同性質 → **應提交**。現行規則不擋（正確），已補進 🟢 清單 | 官方文件 | 2026-07-30 | — | 已驗證 |
| C-24 | `.gemini/` 專案目錄其餘內容 | Session 存於 **家目錄** `~/.gemini/tmp/<project_hash>/chats/`，不寫入專案。專案內 `.gemini/` 以 `settings.json`、`skills/` 等共享內容為主，無需額外 cache 排除規則 | 官方文件 | 2026-07-30 | — | 已驗證 |

## Cursor

| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-30 | `.cursor/*` | 擋直接子項 | 結構性 | — | — | 結構性 |
| C-31 | `.cursor/rules/` | 團隊規則，官方建議 commit | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-32 | `.cursor/rules/imported/` | Cursor 會自 **其他 repo** pull and sync 規則並放到 `.cursor/rules/imported/<repoName>`，屬可重新取得的鏡像，提交等同 vendoring 他人內容且會持續 churn → **已在 `!.cursor/rules/` 之後 explicit 排除** | 官方文件 | 2026-07-30 | — | 已驗證 |

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
| C-44 | `.agents/hooks.json` | 工作區層級 hooks；**會合併多個 hooks.json 檔**（二進位字串 `loaded %d named hooks from %d hooks.json file(s)` 為複數）。信任狀態以工作區絕對路徑為 key 存於家目錄 `~/.gemini/trusted_hooks.json` —— 此設計意味 hooks 定義可來自他人 commit 的 repo，故**屬可共享檔**；是否提交屬專案決策，非待驗事實 | 二進位字串分析＋`trusted_hooks.json` 結構 | 2026-07-30 | 1.0.13 | 已驗證 |
| C-45 | `.antigravitycli/` | 舊版工作區對應檔，現行版本不再產生；規則保留供舊專案 | 官方 changelog＋實機 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-46 | `.agent/` | 舊版佈局的專案工作區暫存，現行版本不再產生；規則保留供舊專案 | 實機＋維護者複驗 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-47 | `~/.gemini/config/skills/` | **現行**全域 skills 路徑；實查含工具自身的 `.datacloud_skills_manifest` 與 22 個內建技能 | 實機＋維護者複驗 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-48 | `~/.gemini/antigravity/skills/` | ~~1.x 全域路徑~~ → **死路徑，1.0.13 已不掃描**。標記技能實驗：探針只放此路徑，開全新子代理重新初始化後不在可用技能中，且子代理指認實際載入路徑為 `~/.gemini/config/skills/`。安裝器偵測邏輯已連帶修正 | 實驗（探針技能＋對照組） | 2026-07-30 | 1.0.13 | 已驗證 |
| C-49 | Antigravity 對話紀錄位置 | 在家目錄 `~/.gemini/antigravity/conversations/`（實查 21 項）與 `~/.gemini/antigravity-cli/conversations/`（1 項），**不寫入專案** | 實機＋維護者複驗 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-50 | `AGENTS.md`（根目錄） | Antigravity 已支援讀取，與 `GEMINI.md` 並列 | 官方 changelog＋實機 | 2026-07-29 | 1.0.13 | 已驗證 |
| C-51 | 技能觸發語法 | `@skill-name` **已不適用**；技能由 Agent 依任務自動掃描載入 | 實機（回報） | 2026-07-29 | 1.0.13 | 已驗證 |
| C-52 | 專案目錄自動產生物 | ~~不在專案目錄產生任何 cache／log~~ → **回報有誤**：對話紀錄確實在家目錄，但 agent 會寫入 `.agents/ORIGINAL_REQUEST.md`（見 C-55） | 二進位字串分析**推翻**回報結論 | 2026-07-30 | 1.0.13 | 已驗證 |
| C-54 | `.agents/agents/<name>/agent.json` | 工作區層級自訂子代理定義，**應提交**（已放行）。依據不是類比其他工具，而是 agy 自身的**對稱設計**：`GetAgentsCreatePath`／`GetGlobalAgentsCreatePath` 與 `GetSkillsCreatePath`／`GetGlobalSkillsCreatePath` 成對存在（各 3 次），即工具把 agents 與 skills 視為同類的兩層結構，而 `.agents/skills/` 本已放行；另有 `writing agent.json`／`marshaling agent.json` 顯示為使用者發起的持久化宣告，且執行期狀態另有去處（C-56 與家目錄 `brain/`）。**殘留未知**：實體檔案內容尚無人目視 | 二進位字串分析（架構對稱） | 2026-07-30 | 1.0.13 | 已驗證 |
| C-55 | `.agents/ORIGINAL_REQUEST.md` | agent 會把使用者訊息**逐字**附加至此檔（含 UTC 時間戳），亦有 `.agents/<agent_folder>/ORIGINAL_REQUEST.md` 變體。**屬敏感內容，必須排除** | 二進位字串分析 | 2026-07-30 | 1.0.13 | 已驗證 |
| C-56 | `.agents/<type>_<milestone>[_<N>][_gen<N>]/` | 子代理在**專案內**建立的工作目錄命名規則（二進位字串），內含 `ORIGINAL_REQUEST.md` 等記錄。已被 `.agents/*` 完整涵蓋 | 二進位字串分析 | 2026-07-30 | 1.0.13 | 已驗證 |

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
> Cursor will pull and sync the rule(s) into your project. Rules will be placed in `.cursor/rules/imported/<repoName>`

**C-08** — [docs.claude.com/en/docs/claude-code/plugins](https://docs.claude.com/en/docs/claude-code/plugins)
> **Plugins** (self-contained directories with skills, agents, hooks, or a `.claude-plugin/plugin.json` manifest) … Sharing with teammates, distributing to community, versioned releases, reusable across projects

**C-09** — [claude-code CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
> project-scope workflow saves now target the closest existing `.claude/workflows/`
>
> Fixed worktree creation following a repository-committed symlink at `.claude/worktrees`, which could create files outside the repository

**C-53** — [docs.claude.com/en/docs/claude-code/skills](https://docs.claude.com/en/docs/claude-code/skills)
> it writes what worked to `.claude/skills/verify/SKILL.md` at the repo root, or in the touched package directory in a monorepo, so later runs and other agents follow the same steps

**C-15／C-16** — [developers.openai.com/codex/changelog](https://developers.openai.com/codex/changelog)
> for everyone on a project with `.agents/plugins/marketplace.json` and a repo-local plugin directory such as `./plugins/`
>
> Every plugin is a folder with a required `.codex-plugin/plugin.json` manifest

**C-17** — [developers.openai.com/codex/hooks](https://developers.openai.com/codex/hooks)、[/rules](https://developers.openai.com/codex/rules)
> the four most useful locations are: `~/.codex/hooks.json` … `<repo>/.codex/…`
>
> Create a `.rules` file under a `rules/` folder next to an active config layer (for example, `~/.codex/rules/default.rules`)
>
> Untrusted projects skip project-scoped `.codex/` layers, including project-local config, hooks, and rules.

**C-23** — [gemini-cli docs/cli/gemini-ignore.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-ignore.md)
> Gemini CLI includes the ability to automatically ignore files, similar to `.gitignore` (used by Git) and `.aiexclude` (used by Gemini Code Assist).

**C-24** — [gemini-cli docs/cli/session-management.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/session-management.md)
> Sessions are stored in `~/.gemini/tmp/<project_hash>/chats/`

**C-44** `.agents/hooks.json` — [antigravity.google/changelog](https://antigravity.google/changelog)
> Fixed workspace-local hooks defined in `/.agents/hooks.json` not loading after trusting a folder

**C-45** `.antigravitycli/` — 同上
> Decoupled project discovery from local `.antigravitycli` workspace directories. The CLI now stores workspace-to-project mappings in a centralized `~/.gemini/antigravity-cli/cache/projects.json` file, eliminating repository clutter

**C-47** `~/.gemini/config/` — 同上
> Fixed the /agents panel's "Create New Agents" section displaying the wrong global configuration directory (`~/.gemini/antigravity-cli/` instead of `~/.gemini/config/`)

**C-50** `AGENTS.md` — 同上
> Added support for reading rules from `AGENTS.md` in addition to `GEMINI.md`

**C-44／C-54／C-55** — `agy.exe` 1.0.13 二進位字串（`%LOCALAPPDATA%\agy\bin\agy.exe`，152 MB）
> `{workspace}/.agents/skills/{skill_name}/SKILL.md`
> `{workspace}/.agents/agents/{agent_name}/agent.json`
> `- Path: ".agents" (relative to the workspace root)`
> `loaded %d named hooks from %d hooks.json file(s)`
> `Maintain an **ORIGINAL_REQUEST.md** file that captures user requests verbatim.`
> `append it to .agents/ORIGINAL_REQUEST.md with a UTC timestamp header`
> `append it to .agents/<your_folder>/ORIGINAL_REQUEST.md with a UTC timestamp header`

**C-54** — 同上，agents／skills 的建立路徑函式對稱（各 3 次出現）
> `{workspace}/.agents/agents/{agent_name}/agent.json`
> `{appDataDir}/agents/{agent_name}/agent.json`
> `store.(*Manager).GetAgentsCreatePath` ／ `store.(*Manager).GetGlobalAgentsCreatePath`
> `store.(*SkillsManager).GetSkillsCreatePath` ／ `GetGlobalSkillsCreatePath`
> `writing agent.json` ／ `marshaling agent.json`

---

## 交接輪次紀錄

| 日期 | 工具 | 涵蓋項目 | 交接包 | 回覆 |
| :--- | :--- | :--- | :--- | :--- |
| 2026-07-29 | Antigravity 1.0.13 | C-41～C-49（新增 C-51、C-52） | [交接包](./rounds/2026-07-29-antigravity.md) | [回覆](./rounds/2026-07-29-antigravity.reply.md)　已回填；其中 C-44、C-48 經維護者複驗後**未採信**回報結論 |
| 2026-07-30 | Antigravity 1.0.13 | C-48、C-54（Q1 為實驗題） | [交接包](./rounds/2026-07-30-antigravity-round2.md) | [回覆](./rounds/2026-07-30-antigravity-round2.reply.md)　C-48 結案（實驗方法正確）；C-54 與自由敘述的 4 條路徑未採信，C-54 改由二進位對稱設計自行結案 |
| 2026-07-30 | 官方文件研究（無需交接） | C-08、C-09、C-15～C-17、C-23、C-24、C-32、C-53 | — | 九項全部由官方文件直接定案，未動用交接輪次 |
