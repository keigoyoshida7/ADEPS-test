#!/bin/zsh
set -e
LAB_ROOT="${0:A:h}"
cd "$LAB_ROOT"
LAB_BUNDLED_NODE="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin"
if [[ -x "$LAB_BUNDLED_NODE/node" ]]; then export PATH="$LAB_BUNDLED_NODE:$PATH"; fi
if ! command -v node >/dev/null || ! command -v npm >/dev/null; then
  print 'Node.js 22.13以降とnpmをインストールしてから、再度開いてください。'; read '?Enterで閉じる'; exit 1
fi
node -e 'const [a,b]=process.versions.node.split(".").map(Number);if(a<22||(a===22&&b<13))process.exit(1)' || { print 'Node.js 22.13以降が必要です。'; read '?Enterで閉じる'; exit 1; }
python3 scripts/prepare.py
LAB_PY="$(python3 scripts/prepare.py --python-path)"
"$LAB_PY" scripts/start.py "$@"
