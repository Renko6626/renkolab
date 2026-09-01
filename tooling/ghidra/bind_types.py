#!/usr/bin/env python3
"""把 ExpHP 的结构体**绑到函数签名上** —— 让反编译从 `param_1 + 0x54` 变成 `self->flags`。

ExpHP 给的是「名字 + 结构体布局」，**不给绑定**（哪个函数的哪个参数是哪个类型）。
没绑之前，`CardTenshi__c_press` 长这样：

    undefined4 __fastcall CardTenshi__c_press(int param_1)
        if ((*(int *)(param_1 + 0x54) == 0) && (*(int *)(param_1 + 0x38) < 1)) {

绑上之后是 `zCardBaseClass *self`，字段名直接出来。**这是这个库里投入产出比最高的一步。**

## 三层回退口子（这事会手滑，也可能 ExpHP 就是错的）

1. **`--revert`**：重算一遍计划，凡 DB 里的签名**仍等于我们当初写进去的**，就恢复成
   Ghidra 自动推断（`SourceType.DEFAULT`）。**被人改过的一律跳过并报出来**——
   我们只收自己下的蛋。
2. **git**：绑定会被 `symbols.py export` 吸进 `games/<版本>/symbols.json` 并入库。
   `git checkout` 那个文件 + `bootstrap.py --reanalyze` = 干净重建，绑定全消失。
3. **不覆盖既有人工签名**：任何 `getSignatureSource() == USER_DEFINED` 的函数默认跳过
   （那是人或我们那层的决定），要压过去得显式 `--force`。

外加**预防**：默认只跑 `--dry-run`（出计划不写库）；`--sample K` 会把 K 个函数绑定
前后的反编译写成对照报告，先看了再决定。

## 规则是数据，不是代码

规则在 `tooling/ghidra/bindings/<版本目录名>.json`，入库、可 diff、可 review：

- `vtable_rules`（tier 1，默认应用）：签名**逐字取自 ExpHP 的 vtable 成员注释**
  （`void (*)(struct zCardBaseClass*, struct zPlayer*)`），函数名后缀 == 槽名。
  th18 里只有 `zVTableCard` 给了真签名，其余 vtable 的注释是 `void*`，无从取用。
- `this_rules`（tier 2，`--tier 2` 才应用）：只绑 **this 一个参数** + 调用约定，
  其余参数保持 Ghidra 的推断不动 —— 信息量最大化、风险最小化。
- `ambiguous`：**故意不绑**的族，每条写清理由。`Player__*` 就在里面：
  它的 this 有时是 `zPlayer*` 有时是 `zPlayerInner*`，一刀切必错。

    bind_types.py th18                 # 出计划（不写库）
    bind_types.py th18 --sample 6      # 出计划 + 6 个函数的前后反编译对照（不写库）
    bind_types.py th18 --apply         # 应用 tier 1
    bind_types.py th18 --apply --tier 2
    bind_types.py th18 --revert        # 撤销我们下过的蛋
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _driver import REPO, add_project_args, ghidra_install, open_program, resolve   # noqa: E402
from import_th_re_data import _san                                                 # noqa: E402

RULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bindings")

# ExpHP 注释里的 C 类型 → Ghidra 内建名。别指望 DataTypeParser 认识 int32_t。
TYPEMAP = {
    "int8_t": "char", "uint8_t": "byte", "int16_t": "short", "uint16_t": "ushort",
    "int32_t": "int", "uint32_t": "uint", "int64_t": "longlong", "uint64_t": "ulonglong",
    "bool": "bool", "float": "float", "double": "double", "void": "void", "char": "char",
}


# ──────────────────────────────────────────────────────── 解析 ExpHP 的 vtable 注释

def norm_type(s):
    """`struct zPlayer*` -> `zPlayer *`；`int32_t` -> `int`。"""
    s = re.sub(r"\b(struct|union|enum)\b", " ", s).strip()
    stars = s.count("*")
    base = s.replace("*", "").strip()
    base = TYPEMAP.get(base, base)
    return (base + " " + "*" * stars).strip() if stars else base


def split_args(s):
    """按深度 0 的逗号切参数表。"""
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return [a.strip() for a in out if a.strip()]


FUNCPTR = re.compile(r"^\s*(?P<ret>[\w \t*]+?)\s*\(\s*\*\s*\)\s*\((?P<args>.*)\)\s*$", re.S)


def parse_funcptr(comment):
    """`void (*)(struct zCardBaseClass*, int32_t short_timer)` -> (ret, [(type,name)...])

    认不出来返回 None —— th18 里多数 vtable 的注释就是个 `void*`，认不出是正常的。
    """
    if not comment:
        return None
    m = FUNCPTR.match(comment.strip())
    if not m:
        return None
    args = []
    for a in split_args(m.group("args")):
        if a in ("void", ""):
            continue
        # 先摘掉 struct/union/enum 关键字再切词，否则 `struct zAnmId` 会把 zAnmId 当成参数名
        toks = re.sub(r"\b(struct|union|enum)\b", " ", a).split()
        # 末尾是裸标识符（不带 *）就当参数名，否则整串都是类型
        name = None
        if len(toks) > 1 and re.fullmatch(r"[A-Za-z_]\w*", toks[-1]) and toks[-1] not in TYPEMAP:
            name, toks = toks[-1], toks[:-1]
        args.append((norm_type(" ".join(toks)), name))
    return norm_type(m.group("ret")), args


def load_vtables(data_dir):
    """{vtable 名: {槽名: (ret, [(type,name)...])}}，只收注释里真有 C 签名的。"""
    out = {}
    if not data_dir:
        return out
    structs = {}
    for fn in ("type-structs-own.json", "type-structs-ext.json"):
        p = os.path.join(data_dir, fn)
        if os.path.exists(p):
            structs.update(json.load(open(p, encoding="utf-8")))
    for name, rows in structs.items():
        slots = {}
        for row in rows:
            if len(row) < 3:
                continue
            _off, member, comment = row[0], row[1], row[2]
            if not member or member == "__end":
                continue
            sig = parse_funcptr(comment)
            if sig:
                slots[_san(member)] = sig
        if slots:
            out[_san(name)] = slots
    return out


# ──────────────────────────────────────────────────────── 子类结构体（防止 self[1].x 那种误导）

def ensure_subclass_structs(prog, cfg, dry=False):
    """给每个比基类大的卡类建一个「基类字段 + 尾部填充」的同名结构体。

    不建的话，绑 `zCardBaseClass *`(0x54) 之后，子类自有字段会被 Ghidra 渲染成
    `self[1].card_id` —— 那是**误导**：真身是 `card+0x58`，一个浮点坐标。
    建了之后同一处显示成 `self->field_0x58`，偏移一眼可回推，不骗人。

    幂等：已存在且长度正确就原样复用。
    """
    from ghidra.program.model.data import (CategoryPath, DataTypeConflictHandler,
                                           StructureDataType)
    out = {}
    if not cfg:
        return out, dict(made=0, reused=0, failed=0)
    dtm = prog.getDataTypeManager()
    base = dtm.getDataType(CategoryPath("/"), cfg["base"])
    if base is None:
        return out, dict(made=0, reused=0, failed=len(cfg.get("sizes", {})))
    n = dict(made=0, reused=0, failed=0)
    for cls, size_hex in cfg.get("sizes", {}).items():
        size = int(size_hex, 16)
        if size <= base.getLength():
            continue                              # 不比基类大，直接用基类
        name = cfg["name_template"].format(cls=cls)
        cur = dtm.getDataType(CategoryPath("/"), name)
        if cur is not None and cur.getLength() == size:
            out[cls] = name + " *"
            n["reused"] += 1
            continue
        if dry:
            out[cls] = name + " *"
            n["made"] += 1
            continue
        try:
            s = StructureDataType(CategoryPath("/"), name, size, dtm)
            for c in base.getComponents():
                if c.getFieldName() is None:
                    continue
                s.replaceAtOffset(c.getOffset(), c.getDataType(), c.getLength(),
                                  c.getFieldName(), c.getComment())
            dtm.addDataType(s, DataTypeConflictHandler.REPLACE_HANDLER)
            out[cls] = name + " *"
            n["made"] += 1
        except Exception:                                            # noqa: BLE001
            n["failed"] += 1
    return out, n


# ──────────────────────────────────────────────────────── 出计划

def load_rules(version_dirname, path=None):
    p = path or os.path.join(RULES_DIR, f"{version_dirname}.json")
    if not os.path.exists(p):
        sys.exit(f"[bind] 没有规则文件 {p} —— 新版本要先写一份，照 th18.v1.00a.json 抄。")
    return json.load(open(p, encoding="utf-8")), p


def build_plan(prog, rules, vtables, tier, subclass=None):
    """算出「该把哪些函数绑成什么」。纯计算，不碰 DB 状态。"""
    fm = prog.getFunctionManager()
    skip_addrs = {int(a, 16) for a in rules.get("skip_addrs", [])}
    amb = [(re.compile(r["pattern"]), r.get("why", "")) for r in rules.get("ambiguous", [])]
    vrules = [r for r in rules.get("vtable_rules", []) if r.get("tier", 1) <= tier]
    trules = [r for r in rules.get("this_rules", []) if r.get("tier", 2) <= tier]
    for r in vrules:
        r["_re"] = re.compile(r["name_pattern"])
    for r in trules:
        r["_re"] = re.compile(r["pattern"])

    plan, stats = [], dict(vtable=0, this=0, ambiguous=0, no_slot=0, skipped_addr=0)
    for f in fm.getFunctions(True):
        addr, name = f.getEntryPoint().getOffset(), f.getName()
        if addr in skip_addrs:
            stats["skipped_addr"] += 1
            continue
        if any(rx.search(name) for rx, _ in amb):
            stats["ambiguous"] += 1
            continue

        hit = None
        for r in vrules:
            m = r["_re"].match(name)
            if not m:
                continue
            slot = m.groupdict().get("slot")
            slot = r.get("slot_aliases", {}).get(slot, slot)
            sig = vtables.get(r["vtable"], {}).get(slot)
            if sig is None:
                stats["no_slot"] += 1
                break
            ret, args = sig
            this_ty = (subclass or {}).get(m.groupdict().get("cls"), r["this"])
            params = [{"name": "self", "type": this_ty}]
            for i, (ty, pname) in enumerate(args[1:], 1):        # args[0] 是 this，用规则里的具体类型
                params.append({"name": pname or f"a{i}", "type": ty})
            # 我们的一手结论压过 ExpHP 的注释（它的 vtable 签名并非处处可信）
            for i, ov in enumerate(r.get("slot_param_overrides", {}).get(slot) or []):
                if ov and i < len(params):
                    params[i] = {"name": ov["name"], "type": ov["type"]}
            hit = dict(kind="vtable", rule=r["vtable"] + "." + slot,
                       cc="__thiscall", ret=ret, params=params)
            break
        if hit is None:
            for r in trules:
                if r["_re"].match(name):
                    hit = dict(kind="this", rule=r["pattern"], cc="__thiscall",
                               ret=None, params=None, this=r["this"])
                    break
        if hit is None:
            continue
        hit.update(addr=addr, name=name)
        plan.append(hit)
        stats[hit["kind"]] += 1
    return plan, stats


# ──────────────────────────────────────────────────────── 读 / 写 DB 签名

def read_sig(f):
    return dict(cc=f.getCallingConventionName(),
                ret=f.getReturnType().getName(),
                params=[{"name": p.getName(), "type": p.getDataType().getName(),
                          "auto": bool(p.isAutoParameter())}
                        for p in f.getParameters()])


def same_sig(a, b):
    if a is None or b is None:
        return False
    if a["cc"] != b["cc"] or a["ret"] != b["ret"]:
        return False
    if len(a["params"]) != len(b["params"]):
        return False
    return all(x["name"] == y["name"] and x["type"].replace(" ", "") == y["type"].replace(" ", "")
               for x, y in zip(a["params"], b["params"]))


def make_writer(prog):
    """写签名。

    ⚠️ **必须用自定义存储**，这是踩出来的：`__thiscall` 下 Ghidra 会自己插一个 auto 参数
    `this`（ECX，类型 `void *`，**改不动**），显式参数一律从 `Stack[0x4]` 起。所以若按
    「动态存储 + 把 self 当第一个显式参数」去写，self 会落到第一个**栈**参数位上，
    把真正的第一个参数整体挤后一格 —— 实测把
    `CardChimata__operator_delete(this, bool should_deallocate)` 写成了
    `(void *this, zCardBaseClass *self, bool should_deallocate)`，纯错。

    自定义存储把 self 钉在 ECX，其余参数按 Stack[0x4]、[0x8]… 排，与 Ghidra 自己
    对同类函数推断出的布局逐字一致（probe 过 AbilityManager__allocate_new_card）。
    """
    from ghidra.program.model.data import CategoryPath
    from ghidra.program.model.listing import (Function, ParameterImpl, ReturnParameterImpl,
                                              VariableStorage)
    from ghidra.program.model.symbol import SourceType
    from ghidra.util.data.DataTypeParser import AllowedDataTypes
    from ghidra.util.data import DataTypeParser

    dtm = prog.getDataTypeManager()
    parser = DataTypeParser(dtm, dtm, None, AllowedDataTypes.ALL)
    US, DEF = SourceType.USER_DEFINED, SourceType.DEFAULT
    ECX = prog.getRegister("ECX")

    def dt(spec):
        try:
            return parser.parse(spec)
        except Exception:                                            # noqa: BLE001
            return None

    def write(f, cc, ret, params):
        """params[0] 必须是 this；它去 ECX，其余按 4 字节对齐排栈。"""
        rt = dt(ret or "void")
        if rt is None:
            return False
        types = []
        for p in params:
            d = dt(p["type"])
            if d is None:
                return False
            types.append(d)
        try:
            # 返回值也得给存储：CUSTOM_STORAGE 下留 <UNASSIGNED> 会让反编译把
            # 1 字节的 bool 渲染成 undefined4（DB 里类型是对的，只是看不出来）。
            if rt.getLength() <= 0 or rt.getName() == "void":
                rv = ReturnParameterImpl(rt, prog)
            else:
                reg = {1: "AL", 2: "AX", 8: "EDX:EAX"}.get(rt.getLength(), "EAX")
                rv = ReturnParameterImpl(rt, VariableStorage(prog, prog.getRegister(reg)), prog)
            vs = [ParameterImpl(params[0]["name"], types[0],
                                VariableStorage(prog, ECX), prog)]
            off = 4
            for p, d in zip(params[1:], types[1:]):
                size = max(1, d.getLength())
                vs.append(ParameterImpl(p["name"], d, VariableStorage(prog, off, size), prog))
                off += (size + 3) // 4 * 4                 # 栈槽按 4 字节步进
            # ⚠️ 必须走 varargs 重载：传 python list 的那个 List<Variable> 重载在
            # JPype 下匹配不上（No matching overloads found）。踩过。
            f.updateFunction(cc, rv,
                             Function.FunctionUpdateType.CUSTOM_STORAGE, True, US, *vs)
            # CUSTOM_STORAGE 下 ReturnParameterImpl 兜不住 1 字节返回（bool 会退化成
            # undefined4），补一刀把返回类型钉死。
            f.setReturnType(rt, US)
        except Exception:                                            # noqa: BLE001
            return False
        return True

    def clear(f):
        """恢复成 Ghidra 自动推断。"""
        f.setCustomVariableStorage(False)
        f.updateFunction(None, None, Function.FunctionUpdateType.DYNAMIC_STORAGE_FORMAL_PARAMS,
                         True, DEF)
        # 返回类型也要退干净，否则 revert 不是严格的逆运算（会留下我们写进去的返回类型）
        und = dtm.getDataType(CategoryPath("/"), "undefined")
        if und is not None:
            f.setReturnType(und, DEF)
        f.setSignatureSource(DEF)

    return write, clear, read_sig


# ──────────────────────────────────────────────────────── 反编译对照报告

def decompile(prog, f, timeout=45):
    from ghidra.app.decompiler import DecompInterface
    from ghidra.util.task import ConsoleTaskMonitor
    di = DecompInterface()
    try:
        di.openProgram(prog)
        r = di.decompileFunction(f, timeout, ConsoleTaskMonitor())
        if r and r.decompileCompleted():
            return r.getDecompiledFunction().getC()
    except Exception as e:                                           # noqa: BLE001
        return f"<反编译失败: {e}>"
    finally:
        try:
            di.dispose()
        except Exception:                                            # noqa: BLE001
            pass
    return "<反编译失败>"


def head(text, n=26):
    return "\n".join(text.split("\n")[:n])


# ──────────────────────────────────────────────────────── 清单（回退的依据）

def manifest_path(pd):
    return REPO / "games" / pd["vdir"].name / "bindings.json"


def load_manifest(pd):
    p = manifest_path(pd)
    if not p.exists():
        return {"entries": []}
    return json.loads(p.read_text(encoding="utf-8"))


def save_manifest(pd, entries, rules_path, tier):
    p = manifest_path(pd)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "_README": "bind_types.py 下过的蛋，逐条记录**写完之后读回来的**签名。"
                   "`bind_types.py <ver> --revert` 按它回退：签名仍等于这里记的才恢复，"
                   "被人改过的一律跳过。删掉这个文件 = 放弃细粒度回退（还剩 git + bootstrap --reanalyze）。",
        "generated_by": "tooling/ghidra/bind_types.py",
        "rules": os.path.relpath(rules_path, REPO),
        "tier": tier,
        "count": len(entries),
        "entries": entries,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return p


# ──────────────────────────────────────────────────────── main

def main():
    ap = argparse.ArgumentParser(description="把 ExpHP 结构体绑到函数签名（可 dry-run / 可回退）")
    ap.add_argument("version", help="th16 / th18")
    ap.add_argument("--rules", help="规则文件路径（默认 bindings/<版本目录名>.json）")
    ap.add_argument("--tier", type=int, default=1, help="应用到哪一层（1=只高置信，2=含只绑 this）")
    ap.add_argument("--apply", action="store_true", help="真的写库（默认只出计划）")
    ap.add_argument("--revert", action="store_true", help="按 bindings.json 回退我们下过的蛋")
    ap.add_argument("--force", action="store_true", help="连既有人工签名一起覆盖（危险）")
    ap.add_argument("--sample", type=int, default=0, help="额外产出 N 个函数绑定前后的反编译对照")
    ap.add_argument("--report", help="对照报告写到哪（默认 local/<版本>/state/bindings-report.txt）")
    a = ap.parse_args()

    ghidra_install()
    pd = resolve(a.version)
    rules, rules_path = load_rules(pd["vdir"].name, a.rules)
    vtables = load_vtables(str(pd["data_dir"]) if pd["data_dir"] else None)
    write_mode = a.apply or a.revert

    with open_program(str(pd["proj_dir"]), pd["proj_name"], pd["program"],
                      tx=("bind_types 回退" if a.revert else "bind_types 绑定") if write_mode else None,
                      commit=write_mode) as prog:
        fm = prog.getFunctionManager()
        af = prog.getAddressFactory().getDefaultAddressSpace().getAddress
        write, clear, read = make_writer(prog)

        # ── 回退：只认清单，不重算规则（规则改了也照样能退干净） ──
        if a.revert:
            man = load_manifest(pd)
            n = dict(done=0, changed=0, missing=0)
            for e in man["entries"]:
                f = fm.getFunctionAt(af(int(e["addr"], 16)))
                if f is None:
                    n["missing"] += 1
                    continue
                if not same_sig(read(f), e["sig"]):
                    n["changed"] += 1          # 应用之后被人改过 → 不碰，报出来
                    continue
                clear(f)
                n["done"] += 1
            print(f"[bind] 回退 {n['done']} 条 · 之后被改过所以不动 {n['changed']}"
                  f" · 函数不存在 {n['missing']}（清单 {len(man['entries'])} 条）")
            if n["done"]:
                save_manifest(pd, [e for e in man["entries"]
                                   if fm.getFunctionAt(af(int(e["addr"], 16))) is not None
                                   and same_sig(read(fm.getFunctionAt(af(int(e["addr"], 16)))),
                                                e["sig"])],
                              rules_path, man.get("tier", a.tier))
            print("[bind] 记得跑 tooling/ghidra/symbols.py export " + a.version)
            return

        subclass, sn = ensure_subclass_structs(prog, rules.get("subclass_structs"),
                                               dry=not a.apply)
        plan, stats = build_plan(prog, rules, vtables, a.tier, subclass)
        vt_slots = sum(len(v) for v in vtables.values())
        print(f"[bind] 子类结构体：新建/更新 {sn['made']} · 复用 {sn['reused']} · 失败 {sn['failed']}")
        print(f"[bind] 规则 {os.path.relpath(rules_path, REPO)}"
              f" · zVTableCard 等带签名的 vtable {len(vtables)} 个 / 槽 {vt_slots} 个")
        print(f"[bind] 计划 {len(plan)} 条：vtable {stats['vtable']} · this {stats['this']}"
              f" | 故意跳过：ambiguous {stats['ambiguous']}"
              f" · 槽名对不上 {stats['no_slot']} · 地址黑名单 {stats['skipped_addr']}")

        n = dict(done=0, already=0, human=0, failed=0, missing=0)
        samples, entries, want = [], [], a.sample
        # 幂等：上次下过的蛋若原样还在，就算「已是目标态」，别误报成「人工签名」
        prev = {e["addr"]: e for e in load_manifest(pd).get("entries", [])}

        for e in plan:
            f = fm.getFunctionAt(af(e["addr"]))
            if f is None:
                n["missing"] += 1
                continue
            cur = read(f)
            if e["kind"] == "this":                    # 只换 this，其余参数原样保留
                rest = [dict(p) for p in cur["params"] if not p.get("auto")][1:]
                target = dict(cc="__thiscall", ret=cur["ret"],
                              params=[{"name": "self", "type": e["this"]}] + rest)
            else:
                target = dict(cc=e["cc"], ret=e["ret"], params=e["params"])

            key = "0x%08x" % e["addr"]
            was = prev.get(key)
            # 幂等判据要两头都对：①「这次想要的」== 上次想要的（规则改了就得重来）
            #                    ②「库里现在的」== 上次写完读回来的（没人动过）
            if (was and not a.force
                    and same_sig(target, was.get("want")) and same_sig(cur, was["sig"])):
                n["already"] += 1
                entries.append(was)
                continue
            if str(f.getSignatureSource()) == "USER_DEFINED" and not a.force:
                n["human"] += 1                     # 人工/我们那层的决定，不覆盖
                continue

            before = decompile(prog, f) if (want and len(samples) < want) else None
            if a.apply:
                if not write(f, target["cc"], target["ret"], target["params"]):
                    n["failed"] += 1
                    continue
                entries.append({"addr": "0x%08x" % e["addr"], "name": e["name"],
                                "rule": e["rule"],
                                "want": target,        # 这次要求的（规则变了能看出来）
                                "sig": read(f)})       # 写完读回来的（回退比对用）
            n["done"] += 1
            if before is not None:
                samples.append((e["name"], "0x%08x" % e["addr"], e["rule"], before,
                                decompile(prog, f) if a.apply else "<--dry-run，未应用>"))

        print(f"[bind] {'应用' if a.apply else '待应用（dry-run）'} {n['done']} 条"
              f" · 已是目标态 {n['already']} · 保护既有人工签名 {n['human']}"
              f" · 写入失败 {n['failed']} · 函数不存在 {n['missing']}")

        if samples:
            out = a.report or str(pd["vdir"] / "state" / "bindings-report.txt")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "w", encoding="utf-8") as fh:
                for name, addr, rule, b, af_ in samples:
                    fh.write(f"{'='*78}\n{name}  {addr}   [{rule}]\n{'-'*78}\n"
                             f"--- 绑定前 ---\n{head(b)}\n\n--- 绑定后 ---\n{head(af_)}\n\n")
            print(f"[bind] 对照报告 -> {os.path.relpath(out, REPO)}（{len(samples)} 个函数）")

        if a.apply:
            mp = save_manifest(pd, entries, rules_path, a.tier)
            print(f"[bind] 清单 -> {os.path.relpath(mp, REPO)}（{len(entries)} 条，--revert 靠它）")
            print("[bind] 干完记得：tooling/ghidra/symbols.py export " + a.version)
        else:
            print("[bind] 只出了计划，没写库。确认无误后加 --apply。")


if __name__ == "__main__":
    main()
