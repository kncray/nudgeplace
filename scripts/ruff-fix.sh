#!/usr/bin/env bash
# Claude Code PostToolUse 훅: Edit/Write 후 ruff format + ruff check --fix 자동 실행.
# stdin의 hook JSON에서 file_path를 추출해 .py 파일에만 적용한다.
set -euo pipefail

INPUT=$(cat)
FILE=$(echo "$INPUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(d.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null || echo "")

[[ "$FILE" == *.py ]] || exit 0
[[ -f "$FILE" ]] || exit 0

# uv 프로젝트 — .venv의 ruff를 우선 사용하고, 없으면 PATH의 ruff로 폴백한다.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUFF="$ROOT/.venv/bin/ruff"
[[ -x "$RUFF" ]] || RUFF="ruff"

"$RUFF" format "$FILE" 2>/dev/null || true
"$RUFF" check --fix --silent "$FILE" 2>/dev/null || true
