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
LAB_PAPER_PY="$LAB_ROOT/.venv-paper/bin/python"
# Probe libraries only: do not load weights, start training, or download data.
if [[ -x "$LAB_PAPER_PY" ]] && "$LAB_PAPER_PY" -c 'import numpy, scipy, torch, pyroomacoustics, soundfile, requests' >/dev/null 2>&1; then
  LAB_PY="$LAB_PAPER_PY"
  print '新モデル用のPython環境を選択しました。再計算には対応する重み・評価記録・音声データも必要です。'
else
  LAB_PY="$(python3 scripts/prepare.py --python-path)"
  print '閲覧・基本API用の環境で起動します。新モデルの再計算環境は未準備です。'
  print '専用環境 .venv-paper と requirements-paper-training.txt の依存関係を準備してください。別モデルでの代用計算は行いません。'
fi
print -r -- "環境・重み・データの準備手順: $LAB_ROOT/docs/PAPER_PRIOR.md"
print '既存のAPIを再利用する場合、そのAPIのPython環境は切り替わりません。'
"$LAB_PY" scripts/start.py "$@"
