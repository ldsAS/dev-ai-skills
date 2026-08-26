#!/usr/bin/env python3
"""偵測 ai-git-ignore-strategy 技能所依賴的「AI 工具路徑與機制」是否異動。

設計原則
--------
本技能的正確性不繫於工具版本號，而繫於一組**路徑事實**：
`.claude/settings.local.json` 這類檔案還在不在、Antigravity 到底用 `.agent/`
還是 `.agents/`、Claude Code 的對話紀錄是否仍在 `~/.claude/projects/`。

因此監控目標是官方文件裡出現的**路徑 token 集合**，而非版本字串：

* 版本號每天 patch bump → token 集合不變 → 不告警（消除日常噪音）
* 官方把 `.agent/` 改成 `.agents/` → token 集合變動 → 告警（真正該知道的事）

版本號僅作為報告中的參考資訊；只有 **major 版號**跳動才視為機制可能重構而告警
（Antigravity 1.x → 2.0 把 `.agent/` 改名為 `.agents/` 就是這種情況）。

輸出
----
Markdown 報告寫到 stdout，並在結尾印出給 CI grep 的訊號：
`[SIGNAL: UPDATE_DETECTED]` / `[SIGNAL: CHECK_FAILED]`
"""

import argparse
import gzip
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zlib

# Windows 主控台預設可能是 cp950／cp1252；本腳本的 Markdown 報告包含
# ↔、⚠️、❌ 等字元。若不先固定輸出編碼，檢查邏輯即使成功也會在 print 階段崩潰，
# 甚至連例外處理本身都可能因 ❌ 再次觸發 UnicodeEncodeError。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

_HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE_PATH = os.path.join(_HERE, "last_checked.json")
# 路徑主張帳本；異動時用來標出「本次觸及哪幾條已登記的主張」
CLAIMS_PATH = os.path.join(_HERE, os.pardir, "skills", "ai-git-ignore-strategy",
                           "verification", "CLAIMS.md")
SCHEMA_VERSION = 2

USER_AGENT = "Mozilla/5.0 (compatible; dev-ai-skills-watch/2.0; +https://github.com/ldsAS/dev-ai-skills)"
TIMEOUT = 25
RETRIES = 3

# --------------------------------------------------------------------------
# 監控來源：每一筆都是「技能引用過的路徑事實」的權威出處
# --------------------------------------------------------------------------
SOURCES = [
    # Claude Code — 官方文件的 .md 端點回傳原始 markdown，最穩定
    ("claude-code", "settings", "https://docs.claude.com/en/docs/claude-code/settings.md"),
    ("claude-code", "memory", "https://docs.claude.com/en/docs/claude-code/memory.md"),
    ("claude-code", "skills", "https://docs.claude.com/en/docs/claude-code/skills.md"),
    ("claude-code", "changelog", "https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md"),
    # Codex — repo 內的 docs/*.md 多已改為導向連結；官方文件已自
    # developers.openai.com 搬遷至 learn.chatgpt.com（舊網址仍 302 導向，
    # 但直接指向正式位置以免日後斷鏈）。2026-08-03 由 Codex 實機回覆指出。
    ("codex", "config-reference", "https://learn.chatgpt.com/docs/config-file/config-reference"),
    ("codex", "config-basic", "https://learn.chatgpt.com/docs/config-file/config-basic"),
    ("codex", "changelog", "https://learn.chatgpt.com/docs/changelog"),
    ("codex", "skills", "https://learn.chatgpt.com/docs/build-skills"),
    ("codex", "hooks", "https://learn.chatgpt.com/docs/hooks"),
    # Gemini CLI — repo docs 內容完整，直接讀 raw markdown
    ("gemini-cli", "settings", "https://raw.githubusercontent.com/google-gemini/gemini-cli/main/docs/cli/settings.md"),
    ("gemini-cli", "gemini-md", "https://raw.githubusercontent.com/google-gemini/gemini-cli/main/docs/cli/gemini-md.md"),
    ("gemini-cli", "skills", "https://raw.githubusercontent.com/google-gemini/gemini-cli/main/docs/cli/skills.md"),
    ("gemini-cli", "ignore", "https://raw.githubusercontent.com/google-gemini/gemini-cli/main/docs/cli/gemini-ignore.md"),
    # Antigravity — 官方文件站在 /docs/<section> 之下（索引頁 /docs 只是 stub，
    # 2026-07-30 曾因此誤判為「沒有公開文件站」）。
    # /docs/* 與 /docs/ide/* 兩套並存：前者是 CLI、後者是 IDE，全域路徑不同（見 C-47／C-48）。
    ("antigravity", "changelog", "https://antigravity.google/changelog"),
    ("antigravity", "skills", "https://antigravity.google/docs/skills"),
    ("antigravity", "ide-skills", "https://antigravity.google/docs/ide/skills"),
    ("antigravity", "subagents", "https://antigravity.google/docs/subagents"),
    ("antigravity", "hooks", "https://antigravity.google/docs/hooks"),
    ("antigravity", "rules-workflows", "https://antigravity.google/docs/rules-workflows"),
    ("antigravity", "plugins", "https://antigravity.google/docs/plugins"),
    ("antigravity", "gcli-migration", "https://antigravity.google/docs/cli/gcli-migration"),
    # VS Code / GitHub Copilot
    ("copilot", "customization", "https://code.visualstudio.com/docs/copilot/customization/overview"),
    ("copilot", "prompt-files", "https://code.visualstudio.com/docs/copilot/customization/prompt-files"),
    ("copilot", "agent-skills", "https://code.visualstudio.com/docs/copilot/customization/agent-skills"),
    ("copilot", "hooks", "https://code.visualstudio.com/docs/copilot/customization/hooks"),
    ("copilot", "repo-instructions",
     "https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions"),
]

