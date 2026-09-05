#!/usr/bin/env python3
"""build_voice.py —— 语音资源的校验与索引生成。

  assets/voice/ORDER.txt   一行一个 NAME，**只追加**。行号 k → 音效 id 0x54+k、wav 下标 72+k
  assets/voice/<NAME>.wav  PCM（fmt tag 1）。零售 71 个 se 就是 44.1k/22.05k × 8/16 bit ×
                           单/双声道混用，引擎的 RIFF 解析不挑格式；建议 16-bit 单声道
                           （声像对单声道才有意义）。

跑：
  python3 assets/build_voice.py            校验 + 拷进 patch/th18/voice/ + 生成 native/voice_ids.h
  python3 assets/build_voice.py --check    只校验，不产出

上限、id 起点、wav 下标起点一律从 native/sound_sites.py 取 —— 那里是单一事实源。
"""
import argparse
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "native"))
import sound_sites as S                                       # noqa: E402

VOICE_DIR = os.path.join(HERE, "voice")
ORDER_TXT = os.path.join(VOICE_DIR, "ORDER.txt")
VOICE_JS  = os.path.join(HERE, "..", "patch", "th18", "voice.js")
PATCH_DIR = os.path.join(HERE, "..", "patch", "th18", "voice")
IDS_H     = os.path.join(HERE, "..", "native", "voice_ids.h")

MAX_N     = S.NEW_N          # 32
FIRST_ID  = S.FIRST_ID       # 0x54
FIRST_WAV = S.NAMES_N        # 72


class VoiceError(Exception):
    pass


def parse_fmt(path):
    """读 RIFF 的 fmt 块。只接受 PCM —— 别的 tag 引擎那边行为未验。"""
    b = open(path, "rb").read()
    name = os.path.basename(path)
    if len(b) < 44 or b[:4] != b"RIFF" or b[8:12] != b"WAVE":
        raise VoiceError("%s：不是 RIFF/WAVE" % name)
    i = 12
    while i + 8 <= len(b):
        cid = b[i:i + 4]
        sz = struct.unpack_from("<I", b, i + 4)[0]
        if cid == b"fmt ":
            if sz < 16:
                raise VoiceError("%s：fmt 块只有 %d 字节" % (name, sz))
            tag, ch, rate, _bps, _align, bits = struct.unpack_from("<HHIIHH", b, i + 8)
            if tag != 1:
                raise VoiceError("%s：format tag %d，只支持 PCM(1)" % (name, tag))
            return {"bytes": len(b), "rate": rate, "bits": bits, "channels": ch}
        i += 8 + sz + (sz & 1)
    raise VoiceError("%s：找不到 fmt 块" % name)


def validate(order_lines, wav_dir):
    """ORDER.txt 的行 → [{name,index,id,wav_index,path,bytes,rate,bits,channels}]。"""
    names = [ln.strip() for ln in order_lines
             if ln.strip() and not ln.strip().startswith("#")]
    if len(names) > MAX_N:
        raise VoiceError("ORDER.txt 有 %d 行，上限 %d（= sound_sites.NEW_N）" % (len(names), MAX_N))
    if len(set(names)) != len(names):
        dup = sorted({n for n in names if names.count(n) > 1})
        raise VoiceError("ORDER.txt 有重复的 NAME：%s" % ", ".join(dup))
    out = []
    for k, n in enumerate(names):
        if not n.replace("_", "").isalnum() or not n.replace("_", ""):
            raise VoiceError("NAME %r 只能是字母数字下划线（要当 C 宏名用）" % n)
        p = os.path.join(wav_dir, n + ".wav")
        if not os.path.exists(p):
            raise VoiceError("缺文件：%s.wav" % n)
        info = parse_fmt(p)
        info.update({"name": n, "index": k, "id": FIRST_ID + k,
                     "wav_index": FIRST_WAV + k, "path": p})
        out.append(info)
    return out


