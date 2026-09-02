#!/usr/bin/env python3
"""card-expand 站点扫描器 / thcrap patch 生成器。

    python3 sites.py list             # 25 个查表实例的全表
    python3 sites.py check            # 只校验(CI / make check 用)
    python3 sites.py gen --rows 58 -o ../patch/th18.v1.00a.js

不依赖任何外部反汇编器，不写死任何机器上的路径。

**为什么必须生成而不是手写**：99 处 `expected` 手写等于必然出错，而 thcrap
对 `expected` 不匹配的处理是「记一行日志然后跳过」（binhack.cpp:1420）——
对整表搬迁来说，部分应用就是灾难。

两层结构：
  shape.py  —— **权威**站点来源，整体匹配内联查表的骨架，
                每次命中自带「四条臂配套」的保证；
  x86imm.py —— **完整性审计**，扫出所有撞上这些值的地方，
                凡不在已匹配站点内的都列出来人工过目。
"""
import argparse, hashlib, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from shape import find_all, find_walks, ShapeError             # noqa: E402
from x86imm import classify, UnknownEncoding, Ambiguous       # noqa: E402

REPO    = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
VERSION = "th18.v1.00a"
EXE     = os.path.join(REPO, "local", VERSION, "th18.exe")
EXE_MD5 = "9969cac756098c1da05a81de45437a70"

# ---- 死绑量（出处：engine/card/th18/11-sentinels-56-57.md 的一手穷举）----
TABLE_BASE = 0x4c53c0     # zTableCardData[]
ROW_SIZE   = 0x34
ROW_COUNT  = 58           # 零售行数
NULL_ROW   = 56           # 查不到时的回退行 = 行 56 ("NULL")
TABLE_END  = TABLE_BASE + ROW_COUNT * ROW_SIZE        # 0x4c5f88
FALLBACK   = TABLE_BASE + NULL_ROW  * ROW_SIZE        # 0x4c5f20
CODECAVE   = "th18_card_table"
CAVE_INIT  = CODECAVE + "_patch_init"
TABLE_RVA  = 0x0c53c0     # = TABLE_BASE - imagebase；用 thcrap 的 Rx 记法,不写死基址

PART_ORDER = ("start", "end", "fallback", "hit")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_text_section(path):
    """极简 PE 解析：返回 (.text 字节, .text 的 VA, .text 的文件偏移)。"""
    data = open(path, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3c)[0]
    assert data[pe:pe + 4] == b"PE\0\0", "不是 PE"
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt_size = struct.unpack_from("<H", data, pe + 20)[0]
    imagebase = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    sec = pe + 24 + opt_size
    for i in range(nsec):
        off = sec + i * 40
        name = data[off:off + 8].rstrip(b"\0").decode()
        vsize, va, rawsize, rawptr = struct.unpack_from("<IIII", data, off + 8)
        if name == ".text":
            return data[rawptr:rawptr + rawsize], imagebase + va, rawptr
    raise SystemExit("找不到 .text")


def check_invariants(inst):
    """两条不变式 —— 它们就是「搬表不会静默算错」的全部依据。

    ① `END - TABLE_END == LOOP_START - TABLE_BASE`
       循环比较的字段和终止条件必须是同一个字段。
    ② `FALLBACK - 回退行基址 == HIT_ARM - TABLE_BASE`
       两条臂必须取同一个字段；否则「查到」和「查不到」返回的不是一种东西。

    ★ 违反 ② 正是整表搬迁唯一会**静默算错**的失败模式：LOOP_START 指了新表、
      HIT_ARM 还指旧表时，`下标 * 0x34 + 旧基址` 会返回另一张卡的行——
      不崩、不报错。所以必须按实例校验，不能按站点。
    """
    bad = []
    for x in inst:
        p = x["parts"]
        f_start = p["start"]["value"] - TABLE_BASE
        f_end   = p["end"]["value"]   - TABLE_END
        f_fb    = p["fallback"]["value"] - FALLBACK
        f_hit   = p["hit"]["value"]   - TABLE_BASE
        if not (0 <= f_start < ROW_SIZE and 0 <= f_fb < ROW_SIZE):
            bad.append("0x%06x：字段偏移越界" % x["anchor"])
        elif f_start != f_end:
            bad.append("0x%06x：循环比较 +0x%x 但终止于 +0x%x"
                       % (x["anchor"], f_start, f_end))
        elif f_fb != f_hit:
            bad.append("0x%06x：★ 两条臂字段不一致 命中+0x%x vs 回退+0x%x"
                       % (x["anchor"], f_hit, f_fb))
        x["field_cmp"], x["field_ret"] = f_start, f_fb
    return bad


