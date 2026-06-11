#!/usr/bin/env bash
# 便捷封装:用 PyGhidra(Python 3)对一个二进制跑一个 Ghidra 脚本。
# 已在本服务器验证可用(Ghidra 12.1.2 + conda env `ghidra` 的 openjdk21/python3.11)。
#
# 用法:
#   scripts/run.sh <binary> <script.py> [script args...]
# 例:
#   scripts/run.sh ./samples/th18.exe scripts/find_sht.py
#
# 注:pyghidra 首次会对二进制建临时工程并自动分析(大 exe 可能数分钟)。
# 若要复用已分析工程/批量,改用 analyzeHeadless(见 ../README.md)。
set -euo pipefail

export GHIDRA_INSTALL_DIR=/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC
export JAVA_HOME=/data/sunyunbo/miniconda3/envs/ghidra
PYGHIDRA=/data/sunyunbo/miniconda3/envs/ghidra/bin/pyghidra

if [ $# -lt 2 ]; then
  echo "usage: $0 <binary> <script.py> [args...]" >&2
  exit 2
fi

exec "$PYGHIDRA" "$@"
