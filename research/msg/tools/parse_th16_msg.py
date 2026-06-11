#!/usr/bin/env python3
"""
parse_th16_msg.py — TH16 .msg 解析器(结局/staff/对话通用),验证 msg/02 + msg/04 的结论。

用法:
    python3 parse_th16_msg.py <file.msg> [--kind ending|stage]

- 不含任何版权字节;输入的 .msg 是游戏资产(版权,用户本地提供,勿入库)。
- 指令格式 zMsgRawInstr:{int16 time, uint8 opcode, uint8 args_size, args[args_size]}(见 msg/01)。
- 文件头:u32 count, 然后(对结局 e/staff)u32 script0_offset @+4;脚本从该偏移起(见 msg/04 §1.5)。
- 文本编码:Shift-JIS + 自 TH09 的"加速 XOR 掩码"(init 0x77 / vel 0x07 / acc 0x10,逐字节含 padding;见 msg/02 §1)。

opcode→名 表来自 msg/02(stage)与 msg/04(ending/staff);ending 命名为我们一手提案(无社区对名)。
"""
import sys
import struct
import argparse

# ending/staff 指令集(msg/04;命名=我们提案,behavior 一手+e01 实测)
ENDING_OPS = {
    0: "end", 3: "text_line", 4: "text_clear", 5: "wait", 6: "wait_page",
    7: "load_anm_present", 8: "show_image", 9: "set_text_color",
    10: "music_by_name", 11: "music_fade", 12: "goto_staff_roll",
    13: "screen_effect_d", 14: "screen_effect_e",
    15: "show_image_d1", 16: "show_image_d2", 17: "show_image_d3",
}

# 哪些 opcode 的实参整体是一条加密 SJIS 文本串(其余按原始字节展示)
ENDING_TEXT_OPS = {3}
# 哪些 opcode 的实参是 {u32, 然后明文 ascii 文件名/路径串}
ENDING_STR_AT8 = {7}          # {idx, filename@+8}
ENDING_STR_AT4 = {10, 12}     # music name / staff filename @+4


def dexor(b: bytes) -> bytes:
    """加速 XOR 掩码解密(init 0x77, vel 0x07, acc 0x10)。"""
    out = bytearray()
    mask, vel = 0x77, 0x07
    for c in b:
        out.append(c ^ mask)
        mask = (mask + vel) & 0xff
        vel = (vel + 0x10) & 0xff
    return bytes(out)


def decode_text(args: bytes) -> str:
    s = dexor(args).split(b"\x00", 1)[0]
    try:
        return s.decode("shift_jis")
    except UnicodeDecodeError:
        return repr(s)


def ascii_str(b: bytes) -> str:
    return b.split(b"\x00", 1)[0].decode("ascii", "replace")


def parse(path: str, kind: str):
    data = open(path, "rb").read()
    count = struct.unpack_from("<I", data, 0)[0]
    off0 = struct.unpack_from("<I", data, 4)[0]
    print(f"# {path}  size={len(data)}  header: count={count} script0_off=0x{off0:x}")
    p = off0
    n = 0
    while p + 4 <= len(data):
        time = struct.unpack_from("<h", data, p)[0]
        op = data[p + 2]
        size = data[p + 3]
        args = data[p + 4:p + 4 + size]
        name = ENDING_OPS.get(op, f"op{op}")
        detail = ""
        if op in ENDING_TEXT_OPS and size:
            detail = "  text=" + repr(decode_text(args))
        elif op in ENDING_STR_AT8 and size > 4:
            idx = struct.unpack_from("<I", args, 0)[0]
            detail = f"  {{idx={idx}, name={ascii_str(args[4:])!r}}}"
        elif op in ENDING_STR_AT4 and size:
            detail = f"  name={ascii_str(args)!r}"
        elif size in (4, 8, 12) and size:
            ints = struct.unpack_from("<%dI" % (size // 4), args, 0)
            detail = "  " + repr(ints)
        print(f"@0x{p:04x} t={time:<4d} {op:<3d} {name:<16s} sz={size:<3d}{detail}")
        p += 4 + size
        n += 1
        if op == 0:
            break
    print(f"# parsed {n} instrs, ended @0x{p:x}/0x{len(data):x}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--kind", default="ending", choices=["ending", "stage"])
    a = ap.parse_args()
    if a.kind != "ending":
        sys.exit("stage-MSG opcode 表见 msg/02;本脚本当前内置 ending/staff 表(msg/04)。")
    parse(a.file, a.kind)
