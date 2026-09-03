#!/usr/bin/env bash
# 一键编标准 thtk（thanm + thdat + thecl）到 local/vendor/thtk/build/。
#
#   bash tooling/thtk/build.sh          # 幂等，可重跑
#
# 为什么要自己编：thtk 发布页只有 Windows exe，这台 Linux 没有 wine；thanm 的
# 语法解析器要 bison + flex 现场生成。没有 sudo 时，bison/flex/m4 用
# `apt-get download` 拉发行版 .deb，`dpkg -x` 解到 local/vendor/bisonflex/ 直接用
# （bison 搬家后要用 BISON_PKGDATADIR 指回它的 share/bison）。
# 不写死任何机器路径；非 apt 系统请自行装好 bison flex m4 再跑。
set -eu

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENDOR="$ROOT/local/vendor"
THTK="$VENDOR/thtk"
BF="$VENDOR/bisonflex"
BUILD="$THTK/build"
JOBS="$(nproc 2>/dev/null || echo 4)"

mkdir -p "$VENDOR"

# ── 1. 源码 + 子模块（libpng / zlib-ng / thtypes）─────────────────────
if [ ! -d "$THTK/.git" ]; then
    echo ">> clone thtk"
    git clone https://github.com/thpatch/thtk "$THTK"
fi
if [ ! -f "$THTK/extlib/libpng/CMakeLists.txt" ]; then
    echo ">> submodules"
    git -C "$THTK" submodule update --init --depth 1
fi

# ── 2. bison / flex / m4 ─────────────────────────────────────────────
CMAKE_EXTRA=()
have_all() { command -v bison >/dev/null && command -v flex >/dev/null && command -v m4 >/dev/null; }
if ! have_all; then
    if [ -x "$BF/usr/bin/bison" ] && [ -x "$BF/usr/bin/flex" ] && [ -x "$BF/usr/bin/m4" ]; then
        : # 之前已经解过
    elif command -v apt-get >/dev/null && command -v dpkg >/dev/null; then
        echo ">> 系统没有 bison/flex/m4，用 apt-get download 拉 .deb（不需要 sudo）"
        mkdir -p "$BF/debs"
        (cd "$BF/debs" && apt-get download bison flex m4 libfl2 libfl-dev)
        for d in "$BF"/debs/*.deb; do dpkg -x "$d" "$BF"; done
    else
        echo "!! 缺 bison / flex / m4，且这不是 apt 系统。请自行安装后重跑。" >&2
        exit 2
    fi
    export PATH="$BF/usr/bin:$PATH"
    export BISON_PKGDATADIR="$BF/usr/share/bison"
    export M4="$BF/usr/bin/m4"
    CMAKE_EXTRA+=("-DFL_LIBRARY=$BF/usr/lib/x86_64-linux-gnu/libfl.a" "-DFL_INCLUDE_DIR=$BF/usr/include")
fi
echo ">> bison: $(bison --version | head -1) · flex: $(flex --version)"

# ── 3. cmake + make ──────────────────────────────────────────────────
if [ ! -f "$BUILD/CMakeCache.txt" ]; then
    mkdir -p "$BUILD"
    (cd "$BUILD" && cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF "${CMAKE_EXTRA[@]}" > cmake.log 2>&1) \
        || { echo "!! cmake 失败，见 $BUILD/cmake.log" >&2; exit 1; }
fi
(cd "$BUILD" && make -j"$JOBS" thanm thdat thecl > make.log 2>&1) \
    || { echo "!! make 失败，见 $BUILD/make.log" >&2; exit 1; }

echo ">> 产物："
ls -la "$BUILD/thanm/thanm" "$BUILD/thdat/thdat" "$BUILD/thecl/thecl"
"$BUILD/thanm/thanm" -V
