---
name: ai-git-ignore-strategy
description: Review, design, fix, or clean up Git tracking rules for Codex workspaces, including .gitignore, .gitattributes, AI agent folders, local Codex skills, runtime logs, line-ending noise, file mode drift, and commit-before-push hygiene. Use when the user asks in Chinese or English to "檢核 gitignore", "整理 repo", "commit 前審查", "清理 AI 追蹤紀錄", "行尾 CRLF 問題", "0 byte diff", "file mode 漂移", or similar Git hygiene requests while working in Codex.
---

# AI Git Ignore Strategy for Codex

Use this skill when the user asks Codex to inspect or fix `.gitignore`, `.gitattributes`, repo cleanliness, AI agent workspaces, runtime logs, line-ending drift, file mode drift, or commit hygiene before pushing.

Core principle: do not blindly ignore everything that looks AI-generated. Read or list it first, infer its purpose, then separate project assets from local session/cache data.

## Codex Operating Rules

- Prefer `rg` / `rg --files` for search. Fall back only if unavailable.
- Use `multi_tool_use.parallel` for independent reads such as `git status`, `git diff`, `Get-Content`, `rg`, and directory listings.
- Use `apply_patch` for edits inside the current writable workspace.
- If the target repo root, `.git` directory, or installed skill folder is outside the sandbox, use `functions.shell_command` with `sandbox_permissions: "require_escalated"` and a clear justification.
- If an important command fails because of sandbox or network restrictions, rerun the same command with escalation instead of working around the approval flow.
- Do not use `git add .` unless the entire worktree has been reviewed and the user explicitly agrees. Stage exact paths.
- Never revert unrelated user changes. Work with dirty trees; identify unrelated runtime or user changes separately.
- Push only when the user clearly asks for it in the current task.
- On Windows + SSHFS projects, treat mode-only diffs as environment noise until proven otherwise.

Codex user skills normally live at `$env:USERPROFILE\.codex\skills\<skill-name>\SKILL.md` on Windows, or `~/.codex/skills/<skill-name>/SKILL.md` on Unix-like systems. Project-local `.codex/skills/` folders may be intentionally tracked only when they contain project-owned custom skills.

## Diagnose First

Read repo rules and Git state before changing ignore rules:

```powershell
Get-Content .gitignore -ErrorAction SilentlyContinue
Get-Content .gitattributes -ErrorAction SilentlyContinue
git status --short
git ls-files
git diff --stat
git diff --summary
git log --oneline -10
```

For suspicious ignored paths, check which rule applies:

```powershell
git check-ignore -v <path>
```

If `git status` shows many modified files but `git diff --stat` shows `0 insertions, 0 deletions`, run:

```powershell
git diff --summary
git config --get core.fileMode
```

For Windows + SSHFS mode drift, compare with temporary file mode tracking disabled:

```powershell
git -c core.fileMode=false status --short
git -c core.fileMode=false diff --summary
```

If Git reports `index file corrupt`, pause and explain that the index must be repaired before normal status/diff review. Do not treat it as a normal file-change problem.

## Classify Files

Create a concise report with these groups before changing rules unless the user already asked for direct execution and the classification is low risk.

### Keep And Commit

- Source code: `.py`, `.html`, `.css`, `.js`, `.ts`, `.sh`, `.bat`, `.ps1`.
- Documentation and operations: `README.md`, `DEPLOY.md`, `docs/`, `CHANGELOG.md`.
- Cross-platform repo policy: `.gitattributes`, `.editorconfig`, `.nvmrc`.
- Project automation references: exported task XML, systemd service samples, Docker/CI config.
- Project design source of truth: `design-system/MASTER.md`, relevant page overrides.
- Team AI instructions: `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.github/copilot-instructions.md`, or project-specific skill files explicitly meant to be shared.
- Custom project skills: for example `.codex/skills/<project-skill>/SKILL.md`, only after confirming it is not merely a local installed third-party skill.

### Ignore Or Untrack

- Local AI workspaces and caches: `.agent/`, `.claude/`, `.codex/`, `.gemini/`, `.cursor/`, `.github/prompts/`, except confirmed project skills.
- Runtime logs: `*.log`, `*.jsonl`, such as `audit_log.jsonl`, `line_notify.log`, `cron.log`, `holiday.log`.
- Runtime state: `last_run.txt`, `last_holiday_scan.txt`, `last_download_run.txt`, `*.pid`, `*.lock`.
- Secrets: `.env`, `.env.*` except `!.env.example`, `*.pem`, `*.key`, `credentials.json`, `certs/`.
- Dependencies/build output: `venv/`, `.venv/`, `node_modules/`, `__pycache__/`, `dist/`, `build/`, `target/`.
- Large generated/binary artifacts unless intentionally tracked through Git LFS or as deployment references.

