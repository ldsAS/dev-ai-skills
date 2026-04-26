<#
.SYNOPSIS
  dev-ai-skills installer (Windows / PowerShell)

.DESCRIPTION
  Copies AI skills from this repo into the corresponding AI tool's skills directory.

  Supported AI tools:
    - Claude Code  : $env:USERPROFILE\.claude\skills\
    - Antigravity  : $env:USERPROFILE\.gemini\antigravity\skills\
    - Codex        : $env:USERPROFILE\.codex\skills\
    - VS Code (GitHub Copilot) : $env:USERPROFILE\.copilot\skills\

  Behaviour: COPY mode (not symlink). Re-run after git pull to sync updates.

.PARAMETER Mode
  auto         (default) Install each skill's tool-specific variant to all detected AI tools
  claude       Only install claude/ variant to ~/.claude/skills/
  antigravity  Only install antigravity/ variant to ~/.gemini/antigravity/skills/
  codex        Only install codex/ variant to ~/.codex/skills/
  vscode       Only install vscode/ variant to ~/.copilot/skills/ (GitHub Copilot in VS Code)
  generic      Install generic/ variant to all detected AI tool dirs (fallback)

.EXAMPLE
  .\install.ps1
  .\install.ps1 claude
  .\install.ps1 codex
  .\install.ps1 vscode
  .\install.ps1 generic
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet('auto', 'claude', 'antigravity', 'codex', 'vscode', 'generic')]
    [string]$Mode = 'auto'
)

$ErrorActionPreference = 'Stop'

# ---- paths ----------------------------------------------------------
$ScriptDir         = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillsDir         = Join-Path $ScriptDir 'skills'
$ClaudeTarget      = Join-Path $env:USERPROFILE '.claude\skills'
$AntigravityTarget = Join-Path $env:USERPROFILE '.gemini\antigravity\skills'
$CodexTarget       = Join-Path $env:USERPROFILE '.codex\skills'
$VSCodeTarget      = Join-Path $env:USERPROFILE '.copilot\skills'

function Write-Info  { param($msg) Write-Host "[info] $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "[ ok ] $msg" -ForegroundColor Green }
function Write-Warn2 { param($msg) Write-Host "[warn] $msg" -ForegroundColor Yellow }
function Write-Err2  { param($msg) Write-Host "[err ] $msg" -ForegroundColor Red }

# ---- detection ------------------------------------------------------
$HasClaude      = Test-Path (Join-Path $env:USERPROFILE '.claude')
$HasAntigravity = Test-Path (Join-Path $env:USERPROFILE '.gemini\antigravity')
$HasCodex       = Test-Path (Join-Path $env:USERPROFILE '.codex')
$HasVSCode      = (Get-Command code -ErrorAction SilentlyContinue) -ne $null

Write-Info '偵測到的 AI 工具：'
if ($HasClaude)      { Write-Ok    "Claude Code       → $ClaudeTarget" }      else { Write-Warn2 'Claude Code       → 未偵測到 ~/.claude' }
if ($HasAntigravity) { Write-Ok    "Antigravity       → $AntigravityTarget" } else { Write-Warn2 'Antigravity       → 未偵測到 ~/.gemini/antigravity' }
if ($HasCodex)       { Write-Ok    "Codex             → $CodexTarget" }       else { Write-Warn2 'Codex             → 未偵測到 ~/.codex' }
if ($HasVSCode)      { Write-Ok    "VS Code Copilot   → $VSCodeTarget" }      else { Write-Warn2 'VS Code Copilot   → 未偵測到 code 指令，仍可用 vscode 模式強制安裝' }

if (-not $HasClaude -and -not $HasAntigravity -and -not $HasCodex -and -not $HasVSCode) {
    Write-Err2 '沒有偵測到任何支援的 AI 工具。請先安裝 Claude Code、Antigravity、Codex 或 VS Code。'
    exit 1
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

    Write-Ok "  └ $skillName ($Variant) → $dst"
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

# ---- main -----------------------------------------------------------
switch ($Mode) {
    'auto' {
        if ($HasClaude)      { Install-AllForTool -Tool 'claude'      -Target $ClaudeTarget }
        if ($HasAntigravity) { Install-AllForTool -Tool 'antigravity' -Target $AntigravityTarget }
        if ($HasCodex)       { Install-AllForTool -Tool 'codex'       -Target $CodexTarget }
        if ($HasVSCode)      { Install-AllForTool -Tool 'vscode'      -Target $VSCodeTarget }
    }
    'claude' {
        if (-not $HasClaude) { Write-Err2 '未偵測到 ~/.claude/'; exit 1 }
        Install-AllForTool -Tool 'claude' -Target $ClaudeTarget
    }
    'antigravity' {
        if (-not $HasAntigravity) { Write-Err2 '未偵測到 ~/.gemini/antigravity/'; exit 1 }
        Install-AllForTool -Tool 'antigravity' -Target $AntigravityTarget
    }
    'codex' {
        if (-not $HasCodex) { Write-Err2 '未偵測到 ~/.codex/'; exit 1 }
        Install-AllForTool -Tool 'codex' -Target $CodexTarget
    }
    'vscode' {
        # ~/.copilot/skills/ 是 VS Code Copilot 原生掃描的個人 skill 目錄
        # 不強制要求 code 指令存在，允許手動指定路徑情境
        Install-AllForTool -Tool 'vscode' -Target $VSCodeTarget
    }
    'generic' {
        if ($HasClaude)      { Install-AllForTool -Tool 'claude'      -Target $ClaudeTarget      -ForceVariant 'generic' }
        if ($HasAntigravity) { Install-AllForTool -Tool 'antigravity' -Target $AntigravityTarget -ForceVariant 'generic' }
        if ($HasCodex)       { Install-AllForTool -Tool 'codex'       -Target $CodexTarget       -ForceVariant 'generic' }
    }
}

Write-Host ''
Write-Ok '全部完成！'