def collect_sites(inst, walks):
    """去重后的待改站点：{va: {part, rec, insts}}。"""
    sites = {}
    for x in walks:
        p = x["parts"]["start"]
        sites[p["va"]] = {"part": "start", "rec": p, "insts": 1}
    for x in inst:
        for k in PART_ORDER:
            p = x["parts"][k]
            cur = sites.setdefault(p["va"], {"part": k, "rec": p, "insts": 0})
            cur["insts"] += 1
            if cur["part"] != k:
                raise ShapeError("0x%06x 同时被当成 %s 和 %s" % (p["va"], cur["part"], k))
    return sites


def audit_uncovered(text, text_va, sites):
    """完整性审计：扫出所有撞上这三段值的地方，列出不在已匹配站点内的。

    这些**不该被改**——它们要么是同名的热全局（`0x4c5f88` / `0x4c5f8c`
    同时是两个被大量读写的 int 全局），要么是别的表。列出来是为了让人
    确认「漏掉的都是该漏的」。
    """
    covered = set()
    for va, s in sites.items():
        for k in range(s["rec"]["len"]):
            covered.add(va + k)
    ranges = list(range(TABLE_BASE, TABLE_BASE + ROW_SIZE)) + \
             list(range(FALLBACK, FALLBACK + ROW_SIZE)) + \
             list(range(TABLE_END, TABLE_END + 5))
    out = []
    for v in ranges:
        needle = struct.pack("<I", v)
        p = text.find(needle)
        while p >= 0:
            if (text_va + p) not in covered:
                try:
                    info = classify(text, p, text_va, 0)
                    desc, kind = info["text"], info["kind"]
                except (UnknownEncoding, Ambiguous):
                    desc, kind = "(无法归类)", "?"
                out.append((text_va + p, v, kind, desc))
            p = text.find(needle, p + 1)
    out.sort()
    return out


def audit_interior(path, sites):
    """完整性检查之二：**整张表的地址区间**在全文件里还有没有别的引用。

    前一项审计只扫「表基 / 回退行 / 表尾」三小段，扫不到「直接引用第 12 行」
    这种写法（`0x4c53c0 + 12*0x34` 落在三段之外）。这里把
    `[表基, 表尾)` 整段 0xbc8 字节的地址全扫一遍，分两路：
      · `.text` 里 —— 漏掉就是漏掉一个必须改的站点；
      · 数据节里 4 字节对齐的 —— 那会是「指向表内某行的指针表」，同样要跟着搬。
    两路当前都是 **0 处**，所以那 100 处就是全集。
    """
    data = open(path, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3c)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    ib = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    secs = []
    for i in range(nsec):
        o = pe + 24 + opt + i * 40
        nm = data[o:o + 8].rstrip(b"\0").decode()
        vs, va, rs, rp = struct.unpack_from("<IIII", data, o + 8)
        secs.append((nm, ib + va, rp, rs))
    covered = set()
    for va, s_ in sites.items():
        for k in range(s_["rec"]["len"]):
            covered.add(va + k)
    lo, hi = TABLE_BASE, TABLE_BASE + ROW_COUNT * ROW_SIZE
    in_text, in_data = [], []
    for nm, sva, rp, rs in secs:
        step = 1 if nm == ".text" else 4
        for off in range(rp, rp + max(rs - 4, 0), step):
            v = struct.unpack_from("<I", data, off)[0]
            if not (lo <= v < hi):
                continue
            va = sva + (off - rp)
            if nm == ".text":
                if any((va - k) in covered for k in range(8)):
                    continue
                in_text.append((va, v))
            else:
                in_data.append((nm, va, v))
    return secs, in_text, in_data


