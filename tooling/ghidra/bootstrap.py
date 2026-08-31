#!/usr/bin/env python3
"""从一个游戏 exe 一键起出可用的 Ghidra 库。

把原来手动的五步固化成一条命令：

    建库 → headless 分析 → 套 ExpHP 函数/静态名 → 套 ExpHP 结构体 → dump 函数清单 → 落盘

用法（必须用 conda 环境 `ghidra` 的 python，Ghidra 12 没有 Jython）：

    P=/data/sunyunbo/miniconda3/envs/ghidra
    JAVA_HOME=$P GHIDRA_INSTALL_DIR=/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC \
      $P/bin/python tooling/ghidra/bootstrap.py th18

路径按约定推导，不用逐个指定：

    local/<ver>*/            版本目录（th18 → local/th18.v1.00a/）
      <name>.exe             该目录下唯一的 exe
      ghidra_projects/       工程放这里，工程名 = exe 文件名
    local/vendor/th-re-data/data/<版本目录名>/    ExpHP 符号金矿

已存在的工程默认跳过分析（幂等），要重来加 --reanalyze。
"""
import argparse, json, os, re, subprocess, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DEFAULT_GHIDRA = "/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC"


def die(msg):
    sys.exit(f"[bootstrap] 错误：{msg}")


def resolve(version):
    """按约定把一个版本号（th16 / th18）解析成一组路径。"""
    cands = sorted(p for p in (REPO / "local").glob(f"{version}*") if p.is_dir())
    if not cands:
        die(f"找不到版本目录 local/{version}* —— 样本要自己放，见 local/README.md")
    vdir = cands[0]

    exes = sorted(vdir.glob("*.exe"))
    if not exes:
        die(f"{vdir.relative_to(REPO)} 下没有 .exe")
    if len(exes) > 1:
        die(f"{vdir.relative_to(REPO)} 下有多个 exe：{[e.name for e in exes]}，请用 --exe 指定")
    exe = exes[0]

    data = REPO / "local/vendor/th-re-data/data" / vdir.name
    return dict(
        version=version,
        vdir=vdir,
        exe=exe,
        proj_dir=vdir / "ghidra_projects",
        proj_name=exe.name,          # 与现有工程一致：项目名就是 exe 文件名
        program=f"/{exe.name}",
        data_dir=data if data.is_dir() else None,
        out_funcs=vdir / f"{version}-funcs.json",
    )


def ghidra_env():
    inst = os.environ.get("GHIDRA_INSTALL_DIR", DEFAULT_GHIDRA)
    if not Path(inst, "support/analyzeHeadless").is_file():
        die(f"GHIDRA_INSTALL_DIR 无效：{inst}")
    if not os.environ.get("JAVA_HOME"):
        die("未设 JAVA_HOME —— 用 conda 环境 `ghidra`（openjdk 21），见本文件顶部用法")
    return inst


def step(n, total, title):
    print(f"\n[{n}/{total}] {title}", flush=True)


def run(cmd, **kw):
    print("      $ " + " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, **kw)


def analyze(P, inst, reanalyze):
    gpr = P["proj_dir"] / f"{P['proj_name']}.gpr"
    if gpr.exists() and not reanalyze:
        print(f"      工程已存在，跳过分析：{gpr.relative_to(REPO)}（要重来加 --reanalyze）")
        return
    P["proj_dir"].mkdir(parents=True, exist_ok=True)
    # ⚠️ analyzeHeadless 的工程目录必须是绝对路径（不接受 "." 开头）
    cmd = [str(Path(inst, "support/analyzeHeadless")),
           str(P["proj_dir"].resolve()), P["proj_name"],
           "-import", str(P["exe"].resolve()), "-overwrite"]
    t = time.time()
    r = run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:]); print(r.stderr[-3000:])
        die("analyzeHeadless 失败")
    print(f"      分析完成，用时 {time.time() - t:.0f}s")


