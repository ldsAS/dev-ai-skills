<#
.SYNOPSIS
  dev-ai-skills installer (Windows / PowerShell)

.DESCRIPTION
  Copies AI skills from this repo into the corresponding AI tool's skills directory.

  Supported AI tools (see README "安裝邏輯" for the authoritative path map):
    - Claude Code      : $env:USERPROFILE\.claude\skills\
    - Antigravity CLI  : $env:USERPROFILE\.gemini\config\skills\
    - Antigravity IDE  : $env:USERPROFILE\.gemini\antigravity\skills\
    - Codex            : $env:USERPROFILE\.agents\skills\   (official USER scope)
    - Gemini CLI       : $env:USERPROFILE\.agents\skills\   (same copy, not installed separately)
    - VS Code (Copilot): $env:USERPROFILE\.agents\skills\   (same copy, not installed separately)

  Legacy-compat paths, never created — only refreshed when a copy is already there:
    - $env:USERPROFILE\.codex\skills\      (absent from Codex's official scope table)
    - $env:USERPROFILE\.copilot\skills\    (Copilot also reads ~\.agents\skills)

  Behaviour: COPY mode (not symlink). Re-run after git pull to sync updates.

.PARAMETER Mode
  auto         (default) Install each skill's tool-specific variant to all detected AI tools
  claude       Only install claude/ variant to ~/.claude/skills/
  antigravity  Install antigravity/ variant to BOTH global paths:
               ~/.gemini/config/skills/ (CLI) and ~/.gemini/antigravity/skills/ (IDE)
  codex        Install to ~/.agents/skills/ (official USER path, generic variant);
               ~/.codex/skills/ only if a copy is already installed there
  vscode       Only install vscode/ variant to ~/.copilot/skills/ (GitHub Copilot in VS Code)
  generic      Install generic/ variant to all detected AI tool dirs (fallback)
  project      Install ONE copy into <ProjectPath>\.agents\skills\ (cross-tool path)

.PARAMETER ProjectPath
  Target repo for 'project' mode. Defaults to the current directory.

.EXAMPLE
  .\install.ps1
  .\install.ps1 claude
  .\install.ps1 codex
  .\install.ps1 vscode
  .\install.ps1 generic
  .\install.ps1 project
  .\install.ps1 project C:\path	oepo
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet('auto', 'claude', 'antigravity', 'codex', 'vscode', 'generic', 'project')]
    [string]$Mode = 'auto',

    [Parameter(Position = 1)]
    [string]$ProjectPath = ''
)

$ErrorActionPreference = 'Stop'

# ---- paths ----------------------------------------------------------
$ScriptDir         = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillsDir         = Join-Path $ScriptDir 'skills'
$ClaudeTarget        = Join-Path $env:USERPROFILE '.claude\skills'
$AntigravityTargetV2 = Join-Path $env:USERPROFILE '.gemini\config\skills'       # Antigravity CLI 全域
$AntigravityTargetV1 = Join-Path $env:USERPROFILE '.gemini\antigravity\skills'  # Antigravity IDE 全域
# 官方 skills scope 表（2026-08-03）列的 USER 路徑是 $HOME/.agents/skills（C-12），
# 該路徑亦為 Gemini CLI（C-22）與 Copilot（C-77）的使用者層技能位置 —— 一份共用。
# .codex\skills 未出現於官方表中：2026-08-04 起降為「已裝過才續寫」的相容路徑，
# 不再主動建立（判準見下方 Test-SkillInstalledIn）。2026-08-09 由 Codex 實機確認：
# 刪除該處複本後技能仍從 ~\.agents\skills 正常載入，未消失（C-85）。
$CodexTarget         = Join-Path $env:USERPROFILE '.codex\skills'   # 舊版相容（不主動建立）
$AgentsTarget        = Join-Path $env:USERPROFILE '.agents\skills'  # 官方 USER 路徑（跨工具）
$VSCodeTarget        = Join-Path $env:USERPROFILE '.copilot\skills'

