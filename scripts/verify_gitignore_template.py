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
再對下方 CASES 的每個路徑跑 `git check-ignore -q`，比對「擋／放行」是否符合預期。

不碰本 repo、不連網。暫時目錄用完即刪。

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

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.join(HERE, os.pardir, "skills", "ai-git-ignore-strategy")
FENCE_RE = re.compile(r"(?ms)^```[a-zA-Z]*\n(.*?)^```$")

# (路徑, 是否應該被擋)；括號內為對應的帳本編號，依據見 verification/CLAIMS.md
CASES = [
    # --- Antigravity 工作區（C-41～C-56）---
    # 原有 .agents/AGENTS.md、.agents/settings.json 兩案（預期放行）已於 2026-08-04 移除：
    # 兩者皆為不存在的檔案，白名單規則本身已刪（見 C-41、C-42）。對不存在的路徑斷言行為
    # 沒有保護價值，且會讓人誤以為該路徑有效 —— 與 .codex/rollout.jsonl 同樣的處置
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
    (".claude/worktrees/feat-x/main.py", True),          # C-09 git worktree，且有逃逸風險
    (".claude-plugin/plugin.json", False),               # C-08
    (".claude-plugin/marketplace.json", False),          # C-08
    (".mcp.json", False),                                # C-61 專案層 MCP 設定
    # --- Gemini CLI（C-21～C-23）---
    (".gemini/settings.json", False),                    # C-21 Workspace 設定
    (".geminiignore", False),                            # C-23 忽略規則，與 .gitignore 同性質
    (".aiexclude", False),                               # C-23
    (".gemini/cache/x", True),
    # --- 一般檔案不可被誤殺 ---
    (".github/prompts/a.prompt.md", False),
    ("CLAUDE.md", False),
    ("AGENTS.md", False),
    ("src/main.py", False),
    (".env.example", False),
    (".env.production", True),
]


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
    text = open(path, encoding="utf-8").read()
    for match in FENCE_RE.finditer(text):
        if ".agents/*" in match.group(1):
            return match.group(1)
    return None


def check_variant(variant):
    """回傳不符預期的案例清單；找不到範本時視為失敗。"""
    template = extract_template(variant)
    if template is None:
        return None

    tmp = tempfile.mkdtemp(prefix=f"gitignore-{variant}-")
    try:
        subprocess.run(["git", "init", "-q"], cwd=tmp, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(os.path.join(tmp, ".gitignore"), "w",
                  encoding="utf-8", newline="\n") as handle:
            handle.write(template)

        mismatches = []
        for path, expect_blocked in CASES:
            result = subprocess.run(["git", "check-ignore", "-q", path], cwd=tmp)
            blocked = (result.returncode == 0)
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

    if failed:
        print("\n提示：`git check-ignore -v <path>` 可看命中哪一條規則；"
              "注意輸出以 `!` 開頭代表放行而非擋下。")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
