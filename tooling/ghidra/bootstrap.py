#!/usr/bin/env python3
"""从一个游戏 exe 一键起出可用的 Ghidra 库。

把原来手动的一串步骤固化成一条命令：

    建库 → 分析 → 补建漏掉的函数 → 套 ExpHP 名/结构体/labels
    → 回放我们自己那层 → dump 函数清单 → 落盘

用法（必须用 conda 环境 `ghidra` 的 python，Ghidra 12 没有 Jython）：

    P=/data/sunyunbo/miniconda3/envs/ghidra
    JAVA_HOME=$P GHIDRA_INSTALL_DIR=/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC \\
      $P/bin/python tooling/ghidra/bootstrap.py th18

路径按约定推导（见 `_driver.resolve`），不用逐个指定。

**两层符号**：ExpHP 那层（`local/vendor/th-re-data/`，不入库）每次从头重放；
我们那层（`games/<版本>/symbols.json`，入库）在最后回放，**压过** ExpHP——
它的存在意义就是订正 ExpHP，safe 模式会让订正永远落不下去。

已存在的工程默认跳过分析（幂等），要重来加 `--reanalyze`。⚠️ `--reanalyze` 会炸掉现有 DB，
所以它前面有一道硬拦截：`symbols.py status` 若报有未导出的成果，直接中止让你先 export。
"""
import argparse, json, os, re, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _driver import REPO, ghidra_install, resolve                    # noqa: E402

HERE = Path(__file__).resolve().parent


def die(msg):
    sys.exit(f"[bootstrap] 错误：{msg}")


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


def driver(script, P, extra=(), data_dir=True):
    """以 PyGhidra driver 模式跑一个脚本，回传它最后一行统计。"""
    cmd = [sys.executable, str(HERE / script)]
    if data_dir:
        cmd.append(str(P["data_dir"]))
    cmd += ["--project-dir", str(P["proj_dir"].resolve()),
            "--project", P["proj_name"], "--program", P["program"], *extra]
    r = run(cmd, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-3000:])
        die(f"{script} 失败")
    return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""


def symbols(P, action, extra=()):
    cmd = [sys.executable, str(HERE / "symbols.py"), action, P["version"], *extra]
    r = run(cmd, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-3000:])
        die(f"symbols.py {action} 失败")
    return r.stdout


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
    ap.add_argument("--reanalyze", action="store_true", help="工程已存在也重新分析（会炸掉现有 DB）")
    ap.add_argument("--skip-names", action="store_true", help="不套 ExpHP 名字/结构体/labels")
    ap.add_argument("--force", action="store_true",
                    help="--reanalyze 时即使有未导出的成果也照跑（会丢东西）")
    ap.add_argument("--dry-run", action="store_true",
                    help="只预览各步计数，不写库（用于验证接线与回归基线）")
    a = ap.parse_args()

    P = resolve(a.version, exe=a.exe, data_dir=a.data_dir)
    inst = ghidra_install()

    print(f"[bootstrap] {a.version}")
    print(f"      exe        {P['exe'].relative_to(REPO)}")
    print(f"      工程       {P['proj_dir'].relative_to(REPO)} / {P['proj_name']}")
    print(f"      th-re-data {P['data_dir'].relative_to(REPO) if P['data_dir'] else '(缺失,跳过命名)'}")
    print(f"      我们那层   {P['symbols'].relative_to(REPO)}"
          f"{'' if P['symbols'].exists() else '（尚不存在）'}")

    dry = ["--dry-run"] if a.dry_run else []
    has_names = not a.skip_names and P["data_dir"]
    total = 8 if has_names else 4          # 漂移拦截另算「第 0 步」，只在 --reanalyze 时出现
    lines = []
    n = 1

    # ── 0. 漂移拦截 ──────────────────────────────────────────────
    # --reanalyze 会重建 DB。手动导出是常态，所以这是唯一的安全网：
    # DB 里若有还没写回仓库的成果，先别炸。
    if a.reanalyze and not a.force and (P["proj_dir"] / f"{P['proj_name']}.gpr").exists():
        step(0, total, "漂移拦截（--reanalyze 前检查有无未导出的成果）")
        out = symbols(P, "status")
        if "0 漂移" not in out:
            die("DB 里有还没导出的东西，--reanalyze 会把它们炸掉。\n"
                f"       先跑：tooling/ghidra/symbols.py export {a.version}\n"
                "       确认要丢弃就加 --force。")

    step(n, total, "建库 + headless 分析"); n += 1
    analyze(P, inst, a.reanalyze)

    if has_names:
        step(n, total, "补建 ExpHP 标了、而 Ghidra 没建函数的地址"); n += 1
        lines.append(driver("create_missing_funcs.py", P, dry))

        step(n, total, "套 ExpHP 函数名 / 静态符号（safe，不覆盖已有名）"); n += 1
        lines.append(driver("import_th_re_data.py", P, dry))

        step(n, total, "套 ExpHP 结构体 / 枚举 / 位域 / statics 类型"); n += 1
        lines.append(driver("import_th_re_data_structs.py", P,
                            [*dry, "--apply-statics", "--overwrite"]))

        step(n, total, "套 ExpHP labels（VM opcode case）"); n += 1
        lines.append(driver("import_th_re_data_labels.py", P, dry))
    elif not P["data_dir"]:
        print("\n      ⚠️ 没有 th-re-data，跳过命名。逆向新 exe 的第一件事就是翻它——")
        print("         见 engine/_shared/community-sources.md 的金矿条目。")

    step(n, total, "回放我们自己那层（覆盖语义，压过 ExpHP）"); n += 1
    if P["symbols"].exists():
        symbols(P, "apply", dry)
    else:
        print(f"      {P['symbols'].relative_to(REPO)} 不存在，跳过"
              f"（干完活记得 symbols.py export {a.version}）")

    step(n, total, "dump 函数清单"); n += 1
    dump(P)

    step(n, total, "汇总")
    report(P, lines)


if __name__ == "__main__":
    main()
