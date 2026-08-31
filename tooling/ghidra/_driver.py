#!/usr/bin/env python3
"""所有 PyGhidra driver 共用的开库 / 落盘骨架 + 路径推导。

存在的理由是**别把活干丢了**。手写 open→transaction→save→close 有四个坑，
每个都会静默吃掉一下午的成果：

1. **撞锁**：MCP `ghidra-re` 开着库时 driver 打不开工程，报的是一句 Java 异常，
   看不出该去 `close_database`。
2. **异常时提交了半截事务**：`finally: endTransaction(tx, True)` 会把出错前改的一半存进去。
   正确做法是出错一律回滚。
3. **以为存了其实没存**：`proj.save()` 之后没人检查 `prog.isChanged()`。
   真没存下去时脚本照样打印成功。
4. **开错程序**：工程里同名程序、或换了 build 的 exe，地址全对不上却毫无提示。

`open_program()` 把这四条一次性堵住。用法：

    from _driver import open_program, resolve

    with open_program(pd, "th18.exe", "/th18.exe", tx="套 labels", commit=not dry) as prog:
        ...                      # 抛异常 = 整个事务回滚，且不落盘

`tx=None` 开只读；`commit=False` 跑完回滚（dry-run 用）。
"""
import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_GHIDRA = "/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC"

_started = False


def die(msg, code=1):
    sys.exit(f"[ghidra] 错误：{msg}")


def start():
    """启动 JVM（幂等）。"""
    global _started
    if not _started:
        import pyghidra
        pyghidra.start()
        _started = True


def resolve(version, exe=None, data_dir=None):
    """按约定把版本号（th16 / th18）解析成一组路径。

    local/<ver>*/            版本目录（th18 -> local/th18.v1.00a/）
      <name>.exe             该目录下唯一的 exe
      ghidra_projects/       工程放这里，工程名 = exe 文件名
    local/vendor/th-re-data/data/<版本目录名>/    ExpHP 符号金矿
    games/<版本目录名>/symbols.json               我们自己那层（入库）
    """
    cands = sorted(p for p in (REPO / "local").glob(f"{version}*") if p.is_dir())
    if not cands:
        die(f"找不到版本目录 local/{version}* —— 样本要自己放，见 local/README.md")
    vdir = cands[0]

    if exe:
        exe = Path(exe).resolve()
    else:
        exes = sorted(vdir.glob("*.exe"))
        if not exes:
            die(f"{vdir.relative_to(REPO)} 下没有 .exe")
        if len(exes) > 1:
            die(f"{vdir.relative_to(REPO)} 下有多个 exe：{[e.name for e in exes]}，请用 --exe 指定")
        exe = exes[0]

    data = Path(data_dir).resolve() if data_dir else REPO / "local/vendor/th-re-data/data" / vdir.name
    return dict(
        version=version,
        vdir=vdir,
        exe=exe,
        proj_dir=vdir / "ghidra_projects",
        proj_name=exe.name,          # 与现有工程一致：项目名就是 exe 文件名
        program=f"/{exe.name}",
        data_dir=data if data.is_dir() else None,
        out_funcs=vdir / f"{version}-funcs.json",
        symbols=REPO / "games" / vdir.name / "symbols.json",
    )


def ghidra_install():
    inst = os.environ.get("GHIDRA_INSTALL_DIR", DEFAULT_GHIDRA)
    if not Path(inst, "support/analyzeHeadless").is_file():
        die(f"GHIDRA_INSTALL_DIR 无效：{inst}")
    if not os.environ.get("JAVA_HOME"):
        die("未设 JAVA_HOME —— 用 conda 环境 `ghidra`（openjdk 21），见 tooling/ghidra/README.md")
    return inst


_LOCK_HINT = """工程被占用，打不开。

  多半是 MCP `ghidra-re` 正开着这个库。先在 MCP 里跑 close_database，再重试。
  若确认没人用（比如上次 driver 被 kill 了），删掉残留锁文件：
      rm -f {lockglob}"""


def _lock_files(project_dir, project):
    rep = Path(project_dir) / f"{project}.rep"
    return sorted(str(p) for p in rep.glob("*.lock")) + \
           sorted(str(p) for p in Path(project_dir).glob(f"{project}.lock"))


@contextmanager
def open_program(project_dir, project, program, tx=None, commit=True, expect_md5=None):
    """开一个工程里的程序；tx 非空则开事务，正常退出时提交并**验证**落盘。

    tx=None      -> 只读打开
    commit=False -> 事务跑完回滚，且不落盘（dry-run）
    expect_md5   -> 校验打开的确实是那个 build，对不上直接拒绝
    """
    start()
    from ghidra.base.project import GhidraProject

    project_dir = os.path.abspath(project_dir)
    folder, _, name = program.rpartition("/")
    readonly = tx is None

    try:
        proj = GhidraProject.openProject(project_dir, project, False)
    except Exception as e:                                   # noqa: BLE001 — Java 异常
        if "lock" in str(e).lower():
            die(_LOCK_HINT.format(lockglob=os.path.join(project_dir, f"{project}.rep", "*.lock")))
        die(f"打不开工程 {project_dir}/{project}：{e}")

    prog = None
    try:
        try:
            prog = proj.openProgram(folder or "/", name, readonly)
        except Exception as e:                               # noqa: BLE001
            if "lock" in str(e).lower():
                die(_LOCK_HINT.format(lockglob=os.path.join(project_dir, f"{project}.rep", "*.lock")))
            die(f"打不开程序 {program}：{e}")

        if expect_md5:
            got = str(prog.getExecutableMD5() or "").lower()
            if got != expect_md5.lower():
                die(f"exe 对不上：工程里是 md5 {got}，期望 {expect_md5}。\n"
                    f"       地址死绑 build，换了 build 的符号一律不能套。")

        if readonly:
            yield prog
            return

        txid = prog.startTransaction(tx)
        ok = False
        try:
            yield prog
            ok = True
        finally:
            # 出错一律回滚：宁可白干一次，也不要半截状态进库
            prog.endTransaction(txid, ok and commit)

        if commit:
            proj.save(prog)
            if prog.isChanged():
                die(f"落盘失败：save() 之后 {program} 仍是 changed 状态，改动没写进去。\n"
                    f"       别当成功处理——重跑一次，若仍失败检查磁盘空间与工程权限。")
    finally:
        try:
            proj.close()
        except Exception:                                    # noqa: BLE001
            pass


def add_project_args(ap):
    """给 argparse 挂上四个标准工程参数。"""
    ap.add_argument("--project-dir", required=True, help="工程目录（绝对路径）")
    ap.add_argument("--project", required=True, help="工程名，如 th18.exe")
    ap.add_argument("--program", required=True, help="工程内程序路径，如 /th18.exe")
    ap.add_argument("--dry-run", action="store_true", help="只统计，不写库")
