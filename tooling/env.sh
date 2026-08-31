# 用法： source tooling/env.sh
#
# 探测并导出 GHIDRA_INSTALL_DIR / JAVA_HOME，然后把 $JAVA_HOME/bin 放进 PATH
# （conda 的 `ghidra` 环境里同时装着 JDK 21 和带 pyghidra 的 python，所以这一步
# 顺带让 `python` 指向对的解释器）。
#
# 探测逻辑在 tooling/ghidra/_driver.py 里，与所有 driver 共用同一套——
# 不在这儿复制一份 bash 版，免得两边漂移。缺东西时跑 python tooling/doctor.py。
_renkolab_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if _renkolab_env="$(python3 "$_renkolab_root/tooling/ghidra/_driver.py" 2>&1)"; then
    eval "$_renkolab_env"
    [ -d "$JAVA_HOME/bin" ] && export PATH="$JAVA_HOME/bin:$PATH"
    echo "GHIDRA_INSTALL_DIR=$GHIDRA_INSTALL_DIR"
    echo "JAVA_HOME=$JAVA_HOME"
else
    echo "$_renkolab_env" >&2
fi
unset _renkolab_root _renkolab_env
