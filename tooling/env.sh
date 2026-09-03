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

# ── thtk（thanm / thdat / anmmap）——与 Ghidra 无关，纯 bash 探测 ────────────
# PATH 里有就用 PATH 的；否则用 tooling/thtk/build.sh 编在 local/vendor/thtk/build/ 的。
_renkolab_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for _t in thanm thdat; do
    _p="$(command -v "$_t" 2>/dev/null || true)"
    [ -z "$_p" ] && [ -x "$_renkolab_root/local/vendor/thtk/build/$_t/$_t" ] && _p="$_renkolab_root/local/vendor/thtk/build/$_t/$_t"
    if [ -n "$_p" ]; then
        export "$(echo "$_t" | tr a-z A-Z)=$_p"
        echo "$(echo "$_t" | tr a-z A-Z)=$_p"
    fi
done
for _d in "$_renkolab_root/local/vendor/thpages/static/mapfile" "$_renkolab_root/local/vendor/truth/map"; do
    if [ -f "$_d/v8.anmm" ]; then export THTK_ANMMAP_DIR="$_d"; echo "THTK_ANMMAP_DIR=$_d"; break; fi
done
unset _renkolab_root _t _p _d
