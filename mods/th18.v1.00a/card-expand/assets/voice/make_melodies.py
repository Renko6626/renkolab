#!/usr/bin/env python3
"""make_melodies.py —— 合成 assets/voice/ 下的钢琴曲。

**纯 stdlib、完全可复现**，所以产物是我们自己的内容，可以入库 ——
不像零售 wav 那样只能 gitignore 后靠 modkit 带过去。

现有曲目（`MELODIES`）：

| NAME | 用在哪 | 形状 |
| --- | --- | --- |
| `ROYAL_FANFARE` | 皇家同花顺（`cards/royal.c`）的演出，从第 0 帧起 | I–IV–V–I 号角，与 script70 的 194 帧时间线对齐 |

**响度基准**（2026-09-05 实测零售 dat 的 71 个 se_*.wav，见 engine/_shared/th18-sound-table.md §9）：
零售 wav 一律 peak 归一化（peak 中位 −0.06 dBFS），响度差异全压在 cfg 行的 dB 衰减上；
而那个字段**只能衰减不能增益**（DirectSound SetVolume 范围 −10000…0），所以响度只能由 wav 承载。
零售 wav 的 RMS 中位 −13.1 dBFS，最响的 se_release（Tenshi 发动音，与本段同帧一起响）是 −5.1。
本段目标 TARGET_RMS_DBFS = −10：比 se_release 低 5 dB、比零售中位高 3 dB。

钢琴音色是加法合成：
  · 谐波 1..10，振幅 ~1/n^1.3；高次谐波衰减更快（真钢琴的高频先掉）
  · 轻微非谐性 f_n = n*f0*sqrt(1 + B n²)（钢琴弦的刚度，B≈4e-4），让音色不「电子」
  · 3 ms 升余弦起音 + 指数衰减包络
  · 起音处叠 6 ms 的噪声瞬态当槌击声
  · peak 归一化到 −0.5 dBFS（照零售规矩）后 tanh 软限幅顶到目标 RMS，收尾 20 ms 淡出防 click

跑：python3 assets/voice/make_melodies.py [NAME…]   → 同目录 <NAME>.wav（不给参数就全出）
"""
import math
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))

RATE = 44100
BITS = 16
CHANNELS = 1                       # 单声道 —— 声像（cfg 行的 +8 低 word）对单声道才有意义

N_PARTIALS = 10
INHARMONICITY = 4e-4
HAMMER_MS = 6.0
ATTACK_MS = 3.0
FADE_MS = 20.0
PEAK_DB = -0.5                     # 照零售的规矩 peak 归一化（它们的 peak 中位是 -0.06）
TARGET_RMS_DBFS = -10.0            # ★ 响度基准，见文件头
TAIL_TRIM_DB = -46.0               # 尾巴衰到这个电平就截断，免得一段近似静音把 RMS 拉低


def note(name, octave):
    """科学音高记号 → 频率（A4 = 440 Hz）。"""
    semis = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4,
             "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}[name]
    return 440.0 * 2.0 ** (semis / 12.0 + (octave - 4))


FPS = 60.0                         # 乐谱按游戏帧写，好和 ANM 时间线对齐


def fr(f):
    return f / FPS


def chord(*specs):
    return [note(n, o) for n, o in specs]


# (起始秒, [频率…], 力度, 衰减时间常数秒)
def build_royal():
    """皇家同花顺的号角 —— 与 ability.anm script70 的 194 帧时间线对齐。

        帧 0/10/20/30/40   五张黑桃逐张弹出   → 五个上行音 C4 E4 G4 C5 E5
        帧 50              （承接）           → G5 短促带起
        帧 60              金色横幅弹出 + trophy 音效 → **C 大和弦重击**（高潮）
        帧 90 / 105        F → G              → 下属、属，把张力再拉一次
        帧 125             收在宽 C 大和弦上   → 一直响到 170–194 帧的淡出
    """
    s = []
    for f, (n, o) in zip((0, 10, 20, 30, 40),
                         (("C", 4), ("E", 4), ("G", 4), ("C", 5), ("E", 5))):
        s.append((fr(f), [note(n, o)], 0.80, 0.70))
    s.append((fr(50), [note("G", 5)], 0.70, 0.45))
    s.append((fr(60), chord(("C", 3), ("G", 3), ("C", 4), ("E", 4),
                            ("G", 4), ("C", 5), ("E", 5), ("G", 5)), 0.95, 1.10))
    s.append((fr(90), chord(("F", 3), ("C", 4), ("F", 4), ("A", 4), ("C", 5)), 0.70, 0.75))
    s.append((fr(105), chord(("G", 3), ("D", 4), ("G", 4), ("B", 4), ("D", 5)), 0.78, 0.75))
    s.append((fr(125), chord(("C", 2), ("C", 3), ("G", 3), ("C", 4), ("E", 4),
                             ("G", 4), ("C", 5), ("E", 5)), 1.00, 1.55))
    return s


MELODIES = {
    "ROYAL_FANFARE": build_royal,
}


def piano_partial_gain(k):
    """第 k 个谐波（1 起）的初始振幅与衰减加速度。"""
    amp = 1.0 / (k ** 1.3)
    decay_mult = 1.0 + 0.42 * (k - 1)                  # 高次谐波掉得快
    return amp, decay_mult