function Write-Info  { param($msg) Write-Host "[info] $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "[ ok ] $msg" -ForegroundColor Green }
function Write-Warn2 { param($msg) Write-Host "[warn] $msg" -ForegroundColor Yellow }
function Write-Err2  { param($msg) Write-Host "[err ] $msg" -ForegroundColor Red }

# 相容路徑的判準是「該目錄裡已經有本專案裝過的技能」，**不是「目錄存在」**。
# ~/.codex/skills 底下有 Codex 內建的 .system/，該目錄永遠存在；用「目錄存在」
# 當判準的話，使用者手動刪掉的舊複本會在下次安裝時復活。
function Test-SkillInstalledIn {
    param([string]$Target)
    if (-not (Test-Path $Target)) { return $false }
    foreach ($d in Get-ChildItem -Path $SkillsDir -Directory) {
        if (Test-Path (Join-Path $Target $d.Name)) { return $true }
    }
    return $false
}

# ---- detection ------------------------------------------------------
$HasClaude        = Test-Path (Join-Path $env:USERPROFILE '.claude')
# 兩條全域路徑都要寫，它們屬於不同產品，不是新舊關係（官方文件明載）：
#   Antigravity IDE → .gemini\antigravity\skills   (/docs/ide/skills)
#   Antigravity CLI → .gemini\config\skills        (/docs/skills)
# 2026-07-30 曾誤判為新舊關係而改成 fallback，導致 IDE 端失效；2026-08-03 已還原。見 C-48。
$HasAntigravityV1 = Test-Path (Join-Path $env:USERPROFILE '.gemini\antigravity')
$HasAntigravityV2 = Test-Path (Join-Path $env:USERPROFILE '.gemini\config')
$HasCodex         = Test-Path (Join-Path $env:USERPROFILE '.codex')
$HasGeminiCli     = ((Get-Command gemini -ErrorAction SilentlyContinue) -ne $null)
# P1-2a：下列兩條沒有官方依據 —— .codex\skills 未見於 Codex 官方 scope 表（C-12），
# 而 Copilot 亦讀 ~/.agents/skills（C-77）。降為相容模式：只續寫已經裝過的目錄，
# 不主動建立（判準見上方 Test-SkillInstalledIn 的說明）。
$HasCodexLegacy   = Test-SkillInstalledIn $CodexTarget
$HasVSCodeLegacy  = Test-SkillInstalledIn $VSCodeTarget
$HasVSCode        = ((Get-Command code -ErrorAction SilentlyContinue) -ne $null) -or (Test-Path (Join-Path $env:USERPROFILE '.copilot'))
$NeedsAgentsTarget = $HasCodex -or $HasGeminiCli -or $HasVSCode

# project 模式是專案層安裝，不依賴任何全域工具目錄 —— 跳過偵測與「找不到工具」的中止
if ($Mode -ne 'project') {

Write-Info '偵測到的 AI 工具：'
if ($HasClaude)        { Write-Ok    "Claude Code       → $ClaudeTarget" }        else { Write-Warn2 'Claude Code       → 未偵測到 ~/.claude' }
if ($HasAntigravityV2) { Write-Ok    "Antigravity CLI   → $AntigravityTargetV2" } else { Write-Warn2 'Antigravity CLI   → 未偵測到 ~/.gemini/config' }
if ($HasAntigravityV1) { Write-Ok    "Antigravity IDE   → $AntigravityTargetV1" } else { Write-Warn2 'Antigravity IDE   → 未偵測到 ~/.gemini/antigravity' }
if ($HasCodex)         { Write-Ok    "Codex             → $AgentsTarget" }        else { Write-Warn2 'Codex             → 未偵測到 ~/.codex' }
if ($HasGeminiCli)     { Write-Ok    "Gemini CLI        → 經 $AgentsTarget" }      else { Write-Warn2 'Gemini CLI        → 未偵測到 gemini 指令' }
if ($HasCodexLegacy)   { Write-Warn2 "  └ 相容路徑       → $CodexTarget（已裝過才續寫，不主動建立）" }
if ($HasVSCodeLegacy)  { Write-Warn2 "  └ 相容路徑       → $VSCodeTarget（已裝過才續寫，不主動建立）" }
if ($HasVSCode)        { Write-Ok    "VS Code Copilot   → 經 $AgentsTarget（Copilot 亦讀此路徑）" } else { Write-Warn2 'VS Code Copilot   → 未偵測到 code 指令或 ~/.copilot，仍可用 vscode 模式強制安裝' }

if (-not $HasClaude -and -not $HasAntigravityV1 -and -not $HasAntigravityV2 -and -not $HasCodex -and -not $HasGeminiCli -and -not $HasVSCode) {
    Write-Err2 '沒有偵測到任何支援的 AI 工具。請先安裝 Claude Code、Antigravity、Codex、Gemini CLI 或 VS Code。'
    exit 1
}

}

# ---- install one skill variant to one target -----------------------
function Install-SkillVariant {
    param(
        [string]$SkillDir,   # e.g. C:\repo\skills\ai-git-ignore-strategy
        [string]$Variant,    # antigravity | claude | generic
        [string]$Target      # e.g. C:\Users\X\.claude\skills
    )
    $skillName = Split-Path -Leaf $SkillDir
    $src       = Join-Path $SkillDir $Variant
    $dst       = Join-Path $Target $skillName

    if (-not (Test-Path $src)) { return $false }

    if (-not (Test-Path $Target)) { New-Item -ItemType Directory -Path $Target -Force | Out-Null }
    if (Test-Path $dst)           { Remove-Item -Path $dst -Recurse -Force }
    New-Item -ItemType Directory -Path $dst -Force | Out-Null
    Copy-Item -Path "$src\*" -Destination $dst -Recurse -Force

    # Copy-Item 成功不代表內容一定一致；安裝完成當下立即做 byte-level 雜湊驗證。
    # 這只能保證「此刻」同步，若之後再修改 source，仍必須重新執行安裝器。
    $srcSkill = Join-Path $src 'SKILL.md'
    $dstSkill = Join-Path $dst 'SKILL.md'
    if (-not (Test-Path $dstSkill)) {
        throw "安裝驗證失敗：找不到 $dstSkill"
    }
    $srcHash = (Get-FileHash -LiteralPath $srcSkill -Algorithm SHA256).Hash
    $dstHash = (Get-FileHash -LiteralPath $dstSkill -Algorithm SHA256).Hash
    if ($srcHash -ne $dstHash) {
        throw "安裝驗證失敗：$srcSkill 與 $dstSkill 的 SHA256 不一致"
    }

    Write-Ok "  └ $skillName ($Variant) → $dst [SHA256 $($srcHash.Substring(0, 12))]"
    return $true
}

# ---- install all skills for a given tool ----------------------------
function Install-AllForTool {
    param(
        [string]$Tool,            # antigravity | claude | codex
        [string]$Target,
        [string]$ForceVariant = ''
    )
    Write-Info "安裝到 $Tool ($Target) ..."
    $count = 0
    Get-ChildItem -Path $SkillsDir -Directory | ForEach-Object {
        $skillDir = $_.FullName
        $variant  = if ($ForceVariant) { $ForceVariant } else { $Tool }

        if (Install-SkillVariant -SkillDir $skillDir -Variant $variant -Target $Target) {
            $count++
        } elseif (-not $ForceVariant -and (Install-SkillVariant -SkillDir $skillDir -Variant 'generic' -Target $Target)) {
            $count++
            Write-Warn2 "    ↑ 找不到 $variant 版本，已 fallback 到 generic"
        } else {
            Write-Warn2 "  └ $($_.Name)：找不到 $variant 版本，略過"
        }
    }
    Write-Ok "完成：$count 個 skill 已安裝到 $Tool"
}

# ---- project-scoped install -----------------------------------------
# 只寫 <repo>\.agents\skills\ 一條路徑、一份複製 —— 與上游 uipro init --ai universal 同作法。
# 不逐工具各裝一份：.agents\skills 已同時被 Codex、Gemini CLI、Copilot、Antigravity
# 讀取（C-13、C-22、C-60、C-77），分開裝只會製造多份會各自過期的複本。
function Install-Project {
    param([string]$Root)

    if (-not $Root) { $Root = (Get-Location).Path }
    if (-not (Test-Path $Root)) { Write-Err2 "找不到目錄：$Root"; exit 1 }
    $Root = (Resolve-Path $Root).Path

    $inGit = $false
    & git -C $Root rev-parse --show-toplevel *> $null
    if ($LASTEXITCODE -eq 0) { $inGit = $true }
    if (-not $inGit) { Write-Warn2 "$Root 不是 git repo；安裝照做，但下方的 .gitignore 提示要 git init 之後才有意義" }

    Install-AllForTool -Tool 'project' -Target (Join-Path $Root '.agents\skills') -ForceVariant 'generic'

    Write-Host ''
    Write-Info '還有兩件事要手動做：'
    Write-Host ''
    Write-Host '  1. 在專案 .gitignore 放行剛裝的技能'
    Write-Host '     本 skill 自己的範本會擋掉 .agents/skills/* —— 不放行的話它會把自己藏起來：'
    Write-Host ''
    Get-ChildItem -Path $SkillsDir -Directory | ForEach-Object {
        Write-Host "       !.agents/skills/$($_.Name)/"
        Write-Host "       !.agents/skills/$($_.Name)/**"
    }
    Write-Host ''
    Write-Host '     驗證：git check-ignore --no-index -v -- .agents/skills/<name>/SKILL.md'
    Write-Host '     （輸出以 ! 開頭＝已放行；無輸出＝沒被任何規則命中，也算放行）'
    Write-Host ''
    Write-Host '  2. 在專案 AGENTS.md 寫明什麼時候要用它'
    Write-Host '     專案層技能不該只靠觸發詞被撞到，講清楚使用時機比較可靠：'
    Write-Host ''
    Write-Host '       ## 專案技能'
    Write-Host '       - 要調整 .gitignore／.gitattributes，或 commit 前要確認哪些檔案會被提交時，'
    Write-Host '         使用 .agents/skills/ai-git-ignore-strategy/'
    Write-Host ''
    if ($inGit) { Write-Ok "專案層安裝完成：$Root\.agents\skills\" }
}

# ---- main -----------------------------------------------------------
switch ($Mode) {
    'auto' {
        if ($HasClaude)        { Install-AllForTool -Tool 'claude'      -Target $ClaudeTarget }
        if ($HasAntigravityV2) { Install-AllForTool -Tool 'antigravity' -Target $AntigravityTargetV2 }
        if ($HasAntigravityV1) { Install-AllForTool -Tool 'antigravity' -Target $AntigravityTargetV1 }
        # 共用路徑放 generic：Codex、Gemini CLI、Copilot 任一存在就寫入一次（C-79）
        if ($NeedsAgentsTarget) { Install-AllForTool -Tool 'shared'      -Target $AgentsTarget -ForceVariant 'generic' }
        if ($HasCodexLegacy)   { Install-AllForTool -Tool 'codex'       -Target $CodexTarget }
        if ($HasVSCodeLegacy)  { Install-AllForTool -Tool 'vscode'      -Target $VSCodeTarget }
    }
    'claude' {
        if (-not $HasClaude) { Write-Err2 '未偵測到 ~/.claude/'; exit 1 }
        Install-AllForTool -Tool 'claude' -Target $ClaudeTarget
    }
    'antigravity' {
        if (-not $HasAntigravityV1 -and -not $HasAntigravityV2) {
            Write-Err2 '未偵測到 ~/.gemini/config/ 或 ~/.gemini/antigravity/'; exit 1
        }
        if ($HasAntigravityV2) { Install-AllForTool -Tool 'antigravity' -Target $AntigravityTargetV2 }
        if ($HasAntigravityV1) { Install-AllForTool -Tool 'antigravity' -Target $AntigravityTargetV1 }
    }
    'codex' {
        if (-not $HasCodex) { Write-Err2 '未偵測到 ~/.codex/'; exit 1 }
        Install-AllForTool -Tool 'codex' -Target $AgentsTarget -ForceVariant 'generic'
        if ($HasCodexLegacy) { Install-AllForTool -Tool 'codex' -Target $CodexTarget }
    }
    'vscode' {
        # ~/.copilot/skills/ 是 VS Code Copilot 原生掃描的個人 skill 目錄
        # 不強制要求 code 指令存在，允許手動指定路徑情境
        Install-AllForTool -Tool 'vscode' -Target $VSCodeTarget   # 明確指定 vscode 模式時仍寫
    }
    'project' {
        Install-Project -Root $ProjectPath
    }
    'generic' {
        if ($HasClaude)        { Install-AllForTool -Tool 'claude'      -Target $ClaudeTarget        -ForceVariant 'generic' }
        if ($HasAntigravityV2) { Install-AllForTool -Tool 'antigravity' -Target $AntigravityTargetV2 -ForceVariant 'generic' }
        if ($HasAntigravityV1) { Install-AllForTool -Tool 'antigravity' -Target $AntigravityTargetV1 -ForceVariant 'generic' }
        if ($NeedsAgentsTarget) { Install-AllForTool -Tool 'shared'      -Target $AgentsTarget        -ForceVariant 'generic' }
        if ($HasCodexLegacy)   { Install-AllForTool -Tool 'codex'       -Target $CodexTarget         -ForceVariant 'generic' }
        if ($HasVSCodeLegacy)  { Install-AllForTool -Tool 'vscode'      -Target $VSCodeTarget        -ForceVariant 'generic' }
    }
}

Write-Host ''
Write-Ok '全部完成！'
