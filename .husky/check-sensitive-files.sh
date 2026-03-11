#!/usr/bin/env bash
# Block commit if staged files look sensitive
set -e
SENSITIVE=$(git diff --cached --name-only | grep -E '\.(env|db|sqlite|sqlite3|pem|key|p12|pfx)(\.|$)|/node_modules/|/\.venv/|/venv/|/secrets/|/credentials/|__pycache__' | grep -v '\.env\.example$' || true)
if [ -n "$SENSITIVE" ]; then
    echo "Error: Attempting to commit sensitive files:"
    echo "$SENSITIVE"
    echo "Unstage them (git reset HEAD <file>) and add to .gitignore"
    exit 1
fi