# npm 版本（僅供參考；預設只有 major 版號跳動才告警）
NPM_PACKAGES = {
    "claude-code": "@anthropic-ai/claude-code",
    "codex": "@openai/codex",
    "gemini-cli": "@google/gemini-cli",
}

# Antigravity 不在 npm 上，版本號改由 changelog 的發行表取得
# （表格形如「2.4.3　July 28, 2026　Preview tabs, ...」）
ANTIGRAVITY_CHANGELOG = "https://antigravity.google/changelog"
RELEASE_ROW_RE = re.compile(
    r"\b(\d+\.\d+\.\d+)\s+(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{1,2},\s+\d{4}"
)

# 各工具偏離預設值的版本告警門檻 override。
# 預設 major：路徑事實以官方文件監控為主，版本號只是低頻輔助訊號。
# 目前沒有例外；不要用工具是否存在於此 map 判斷報告提示。
ALERT_LEVEL = {}

# --------------------------------------------------------------------------
# 路徑 token 抽取
# --------------------------------------------------------------------------
# 長名仍排在短名前面，讓 alternation 優先命中最具體的已知名稱。
# 另在 dot-name 分支尾端加右邊界：即使未來出現尚未列入清單的更長名稱，
# 也不能靜默截成已知前綴。2026-08-22 起 `.antigravityignore` 曾因此被存成
# `.antigravity`，baseline 保存的不是官方原文的檔名（2026-08-26 補強）。
# tests/test_check_updates.py 同時守住已知長名順序與未知長名的右邊界。
DOT_NAMES = "|".join([
    "claude-plugin", "claude",
    "codex-plugin", "codexignore", "codex",
    "geminiignore", "gemini",
    "antigravity-cli", "antigravitycli", "antigravityignore", "antigravity",
    "agents", "agent",
    "aiexclude", "aiignore",
    "copilot",
])

TOKEN_RE = re.compile(
    # 前置不可為單字字元 —— 這一條 lookbehind 負責擋掉網域名，
    # 例如 docs.claude.com 的 `.claude` 前面是 `s`，直接不視為路徑。
    r"(?<![\w-])"
    r"(?:"
    # Copilot 的自訂檔型別（prompt / instructions / agent）必須排在 dot-dir 之前，
    # 否則 `*.agent.md` 會先被 DOT_NAMES 的 `agent` 吃掉、只留下 `.agent`。
    r"[\w.\-]*\.(?:prompt|instructions|agent)\.md"
    r"|(?:(?:~|\$HOME|\.{1,2})?[/\\])?"
    rf"\.(?:{DOT_NAMES})"
    r"(?:[/\\][\w.\-]+)*[/\\]?"
    # 右側不可緊接檔名字元：否則 `.agentsfoo` 會被誤抓成 `.agents`，
    # `.antigravityignore.bak` 也會被誤當成 `.antigravityignore`。
    # 單獨的句尾 `.` 可接在 token 後；但 `.` 後若還有檔名字元（如 `.bak`）則阻擋。
    r"(?![\w\-]|\.[\w\-])"
    # Copilot 的專案層自訂目錄全在 .github/ 底下（官方 monorepo 範例：
    # .github/{copilot-instructions.md, instructions/, prompts/, agents/}，另有 skills/ 與 hooks/）
    r"|\.github[/\\](?:prompts|skills|hooks|instructions|agents)(?:[/\\][\w.\-]+)*[/\\]?"
    r"|(?:CLAUDE|AGENTS|GEMINI|QWEN)\.(?:local\.)?md"
    r"|copilot-instructions\.md"
    # Claude Code 的專案層 MCP 設定，位於 repo 根目錄而非 .claude/ 底下（C-61）
    r"|\.mcp\.json"
    r"|settings\.local\.json"
    r")"
)

