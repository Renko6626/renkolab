#!/usr/bin/env python3
"""环境自检 —— 「我 clone 下来了，还差什么？」

    python3 tooling/doctor.py            # 全查
    python3 tooling/doctor.py th18       # 顺带查某一作的样本与工程

每条查不过的都给出**可直接粘的修复命令**，而不是让你回去翻文档。纯标准库，
不需要先把环境配好才能跑——这正是它存在的意义。
"""
import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ghidra"))
from _driver import MIN_JDK, REPO, find_ghidra, find_java, java_major   # noqa: E402

OK, WARN, BAD = "✅", "⚠️ ", "❌"
rows, fixes = [], []


def check(name, ok, detail="", fix=None, soft=False):
    rows.append(((OK if ok else (WARN if soft else BAD)), name, detail))
    if not ok and fix:
        fixes.append((name, fix))
    return ok


# ── 1. 基础 ────────────────────────────────────────────────────────────
def check_basics():
    v = sys.version_info
    check("python3", v >= (3, 8), f"{v.major}.{v.minor}.{v.micro}",
          "装 python 3.8+（conda 环境里会带 3.11）")
    check("git 仓库", (REPO / ".git").exists(), str(REPO),
          "在仓库根目录跑本脚本")


# ── 2. Ghidra + JDK + pyghidra ────────────────────────────────────────
def check_ghidra():
    g = find_ghidra()
    check("Ghidra", bool(g), g or "没找到",
          "去 https://github.com/NationalSecurityAgency/ghidra/releases 下 12.x，\n"
          "     解压到 ~/opt/ 下（脚本会自动找 ~/opt/ghidra_*_PUBLIC），\n"
          "     或者自己 export GHIDRA_INSTALL_DIR=<解压路径>")
    if g:
        ver = "?"
        p = Path(g, "Ghidra/application.properties")
        if p.is_file():
            for ln in p.read_text(errors="ignore").splitlines():
                if ln.startswith("application.version="):
                    ver = ln.split("=", 1)[1].strip()
        check("Ghidra 版本", ver.startswith("12"), ver,
              "本仓的脚本按 Ghidra 12 写（12 移除了 Jython，必须走 PyGhidra）", soft=True)

    try:
        j = find_java()
    except SystemExit:
        j = None                                   # find_java 版本不够时会 die
    check(f"JDK {MIN_JDK}+", bool(j),
          f"{j}（JDK {java_major(j)}）" if j else f"没有 {MIN_JDK}+ 的 JDK",
          "conda create -n ghidra -c conda-forge openjdk=21 python=3.11")
    return g, j


def check_pyghidra(java_home):
    """找一个既能 import pyghidra、又跟 JDK 同环境的 python。"""
    cands = [sys.executable]
    if java_home:
        cands.insert(0, str(Path(java_home, "bin/python")))
    for c in cands:
        if not Path(c).is_file():
            continue
        try:
            r = subprocess.run([c, "-c", "import pyghidra;print(pyghidra.__version__)"],
                               capture_output=True, text=True, timeout=90)
            if r.returncode == 0:
                check("pyghidra", True, f"{r.stdout.strip()} @ {c}")
                return c
        except Exception:                          # noqa: BLE001
            pass
    check("pyghidra", False, "没有能 import pyghidra 的 python",
          "conda activate ghidra && pip install pyghidra")
    return None


