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
| `make_test_melody.py` | 合成 `TEST_VOICE.wav` 的脚本（实跑素材，可复现）|

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
- `TEST_VOICE.wav` 由 [`make_test_melody.py`](make_test_melody.py) 合成（纯 stdlib，2.9 s 钢琴旋律：
  上行动机 C5–E5–G5–C6 再逆行弹回，照反转牌的主题）。**我们自己的内容，入库** ——
  实跑不需要先从 dat 里翻零售 wav。放零售 wav 当素材的话记得单独 gitignore 它。

## `files.js` 与分发

`patch/th18/voice/*.wav` 是构建产物（`make voice` 从 `assets/voice/` 拷过去），在**本仓**
gitignored，所以入库的 `patch/files.js` **不会**列出语音 wav。素材本身（`assets/voice/*.wav`）入库
—— 除非是零售 wav，那种要单独 gitignore（renkolab 不留版权字节，同 `abcard.anm` 的政策）。
`make dist` / `make release` 会对 `dist/patch-step3/` 重新生成 files.js，那份**会**列出它们
—— 语音随 modkit 发布。thcrap 本地解析文件不看 files.js（那是更新/下载机制用的），
所以本地开发时 wav 不在 files.js 里也照样能播。