# 抽到 0 個 token 但基準線原有 ≥ 這個數量時，視為抓取異常而非「路徑全被刪除」
EMPTY_SUSPICION_THRESHOLD = 3


def fetch(url):
    """取回 URL 內容；失敗時重試，全數失敗才拋出。"""
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
    last_error = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
                encoding = (resp.headers.get("Content-Encoding") or "").lower()
                if encoding == "gzip":
                    raw = gzip.decompress(raw)
                elif encoding == "deflate":
                    raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                return raw.decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001 — 任何失敗都要重試並保留原因
            last_error = exc
            if attempt < RETRIES - 1:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{type(last_error).__name__}: {last_error}")


def normalize(body):
    """把 HTML / JS 序列化內容壓成純文字，讓路徑 token 能被穩定抽出。"""
    if re.search(r"(?i)<(!doctype html|html[ >])", body[:2000]):
        body = re.sub(r"(?is)<(style|svg)[^>]*>.*?</\1\s*>", " ", body)
        body = re.sub(r"(?s)<!--.*?-->", " ", body)
        body = re.sub(r"(?s)<[^>]+>", " ", body)
        body = html.unescape(body)
    # Next.js 等框架會把文件內容以 JSON 字串內嵌，需還原跳脫序列
    body = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), body)
    body = body.replace("\\n", " ").replace("\\t", " ").replace('\\"', '"').replace("\\/", "/")
    # class 名稱純屬版面雜訊，且改版時會整批變動
    body = re.sub(r'"className":"[^"]*"', " ", body)
    return body


def extract_tokens(text):
    """從正規化後的文字抽出路徑 token 集合。"""
    tokens = set()
    for match in TOKEN_RE.finditer(text):
        token = match.group(0).strip().rstrip("`\"'.,;:!?)]}")
        if len(token) <= 2 or "://" in token:
            continue
        tokens.add(token)
    return tokens


def context_for(text, token, window=120):
    """取 token 在原文中的一段前後文，讓 issue 能說明「改了什麼」。"""
    index = text.find(token)
    if index < 0:
        return ""
    start = max(0, index - window)
    end = min(len(text), index + len(token) + window)
    return re.sub(r"\s+", " ", text[start:end]).strip()


CLAIM_ROW_RE = re.compile(
    r"^\|\s*(C-\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$",
    re.M,
)


def _norm_path(value):
    return value.strip().strip("`").rstrip("/")


def _claim_paths(cell):
    """從帳本「路徑」欄抽出可比對的路徑。

    兩種情況會被丟掉，因為比對範圍過寬會把整個工具目錄底下的異動
    全部算成同一條主張：

    * 含 `<name>` / `[_<N>]` 佔位符者截到第一個佔位符為止，截完只剩單段時丟掉
      （例：`.agents/<type>_<milestone>/` → `.agents`）
    * 指向單一段**目錄**者丟掉（例：`.agents/`、`.claude/*`）；
      單段**檔名**則保留（例：`.geminiignore`、`.aiexclude`）
    """
    paths = []
    for raw in re.findall(r"`([^`]+)`", cell):
        value = raw.strip()
        is_dir = value.endswith("/") or value.endswith("/*")
        cuts = [i for i in (value.find("<"), value.find("[")) if i >= 0]
        if cuts:
            value = value[:min(cuts)]
            is_dir = True
        value = _norm_path(value.rstrip("*"))
        if not value or value.startswith("http"):
            continue
        if is_dir and "/" not in value:
            continue
        paths.append(value)
    return paths


