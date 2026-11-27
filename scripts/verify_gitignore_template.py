#!/usr/bin/env python3
"""驗證五版 SKILL.md 的 `.gitignore` 範本規則邊界是否符合預期。

為什麼需要這支腳本
------------------
`.gitignore` 有兩種**靜默失效**模式，肉眼審不出來：

1. `#` 只有在行首才是註解。寫成 `!.claude/settings.json  # 團隊共用` 會讓整條規則
   連同註解被當成檔名比對而完全失效 —— 白名單看起來存在，實際一條都沒生效。
   2026-07-30 的一次審查中，四個變體共 **72 條**規則因此失效。
2. `!` 救不回「位於已被忽略之**目錄**底下」的檔案。`.claude/` 整包忽略後，
   `!.claude/skills/` 完全無效，必須改成 `.claude/*` 搭配白名單。

兩者都不會報錯，只會安靜地讓規則不生效 —— 該擋的沒擋、該放行的被誤殺。
唯一可靠的檢驗方式是實際跑 `git check-ignore`。

做法
----
把每個變體的範本抽出來，各自寫進一個**暫時 git repo** 的 `.gitignore`，
再對下方 CASES 的每個路徑跑 `git check-ignore --no-index -q --`，比對「擋／放行」是否符合預期。
`--no-index` 讓結果只反映 ignore 規則，不會因探測檔已被 Git 追蹤而得到假放行。

另外檢查本 repo 根目錄的 `.gitignore`：AI 規則行必須與 generic 範本同步，
AI 相關案例也必須成立（2026-11-27 起；先前這裡長期整包排除 `.claude/` 而無人察覺）。

不修改本 repo、不連網。暫時目錄用完即刪。

用法
----
    python scripts/verify_gitignore_template.py          # 驗證，全過回傳 0
    python scripts/verify_gitignore_template.py --list   # 只列出測試案例

新增或修改規則時，請一併在 CASES 補上對應案例；
若某條規則的判斷依據有變，請同步更新 `verification/CLAIMS.md`（見 CONTRIBUTING.md）。
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

# Windows 主控台預設是 cp950／cp1252 等 ANSI codepage，印 ✅ ❌ 會噴 UnicodeEncodeError。
# 檢查其實已經跑完，卻在輸出那一步崩潰 —— 看起來像驗證失敗，實際上只是終端機編碼問題。
# CONTRIBUTING 要求 contributor 本機跑這支，而 Linux CI 是 UTF-8 不受影響，
# 所以這個坑只砸在 Windows 貢獻者身上，且永遠不會在 CI 上現形。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.join(HERE, os.pardir, "skills", "ai-git-ignore-strategy")
FENCE_RE = re.compile(r"(?ms)^```[a-zA-Z]*\n(.*?)^```$")

# (路徑, 是否應該被擋)；括號內為對應的帳本編號，依據見 verification/CLAIMS.md
CASES = [
    # --- Antigravity 工作區（C-41～C-56）---
    # C-115 取代 C-41 的無版本限制否定；settings.json 仍不放行（C-116）。
    (".agents/AGENTS.md", False),
    (".agents/GEMINI.md", False),
    (".agents/rules.json", False),
    (".agents/skills.json", False),                    # C-119 精準團隊登記檔
    (".agents/skills.json.bak", True),
    (".agents/agents.json", False),                    # C-120／C-121 與 skills.json 同一套登記機制
    (".agents/plugins.json", False),
    (".agents/agents.json.bak", True),
    (".agents/plugins.json.bak", True),
    (".agents/plugins/plugins.json", True),             # 只放行 .agents/ 直下的登記檔
    ("apps/web/.agents/skills.json", False),            # 既有子目錄行為，不是 runtime 證據
    (".agents/AGENTS.md.bak", True),
    (".agents/settings.json", True),
    ("apps/web/.agents/AGENTS.md", False),
    ("apps/web/.agents/GEMINI.md", False),
    ("apps/web/.agents/rules.json", False),
    # C-117 防禦性政策；不代表下列位置有 runtime 寫入證據。
    (".agents/rules/ORIGINAL_REQUEST.md", True),
    (".agents/skills/foo/ORIGINAL_REQUEST.md", True),
    (".agents/plugins/ORIGINAL_REQUEST.md", True),
    (".agents/agents/x/ORIGINAL_REQUEST.md", True),
    ("apps/web/.agents/ORIGINAL_REQUEST.md", True),
    ("apps/web/.agents/x/ORIGINAL_REQUEST.md", True),
    ("apps/web/.agents/x/y/ORIGINAL_REQUEST.md", True),
    ("apps/web/.agents/rules/ORIGINAL_REQUEST.md", True),
    ("docs/ORIGINAL_REQUEST.md", False),
    ("apps/web/.agents/ORIGINAL_REQUEST.md.example", False),
    ("apps/web/.agents-other/ORIGINAL_REQUEST.md", False),
    (".agents/settings.local.json", True),               # C-43 規則已移除，仍被 .agents/* 涵蓋
    (".agents/hooks.json", True),                        # C-44 白名單預設註解，由開發者決定
    (".agents/ORIGINAL_REQUEST.md", True),               # C-55 逐字記錄使用者訊息，敏感
    (".agents/sentinel/ORIGINAL_REQUEST.md", True),      # C-55 子目錄變體
    (".agents/impl_lexer/ORIGINAL_REQUEST.md", True),    # C-56 子代理工作目錄
    (".agents/plan_parser_2_gen3/notes.md", True),       # C-56 同上
    (".agents/agents/reviewer/agent.json", True),        # C-54 白名單預設註解：尚無人目視過內容
    (".agents/agents/nested/deep/agent.json", True),     # C-54 同上
    (".agents/rules/style.md", False),                   # C-57 工作區規則，團隊共用
    (".agent/rules/legacy.md", False),                   # C-57 舊佈局仍向後相容
    (".agents/mcp_config.json", False),                  # C-58 工作區 MCP 定義
    (".agents/cache/session.db", True),
    (".agents/skills/thirdparty/SKILL.md", True),        # 第三方技能預設不追蹤
    (".antigravitycli/projects.json", True),             # C-45 舊版殘留
    (".agent/cache/x.db", True),                         # C-46 舊佈局
    (".agent/skills/thirdparty/SKILL.md", True),
    # --- Codex（C-11～C-17）---
    (".codex/config.toml", False),                       # C-11 專案層設定，官方明示放進 repo
    (".codex/hooks.json", False),                        # C-17 專案層 hooks
    (".codex/hooks/session_start.py", False),            # C-17 hook 腳本
    (".codex/rules/default.rules", False),               # C-17 沙箱指令規則
    (".codex/skills/thirdparty/SKILL.md", True),
    (".codex-plugin/plugin.json", False),                # C-16 外掛清單檔
    (".agents/plugins/marketplace.json", False),         # C-14 團隊共用市集
    (".agents/plugins/some-plugin/index.js", True),      # C-15 外掛本體不在此
    # --- Claude Code（C-02～C-09、C-53）---
    (".claude/settings.json", False),                    # C-02
    (".claude/launch.json", True),                      # C-83 白名單預設註解：可能含個人絕對路徑
    (".claude/settings.local.json", True),               # C-03
    (".claude/commands/deploy.md", False),               # C-04
    (".claude/agents/reviewer.md", False),               # C-04
    (".claude/rules/security.md", False),                # C-05
    (".claude/skills/thirdparty/SKILL.md", True),        # C-06 第三方技能
    (".claude/skills/verify/SKILL.md", False),           # C-53 自動產生但官方定位為共享
    (".claude/workflows/deploy.md", False),              # C-09 專案層 workflow
    (".claude/output-styles/review.md", False),          # C-122 團隊共用 output style
    (".claude/output-styles-local/mine.md", True),       # 不放行名稱相近的目錄
    (".claude/worktrees/feat-x/main.py", True),          # C-09 git worktree，且有逃逸風險
    (".claude-plugin/plugin.json", False),               # C-08
    # --- monorepo 子目錄的 .claude/（C-97）---
    # 含中段 / 的規則錨定在 .gitignore 所在層級，因此根目錄那組規則碰不到子目錄。
    # 個人本機檔必須靠 **/ 前綴補上；其餘 nested 內容屬團隊共享，維持放行。
    ("apps/web/.claude/settings.local.json", True),      # C-97 個人本機設定，nested 也要擋
    ("apps/web/.claude/settings.json", False),           # C-97 團隊共用設定
    ("apps/web/.claude/skills/deploy/SKILL.md", False),  # C-97 nested 專案技能（官方 Nested 位置）
    ("apps/web/.claude/commands/deploy.md", False),      # C-97 nested 團隊共用指令
    ("apps/web/.claude/output-styles/review.md", False), # C-122 官方：repo root 以下每一層都載入
    (".claude-plugin/marketplace.json", False),          # C-08
    (".mcp.json", False),                                # C-61 專案層 MCP 設定
    # --- Claude 團隊指令、hooks 與記憶（C-103～C-109）---
    (".claude/CLAUDE.md", False),                        # C-103 第二個專案指令位置
    (".claude/AGENTS.md", False),                        # C-109 有條件載入的跨工具指令
    (".claude/CLAUDE.md.bak", True),                     # 精準放行，不擴及備份
    (".claude/AGENTS.md.bak", True),
    (".claude/hooks/block-rm.sh", False),                # C-104 團隊 hook 的腳本
    (".claude/hooks/block-rm.ps1", False),
    (".claude/hooks/.env", True),                       # 既有機密／日誌規則仍有效
    (".claude/hooks/debug.log", True),
    (".claude/hooks-private/local.sh", True),           # 不放行名稱相近的目錄
    (".claude/agent-memory/reviewer/MEMORY.md", False),  # C-105 project 記憶
    ("apps/web/.claude/agent-memory/reviewer/MEMORY.md", False),
    (".claude/agent-memory-local/reviewer/MEMORY.md", True),
    ("apps/web/.claude/agent-memory-local/reviewer/MEMORY.md", True),
    ("CLAUDE.local.md", True),                          # C-106 個人指令，含子目錄
    ("apps/web/CLAUDE.local.md", True),
    ("CLAUDE.local.md.example", False),                 # 不排除不同名稱的範例
    (".claude/scheduled_tasks.json", True),             # C-107 既有廣域規則已涵蓋
    # --- Gemini CLI（C-21～C-23）---
    (".gemini/settings.json", False),                    # C-21 Workspace 設定
    (".gemini/config.json", True),                      # C-116 opt-in 預設不啟用
    (".geminiignore", False),                            # C-23 忽略規則，與 .gitignore 同性質
    (".aiexclude", False),                               # C-23
    (".gemini/cache/x", True),
    # --- 一般檔案不可被誤殺 ---
    (".github/prompts/a.prompt.md", False),
    (".github/hooks/log-tool-use.cjs", False),           # 官方 hook 範例程式
    (".github/hooks/tool-use.log", True),               # 範例執行輸出
    ("CLAUDE.md", False),
    ("AGENTS.md", False),
    ("src/main.py", False),
    (".env.example", False),
    (".env.production", True),
]


# ---------------------------------------------------------------------------
# 本 repo 自己的 .gitignore（dogfooding）
# ---------------------------------------------------------------------------
# 2026-04-25 建 repo 時根目錄 .gitignore 整包排除 .claude/ 等 AI 資料夾；之後的校正
# 只改了五版範本，這裡一直沒跟上，因為本腳本從不檢查它（2026-11-27 才發現）。
# 現在兩道檢查：① AI 規則行與範本同步；② AI 相關案例對根目錄 .gitignore 也成立。
REPO_GITIGNORE = os.path.join(HERE, os.pardir, ".gitignore")
SYNC_VARIANT = "generic"
# 規則行的分組依據：第一個出現的 AI 工具 dot 目錄。各組互不影響，所以只比對組內順序；
# antigravity 版把自家工具排在最前面，組間順序不同不算走樣。
AI_GROUP_RE = re.compile(r"\.(claude|agents?|codex|gemini|antigravitycli|cursor)(?=/|$)")
# 這幾個 AI 相關檔名不在 dot 目錄裡，歸入對應工具組。
AI_FILE_GROUPS = {"CLAUDE.local.md": "claude"}
# 範本的白名單會放行 .claude/hooks/ 等目錄，裡面的機密檔要靠這幾條擋；只搬白名單會漏掉保護。
SHARED_SECRET_RULES = [".env", ".env.*", "!.env.example", "*.pem", "*.key", "credentials.json"]
# 本 repo 特有的決定，範本本身不涵蓋。
REPO_CASES = [
    (".claude/hooks/.env", True),
    (".claude/hooks/deploy.key", True),
    (".env.example", False),
    # 2026-08-04 Codex 回覆：技能原始檔在 skills/，不在 .agents/skills/ 另放同名副本
    (".agents/skills/ai-git-ignore-strategy/SKILL.md", True),
    ("skills/ai-git-ignore-strategy/claude/SKILL.md", False),
    ("scripts/last_checked.json", False),
    (".venv/lib/python3.11/site.py", True),
    ("scripts/__pycache__/check_updates.cpython-311.pyc", True),
]


def ai_rule_groups(text):
    """依工具分組回傳 AI 規則行（去除註解與空行，組內保留順序）。"""
    groups = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = AI_GROUP_RE.search(line)
        group = match.group(1) if match else AI_FILE_GROUPS.get(line.lstrip("!/*"))
        if group:
            groups.setdefault(group, []).append(line)
    return groups


def ai_case(path):
    """CASES 中與 AI 工具路徑相關、因此也要對本 repo 成立的案例。"""
    return bool(AI_GROUP_RE.search(path)) or os.path.basename(path) in AI_FILE_GROUPS


def check_repo_gitignore(repo_text=None, template_text=None):
    """回傳本 repo .gitignore 的問題清單；空清單代表與範本一致。"""
    if repo_text is None:
        with open(REPO_GITIGNORE, encoding="utf-8") as handle:
            repo_text = handle.read()
    if template_text is None:
        template_text = extract_template(SYNC_VARIANT)
    problems = []
    want, have = ai_rule_groups(template_text), ai_rule_groups(repo_text)
    for group in sorted(set(want) | set(have)):
        if want.get(group) != have.get(group):
            missing = [r for r in want.get(group, []) if r not in have.get(group, [])]
            extra = [r for r in have.get(group, []) if r not in want.get(group, [])]
            detail = "；".join(filter(None, [
                f"缺少 {missing}" if missing else "",
                f"多出 {extra}" if extra else "",
                "順序不同" if not missing and not extra else "",
            ]))
            problems.append(f".{group} 規則與 {SYNC_VARIANT} 範本不同步：{detail}")
    repo_rules = {line.strip() for line in repo_text.splitlines()}
    template_rules = {line.strip() for line in template_text.splitlines()}
    for rule in SHARED_SECRET_RULES:
        if rule not in template_rules:
            problems.append(f"範本已不含機密規則 {rule}：請更新 SHARED_SECRET_RULES")
        elif rule not in repo_rules:
            problems.append(f"缺少範本的機密規則 {rule}：AI 白名單放行的目錄會失去保護")
    cases = [case for case in CASES if ai_case(case[0])] + REPO_CASES
    problems.extend(check_text(repo_text, cases, "repo"))
    return problems


def variants():
    if not os.path.isdir(SKILL_ROOT):
        return []
    return sorted(
        name for name in os.listdir(SKILL_ROOT)
        if os.path.isfile(os.path.join(SKILL_ROOT, name, "SKILL.md"))
    )


def extract_template(variant):
    """抽出含 `.agents/*` 的 fenced block，也就是 .gitignore 範本。"""
    path = os.path.join(SKILL_ROOT, variant, "SKILL.md")
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    for match in FENCE_RE.finditer(text):
        if ".agents/*" in match.group(1):
            return match.group(1)
    return None


def check_variant(variant):
    """回傳不符預期的案例清單；找不到範本時視為失敗。"""
    template = extract_template(variant)
    if template is None:
        return None
    return check_text(template, CASES, variant)


def check_text(gitignore_text, cases, label):
    """把 gitignore_text 寫進暫時 repo，回傳 cases 中不符預期的項目。"""
    tmp = tempfile.mkdtemp(prefix=f"gitignore-{label}-")
    try:
        # 驗證範本本身，避免個人 global excludes 掩蓋漏掉的排除規則。
        git_env = os.environ.copy()
        git_env["GIT_CONFIG_NOSYSTEM"] = "1"
        git_env["GIT_CONFIG_GLOBAL"] = os.devnull
        subprocess.run(["git", "init", "-q"], cwd=tmp, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       env=git_env)
        with open(os.path.join(tmp, ".gitignore"), "w",
                  encoding="utf-8", newline="\n") as handle:
            handle.write(gitignore_text)

        mismatches = []
        for path, expect_blocked in cases:
            result = subprocess.run(
                ["git", "-c", f"core.excludesFile={os.devnull}",
                 "check-ignore", "--no-index", "-q", "--", path],
                cwd=tmp, env=git_env,
            )
            blocked = (result.returncode == 0)
            if result.returncode not in (0, 1):
                mismatches.append(
                    f"{path}：git check-ignore 執行失敗（exit {result.returncode}）"
                )
                continue
            if blocked != expect_blocked:
                want = "擋下" if expect_blocked else "放行"
                got = "擋下" if blocked else "放行"
                mismatches.append(f"{path}：預期{want}，實際{got}")
        return mismatches
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="只列出測試案例後結束")
    args = parser.parse_args()

    if args.list:
        for path, blocked in CASES:
            print(f"{'擋下' if blocked else '放行'}  {path}")
        print(f"\n共 {len(CASES)} 個案例")
        return 0

    names = variants()
    if not names:
        print(f"❌ 找不到任何變體：{SKILL_ROOT}")
        return 1

    failed = False
    for variant in names:
        mismatches = check_variant(variant)
        if mismatches is None:
            print(f"❌ {variant}：找不到 .gitignore 範本區塊"
                  f"（應為含 `.agents/*` 的 fenced code block）")
            failed = True
            continue
        if mismatches:
            failed = True
            print(f"❌ {variant}（{len(mismatches)}/{len(CASES)} 不符）")
            for item in mismatches:
                print(f"     {item}")
        else:
            print(f"✅ {variant}：{len(CASES)} 個邊界案例全部符合預期")

    repo_problems = check_repo_gitignore()
    if repo_problems:
        failed = True
        print(f"❌ 本 repo 的 .gitignore（{len(repo_problems)} 項問題）")
        for item in repo_problems:
            print(f"     {item}")
    else:
        repo_cases = sum(1 for case in CASES if ai_case(case[0])) + len(REPO_CASES)
        print(f"✅ 本 repo 的 .gitignore：AI 規則與 {SYNC_VARIANT} 範本同步，{repo_cases} 個案例全部符合預期")

    if failed:
        print("\n提示：`git check-ignore --no-index -v -- <path>` 可看命中哪一條規則；"
              "注意輸出以 `!` 開頭代表放行而非擋下。")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
