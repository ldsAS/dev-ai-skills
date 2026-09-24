# Synthetic reduced Rules fixture

This is parser test input, not a verbatim document or runtime evidence.
Based on the 2026-09-24 https://antigravity.google/docs/rules.md snapshot.

Directory scope: `<dir>/AGENTS.md`, `<dir>/GEMINI.md`,
`<dir>/.agents/AGENTS.md`, `<dir>/.agents/GEMINI.md`,
`<dir>/.agents/rules/*.md`, legacy `<dir>/.agent/rules/*.md`.

Flat directory: `.agents/rules/`. Example: `.agents/rules/typescript.md`.
Nested example: `.agents/rules/frontend/react.md`, registered by `.agents/rules.json`.
Shared configuration examples use `../shared-config/.agents/rules.json` and `../shared-rules`.

General global scope: `~/.gemini/AGENTS.md`, `~/.gemini/GEMINI.md`,
`~/.gemini/config/AGENTS.md`, `~/.gemini/config/GEMINI.md`, `~/.gemini/config/rules/*.md`.
CLI section also lists `~/.gemini/antigravity-cli/rules/*.md`
and `~/.gemini/antigravity-cli/plugins/<plugin_name>/rules/`.
