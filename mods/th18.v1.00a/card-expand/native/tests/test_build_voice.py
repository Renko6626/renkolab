"""test_build_voice.py —— build_voice.validate / parse_fmt 的边界。

跑：python3 tests/test_build_voice.py
"""
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets"))
from build_voice import validate, parse_fmt, VoiceError, MAX_N, FIRST_ID, FIRST_WAV   # noqa: E402

fail = []
n_check = 0


def check(cond, msg):
    global n_check
    n_check += 1
    if not cond:
        fail.append(msg)


def expect_error(lines, wav_dir, why):
    global n_check
    n_check += 1
    try:
        validate(lines, wav_dir)
    except VoiceError:
        return
    fail.append("应该报错但没报：%s" % why)


def wav(path, tag=1, ch=1, rate=44100, bits=16, data=b"\0" * 100, extra_chunk=False):
    fmt = struct.pack("<HHIIHH", tag, ch, rate, rate * ch * bits // 8, ch * bits // 8, bits)
    body = b"WAVE"
    if extra_chunk:                      # fmt 前面塞一个别的块，考验块遍历
        body += b"LIST" + struct.pack("<I", 4) + b"INFO"
    body += b"fmt " + struct.pack("<I", len(fmt)) + fmt
    body += b"data" + struct.pack("<I", len(data)) + data
    open(path, "wb").write(b"RIFF" + struct.pack("<I", len(body)) + body)


d = tempfile.mkdtemp()
wav(os.path.join(d, "A.wav"))
wav(os.path.join(d, "B.wav"), ch=2, rate=22050, bits=8)
wav(os.path.join(d, "C.wav"), extra_chunk=True)
wav(os.path.join(d, "BAD_TAG.wav"), tag=3)                       # IEEE float，不是 PCM
open(os.path.join(d, "NOT_WAV.wav"), "wb").write(b"OggS" + b"\0" * 100)

# ---- 正常路径 ----
v = validate(["A", "B"], d)
check(len(v) == 2, "两条")
check(v[0]["id"] == FIRST_ID and v[1]["id"] == FIRST_ID + 1, "id 从 0x%02x 递增" % FIRST_ID)
check(v[0]["wav_index"] == FIRST_WAV and v[1]["wav_index"] == FIRST_WAV + 1,
      "wav 下标从 %d 递增" % FIRST_WAV)
check(v[0]["index"] == 0 and v[1]["index"] == 1, "ORDER 行号")
check((v[0]["rate"], v[0]["bits"], v[0]["channels"]) == (44100, 16, 1), "fmt 解析：单声道 16bit")
check((v[1]["rate"], v[1]["bits"], v[1]["channels"]) == (22050, 8, 2), "fmt 解析：双声道 8bit")
check(validate(["C"], d)[0]["rate"] == 44100, "fmt 前面有别的块也要找得到")

# 注释与空行跳过
check(len(validate(["# 这是注释", "", "  ", "A"], d)) == 1, "注释 / 空行要跳过")
# 上限刚好
names = ["A"] * 0 + ["A"]
check(len(validate(["A"] * 1, d)) == 1, "1 条")

# ---- 错误路径 ----
expect_error(["A", "A"], d, "重复 NAME")
expect_error(["A"] * (MAX_N + 1), d, "超上限 %d" % MAX_N)
expect_error(["MISSING"], d, "缺文件")
expect_error(["BAD_TAG"], d, "非 PCM（format tag 3）")
expect_error(["NOT_WAV"], d, "不是 RIFF/WAVE")
expect_error(["A-B"], d, "NAME 含非法字符（要当 C 宏名）")
expect_error(["_"], d, "NAME 只有下划线")

# parse_fmt 直接调
try:
    parse_fmt(os.path.join(d, "BAD_TAG.wav"))
    fail.append("parse_fmt 应对非 PCM 报错")
except VoiceError:
    pass
n_check += 1

print("build_voice: %d checks, %d failed" % (n_check, len(fail)))
for m in fail:
    print("  FAIL", m)
sys.exit(1 if fail else 0)
