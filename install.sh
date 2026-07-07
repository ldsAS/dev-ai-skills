#!/usr/bin/env bash
# dev-ai-skills installer (Linux / macOS)
#
# Usage:
#   ./install.sh                 # auto-detect installed AI tools and install all matching variants
#   ./install.sh claude          # only install claude/ variant to ~/.claude/skills/
#   ./install.sh antigravity     # only install antigravity/ variant to ~/.gemini/config/skills/ (2.0)
#                                #   and/or ~/.gemini/antigravity/skills/ (1.x), whichever is detected
#   ./install.sh codex           # only install codex/ variant to ~/.codex/skills/
#   ./install.sh vscode          # only install vscode/ variant to ~/.copilot/skills/ (GitHub Copilot)
#   ./install.sh generic         # install generic/ variant to all detected AI tool dirs (fallback)
#   ./install.sh --help          # show this help
#
# Behaviour: COPY mode (not symlink). Re-run after git pull to sync updates.

set -euo pipefail

# ---- colour helpers -------------------------------------------------
if [[ -t 1 ]]; then
  C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_OK=$'\033[32m'; C_INFO=$'\033[36m'; C_WARN=$'\033[33m'; C_ERR=$'\033[31m'
else
  C_RESET=''; C_BOLD=''; C_OK=''; C_INFO=''; C_WARN=''; C_ERR=''
fi
info()  { printf '%s[info]%s %s\n' "$C_INFO" "$C_RESET" "$*"; }
ok()    { printf '%s[ ok ]%s %s\n' "$C_OK"   "$C_RESET" "$*"; }
warn()  { printf '%s[warn]%s %s\n' "$C_WARN" "$C_RESET" "$*"; }
err()   { printf '%s[err ]%s %s\n' "$C_ERR"  "$C_RESET" "$*" >&2; }

# ---- paths ----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$SCRIPT_DIR/skills"
CLAUDE_TARGET="$HOME/.claude/skills"
ANTIGRAVITY_TARGET_V2="$HOME/.gemini/config/skills"       # Antigravity 2.0
ANTIGRAVITY_TARGET_V1="$HOME/.gemini/antigravity/skills"  # Antigravity 1.x
CODEX_TARGET="$HOME/.codex/skills"
VSCODE_TARGET="$HOME/.copilot/skills"

MODE="${1:-auto}"

show_help() {
  sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}
[[ "$MODE" == "--help" || "$MODE" == "-h" ]] && show_help

# ---- detection ------------------------------------------------------
has_claude=false
has_antigravity_v1=false
has_antigravity_v2=false
has_codex=false
has_vscode=false
[[ -d "$HOME/.claude" ]]              && has_claude=true
[[ -d "$HOME/.gemini/antigravity" ]]  && has_antigravity_v1=true
[[ -d "$HOME/.gemini/config" ]]       && has_antigravity_v2=true
[[ -d "$HOME/.codex" ]]               && has_codex=true
{ command -v code >/dev/null 2>&1 || [[ -d "$HOME/.copilot" ]]; } && has_vscode=true

info "偵測到的 AI 工具："
$has_claude         && ok "Claude Code       → $CLAUDE_TARGET"         || warn "Claude Code       → 未偵測到 ~/.claude"
$has_antigravity_v2 && ok "Antigravity 2.0   → $ANTIGRAVITY_TARGET_V2" || warn "Antigravity 2.0   → 未偵測到 ~/.gemini/config"
$has_antigravity_v1 && ok "Antigravity 1.x   → $ANTIGRAVITY_TARGET_V1" || warn "Antigravity 1.x   → 未偵測到 ~/.gemini/antigravity"
$has_codex          && ok "Codex             → $CODEX_TARGET"          || warn "Codex             → 未偵測到 ~/.codex"
$has_vscode         && ok "VS Code Copilot   → $VSCODE_TARGET"         || warn "VS Code Copilot   → 未偵測到 code 指令或 ~/.copilot，仍可用 vscode 模式強制安裝"

if ! $has_claude && ! $has_antigravity_v1 && ! $has_antigravity_v2 && ! $has_codex && ! $has_vscode; then
  err "沒有偵測到任何支援的 AI 工具。請先安裝 Claude Code、Antigravity、Codex 或 VS Code (Copilot)。"
  exit 1