def new_offset(part, rec, rows):
    """这个站点在新表里应该指向的偏移（相对 codecave 基址）。"""
    if part == "start":
        return rec["value"] - TABLE_BASE
    if part == "hit":
        return rec["value"] - TABLE_BASE
    if part == "fallback":
        return NULL_ROW * ROW_SIZE + (rec["value"] - FALLBACK)
    return rows * ROW_SIZE + (rec["value"] - TABLE_END)      # end


def emit(sites, rows):
    """生成 thcrap binhacks。

    ⚠️ `<codecave:NAME+OFF>` 里的 OFF **按十六进制解析**
       （expression.cpp `GetCodecaveAddress` → `strtouz(…, 16)`），
       写成看起来像十进制的 `+58` 会被当成 0x58。这里一律输出裸十六进制。
    ⚠️ `expected` 与 `code` **渲染后的长度必须相等**，否则 thcrap 会
       「记一行日志然后跳过校验」（binhack.cpp:1264）——静默丢掉护栏。
       这里由同一份记录同时产出两者，长度天然相等。
    """
    out = {}
    for va in sorted(sites):
        s = sites[va]
        part, rec = s["part"], s["rec"]
        pre = rec["bytes"][:rec["const_at"]].hex()
        off = new_offset(part, rec, rows)
        ref = "<codecave:%s%s>" % (CODECAVE, ("+%x" % off) if off else "")
        out["cardtable_%s_%06x" % (part, va)] = {
            "addr": "0x%06x" % va,
            "code": pre + ref,
            "expected": rec["bytes"].hex(),
            "title": "%s | %s | +0x%x" % (part, rec["text"], off),
        }
    return out


def emit_codecaves(rows):
    """新表 codecave + 一段把零售 58 行**运行时**拷进去的初始化代码。

    ★ 为什么不把表的内容直接写进 patch：那是 ZUN 的数据，仓库不留任何版权字节。
      改成开机时从**用户自己那份 exe**里 memcpy 过来，patch 里只有源码和地址。

    ★ 为什么初始化能放在 `*_patch_init`：它由 `patch_func_init` 调用，而后者在
      `codecaves_apply` 的末尾（binhack.cpp:1724），**早于** `binhacks_apply`
      （runconfig.cpp:655-656）。对「先把表填好、再让改过的代码去读它」来说，
      这个时机正好。
      ⚠️ 反过来说，`*_patch_init` **不能**用来验证 binhack 是否都打上了 ——
      它跑的时候一个 binhack 都还没打。那件事得靠游戏内的断点做。

    调用约定：`typedef void (TH_CDECL *mod_call_type)(void *param)`（plugin.h:71）
    —— cdecl、一个参数、调用方清栈，所以结尾是裸 `ret`，不是 `ret 4`。
    `pushad`/`popad` 覆盖了 cdecl 要求被调方保留的 ebx/esi/ebp/edi；
    `cld` 是为 `rep movsd` 显式确保 DF=0（ABI 本就保证，写出来省得复核时争论）。
    """
    copy_dwords = ROW_COUNT * ROW_SIZE // 4          # 58 * 0x34 / 4 = 754
    assert ROW_COUNT * ROW_SIZE % 4 == 0
    code = [
        "fc",                                        # cld
        "60",                                        # pushad
        "bf<codecave:%s>" % CODECAVE,                # mov edi, 新表
        "be<Rx%x>" % TABLE_RVA,                      # mov esi, 零售表(相对模块基址)
        "b9%s" % struct.pack("<I", copy_dwords).hex(),   # mov ecx, 754
        "f3a5",                                      # rep movsd
    ]
    if rows > ROW_COUNT:
        # 多出来的行全部填成「行 56(NULL)」的副本 —— 它们是**休眠**数据：
        # 查表查到它们只会得到那个无害的哨兵行。真正的新卡数据由游戏内的
        # 激活步骤在**验证过全部 binhack 都生效之后**才写进去。
        row_dwords = ROW_SIZE // 4                   # 13
        assert ROW_SIZE % 4 == 0
        body = ("be<codecave:%s+%x>" % (CODECAVE, NULL_ROW * ROW_SIZE)  # mov esi, 新表+NULL行
                + "b9%s" % struct.pack("<I", row_dwords).hex()          # mov ecx, 13
                + "f3a5"                                                # rep movsd
                + "4b")                                                 # dec ebx
        body_len = 5 + 5 + 2 + 1
        code.append("bb%s" % struct.pack("<I", rows - ROW_COUNT).hex())  # mov ebx, 行数差
        code.append(body)
        code.append("75%02x" % ((256 - (body_len + 2)) & 0xff))          # jnz 回到 body
    code += ["61", "c3"]                             # popad ; ret
    return {
        CODECAVE:  {"size": "0x%x" % (rows * ROW_SIZE), "access": "RW",
                    "title": "zTableCardData[] 搬迁目标（%d 行 × 0x%x）" % (rows, ROW_SIZE)},
        CAVE_INIT: {"code": "".join(code), "export": True, "access": "RX",
                    "title": "开机把零售 58 行从游戏自己的 .rdata 拷进新表"},
    }