# ── 3. 样本与第三方数据 ────────────────────────────────────────────────
def check_samples(version=None):
    vdirs = sorted(p for p in (REPO / "local").glob("th*") if p.is_dir())
    if version:
        vdirs = [p for p in vdirs if p.name.startswith(version)]
    check("样本目录 local/th*", bool(vdirs),
          ", ".join(p.name for p in vdirs) or "一个都没有",
          "游戏 exe 是 ZUN 版权商业软件，用你自己合法持有的副本，\n"
          "     按 local/README.md 的哈希表放进 local/<版本>/。**不要去下载。**")
    for v in vdirs:
        exes = list(v.glob("*.exe"))
        if not exes:
            check(f"  {v.name}/*.exe", False, "没有 exe", "见 local/README.md")
            continue
        md5 = hashlib.md5(exes[0].read_bytes()).hexdigest()
        check(f"  {v.name}/{exes[0].name}", True, f"md5 {md5}")
        gpr = list((v / "ghidra_projects").glob("*.gpr"))
        check(f"  {v.name} Ghidra 工程", bool(gpr),
              gpr[0].name if gpr else "还没建",
              f"tooling/ghidra/bootstrap.py {v.name.split('.')[0]}", soft=True)


def check_vendor():
    d = REPO / "local/vendor/th-re-data/data"
    n = len(list(d.glob("th*"))) if d.is_dir() else 0
    check("ExpHP th-re-data", n > 0, f"{n} 作" if n else "没有",
          "git clone https://github.com/exphp-share/th-re-data "
          "local/vendor/th-re-data\n"
          "     （上游无 LICENSE：本地逆向可用，不转发。见 local/README.md）")


# ── 4. MCP ────────────────────────────────────────────────────────────
def check_mcp():
    exe = shutil.which("re-mcp-ghidra") or os.path.expanduser("~/.local/bin/re-mcp-ghidra")
    have = Path(exe).exists()
    check("ghidra-re MCP 已安装", have, exe if have else "没装",
          'uv tool install --force "git+https://github.com/Renko6626/re-mcp'
          '@thtk-patches#subdirectory=packages/re-mcp-ghidra"')

    cfg = Path.home() / ".claude.json"
    reg = False
    if cfg.is_file():
        try:
            d = json.loads(cfg.read_text())
            reg = "ghidra-re" in (d.get("projects", {})
                                  .get(str(REPO), {}).get("mcpServers", {}) or {})
        except Exception:                          # noqa: BLE001
            pass
    check("ghidra-re 已注册到本仓", reg, str(REPO) if reg else "本仓名下没有",
          "cd " + str(REPO) + " && claude mcp add ghidra-re \\\n"
          "       -e GHIDRA_INSTALL_DIR=\"$GHIDRA_INSTALL_DIR\" -e JAVA_HOME=\"$JAVA_HOME\" \\\n"
          "       -- " + exe + " stdio\n"
          "     ⚠️ 注册的作用域绑目录，且要**新开会话**才加载")


# ── 5. 仓库自身 ───────────────────────────────────────────────────────
def check_repo():
    ck = REPO / "tooling/check-docs.py"
    try:
        r = subprocess.run([sys.executable, str(ck)], capture_output=True, text=True, timeout=120)
        check("文档规范 check-docs", r.returncode == 0,
              r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "",
              "python tooling/check-docs.py  看哪一条不过")
    except Exception as e:                         # noqa: BLE001
        check("文档规范 check-docs", False, str(e)[:60])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("version", nargs="?", help="只查某一作，如 th18")
    a = ap.parse_args()

    print(f"renkolab 环境自检 — {REPO}\n")
    check_basics()
    _g, j = check_ghidra()
    py = check_pyghidra(j)
    check_samples(a.version)
    check_vendor()
    check_mcp()
    check_repo()

    w = max(len(r[1]) for r in rows)
    for mark, name, detail in rows:
        print(f"  {mark} {name.ljust(w)}  {detail}")

    if fixes:
        print("\n" + "─" * 70 + "\n要补的东西：\n")
        for name, fix in fixes:
            print(f"  ▸ {name}\n     {fix}\n")
    else:
        print("\n全绿。开工：")
        v = a.version or "th18"
        print(f"  source tooling/env.sh")
        print(f"  {py or 'python'} tooling/ghidra/bootstrap.py {v}")
    return 1 if any(r[0] == BAD for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