fi

# ---- install one skill to one target -------------------------------
install_skill_variant() {
  local skill_dir="$1"   # e.g. /repo/skills/ai-git-ignore-strategy
  local variant="$2"     # antigravity | claude | generic
  local target="$3"      # e.g. ~/.claude/skills

  local skill_name; skill_name="$(basename "$skill_dir")"
  local src="$skill_dir/$variant"
  local dst="$target/$skill_name"

  if [[ ! -d "$src" ]]; then
    return 1
  fi

  mkdir -p "$target"
  rm -rf "$dst"
  mkdir -p "$dst"
  cp -r "$src"/. "$dst"/
  ok "  └ $skill_name ($variant) → $dst"
  return 0
}

# ---- install all skills to a given tool -----------------------------
install_all_for_tool() {
  local tool="$1"        # antigravity | claude | codex
  local target="$2"
  local force_variant="${3:-}"   # if set, forces this variant (e.g. "generic")

  info "安裝到 $tool ($target) ..."

  local count=0
  for skill_dir in "$SKILLS_DIR"/*/; do
    [[ -d "$skill_dir" ]] || continue
    skill_dir="${skill_dir%/}"

    local variant="${force_variant:-$tool}"
    if install_skill_variant "$skill_dir" "$variant" "$target"; then
      count=$((count+1))
    else
      # fallback chain: tool-specific → generic
      if [[ -z "$force_variant" ]] && install_skill_variant "$skill_dir" "generic" "$target"; then
        count=$((count+1))
        warn "    ↑ 找不到 $variant 版本，已 fallback 到 generic"
      else
        warn "  └ $(basename "$skill_dir")：找不到 $variant 版本，略過"
      fi
    fi
  done
  ok "完成：$count 個 skill 已安裝到 $tool"
}

# ---- main -----------------------------------------------------------
case "$MODE" in
  auto|"")
    $has_claude         && install_all_for_tool "claude"      "$CLAUDE_TARGET"
    $has_antigravity_v2 && install_all_for_tool "antigravity" "$ANTIGRAVITY_TARGET_V2"
    $has_antigravity_v1 && install_all_for_tool "antigravity" "$ANTIGRAVITY_TARGET_V1"
    $has_codex          && install_all_for_tool "codex"       "$CODEX_TARGET"
    $has_vscode         && install_all_for_tool "vscode"      "$VSCODE_TARGET"
    ;;
  claude)
    if ! $has_claude; then err "未偵測到 ~/.claude/"; exit 1; fi
    install_all_for_tool "claude" "$CLAUDE_TARGET"
    ;;
  antigravity)
    if ! $has_antigravity_v1 && ! $has_antigravity_v2; then
      err "未偵測到 ~/.gemini/config/ (2.0) 或 ~/.gemini/antigravity/ (1.x)"; exit 1
    fi
    $has_antigravity_v2 && install_all_for_tool "antigravity" "$ANTIGRAVITY_TARGET_V2"
    $has_antigravity_v1 && install_all_for_tool "antigravity" "$ANTIGRAVITY_TARGET_V1"
    ;;
  codex)
    if ! $has_codex; then err "未偵測到 ~/.codex/"; exit 1; fi
    install_all_for_tool "codex" "$CODEX_TARGET"
    ;;
  vscode)
    # ~/.copilot/skills/ 是 GitHub Copilot 原生掃描的個人 skill 目錄
    # 不強制要求偵測結果，允許手動指定情境
    install_all_for_tool "vscode" "$VSCODE_TARGET"
    ;;
  generic)
    $has_claude         && install_all_for_tool "claude"      "$CLAUDE_TARGET"         "generic"
    $has_antigravity_v2 && install_all_for_tool "antigravity" "$ANTIGRAVITY_TARGET_V2" "generic"
    $has_antigravity_v1 && install_all_for_tool "antigravity" "$ANTIGRAVITY_TARGET_V1" "generic"
    $has_codex          && install_all_for_tool "codex"       "$CODEX_TARGET"          "generic"
    $has_vscode         && install_all_for_tool "vscode"      "$VSCODE_TARGET"         "generic"
    ;;
  *)
    err "未知選項：$MODE"
    show_help
    ;;
esac

echo
ok "${C_BOLD}全部完成！${C_RESET}"
