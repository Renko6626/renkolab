# voice/ —— 角色语音（音效表扩容的 32 个新 id）

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。

面向**写卡的人**：给一张卡加一句语音，只需要放一个 wav、在 `ORDER.txt` 加一行、
在 `voice.js` 写一条，然后代码里 `ce_play_voice(NAME, x)`。DLL 不碰 dat，也不走 thcrap 的文件替换。

## 放什么

| 文件 | 说明 |
| --- | --- |
| `ORDER.txt` | 一行一个 `NAME`，**只追加**。行号 k → 音效 id `0x54+k`、wav 下标 `72+k`。`#` 开头是注释 |
| `<NAME>.wav` | PCM（`fmt` tag 1）。**建议 16-bit 单声道** —— 声像对单声道才有意义 |
| `_src/` | 第三方 / 原始素材（原件 + 出处 README）|

`NAME` 只能是字母数字下划线 —— 它要变成 C 宏 `CE_VOICE_<NAME>`。

**上限 32 条**（`native/sound_sites.py` 的 `NEW_N`）。零售 71 个 se 共 5.8 MB；
32 条 × 2 秒 × 44.1 kHz × 16 bit 单声道 ≈ 5.6 MB，同量级，全量常驻内存。

## 索引怎么来

```
ORDER 第 k 行（0 起）  →  音效 id = 0x54 + k,  wav 下标 = 72 + k
```

`make voice` 会打印这张对照表，并生成 `native/voice_ids.h`（`CE_VOICE_<NAME>`）。
**写卡的人不碰数字**：

```c
ce_play_voice(SPADE_10_ACTIVATE, player_x());
```

## `voice.js` 怎么写

`patch/th18/voice.js`（thcrap 会把栈里每个 patch 的这个文件深合并）：

```json
{
  "SPADE_10_ACTIVATE": { "wav": "SPADE_10_ACTIVATE", "id": 84, "volume": 100, "pan": 0 }
}
```

| 字段 | 说明 |
| --- | --- |
| key | 给人看的名字，只出现在日志里 |
| `wav` | **`ORDER.txt` 里的 NAME**，决定用哪个文件 |
| `id` | **必填**，= `0x54 + ORDER.txt 行号`（十进制写）。`make voice` 会与 ORDER.txt 对账，不一致直接报错 |
| `volume` | 0–100，缺省 100 |
| `pan` | DirectSound 声像单位（−10000..10000），缺省 0；零售用到 `0xfe0c` = −500 一档 |

★ **id 显式写死、不靠顺序**：thcrap 会把栈里每个 patch 的 `voice.js` **深合并**成一个对象，
合并后的迭代顺序不由我们决定，所以 DLL 是按 `id` 定位 cfg 行的。`make voice` 负责保证
`id` 与 `ORDER.txt` 的行号一致 —— 写错了构建就停，不会带着错的索引出包。

## 跑什么

```bash
cd ../../native
make voice          # 校验 + 拷进 patch/th18/voice/ + 生成 voice_ids.h
python3 ../assets/build_voice.py --check    # 只校验
```

## 边界

- **语音就是 SE**：可叠加、跟随游戏的 SE 音量（`0x5704ac`）、不做独占通道、不打断、
  过关不停。设计决定见 `docs/superpowers/specs/2026-09-05-voice-expand-design.md` §4。
- 引擎的 RIFF 解析不挑格式（零售 71 个就是 44.1k/22.05k × 8/16 bit × 单/双声道混用），
  但 `build_voice.py` 只放行 PCM —— 别的 tag 我们没验过。
- wav 文件随 `_255` patch 分发（`patch/th18/voice/`），`files.js` 收它们的 crc。
- `TEST_VOICE.wav` 是本地链路验证用的零售 wav，**gitignored，不入库**。
