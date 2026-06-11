#!/usr/bin/env python3
# 批量把 ExpHP th-re-data 的【函数名】导进 th16.exe 的 Ghidra 工程 —— 低垂果实:
# 工程里仍是 FUN_ 且 ExpHP 有意义命名的 ~614 个函数,一次性 rename + 落 [th-re-data] 注释,
# 让全工程瞬间可读,作为后续语义研究(MainMenu 等)的导航底图。
#
# ★ 名字来源 = ExpHP exphp-share/th-re-data(data/th16.v1.00a/funcs.json),社区一手 RE 的 TH16
#   符号表(仅名字,无语义注释)。本仓库已交叉验证语义吻合(ecl/03-thredata-crosscheck.md)。
#   本脚本只导【没人命名(FUN_)】的那部分,绝不覆盖我们已命名的 261 个、也不碰 ExpHP 的
#   sub_/thunk/nullsub/j_/? 占位名(口径与 build_worklist.py 的 "importable" 完全一致 = 614)。
#
# 落盘:函数名经 GhidraProject driver + 显式 proj.saveProgram() 持久(见 memory ghidra-mcp-save-broken;
#   pyghidra CLI / analyzeHeadless-postScript 不持久化)。机械确定性套用一律写脚本,勿派 agent
#   (memory re-workflow-fanout-cost)。
#
# ⚠️ 运行前先 MCP close_database 释放 ghidra_projects/th16.exe 锁!
# 用法:GHIDRA_INSTALL_DIR=/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC \
#       JAVA_HOME=/data/sunyunbo/miniconda3/envs/ghidra \
#       /data/sunyunbo/miniconda3/envs/ghidra/bin/python funcs/apply_th16_thredata_bulk_names.py
# 仅 TH16 v1.00a(imagebase 0x400000)。
import json, re
import pyghidra
pyghidra.start()
from ghidra.base.project import GhidraProject
from ghidra.program.model.symbol import SourceType
from ghidra.program.model.listing import CodeUnit

ROOT = "/data/sunyunbo/www/THTK-Studio-2/research"
PROJ_DIR = ROOT + "/files/ghidra_projects"
EXP = json.load(open(ROOT + "/ecl/vendor/th-re-data/data/th16.v1.00a/funcs.json"))

US = SourceType.USER_DEFINED

def norm(a):
    return a.lower().replace("0x", "").lstrip("0").rjust(1, "0")

def ex_meaningful(n):
    return bool(n) and not re.match(r'^(sub_|thunk|nullsub|j_|\?|FID_)', n)

def sanitize(n):
    # 与既有约定一致:"::" -> "__";其余 Ghidra 符号非法字符(空格/()&+<>等)-> "_"
    n = n.replace("::", "__")
    n = re.sub(r'[^A-Za-z0-9_]', '_', n)
    return n

ex_by = {norm(x["addr"]): x["name"] for x in EXP if ex_meaningful(x["name"])}

proj = GhidraProject.openProject(PROJ_DIR, "th16.exe", False)
prog = proj.openProgram("/", "th16.exe", False)   # 可写
fm = prog.getFunctionManager()
af = prog.getAddressFactory()
listing = prog.getListing()

def va(off):
    return af.getDefaultAddressSpace().getAddress(off)

tx = prog.startTransaction("bulk import th-re-data function names")
renamed = miss = skip_named = collide = 0
try:
    for f in fm.getFunctions(True):
        cur = f.getName()
        if not cur.startswith("FUN_"):          # 只导没人命名的;不覆盖我们/已有命名
            skip_named += 1
            continue
        a = norm("0x%08x" % f.getEntryPoint().getOffset())
        raw = ex_by.get(a)
        if raw is None:                          # ExpHP 也没有意义命名 -> 真·待挖,留着
            continue
        name = sanitize(raw)
        try:
            f.setName(name, US)
        except Exception:
            # 极少数同名冲突:加地址后缀重试
            try:
                f.setName("%s_%s" % (name, a), US); collide += 1
            except Exception as e:
                print("  [FAIL] 0x%s %s: %s" % (a, name, e)); miss += 1; continue
        ep = f.getEntryPoint()
        listing.setComment(ep, CodeUnit.PLATE_COMMENT, "[th-re-data] %s" % raw)
        renamed += 1
finally:
    prog.endTransaction(tx, True)

proj.save(prog)
proj.close()
print("[bulk_names] renamed=%d collide_suffixed=%d fail=%d (skipped already-named=%d)"
      % (renamed, collide, miss, skip_named))