def render(score):
    tail = 1.6
    total = max(s[0] for s in score) + tail
    n = int(total * RATE)
    buf = [0.0] * n

    atk = ATTACK_MS / 1000.0
    ham = HAMMER_MS / 1000.0
    # 一个便宜的伪随机噪声（不引 random，保证跨版本完全一致）
    seed = 0x13579BDF

    for start, freqs, vel, tau in score:
        i0 = int(start * RATE)
        dur = min(tau * 6.0, total - start)
        ns = int(dur * RATE)
        for f0 in freqs:
            for k in range(1, N_PARTIALS + 1):
                amp, dmult = piano_partial_gain(k)
                fk = k * f0 * math.sqrt(1.0 + INHARMONICITY * k * k)
                if fk >= RATE * 0.45:                  # 别超奈奎斯特，免得混叠
                    break
                w = 2.0 * math.pi * fk / RATE
                a = amp * vel
                d = 1.0 / (tau / dmult) / RATE
                ph = 0.0
                env = 1.0
                for i in range(ns):
                    idx = i0 + i
                    if idx >= n:
                        break
                    e = env
                    if i < atk * RATE:                 # 升余弦起音
                        e *= 0.5 - 0.5 * math.cos(math.pi * i / (atk * RATE))
                    buf[idx] += a * e * math.sin(ph)
                    ph += w
                    env -= env * d
                    if env < 1e-4:
                        break
            # 槌击瞬态：一小段噪声，随谐波一起淡入淡出
            nh = int(ham * RATE)
            for i in range(nh):
                idx = i0 + i
                if idx >= n:
                    break
                seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
                white = (seed / 0x3FFFFFFF) - 1.0
                buf[idx] += 0.06 * vel * white * (1.0 - i / nh) ** 2

    # 尾巴截断：从后往前找第一处超过阈值的采样，之后只留一小段淡出
    peak0 = max(abs(x) for x in buf) or 1.0
    thr = peak0 * 10.0 ** (TAIL_TRIM_DB / 20.0)
    end = n
    while end > 1 and abs(buf[end - 1]) < thr:
        end -= 1
    nf = int(FADE_MS / 1000.0 * RATE)
    end = min(n, end + nf)
    buf = buf[:end]
    n = end
    for i in range(nf):                                # 收尾淡出，防 click
        buf[n - nf + i] *= 1.0 - i / nf

    return limit_to_target(buf)


def _rms(x):
    return math.sqrt(sum(v * v for v in x) / len(x))


def limit_to_target(buf):
    """peak 归一化到 PEAK_DB，再用 tanh 软限幅把 RMS 顶到 TARGET_RMS_DBFS。

    tanh 保持峰值不变、只抬中低电平，等于降低波峰因数 —— 钢琴的 14 dB 波峰因数
    正是「峰值已经满了但听着还是轻」的原因。驱动量用二分求解，所以目标电平是
    写死的常量而不是手调出来的魔数。
    """
    pk = max(abs(x) for x in buf) or 1.0
    x = [v / pk for v in buf]
    want = 10.0 ** (TARGET_RMS_DBFS / 20.0)
    peak_g = 10.0 ** (PEAK_DB / 20.0)

    def shaped(d):
        if d < 1e-3:
            return x
        t = math.tanh(d)
        return [math.tanh(d * v) / t for v in x]

    lo, hi = 0.0, 8.0
    if _rms(shaped(hi)) * peak_g < want:
        d = hi                                         # 顶到头也够不着：尽力而为
    else:
        for _ in range(40):
            mid = (lo + hi) / 2.0
            if _rms(shaped(mid)) * peak_g < want:
                lo = mid
            else:
                hi = mid
        d = hi
    y = shaped(d)
    g = peak_g / (max(abs(v) for v in y) or 1.0)
    out = [max(-32768, min(32767, int(v * g * 32767.0))) for v in y]
    rms_db = 20.0 * math.log10(_rms(out) / 32768.0)
    pk_db = 20.0 * math.log10(max(abs(v) for v in out) / 32768.0)
    print("  软限幅 drive=%.3f → peak %.2f dBFS  rms %.2f dBFS  波峰因数 %.1f dB"
          % (d, pk_db, rms_db, pk_db - rms_db))
    return out


def write_wav(path, samples):
    data = struct.pack("<%dh" % len(samples), *samples)
    byte_rate = RATE * CHANNELS * BITS // 8
    fmt = struct.pack("<HHIIHH", 1, CHANNELS, RATE, byte_rate, CHANNELS * BITS // 8, BITS)
    body = (b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt
            + b"data" + struct.pack("<I", len(data)) + data)
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", len(body)) + body)


def main(argv):
    want = argv[1:] or sorted(MELODIES)
    for name in want:
        if name not in MELODIES:
            raise SystemExit("没有这首：%s（有 %s）" % (name, ", ".join(sorted(MELODIES))))
        print("%s：" % name)
        samples = render(MELODIES[name]())
        out = os.path.join(HERE, name + ".wav")
        write_wav(out, samples)
        print("  %s.wav：%d 采样 = %.2f s，%d Hz %d-bit %dch，%d 字节"
              % (name, len(samples), len(samples) / RATE, RATE, BITS, CHANNELS,
                 os.path.getsize(out)))


if __name__ == "__main__":
    import sys
    main(sys.argv)