def verify_patch(path, text, text_va):
    """对账：把**已生成的 patch 文件**逐条拿回真 exe 核对。

    生成器和被核对的对象分开，才算对账；只信生成器等于没查。
    三件事：
      ① `expected` 与 exe 里该地址的字节完全一致；
      ② `code` 渲染后的长度 == `expected` 的长度
         —— 不等时 thcrap 会**静默跳过校验**（binhack.cpp:1264），护栏白装；
      ③ `code` 的前缀（opcode 部分）与 `expected` 的前缀一致
         —— 只准换常量，不准换指令。
    """
    doc = json.load(open(path, encoding="utf-8"))
    bad = []
    for name, bh in doc["binhacks"].items():
        va = int(bh["addr"], 16)
        off = va - text_va
        exp = bytes.fromhex(bh["expected"])
        if text[off:off + len(exp)] != exp:
            bad.append("%s：exe 里是 %s，expected 写的是 %s"
                       % (name, text[off:off + len(exp)].hex(), bh["expected"]))
            continue
        code = bh["code"]
        i = code.index("<")
        pre = code[:i]
        if code.count("<") != 1 or not code.rstrip().endswith(">"):
            bad.append("%s：code 里的表达式不是「前缀 + 单个 <…>」" % name)
            continue
        if len(pre) % 2:
            bad.append("%s：code 前缀不是整字节" % name)
            continue
        rendered = len(pre) // 2 + 4
        if rendered != len(exp):
            bad.append("%s：code 渲染 %d 字节 != expected %d 字节（thcrap 会静默跳过校验）"
                       % (name, rendered, len(exp)))
        if bytes.fromhex(pre) != exp[:len(pre) // 2]:
            bad.append("%s：code 换掉了 opcode 而不只是常量" % name)
    return len(doc["binhacks"]), bad


def conflicts(ours_path, other_paths):
    """和**同一 patch 栈里其它 patch** 的 hackpoint 求区间交集。

    100 处 5–7 字节的写入点，任何一处被别的 binhack / breakpoint 覆盖都是冲突：
    后应用的那个会看到「expected 不匹配」然后**静默跳过**。
    `base_tsa`（本 mod 声明的依赖）不在仓库 vendor 里，得拿装机上的
    `<thcrap>/repos/nmlgc/base_tsa/th18.v1.00a.js` 来跑。
    """
    ours = json.load(open(ours_path, encoding="utf-8"))["binhacks"]
    mine = [(int(b["addr"], 16), int(b["addr"], 16) + len(bytes.fromhex(b["expected"])), n)
            for n, b in ours.items()]
    found, checked = [], 0
    for path in other_paths:
        d = json.load(open(path, encoding="utf-8"))
        for sect in ("binhacks", "breakpoints", "codecaves"):
            for name, item in (d.get(sect) or {}).items():
                if not isinstance(item, dict) or item.get("addr") is None:
                    continue
                addrs = item["addr"] if isinstance(item["addr"], list) else [item["addr"]]
                for a in addrs:
                    if isinstance(a, dict):
                        a = a.get("addr")
                    if not isinstance(a, str) or not a.lower().startswith("0x"):
                        continue
                    lo = int(a, 16)
                    size = item.get("cavesize") or \
                        (len(bytes.fromhex(item["expected"])) if item.get("expected") else 5)
                    checked += 1
                    for mlo, mhi, mname in mine:
                        if lo < mhi and mlo < lo + size:
                            found.append((os.path.basename(os.path.dirname(path)) or path,
                                          sect, name, a, mname))
    return checked, found


def emit_header(sites, rows):
    """给 DLL 生成站点表：post_init 用它回读验证 100 处。

    只有 RVA、长度、opcode 前缀（1–3 字节，已在 patch 的 expected 里）、
    以及相对 codecave 的偏移——**不含游戏数据**。改后应有的 4 字节由 DLL 在
    运行时按 `cave + off` 算，因为 codecave 地址只有运行时才知道。
    """
    lines = [
        "/* 由 sites.py 生成，不要手改。*/",
        "#pragma once",
        "#include <stdint.h>",
        "#define CE_ROWS        %d" % rows,
        "#define CE_ROW_SIZE    0x%x" % ROW_SIZE,
        "#define CE_ROW_COUNT   %d" % ROW_COUNT,
        "#define CE_NULL_ROW    %d" % NULL_ROW,
        "#define CE_TABLE_RVA   0x%06x" % TABLE_RVA,
        "#define CE_CAVE_NAME   \"codecave:%s\"" % CODECAVE,
        "typedef struct { uint32_t rva; uint8_t len, prefix_len, prefix[3]; uint32_t off; } ce_site_t;",
        "static const ce_site_t CE_SITES[] = {",
    ]
    for va in sorted(sites):
        s_ = sites[va]
        rec = s_["rec"]
        pre = rec["bytes"][:rec["const_at"]]
        assert 1 <= len(pre) <= 3
        pfx = ", ".join("0x%02x" % b for b in pre) + (", 0" * (3 - len(pre)))
        lines.append("    { 0x%06x, %d, %d, { %s }, 0x%x },  /* %s */"
                     % (va - 0x400000, rec["len"], len(pre), pfx,
                        new_offset(s_["part"], rec, rows), s_["part"]))
    lines += ["};", "#define CE_NSITES (sizeof(CE_SITES)/sizeof(CE_SITES[0]))", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "check", "gen", "verify", "conflicts"])
    ap.add_argument("others", nargs="*", help="conflicts：其它 patch 的 th18.v1.00a.js")
    ap.add_argument("--rows", type=int, default=ROW_COUNT,
                    help="新表行数（第 1 步用 58 = 行为零变化）")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()

    if not os.path.exists(EXE):
        raise SystemExit("找不到样本：%s\n"
                         "游戏 exe 是 ZUN 版权商业软件，由你自己放进 local/。" % EXE)
    got = md5(EXE)
    if got != EXE_MD5:
        raise SystemExit("exe md5 不符：期望 %s，实得 %s" % (EXE_MD5, got))

    text, text_va, _ = load_text_section(EXE)
    inst, anchors = find_all(text, text_va)
    bad = check_invariants(inst)
    walks = find_walks(text, text_va)
    sites = collect_sites(inst, walks)
    uncovered = audit_uncovered(text, text_va, sites)
    secs, in_text, in_data = audit_interior(EXE, sites)

    if a.cmd == "conflicts":
        if not a.others:
            raise SystemExit("用法：sites.py conflicts <其它 patch 的 th18.v1.00a.js>…")
        path = os.path.join(HERE, "..", "patch", "%s.js" % VERSION)
        n, found = conflicts(path, a.others)
        print("对照 %d 个外部 hackpoint，与我们 100 处重叠的：%d" % (n, len(found)))
        for f in found:
            print("   ❌ %s / %s / %s @ %s  撞上  %s" % f)
        return 1 if found else 0

    if a.cmd == "verify":
        path = a.out or os.path.join(HERE, "..", "patch", "%s.js" % VERSION)
        n, bad = verify_patch(path, text, text_va)
        print("对账 %s：%d 条 binhack" % (os.path.relpath(path, REPO), n))
        if n != len(sites):
            bad.append("patch 里 %d 条，扫描器认为应有 %d 条" % (n, len(sites)))
        for b in bad:
            print("   ❌ " + b)
        print("✅ 全部对上（expected == exe 字节；code 与 expected 等长；只换常量）"
              if not bad else "❌ %d 处不符" % len(bad))
        return 1 if bad else 0

    if a.cmd in ("list", "check"):
        print("样本 %s  md5 %s ✅" % (VERSION, got))
        print("锚点 %d，完整匹配 %d 个查表实例，共用 LOOP_START %d 个"
              % (anchors, len(inst), sum(x["shared_start"] for x in inst)))
        print("表遍历（计数收尾，只搬 start）%d 处：%s"
              % (len(walks), ", ".join("0x%06x(count=%d @0x%06x)"
                                       % (w["parts"]["start"]["va"], w["count"], w["count_at"])
                                       for w in walks)))
        print("去重后待改站点 %d 处" % len(sites))
        if a.cmd == "list":
            print("\n查表实例（比较字段 / 返回字段）：")
            for i, x in enumerate(inst):
                p = x["parts"]
                print(" [%02d] 锚 0x%06x  ptr=%-3s idx=%-3s  cmp +0x%02x  ret +0x%02x%s"
                      % (i, x["anchor"], x["ptr_reg"], x["idx_reg"],
                         x["field_cmp"], x["field_ret"],
                         "  (共用 start)" if x["shared_start"] else ""))
                for k in PART_ORDER:
                    print("        %-9s 0x%06x  %-22s %s"
                          % (k, p[k]["va"], p[k]["text"], p[k]["bytes"].hex()))
        print("\n⛔ 撞上同样的值但**不在查表骨架里**的 %d 处（这些不该改）：" % len(uncovered))
        for va, v, kind, desc in uncovered:
            print("   0x%06x  值 0x%06x  %-5s %s" % (va, v, kind, desc))
        sec_of = next((nm for nm, va, rp, rs in secs
                       if va <= TABLE_BASE < va + rs), "?")
        print("\n完整性检查之二：整张表区间 0x%06x..0x%06x（位于 %s 节）"
              % (TABLE_BASE, TABLE_BASE + ROW_COUNT * ROW_SIZE, sec_of))
        print("   .text 里未被 100 处站点覆盖的引用：%d 处%s"
              % (len(in_text), "" if not in_text
                 else " ← ❌ 漏了站点：" + ", ".join("0x%06x" % v for v, _ in in_text)))
        print("   数据节里指向表内某行的指针：%d 处%s"
              % (len(in_data), "" if not in_data
                 else " ← ❌ 这些指针也要跟着搬"))
        print()
        if in_text or in_data:
            bad.append("表区间还有 %d 处引用不在已知站点里" % (len(in_text) + len(in_data)))
        if bad:
            print("❌ 不变式校验失败：")
            for b in bad:
                print("   " + b)
            return 1
        print("✅ 25 个实例的两条不变式全部成立"
              "（循环比较字段 == 终止字段；命中臂字段 == 回退臂字段）")
        return 0

    if bad:
        raise SystemExit("校验没过，拒绝生成。")
    doc = {"codecaves": emit_codecaves(a.rows), "binhacks": emit(sites, a.rows)}
    txt = json.dumps(doc, indent=2, ensure_ascii=False)
    if a.out:
        out = a.out if os.path.isabs(a.out) else os.path.join(HERE, a.out)
        open(out, "w", encoding="utf-8").write(txt + "\n")
        print("写出 %d 条 binhack + %d 个 codecave -> %s（新表 %d 行 = 0x%x 字节）"
              % (len(doc["binhacks"]), len(doc["codecaves"]), out,
                 a.rows, a.rows * ROW_SIZE))
        hdr = os.path.join(HERE, "sites_gen.h")
        open(hdr, "w", encoding="utf-8").write(emit_header(sites, a.rows))
        print("写出 DLL 站点表 -> %s" % hdr)
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
