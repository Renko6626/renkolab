# runtime-probe —— TH18 只读运行时探针

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。

一个 thcrap 插件 DLL，**只读**：每 100ms 读一次玩家坐标与两个状态位，写进
游戏目录下的 `th18_probe.log`。不装 binhack / breakpoint / codecave，
**不往游戏内存写任何一个字节**。

## 它是用来回答什么的

这是 [`card-rework/ROADMAP.md`](../card-rework/ROADMAP.md) **阶段 0「运行时底座」**的最小切片。
它同时验三件独立的事，一次跑完就都有答案：

1. **交付链路通不通** —— Linux 上交叉编译出的 32 位 DLL，能不能被 thcrap 认出并加载。
2. **`engine/` 的结论在活进程上成不成立** —— `PLAYER_PTR` 与 `zPlayer` 那几个偏移，
   过去只在 Ghidra 里静态验过（[`engine/player/th18/01`](../../../engine/player/th18/01-position-and-state-timers.md)），
   这是第一次拿真进程验。
3. **版本守卫管不管用** —— 签名不匹配时能否干净地自我卸载。

**不验**的是 hook / codecave / ABI —— 探针不调用引擎任何函数，那些留给阶段 1。

## 装法

```
<thcrap 安装目录>/bin/th18_probe.dll      ← 只有这一个文件
```

插件**只从 `<thcrap>/bin` 加载**（一手：`thcrap/src/init.cpp:325-333`；
「从 patch 目录加载 DLL」那条路在源码里被注释掉了，原文 *"Potentially dangerous stuff. Do not want!"*）。
所以**没有 patch 目录、没有 JSON**——探针不需要它们。放好后照常用 thcrap 启动 TH18 即可，
patch 栈里有没有别的补丁都不影响。

## 怎么算成功

**先看 thcrap 的日志**，应出现：

```
[Plugin] th18_probe.dll: initialized and active
```

若是 `not a plugin` → 导出名或位数不对；若是 `not used for this game` → 我们的签名守卫拒绝了，
去看 `th18_probe.log` 里 `[guard]` 那几行说的是哪一处不匹配。

**再看 `th18_probe.log`**（与 `th18.exe` 同目录）。进入关卡移动自机，每行形如：

```
[  12345 ms] x=  -23.45 y=  380.12 z=  0.00 | sub=(  -3002,  48655) /128 -> (  -23.45,  380.12) ok | focus=1 state=2 | IN-RANGE
```

四条验收判据：

| # | 看什么 | 通过 | 不通过说明什么 |
| --- | --- | --- | --- |
| 1 | 行尾 `IN-RANGE` | 坐标落在弹幕区 x∈[-184,184] y∈[32,432] | 偏移错了，或读到的不是玩家对象 |
| 2 | `sub=… /128 -> …` 后的 `ok` | float 坐标与定点副本自洽 | 持续 `MISMATCH` = `0x62c/0x630` 语义错；**孤立一行 `MISMATCH` 是撕裂读**，可忽略（见 [`AUDIT.md`](AUDIT.md) C 节）|
| 3 | 移动自机时 x/y 跟着变，松手即停 | 读的确实是玩家 | 读到的是别的对象或陈旧副本 |
| 4 | 按住 Shift 时 `focus=1`，且移动明显变慢 | `+0x476cc` 是聚焦位 | 该字段判断错了 |

四条全过 = `engine/player/th18/01` 的结论从「Ghidra 里静态闭合」升级为「活进程验证」。
**任一条不过，不要绕过去，回 `engine/` 复核映射**——按 `METHOD.md`，
与可观察行为冲突时先怀疑我们自己的映射。

跑完把结果（含失败与崩溃）回填 [`AUDIT.md`](AUDIT.md)。

## 编译

需要 llvm-mingw（msvcrt 变体，Linux 宿主，无需 sudo）：

```bash
cd ~/Tools
curl -sSLO https://github.com/mstorsjo/llvm-mingw/releases/download/20260826/llvm-mingw-20260826-msvcrt-ubuntu-22.04-x86_64.tar.xz
tar xf llvm-mingw-20260826-msvcrt-ubuntu-22.04-x86_64.tar.xz
```

选 **msvcrt** 而不是 ucrt 变体：thcrap 官方仍用 v141_xp 工具集保老系统兼容，
链 `msvcrt.dll` 的插件在任何 Windows 上都能加载，ucrt 会给老系统添依赖。

```bash
cd native
make check     # 把源码里写死的签名字节与真 exe 对账（换 build 后必须先过这关）
make           # 出 th18_probe.dll
make verify    # 位数 / 导出表 / 依赖
```

`make verify` 必须看到：`PE32 … Intel 80386`，导出表里是**无装饰**的
`thcrap_plugin_init` —— thcrap 在 `LoadLibrary` **之前**就先扫 PE 导出表找这个名字
（`thcrap/src/pe.cpp:88`），x86 `__stdcall` 若不经 `.def` 会被装饰成
`_thcrap_plugin_init@0`，插件将被**静默**判定为「不是插件」。这就是 `th18_probe.def` 存在的理由
（thcrap 自己的插件同样用 `.def`，见 `thcrap_tsa/thcrap_tsa.def`）。

## 目录

```
runtime-probe/
├── README.md                    # 你在这
├── TARGET.md                    # ★ 死绑登记:签名点 / 读取点 / 换版本要重取什么
├── AUDIT.md                     # 审计与实跑记录
└── native/
    ├── th18_probe.c             # 全部逻辑(~230 行,只依赖 kernel32 + msvcrt)
    ├── th18_probe.def           # 导出无装饰名
    ├── Makefile                 # make / make check / make verify
    └── check_constants.py       # 死绑量 ↔ 真 exe 对账
```
