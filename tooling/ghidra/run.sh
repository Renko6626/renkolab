#!/usr/bin/env bash
# 便捷封装:用 PyGhidra(Python 3)对一个二进制跑一个 Ghidra 脚本。
#
# 用法:
#   tooling/ghidra/run.sh <binary> <script.py> [script args...]
# 例:
#   tooling/ghidra/run.sh local/th18.v1.00a/th18.exe tooling/ghidra/scripts/list_functions.py
#
# 环境靠 tooling/env.sh 探测(不写死任何机器的路径);缺东西跑 python3 tooling/doctor.py。
#
# 注:pyghidra 首次会对二进制建临时工程并自动分析(大 exe 可能数分钟)。
# 要复用已分析工程/批量,改用 bootstrap.py(见 ../README.md)。
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=/dev/null
source "$REPO/tooling/env.sh" >/dev/null

if [ $# -lt 2 ]; then
  echo "usage: $0 <binary> <script.py> [args...]" >&2
  exit 2
fi

PYGHIDRA="$JAVA_HOME/bin/pyghidra"
if [ ! -x "$PYGHIDRA" ]; then
  PYGHIDRA="$(command -v pyghidra || true)"
fi
if [ -z "$PYGHIDRA" ]; then
  echo "找不到 pyghidra —— 跑 python3 $REPO/tooling/doctor.py" >&2
  exit 1
fi

exec "$PYGHIDRA" "$@"