def load_claims():
    """讀取路徑主張帳本；讀不到就回空清單，監控本身不受影響。"""
    if not os.path.exists(CLAIMS_PATH):
        return []
    try:
        text = open(CLAIMS_PATH, encoding="utf-8").read()
    except OSError:
        return []
    claims = []
    for match in CLAIM_ROW_RE.finditer(text):
        cid, path_cell, brief, _basis, dated, _version, status = match.groups()
        # 已移出維護範圍者不參與比對，也不列入涵蓋率 ——
        # 它們保留在帳本裡只是歷史紀錄，算進盲區會讓報表失真。
        if status.strip() == "移出範圍":
            continue
        paths = _claim_paths(path_cell)
        if not paths:
            continue
        claims.append({
            "id": cid,
            "label": paths[0],
            "paths": paths,
            "brief": re.sub(r"\s+", " ", brief)[:100],
            "date": dated.strip(),
            "status": status.strip(),
        })
    return claims


def claims_for_token(token, claims):
    """找出哪些主張涵蓋這個 token（雙向前綴比對）。"""
    value = _norm_path(token)
    hits = []
    for claim in claims:
        for path in claim["paths"]:
            if value == path or value.startswith(path + "/") or path.startswith(value + "/"):
                hits.append(claim)
                break
    return hits


def fetch_npm_version(package):
    body = fetch(f"https://registry.npmjs.org/{package}/latest")
    return json.loads(body).get("version")


def fetch_antigravity_version():
    """從 changelog 的發行表取最高版本號。抓不到就回 None（不當成失敗）。"""
    text = normalize(fetch(ANTIGRAVITY_CHANGELOG))
    found = RELEASE_ROW_RE.findall(text)
    if not found:
        return None
    return ".".join(str(n) for n in max(tuple(int(p) for p in v.split(".")) for v in found))


def version_key(version, level):
    """取版本號中決定「是否告警」的前綴：major 取一段，minor 取兩段。"""
    parts = re.findall(r"\d+", version or "")
    if not parts:
        return None
    return ".".join(parts[:2] if level == "minor" else parts[:1])


def load_baseline():
    if not os.path.exists(BASELINE_PATH):
        return {}
    with open(BASELINE_PATH, "r", encoding="utf-8") as handle:
        try:
            return json.load(handle)
        except json.JSONDecodeError:
            return {}


