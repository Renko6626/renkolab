#!/usr/bin/env python3
"""交叉对比本工程当前命名快照（dump_funcs.py 产出）与 ExpHP th-re-data funcs.json，
把函数分成四类，产出 `games/<版本>/unexplored.md` —— 给新会话的「待挖函数地图」。

    python tooling/ghidra/build_worklist.py th18

纯标准库 + `_driver.resolve` 的路径推导；跑之前先 bootstrap（要有 `<ver>-funcs.json`）。
"""
import argparse, json, re, bisect, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _driver import REPO, resolve

_ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
_ap.add_argument("version", nargs="?", default="th16", help="版本号，如 th16 / th18")
_A = _ap.parse_args()
P = resolve(_A.version)
VER = P["vdir"].name
if not P["out_funcs"].exists():
    sys.exit(f"[worklist] 缺 {P['out_funcs'].relative_to(REPO)} —— 先跑 bootstrap.py {_A.version}")
if not P["data_dir"]:
    sys.exit(f"[worklist] 缺 th-re-data/{VER} —— 见 local/README.md")

OURS = json.load(open(P["out_funcs"]))
EXP  = json.load(open(P["data_dir"] / "funcs.json"))

def norm(a): return a.lower().replace("0x", "").lstrip("0").rjust(1, "0")
ex_by = {norm(x["addr"]): x["name"] for x in EXP}

def ex_meaningful(n):
    return bool(n) and not re.match(r'^(sub_|thunk|nullsub|j_|\?|FID_)', n)
def ours_default(n):       # Ghidra 默认名 = 没人命名
    return n.startswith("FUN_")
CRT = re.compile(r'^(_|__|FID_|j_|thunk|\?|operator|std|~|Unwind|Catch|SEH|scrt|_+crt|guard_|nullsub|Mem|Cxx|terminate|memcpy|memset|memmove|strlen|malloc|free|atexit|onexit)', re.I)
def is_crt(n):
    return bool(CRT.match(n))

# 子系统提示:用 ExpHP 有意义命名当锚点(带类前缀),取地址最近的
anchors = sorted((int(norm(x["addr"]), 16), x["name"]) for x in EXP if ex_meaningful(x["name"]))
anchor_addrs = [a for a, _ in anchors]
def nearest_named(addr):
    i = bisect.bisect_right(anchor_addrs, addr) - 1
    if i < 0: return "?"
    name = anchors[i][1]
    return name.split("::")[0] if "::" in name else name
def subsystem(name):       # 从 ExpHP 名取子系统前缀
    return name.split("::")[0] if "::" in name else (name.split("_")[0] if "_" in name else name)

unexplored, importable, ours_named, crt = [], [], [], []
for f in OURS:
    a = norm(f["addr"]); on = f["name"]; en = ex_by.get(a)
    if f.get("thunk") or f.get("external"):
        crt.append(f); continue
    if ours_default(on):                       # 我们没命名(FUN_)
        if en and ex_meaningful(en):
            f["exphp"] = en; importable.append(f)     # ExpHP 命名了 → 可直接导入
        elif (en and is_crt(en)) :
            crt.append(f)
        else:
            f["hint"] = nearest_named(int(a, 16))      # 谁都没命名 → 待挖
            unexplored.append(f)
    else:                                      # 我们/Ghidra 已命名
        (crt if is_crt(on) else ours_named).append(f)

unexplored.sort(key=lambda f: f["size"], reverse=True)     # 大函数 = 更多逻辑,优先
# importable 按子系统分组计数
from collections import Counter
imp_by_sub = Counter(subsystem(f["exphp"]) for f in importable)

lines = []
W = lines.append
W("# %s 未挖函数地图(给新会话的任务指导)" % VER)
W("")
W("> **版本**：%s（`%s`，imagebase `0x400000`）。本文裸地址默认属该版本；"
  "引用其他版本须写成 `th16:0x…`。" % (VER.upper().replace(".V", " v"), P["exe"].name))
W("> 自动生成:`tooling/ghidra/build_worklist.py %s`(交叉当前工程快照 × ExpHP th-re-data)。" % _A.version)
W("> 重生成:`python tooling/ghidra/build_worklist.py %s`。本表 = %s。" % (_A.version, VER))
W("")
W("## 总览")
W("| 类别 | 数量 | 含义 |")
W("| --- | --- | --- |")
W("| 总函数 | %d | 工程内全部 |" % len(OURS))
W("| ✅ 已命名(我们/研究) | %d | 我们反过/命名过(非 FUN_、非 CRT) |" % len(ours_named))
W("| 📥 可从 ExpHP 导入 | %d | 我们还是 FUN_,但 ExpHP 已命名 → 批量导名即得 |" % len(importable))
W("| 🔬 真·待挖 | %d | 我们和 ExpHP 都没命名(非 CRT)= 研究处女地 |" % len(unexplored))
W("| ⚙️ CRT/库/thunk | %d | 编译器运行时,非研究目标 |" % len(crt))
W("")
W("## 📥 可从 ExpHP 导入(低垂果实:先批量导名,白得上下文)")
W("> 这些 ExpHP 已命名、我们工程里还是 `FUN_`。建议先写脚本批量 import(参考 `apply_th16_ecl_names.py` + ExpHP funcs.json),")
W("> 立刻把 ~%d 个函数变可读,再在其上做语义。按子系统分布:" % len(importable))
W("")
W("| 子系统(ExpHP 前缀) | 待导入数 |")
W("| --- | --- |")
for sub, n in imp_by_sub.most_common(30):
    W("| %s | %d |" % (sub, n))
W("")
W("## 🔬 真·待挖函数(谁都没命名,按大小排;大小=字节数,xrefs=被引用数,hint=最近的已命名邻居→子系统线索)")
W("> 这是真正的研究处女地。优先挖**大 + 高 xrefs + hint 指向你关心的子系统**的。⚠️ 个别可能是 Ghidra 没认出的 CRT,反编译时自行判断。")
W("")
W("| addr | size | xrefs | 子系统线索(nearest named) |")
W("| --- | --- | --- | --- |")
for f in unexplored[:60]:
    W("| `%s` | %d | %d | %s |" % (f["addr"], f["size"], f["xrefs"], f.get("hint", "?")))
W("")
W("(共 %d 个真·待挖;上表为最大的 60 个。全量在 `local/%s/%s-funcs.json` 自行筛 name 以 FUN_ 开头者。)"
  % (len(unexplored), VER, _A.version))
W("")
# 按子系统线索聚合待挖函数(帮你"挑一个子系统整片挖")
W("## 🔬 待挖函数按子系统线索聚合(挑一片整体挖)")
W("| 子系统线索 | 待挖数 | 累计字节 |")
W("| --- | --- | --- |")
agg = {}
for f in unexplored:
    h = f.get("hint", "?"); agg.setdefault(h, [0, 0]); agg[h][0]+=1; agg[h][1]+=f["size"]
for h, (n, sz) in sorted(agg.items(), key=lambda kv: kv[1][1], reverse=True)[:25]:
    W("| %s | %d | %d |" % (h, n, sz))

out = REPO / "games" / VER / "unexplored.md"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("named=%d importable=%d unexplored=%d crt=%d -> %s" %
      (len(ours_named), len(importable), len(unexplored), len(crt), out.relative_to(REPO)))