def cross_check(v):
    """★ voice.js 必须与 ORDER.txt 逐条对得上，id 显式写死。

    为什么不靠顺序：DLL 是按 voice.js 里的 `id` 定位 cfg 行的，而 thcrap 会把栈里
    每个 patch 的 voice.js **深合并**成一个对象 —— 合并后的迭代顺序不由我们决定。
    所以 id 必须显式写在 JSON 里，并在构建期与 ORDER.txt 的行号对账（同
    assets/README.md 对 cards.js / ORDER.txt 的处理）。
    """
    if not os.path.exists(VOICE_JS):
        raise VoiceError("缺 patch/th18/voice.js —— ORDER.txt 有 %d 行却没有登记" % len(v))
    doc = json.load(open(VOICE_JS, encoding="utf-8"))
    by_name = {x["name"]: x for x in v}
    seen = set()
    for key, ent in doc.items():
        if not isinstance(ent, dict):
            raise VoiceError("voice.js 的 \"%s\" 不是对象" % key)
        wav = ent.get("wav")
        if wav not in by_name:
            raise VoiceError("voice.js 的 \"%s\"：wav %r 不在 ORDER.txt 里" % (key, wav))
        if wav in seen:
            raise VoiceError("voice.js 里 wav %r 登记了两次" % wav)
        seen.add(wav)
        want = by_name[wav]["id"]
        if "id" not in ent:
            raise VoiceError("voice.js 的 \"%s\"：缺 \"id\"，应为 %d（0x%02x）" % (key, want, want))
        if ent["id"] != want:
            raise VoiceError("voice.js 的 \"%s\"：id 写的是 %s，ORDER.txt 第 %d 行算出来是 %d（0x%02x）"
                             % (key, ent["id"], by_name[wav]["index"], want, want))
        for f, lo, hi in (("volume", 0, 100), ("pan", -10000, 10000)):
            if f in ent and not (isinstance(ent[f], int) and lo <= ent[f] <= hi):
                raise VoiceError("voice.js 的 \"%s\"：%s 必须是 %d..%d 的整数" % (key, f, lo, hi))
    missing = [x["name"] for x in v if x["name"] not in seen]
    if missing:
        raise VoiceError("ORDER.txt 里有没被 voice.js 登记的：%s" % ", ".join(missing))


def write_ids(v):
    """生成 native/voice_ids.h。没有语音时也要写（sdk.h 无条件 include 它）。"""
    with open(IDS_H, "w", encoding="utf-8") as f:
        f.write("/* voice_ids.h —— 由 assets/build_voice.py 从 assets/voice/ORDER.txt 生成，别手改。 */\n")
        f.write("#pragma once\n\n")
        for x in v:
            f.write("#define CE_VOICE_%-24s 0x%02x\n" % (x["name"], x["id"]))
        f.write("\n#define CE_VOICE_REGISTERED %d\n" % len(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验，不产出")
    a = ap.parse_args()

    if not os.path.exists(ORDER_TXT):
        # sdk.h 无条件 include voice_ids.h，所以没有语音时也要产出一个空的
        if not a.check:
            write_ids([])
        print("assets/voice/ORDER.txt 不存在 —— 还没有语音；已写出空的 voice_ids.h")
        return
    v = validate(open(ORDER_TXT, encoding="utf-8").read().splitlines(), VOICE_DIR)
    cross_check(v)
    total = sum(x["bytes"] for x in v)
    print("语音 %d 条（上限 %d），共 %.2f MB" % (len(v), MAX_N, total / 1048576.0))
    print("%-24s %-6s %-5s %s" % ("NAME", "id", "wav", "格式"))
    for x in v:
        print("%-24s 0x%02x   %-5d %d Hz %d-bit %dch  %d B"
              % (x["name"], x["id"], x["wav_index"], x["rate"], x["bits"],
                 x["channels"], x["bytes"]))
    if a.check:
        return

    os.makedirs(PATCH_DIR, exist_ok=True)
    for f in os.listdir(PATCH_DIR):
        if f.endswith(".wav"):
            os.remove(os.path.join(PATCH_DIR, f))
    for x in v:
        shutil.copy2(x["path"], os.path.join(PATCH_DIR, x["name"] + ".wav"))
    write_ids(v)
    print("→ %s（%d 个文件）" % (os.path.normpath(PATCH_DIR), len(v)))
    print("→ %s" % os.path.normpath(IDS_H))


if __name__ == "__main__":
    try:
        main()
    except VoiceError as e:
        print("FAIL:", e)
        sys.exit(1)