def report_coverage():
    """列出每條主張是否有對應的監控 token —— 沒有的就是自動偵測的盲區。"""
    claims = load_claims()
    baseline = load_baseline()
    tokens = {}
    for key, entry in baseline.get("sources", {}).items():
        for token in entry.get("tokens", []):
            tokens.setdefault(_norm_path(token), set()).add(key)

    covered, blind = [], []
    for claim in claims:
        hits = set()
        for value, srcs in tokens.items():
            for path in claim["paths"]:
                if value == path or value.startswith(path + "/") or path.startswith(value + "/"):
                    hits |= srcs
                    break
        (covered if hits else blind).append((claim, sorted(hits)))

    print("# 帳本 ↔ 監控涵蓋率\n")
    print(f"可自動偵測 {len(covered)} 條／盲區 {len(blind)} 條／"
          f"共 {len(claims)} 條有路徑的主張\n")

    if blind:
        print("## ⚠️ 監控盲區（路徑異動不會被自動偵測）\n")
        for claim, _ in blind:
            print(f"- **{claim['id']}** `{claim['label']}` — 狀態 {claim['status']}")
        print()

    print("## ✅ 有監控涵蓋\n")
    for claim, srcs in covered:
        print(f"- **{claim['id']}** `{claim['label']}` ← {', '.join(srcs)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="不寫回基準線，僅輸出報告")
    parser.add_argument("--coverage", action="store_true",
                        help="列出帳本主張與監控 token 的涵蓋關係後結束（不連網）")
    args = parser.parse_args()

    if args.coverage:
        report_coverage()
        return

    raw_baseline = load_baseline()
    # schema 1（僅記錄版本號）視為未建立 token 基準，走 bootstrap 流程
    is_bootstrap = raw_baseline.get("schema") != SCHEMA_VERSION
    baseline_sources = {} if is_bootstrap else raw_baseline.get("sources", {})
    baseline_versions = raw_baseline.get("versions", {})
    if is_bootstrap and "claude_code" in raw_baseline:
        baseline_versions = {"claude-code": raw_baseline["claude_code"]}

    new_sources = {}
    changes = []       # (tool, source, added, removed, text)
    failures = []      # (label, reason)
    bootstrapped = []  # 首次納入監控的來源

    for tool, source, url in SOURCES:
        key = f"{tool}/{source}"
        try:
            text = normalize(fetch(url))
        except Exception as exc:  # noqa: BLE001
            failures.append((key, str(exc)))
            # 抓取失敗時保留舊基準，下次再檢查，避免誤判為「路徑消失」
            if key in baseline_sources:
                new_sources[key] = baseline_sources[key]
            continue

        tokens = extract_tokens(text)
        previous = set(baseline_sources.get(key, {}).get("tokens", []))

        if not tokens and len(previous) >= EMPTY_SUSPICION_THRESHOLD:
            failures.append((key, f"抓取成功但一個路徑都沒抽到（基準線原有 {len(previous)} 個），"
                                  f"疑似頁面改版或內容未載入，本次保留舊基準"))
            new_sources[key] = baseline_sources[key]
            continue

        new_sources[key] = {"tokens": sorted(tokens)}

        if key not in baseline_sources:
            bootstrapped.append((key, len(tokens)))
            continue

        added = sorted(tokens - previous)
        removed = sorted(previous - tokens)
        if added or removed:
            changes.append((tool, source, added, removed, text))

    # ---- 版本（僅供參考；major 跳動才告警） ----
    new_versions = dict(baseline_versions)
    version_alerts = []
    version_notes = []
    version_sources = [(tool, pkg, lambda p=pkg: fetch_npm_version(p))
                       for tool, pkg in NPM_PACKAGES.items()]
    version_sources.append(("antigravity", "antigravity.google/changelog",
                            fetch_antigravity_version))

    for tool, label, getter in version_sources:
        try:
            version = getter()
        except Exception as exc:  # noqa: BLE001
            failures.append((f"version/{label}", str(exc)))
            continue
        if not version:
            continue
        old = baseline_versions.get(tool)
        new_versions[tool] = version
        if old and old != version:
            level = ALERT_LEVEL.get(tool, "major")
            if version_key(old, level) != version_key(version, level):
                version_alerts.append((tool, label, old, version, level))
            else:
                version_notes.append((tool, old, version))

    # ---- 產生報告 ----
    has_update = bool(changes or version_alerts)
    lines = []

    if is_bootstrap or bootstrapped:
        lines.append("## 🌱 基準線建立")
        if is_bootstrap:
            lines.append("偵測到舊版 schema，已重新建立路徑基準線（本次不告警）。")
        for key, count in bootstrapped:
            lines.append(f"- `{key}`：納入監控，記錄 {count} 個路徑 token")
        lines.append("")

    if changes:
        lines.append("## 🚨 偵測到 AI 工具路徑異動")
        lines.append("")
        lines.append("偵測到官方來源中的候選路徑變動。請先判定它是正式機制、使用者自訂路徑、"
                     "文件範例或無關字串，再決定是否更新 `verification/CLAIMS.md` 與五個變體的 SKILL.md。")
        lines.append("")
        claims = load_claims()
        affected = {}      # claim id -> (claim, [觸發說明])
        orphan_tokens = []  # 帳本查無對應主張的新增路徑

        def _tag(token):
            hits = claims_for_token(token, claims)
            return "".join(f" `{c['id']}`" for c in hits), hits

        for tool, source, added, removed, text in changes:
            lines.append(f"### `{tool}` — {source}")
            lines.append("")
            for token in removed:
                tag, hits = _tag(token)
                lines.append(f"- ❌ **消失**：`{token}`" + (f" →{tag}" if tag else ""))
                for c in hits:
                    affected.setdefault(c["id"], (c, []))[1].append(f"`{token}` 消失")
            for token in added:
                context = context_for(text, token)
                tag, hits = _tag(token)
                lines.append(f"- ✅ **新增**：`{token}`" + (f" →{tag}" if tag else ""))
                if context:
                    lines.append(f"  > {context}")
                for c in hits:
                    affected.setdefault(c["id"], (c, []))[1].append(f"`{token}` 新增")
                if claims and not hits:
                    orphan_tokens.append(f"{tool}/{source}: `{token}`")
            lines.append("")

        if affected:
            lines.append("## 📒 受影響的帳本主張")
            lines.append("")
            lines.append("本次異動觸及下列已登記主張。**路徑消失代表原依據可能已不成立**，"
                         "請依 `verification/CLAIMS.md` 重新確認，必要時新增一列並將舊列標為「被取代」。")
            lines.append("")
            for cid, (claim, reasons) in sorted(affected.items()):
                lines.append(f"- **{cid}** `{claim['label']}` — 狀態 {claim['status']}"
                             f"，取證日 {claim['date']}")
                lines.append(f"  - 觸發：{'、'.join(sorted(set(reasons)))}")
                if claim["brief"]:
                    lines.append(f"  - 原主張：{claim['brief']}")
            lines.append("")

        if orphan_tokens:
            lines.append("## 🆕 帳本中查無對應主張的新路徑")
            lines.append("")
            lines.append("下列路徑不屬於任何已登記主張，只是待分類的候選訊號；"
                         "取得正式機制依據後，才決定是否新增帳本條目。")
            lines.append("")
            for item in orphan_tokens:
                lines.append(f"- {item}")
            lines.append("")

    if version_alerts:
        lines.append("## ⬆️ 版本跳動（機制可能重構）")
        lines.append("")
        for tool, label, old, new, level in version_alerts:
            scope = "主版號" if level == "major" else "次版號"
            lines.append(f"- **{tool}**：`{old}` → `{new}`（{scope}變動；來源 {label}）")
        lines.append("")
        if any(level == "major" for _tool, _label, _old, _new, level in version_alerts):
            lines.append("> ⚠️ **主版號跨越是低頻人工複驗訊號，不代表機制一定變更。** "
                         "請針對受影響工具重新確認官方文件與現行實機行為。")
            lines.append(">")
            lines.append("> 1. 比對受影響工具的既有主張與目前官方文件")
            lines.append("> 2. 執行 `python scripts/check_updates.py --coverage` 確認自動監控範圍與盲區")
            lines.append("> 3. 必要時依 `verification/rounds/TEMPLATE.md` 產生交接包並做實機複驗")
            lines.append("> 4. 獨立複驗完成後，才更新帳本或 skill 規則")
            lines.append("")

    if failures:
        lines.append("## ⚠️ 檢查失敗的來源")
        lines.append("")
        lines.append("以下來源本次未能取得，**不代表沒有異動**，基準線已保留待下次重試。")
        lines.append("")
        for label, reason in failures:
            lines.append(f"- `{label}`：{reason}")
        lines.append("")

    if not has_update and not failures and not (is_bootstrap or bootstrapped):
        total = sum(len(v.get("tokens", [])) for v in new_sources.values())
        lines.append("## ✅ 無異動")
        lines.append("")
        lines.append(f"已檢查 {len(SOURCES)} 個來源、比對 {total} 個路徑 token，全數與基準線相符。")
        lines.append("")

    if version_notes:
        lines.append("<details><summary>版本參考（非告警項）</summary>")
        lines.append("")
        lines.append("以下差異是相對上次有意義 baseline 的累積值；不會因這些版本變化單獨寫回基準線。")
        lines.append("")
        for tool, old, new in version_notes:
            lines.append(f"- {tool}: `{old}` → `{new}`")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    print("\n".join(lines).rstrip())

    # ---- 寫回基準線 ----
    payload = {"schema": SCHEMA_VERSION, "versions": new_versions,
               "sources": dict(sorted(new_sources.items()))}
    source_set_changed = set(new_sources) != set(baseline_sources)
    meaningful_baseline_change = (
        is_bootstrap or source_set_changed or bool(changes) or bool(version_alerts)
    )
    baseline_changed = meaningful_baseline_change and payload != raw_baseline
    if baseline_changed and not args.dry_run:
        # 明確指定 newline="\n"：本檔在 Windows 本機與 Linux runner 都會被寫入，
        # 不鎖死行尾的話 Windows 端會寫出 CRLF，與 .gitattributes 的 eol=lf 打架。
        with open(BASELINE_PATH, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=False)
            handle.write("\n")

    # ---- 給 CI grep 的訊號 ----
    print()
    if baseline_changed:
        print("[SIGNAL: BASELINE_CHANGED]")
    if has_update:
        print("[SIGNAL: UPDATE_DETECTED]")
    if failures:
        print("[SIGNAL: CHECK_FAILED]")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — 未預期例外也必須讓 CI 看得見
        import traceback
        print("## ❌ 檢查腳本未預期地中止\n")
        print("```")
        traceback.print_exc(file=sys.stdout)
        print("```")
        print("\n[SIGNAL: CHECK_FAILED]")
        sys.exit(1)
