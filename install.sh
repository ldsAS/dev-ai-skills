#!/usr/bin/env bash
# dev-ai-skills installer (Linux / macOS)
#
# Usage:
#   ./install.sh                 # auto-detect installed AI tools and install all matching variants
#   ./install.sh claude          # only install claude/ variant to ~/.claude/skills/
#   ./install.sh antigravity     # install antigravity/ variant to BOTH global paths:
#                                #   ~/.gemini/config/skills/ (CLI) and ~/.gemini/antigravity/skills/ (IDE)
#   ./install.sh codex           # install to ~/.agents/skills/ (official USER path, generic variant)
#                                #   ~/.codex/skills/ only if a copy is already installed there
#   ./install.sh vscode          # force-install vscode/ variant to ~/.copilot/skills/ (GitHub Copilot)
#   ./install.sh generic         # install generic/ variant to all detected AI tool dirs (fallback)
#   ./install.sh --project [dir] # install ONE copy into <dir>/.agents/skills/ (default: cwd)
#                                #   cross-tool path — Codex / Gemini CLI / Copilot / Antigravity all read it
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
ANTIGRAVITY_TARGET_V2="$HOME/.gemini/config/skills"       # Antigravity CLI 全域
ANTIGRAVITY_TARGET_V1="$HOME/.gemini/antigravity/skills"  # Antigravity IDE 全域
# ⚠️ 官方 skills scope 表（2026-08-03 查證）列的 USER 路徑是 $HOME/.agents/skills，
#    .codex/skills 在該表中完全沒出現。~/.codex/skills 保留為舊版相容，
#    但務必同時寫入 ~/.agents/skills，否則可能裝到 Codex 不讀的位置（同 C-48 的教訓）。
#    ~/.agents/skills 亦為 Gemini CLI 與 Copilot 的使用者層技能路徑，屬跨工具共用。
CODEX_TARGET="$HOME/.codex/skills"          # 舊版相容
AGENTS_TARGET="$HOME/.agents/skills"        # 官方 USER 路徑（跨工具）
VSCODE_TARGET="$HOME/.copilot/skills"

MODE="${1:-auto}"

show_help() {
  sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}
[[ "$MODE" == "--help" || "$MODE" == "-h" ]] && show_help