def driver(script, P, extra=()):
    """以 PyGhidra driver 模式（mode B）跑一个导入脚本。"""
    cmd = [sys.executable, str(HERE / script), str(P["data_dir"]),
           "--project-dir", str(P["proj_dir"].resolve()),
           "--project", P["proj_name"], "--program", P["program"], *extra]
    r = run(cmd, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-3000:])
        die(f"{script} 失败")
    return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""


def dump(P):
    cmd = [sys.executable, str(HERE / "dump_funcs.py"),
           "--project-dir", str(P["proj_dir"].resolve()),
           "--project", P["proj_name"], "--program", P["program"],
           "--out", str(P["out_funcs"])]
    r = run(cmd, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-3000:]); die("dump_funcs.py 失败")


def report(P, lines):
    """打印一段可直接粘进 games/<版本>/INDEX.md 的登记文本。"""
    total = named = 0
    if P["out_funcs"].exists():
        fns = json.load(open(P["out_funcs"]))
        total = len(fns)
        named = sum(1 for f in fns if not re.match(r"^(FUN_|thunk_FUN_)", f["name"]))
    print("\n" + "=" * 72)
    print("登记文本（粘进 games/%s/INDEX.md）：\n" % P["vdir"].name)
    print(f"| exe | `{P['exe'].relative_to(REPO)}` |")
    print(f"| Ghidra 工程 | `{(P['proj_dir'] / (P['proj_name'] + '.gpr')).relative_to(REPO)}` |")
    print(f"| MCP `database_id` | `{P['version']}` |")
    print(f"| exe 内函数总数 | {total} |")
    print(f"| 已命名 | {named} |")
    print(f"| 🔬 真·待挖 | {total - named} |")
    for ln in lines:
        if ln:
            print(f"| 导入统计 | `{ln}` |")
    print("=" * 72)
    print("\n下一步：用 build_worklist.py 生成待挖清单 → games/%s/unexplored.md" % P["vdir"].name)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("version", help="版本号，如 th16 / th18")
    ap.add_argument("--exe", help="覆盖自动推导的 exe 路径")
    ap.add_argument("--data-dir", help="覆盖 th-re-data 版本目录")
    ap.add_argument("--reanalyze", action="store_true", help="工程已存在也重新分析")
    ap.add_argument("--skip-names", action="store_true", help="不套 ExpHP 名字/结构体")
    a = ap.parse_args()

    P = resolve(a.version)
    if a.exe:
        P["exe"] = Path(a.exe).resolve()
    if a.data_dir:
        P["data_dir"] = Path(a.data_dir).resolve()
    inst = ghidra_env()

    print(f"[bootstrap] {a.version}")
    print(f"      exe        {P['exe'].relative_to(REPO)}")
    print(f"      工程       {P['proj_dir'].relative_to(REPO)} / {P['proj_name']}")
    print(f"      th-re-data {P['data_dir'].relative_to(REPO) if P['data_dir'] else '(缺失,跳过命名)'}")

    total = 3 if (a.skip_names or not P["data_dir"]) else 5
    lines = []

    step(1, total, "建库 + headless 分析")
    analyze(P, inst, a.reanalyze)

    n = 2
    if not a.skip_names and P["data_dir"]:
        step(n, total, "套 ExpHP 函数名 / 静态符号（safe，不覆盖已有名）"); n += 1
        lines.append(driver("import_th_re_data.py", P))
        step(n, total, "套 ExpHP 结构体"); n += 1
        lines.append(driver("import_th_re_data_structs.py", P))
    elif not P["data_dir"]:
        print("\n      ⚠️ 没有 th-re-data，跳过命名。逆向新 exe 的第一件事就是翻它——")
        print("         见 engine/_shared/community-sources.md 的金矿条目。")

    step(n, total, "dump 函数清单"); n += 1
    dump(P)

    step(n, total, "汇总")
    report(P, lines)


if __name__ == "__main__":
    main()