### Ask Before Deciding

- `.codex/skills/`, `.claude/skills/`, `.gemini/skills/`: installed third-party skill or project-owned custom skill?
- `$env:USERPROFILE\.codex\skills\` / `~/.codex/skills/`: user-level Codex skill installation; usually do not copy this wholesale into a project repo.
- `*.json`: runtime data or source/config such as `package.json`, `tsconfig.json`, `manifest.json`?
- `*.json.bak`: disposable backup or only recoverable data copy referenced by deployment docs?
- `.vscode/`: personal settings or shared `extensions.json` / `launch.json`?
- Large PDFs, XML, exports: deployment reference or stale snapshot?

## Report Shape

Use a compact table:

```markdown
## Git Tracking Review

### Keep
| Path | Reason |
| :--- | :--- |

### Ignore Or Untrack
| Path | Reason | Action |
| :--- | :--- | :--- |

### Needs Confirmation
| Path | Question |
| :--- | :--- |
```

## Execute Safely

When the classification is confirmed or the user already asked for a direct safe fix:

1. Edit `.gitignore` and `.gitattributes` with minimal changes.
2. For files already tracked but now ignored, remove from the index only:

```powershell
git rm --cached <path>
git rm --cached -r <dir>
```

3. Stage exact files:

```powershell
git add .gitignore .gitattributes DEPLOY.md
```

4. Before commit, inspect staged content:

```powershell
git status --short
git diff --cached --stat
git diff --cached --summary
git diff --cached --name-only
```

5. Split commits by concern: functional changes, ignore cleanup, line-ending normalization, and mode cleanup should not be mixed.

## Recommended .gitattributes

Use LF by default for Linux-deployed projects, with CRLF retained for Windows scripts:

```text
* text=auto eol=lf

*.bat  text eol=crlf
*.cmd  text eol=crlf
*.ps1  text eol=crlf
*.vbs  text eol=crlf

*.pdf          binary
*.png          binary
*.jpg          binary
*.jpeg         binary
*.ico          binary
*.woff         binary
*.woff2        binary
```

Apply normalization only as its own commit:

```powershell
git add --renormalize .
git status --short
git diff --cached --stat
git commit -m "chore: normalize line endings"
```

## Recommended .gitignore Starting Point

Adapt this, do not paste blindly:

```gitignore
# Environment and secrets
.env
.env.*
!.env.example
*.pem
*.key
credentials.json
certs/

# Dependencies and build outputs
venv/
.venv/
node_modules/
__pycache__/
*.pyc
dist/
build/
target/

# OS and editor noise
.DS_Store
Thumbs.db
.idea/
.vscode/settings.json

# AI agent local workspaces
.agent/
.claude/
.codex/
.gemini/
.cursor/
.github/prompts/

# Runtime logs and local state
*.log
*.jsonl
*.pid
*.lock
last_run.txt
last_holiday_scan.txt
last_download_run.txt
```

If project-owned Codex skills should be tracked, use an allowlist instead of ignoring all `.codex/`:

```gitignore
.codex/*
!.codex/skills/
!.codex/skills/<project-skill>/
!.codex/skills/<project-skill>/**
```

## File Mode Drift

On Windows + SSHFS, `git diff --summary` may show only `mode change 100644 => 100755` or the reverse. If content is unchanged, prefer:

```powershell
git config core.fileMode false
```

If `.git/config` cannot be locked because of permissions, use temporary diagnostics:

```powershell
git -c core.fileMode=false status --short
git -c core.fileMode=false diff --summary
```

For a few files, index-only correction is acceptable:

```powershell
git update-index --chmod=-x <file>
git update-index --chmod=+x <file>
```

## Rescue Commands

If AI workspace or runtime log files are already tracked:

```powershell
git rm -r --cached .agent .claude .codex .gemini .cursor .github/prompts
git rm --cached *.log *.jsonl
git add .gitignore .gitattributes
git diff --cached --stat
git diff --cached --summary
git commit -m "chore: clean AI workspace and runtime git tracking"
```

If sensitive or huge files were already pushed, explain the risk first and ask before rewriting history with tools such as `git filter-repo`.
