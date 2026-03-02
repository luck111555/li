#!/usr/bin/env bash
set -euo pipefail

WIN_HOME="/mnt/c/Users/HP"
TS="$(date +%Y%m%d-%H%M%S)"
BACKUP_ROOT="/mnt/d/APP/AI-Session-Viewer-main/win-home-backup-$TS"

mkdir -p "$BACKUP_ROOT"

backup_if_exists() {
  local src="$1"
  local dst="$2"
  if [ -e "$src" ]; then
    mkdir -p "$(dirname "$dst")"
    cp -a "$src" "$dst"
  fi
}

# Backup current Windows-side dirs (if any) to D:.
backup_if_exists "$WIN_HOME/.codex" "$BACKUP_ROOT/.codex"
backup_if_exists "$WIN_HOME/.claude" "$BACKUP_ROOT/.claude"

# Ensure destination dirs exist
mkdir -p "$WIN_HOME/.codex/sessions"
mkdir -p "$WIN_HOME/.claude/projects"

# Sync from current WSL (root home) to Windows home
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete /root/.codex/sessions/ "$WIN_HOME/.codex/sessions/"
  rsync -a --delete /root/.claude/projects/ "$WIN_HOME/.claude/projects/"
else
  # Fallback without delete
  cp -a /root/.codex/sessions/. "$WIN_HOME/.codex/sessions/"
  cp -a /root/.claude/projects/. "$WIN_HOME/.claude/projects/"
fi

# Verification summary
COD_SRC=$(find /root/.codex/sessions -type f | wc -l | awk '{print $1}')
COD_DST=$(find "$WIN_HOME/.codex/sessions" -type f | wc -l | awk '{print $1}')
CLA_SRC=$(find /root/.claude/projects -type f | wc -l | awk '{print $1}')
CLA_DST=$(find "$WIN_HOME/.claude/projects" -type f | wc -l | awk '{print $1}')

echo "BACKUP_ROOT=$BACKUP_ROOT"
echo "CODEX_FILES_SRC=$COD_SRC"
echo "CODEX_FILES_DST=$COD_DST"
echo "CLAUDE_FILES_SRC=$CLA_SRC"
echo "CLAUDE_FILES_DST=$CLA_DST"
