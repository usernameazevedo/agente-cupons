#!/bin/bash
# Executado pelo LaunchAgent (semanal). Roda o agente e enfileira no WhatsApp.
# Log rotativo simples em agente-cupons.log.
set -uo pipefail
DIR="$HOME/claude/agente-cupons"
LOG="$DIR/agente-cupons.log"
cd "$DIR" || exit 1
echo "===== $(date '+%Y-%m-%d %H:%M') =====" >> "$LOG"
/opt/homebrew/bin/python3 "$DIR/rodar.py" >> "$LOG" 2>&1
echo "" >> "$LOG"
# mantem o log nas ultimas 400 linhas
tail -n 400 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