# ---- detection ------------------------------------------------------
has_claude=false
has_antigravity_v1=false
has_antigravity_v2=false
has_codex=false
has_gemini_cli=false
has_codex_legacy=false
has_vscode_legacy=false
has_vscode=false
needs_agents_target=false
[[ -d "$HOME/.claude" ]]              && has_claude=true
# 兩條全域路徑**都要寫**，它們屬於不同產品，不是新舊關係（官方文件明載）：
#   Antigravity IDE  → ~/.gemini/antigravity/skills/   (/docs/ide/skills)
#   Antigravity CLI  → ~/.gemini/config/skills/        (/docs/skills)
# 2026-07-30 曾誤判後者取代前者而改成 fallback，導致同時裝 IDE 與 CLI 時
# 技能在 IDE 端失效；2026-08-03 已還原。詳見 CLAIMS.md 的 C-48。
[[ -d "$HOME/.gemini/antigravity" ]] && has_antigravity_v1=true
[[ -d "$HOME/.gemini/config" ]]       && has_antigravity_v2=true
[[ -d "$HOME/.codex" ]]               && has_codex=true
command -v gemini >/dev/null 2>&1       && has_gemini_cli=true
# P1-2a：下列兩條沒有官方依據 —— .codex/skills 未見於 Codex 官方 scope 表（C-12），
# 而 Copilot 亦讀 ~/.agents/skills（C-77）。降為相容模式：只續寫「已經裝過本專案技能」
# 的目錄，不再為新安裝主動建立，以減少同名技能的重複份數。
#
# ⚠️ 判準是「該目錄裡已經有我們的技能」，**不是「目錄存在」**。
#    ~/.codex/skills 底下有 Codex 內建的 .system/，該目錄永遠存在；
#    用「目錄存在」當判準的話，使用者手動刪掉的舊複本會在下次安裝時復活。
skill_installed_in() {
  local target="$1" d
  [[ -d "$target" ]] || return 1
  for d in "$SKILLS_DIR"/*/; do
    [[ -d "$d" ]] || continue
    [[ -d "$target/$(basename "${d%/}")" ]] && return 0
  done
  return 1
}
skill_installed_in "$CODEX_TARGET"    && has_codex_legacy=true
skill_installed_in "$VSCODE_TARGET"   && has_vscode_legacy=true
{ command -v code >/dev/null 2>&1 || [[ -d "$HOME/.copilot" ]]; } && has_vscode=true
if $has_codex || $has_gemini_cli || $has_vscode; then
  needs_agents_target=true
fi

# --project 是專案層安裝，不依賴任何全域工具目錄 —— 跳過偵測與「找不到工具」的中止
if [[ "$MODE" != "--project" ]]; then
info "偵測到的 AI 工具："
$has_claude         && ok "Claude Code       → $CLAUDE_TARGET"         || warn "Claude Code       → 未偵測到 ~/.claude"
$has_antigravity_v2 && ok "Antigravity CLI   → $ANTIGRAVITY_TARGET_V2" || warn "Antigravity CLI   → 未偵測到 ~/.gemini/config"
$has_antigravity_v1 && ok "Antigravity IDE   → $ANTIGRAVITY_TARGET_V1" || warn "Antigravity IDE   → 未偵測到 ~/.gemini/antigravity"
$has_codex          && ok "Codex             → $AGENTS_TARGET"         || warn "Codex             → 未偵測到 ~/.codex"
$has_gemini_cli     && ok "Gemini CLI        → 經 $AGENTS_TARGET"       || warn "Gemini CLI        → 未偵測到 gemini 指令"
$has_codex_legacy   && warn "  └ 相容路徑       → $CODEX_TARGET（已裝過才續寫，不主動建立）" || true
$has_vscode_legacy  && warn "  └ 相容路徑       → $VSCODE_TARGET（已裝過才續寫，不主動建立）" || true
$has_vscode         && ok "VS Code Copilot   → 經 $AGENTS_TARGET（Copilot 亦讀此路徑）" || warn "VS Code Copilot   → 未偵測到 code 指令或 ~/.copilot，仍可用 vscode 模式強制安裝"

if ! $has_claude && ! $has_antigravity_v1 && ! $has_antigravity_v2 && ! $has_codex && ! $has_gemini_cli && ! $has_vscode; then
  err "沒有偵測到任何支援的 AI 工具。請先安裝 Claude Code、Antigravity、Codex、Gemini CLI 或 VS Code (Copilot)。"
  exit 1
fi
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

  # 安裝完成當下驗證來源與目的 SKILL.md byte-identical。
  # 若稍後又修改 source，仍必須重新執行安裝器。
  if ! cmp -s "$src/SKILL.md" "$dst/SKILL.md"; then
    err "安裝驗證失敗：$src/SKILL.md 與 $dst/SKILL.md 不一致"
    return 1
  fi
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

# ---- project-scoped install -----------------------------------------
# 只寫 <repo>/.agents/skills/ 一條路徑、一份複製 —— 與上游 uipro init --ai universal 同作法。
# 不逐工具各裝一份：`.agents/skills` 已同時被 Codex、Gemini CLI、Copilot、Antigravity
# 讀取（C-13、C-22、C-60、C-77），分開裝只會製造多份會各自過期的複本。
install_project() {
  local root="$1"
  [[ -d "$root" ]] || { err "找不到目錄：$root"; exit 1; }
  root="$(cd "$root" && pwd)"

  local in_git=true
  git -C "$root" rev-parse --show-toplevel >/dev/null 2>&1 || in_git=false
  $in_git || warn "$root 不是 git repo；安裝照做，但下方的 .gitignore 提示要 git init 之後才有意義"

  install_all_for_tool "project" "$root/.agents/skills" "generic"

  echo
  info "${C_BOLD}還有兩件事要手動做：${C_RESET}"
  echo
  echo "  ${C_BOLD}1. 在專案 .gitignore 放行剛裝的技能${C_RESET}"
  echo "     本 skill 自己的範本會擋掉 .agents/skills/* —— 不放行的話它會把自己藏起來："
  echo
  local skill_dir n
  for skill_dir in "$SKILLS_DIR"/*/; do
    [[ -d "$skill_dir" ]] || continue
    n="$(basename "${skill_dir%/}")"
    echo "       !.agents/skills/$n/"
    echo "       !.agents/skills/$n/**"
  done
  echo
  echo "     ${C_INFO}驗證：git check-ignore --no-index -v -- .agents/skills/<name>/SKILL.md${C_RESET}"
  echo "     （輸出以 ! 開頭＝已放行；無輸出＝沒被任何規則命中，也算放行）"
  echo
  echo "  ${C_BOLD}2. 在專案 AGENTS.md 寫明什麼時候要用它${C_RESET}"
  echo "     專案層技能不該只靠觸發詞被撞到，講清楚使用時機比較可靠："
  echo
  echo "       ## 專案技能"
  echo "       - 要調整 .gitignore／.gitattributes，或 commit 前要確認哪些檔案會被提交時，"
  echo "         使用 .agents/skills/ai-git-ignore-strategy/"
  echo
  # 用 if 而非 `$in_git && ok`：後者在 in_git=false 時會讓函式回傳 1，
  # 配上 set -e 會讓整個安裝在最後一步無聲失敗
  if $in_git; then ok "專案層安裝完成：$root/.agents/skills/"; fi
}

# ---- main -----------------------------------------------------------
case "$MODE" in
  auto|"")
    $has_claude         && install_all_for_tool "claude"      "$CLAUDE_TARGET"
    $has_antigravity_v2 && install_all_for_tool "antigravity" "$ANTIGRAVITY_TARGET_V2"
    $has_antigravity_v1 && install_all_for_tool "antigravity" "$ANTIGRAVITY_TARGET_V1"
    # 共用路徑放 generic：Codex、Gemini CLI、Copilot 任一存在就寫入一次（C-79）
    $needs_agents_target && install_all_for_tool "shared"      "$AGENTS_TARGET" "generic"
    $has_codex_legacy   && install_all_for_tool "codex"       "$CODEX_TARGET"
    $has_vscode_legacy  && install_all_for_tool "vscode"      "$VSCODE_TARGET"
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
    install_all_for_tool "codex" "$AGENTS_TARGET" "generic"
    $has_codex_legacy && install_all_for_tool "codex" "$CODEX_TARGET"
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
    $needs_agents_target && install_all_for_tool "shared"      "$AGENTS_TARGET"         "generic"
    $has_codex_legacy   && install_all_for_tool "codex"       "$CODEX_TARGET"          "generic"
    $has_vscode_legacy  && install_all_for_tool "vscode"      "$VSCODE_TARGET"         "generic"
    ;;
  --project)
    install_project "${2:-$PWD}"
    ;;
  *)
    err "未知選項：$MODE"
    show_help
    ;;
esac

echo
ok "${C_BOLD}全部完成！${C_RESET}"
