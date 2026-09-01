# AUDIT —— runtime-probe

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 对照 [`_template/AUDIT-checklist.md`](../../_template/AUDIT-checklist.md)。
> 状态：**静态检查已过，游戏内未实跑**（2026-09-01）。

## 逐节结论

### A. ABI / 栈平衡 —— **整节不适用**

探针不调用引擎任何函数、不构造 codecave、不触碰 FPU 栈，也没有被 patch 的调用点。
历史上唯一的真 BLOCKER（stdcall 误当 cdecl，见 [`mods/README.md`](../../README.md)）在这里
不可能发生。这是把「只读轮询」而不是 breakpoint 选作阶段 0 的主要理由。

### B. 写入点 —— **不适用**（无写入）

替代物是两处签名校验点，逐字节核对过：`native/check_constants.py` 把源码里写死的
字节数组与真 `th18.exe` 比，**CONFIRMED**（2026-09-01 实跑，md5 与 `symbols.json` 登记一致）。
相对/绝对表达式那条坑也不适用——没有 thcrap 表达式参与。

### C. 偏移与内存安全

- **CONFIRMED** 每个偏移都能回指一手文档：读取点 1–5 全部指向
  [`engine/player/th18/01`](../../../engine/player/th18/01-position-and-state-timers.md) §1/§3，
  `PLAYER_PTR` 指向 ExpHP `statics.json`。见 [`TARGET.md`](TARGET.md) 读取点表。
- **CONFIRMED** `PLAYER_PTR` 是**指针变量**不是对象本身（ExpHP 类型 `struct zPlayer*`，
  且 `engine/player/th18/01` §2 里第三方用法写作 `PLAYER_PTR->inner`）→ 代码解引用一次，正确。
- **CONFIRMED** 空指针路径：`*slot` 为 NULL 时不解引用，只打一行「离开关卡」。
- **CONFIRMED** 野指针路径：解引用前用 `VirtualQuery` 确认页已提交且可读
  （不用 `__try/__except`：i686 上 clang 的 SEH 支持不可靠）。
- **CONFIRMED** 卸载竞态：`ExitDll()` 先 `mod_func_run_all("exit")` 再 `plugins_close()`
  （一手：`thcrap/src/init.cpp:458-460`），所以导出的 `probe_mod_exit` 一定在 `FreeLibrary`
  之前跑，能停住并 join 轮询线程 → 不存在「DLL 已卸载而线程仍在其代码里」的悬空执行。
- **OPEN（已接受）** `readable()` 与随后的读之间存在 TOCTOU 窗口。理论上页可在两者之间被释放。
  评估：`zPlayer` 在整个关卡期间存活，窗口 ≈ 数十纳秒，且探针只读不写。**接受**，
  但这意味着「探针从不崩」不是保证，只是极大概率。若实跑中出现崩溃，这是第一嫌疑。
- **OPEN（已接受）** 撕裂读：轮询与游戏主循环无同步，可能读到一帧更新到一半的坐标
  （float 已写、定点未写）。后果仅是**偶发**一行 `MISMATCH`，不会崩。
  → **判读规则：孤立的 `MISMATCH` 是撕裂读，可忽略；持续 `MISMATCH` 才是映射错。**

### D. 量纲 / 常识关

- **CONFIRMED** 探针不做任何「字段 == 常量」的判断——它只打印，不解释。
  唯一的数值判定是范围自校验，其判据来自钳位常量 ÷ 128，量纲已在
  `engine/player/th18/01` §2③ 过过常识关（±184 px vs 弹幕区半宽 184）。
- **CONFIRMED** 自校验设计成**可证伪**：若偏移错了，坐标几乎必然落在 `OUT-OF-RANGE`
  或定点交叉校验 `MISMATCH`，而不是给出一个「看起来合理」的假结果。

### E. 收尾

- **CONFIRMED** 产物是 32 位 PE DLL：`PE32 executable (DLL) (GUI) Intel 80386`。
  依赖仅 `KERNEL32.dll` + `msvcrt.dll`（无 ucrt、无 libgcc 运行时依赖）。
- **CONFIRMED** 导出表是**无装饰名** `thcrap_plugin_init` / `probe_mod_exit`
  （`llvm-readobj --coff-exports` 实测）。这条是硬关卡：thcrap 在 `LoadLibrary` 之前
  就先扫 PE 导出表找该名字（`thcrap/src/pe.cpp:88`），装饰成 `_thcrap_plugin_init@0`
  会被**静默**判为「不是插件」。
- **CONFIRMED** 位数匹配：thcrap 拒绝位数不符的插件（`thcrap/src/plugin.cpp:337`），
  TH18 是 32 位 PE，产物是 i386。
- **CONFIRMED** 可还原：卸载 = 从 `<thcrap>/bin` 删掉这一个 DLL 文件，无残留、无需回滚字节。
- **CONFIRMED** 版本守卫可自我卸载：签名不匹配时 `thcrap_plugin_init` 返回 1，
  thcrap 会 `FreeLibrary` 并记 `not used for this game`（`plugin.cpp:352-357`）。
- ⏳ **OPEN —— 游戏内实跑**。本机无 Windows、无 wine，这一步必须在用户的 Windows 机器上做。
  **静态检查通过 ≠ 能跑**：加载与否、四条验收判据的结果全部未知。

## 产物

| 项 | 值 |
| --- | --- |
| 文件 | `native/th18_probe.dll`（构建产物，不入库） |
| 大小 | 37 KB（`-s` strip 过） |
| md5 | `758361b11e0545054749dbf22866c1b2` |
| 工具链 | llvm-mingw 20260826 msvcrt 变体，clang 23.1.0，target `i686-w64-windows-gnu` |
| 复现 | `cd native && make check && make && make verify` |

## 实跑记录

> 跑完请把结果填进来——**包括失败与崩溃**。四条验收判据见 [`README.md`](README.md)。

| 日期 | 环境 | 加载 | 判据 1 IN-RANGE | 判据 2 定点自洽 | 判据 3 随移动变化 | 判据 4 focus | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 尚未实跑 |
