# 06 — 如何给 TH16 加一条自定义 ECL 指令(指南)

> **问题**:ECL VM 的 opcode→handler 是**硬编码的 switch + 跳转表**(`04`/`05`),没有插件/注册扩展点。要加一条"新指令"=让解释器多认一个 opcode 并多走一个分支。
> **答案**:**注入 DLL,hook 解释器的"范围闸"分支,把超界 opcode 转交你自己的 dispatcher**——这正是 Priw8 **ECLplus**(TH17 mod)的做法。本文把 ECLplus 的真实技术映射到我们反出的 **TH16** 地址,给可操作配方。
> **来源**:ECLplus 源码(`github.com/Priw8/ECLplus`,BSD;读了 `dllmain.cpp`/`ECLplus.cpp`/`binhack.cpp`/`ECLplus.h`)+ 本仓库 TH16 反编译(`04`/`05`,`ecl_run`/`ecl_run_over_300`)。仅 TH16 v1.00a 的地址;换版本/作品需重定位。

---

## 1. 原理:patch "范围闸",不动跳转表(ECLplus 的关键招)

游戏 opcode 派发器(TH16 `ecl_run_over_300` @0x41dcb0)开头有个**范围闸**:把 opcode 减 300、与上界比,**超界就跳 default(no-op)**。ECLplus 不去改那张大跳转表,而是**把这个"超界跳 default"改成"超界跳进自己的 code cave"**——于是**所有超出游戏 opcode 范围的指令(ECLplus 选 ≥2000)自动落进你的 dispatcher**。干净、不碰已有 case。

ECLplus 实际 binhack(`binhack.cpp`,TH17 地址):
```
// 在 0x4211AB(TH17 范围闸的 ja)写:
ja  CAVE                 ; 原本是 ja default
// CAVE(新分配的可执行缓冲):
push edx                 ; ins
push edi                 ; enm
call InsSwitch           ; -> ECLplus 的 DLL 函数
jmp  0x4265f2            ; 跳回派发器函数尾(正常推进 PC)
```
`InsSwitch(ENEMY* enm, INSTR* ins)`(`ECLplus.cpp`)= 按 `ins->id` 分段:`2000..2099→ins_2000`、`2100..2199→ins_2100`、`2200..2299→ins_2200`,每个是 C handler。handler 读参数直接调**游戏自己的取参函数**(`GameGetIntArg=0x00428CC0` 等,thiscall ecx=enm)。
> ECLplus 的 `INSTR` 结构 = 我们的 `zEclRawInstructionHeader`(`time/id/size/paramMask/rankMask/paramCount/popCnt/data[]`)**逐字段一致**——印证我们反得对。

安装:`DllMain(PROCESS_ATTACH)→init()→InitBinhacks()`;用 `ECLplusLoader.exe`(挂起启动游戏+注入 DLL)或 thcrap 加载。

---

## 2. TH16 锚点(把 ECLplus 的 TH17 做法映射过来)

| 用途 | ECLplus(TH17) | **TH16 v1.00a(本仓库反出)** |
| --- | --- | --- |
| 游戏 opcode 派发器 | (TH17 等价) | `ecl_run_over_300` @**0x41dcb0**(`05` §1) |
| **范围闸 hook 点** | `0x4211AB` 的 `ja` | **`0x41DD3A` 的 `JA 0x00422a9b`**(`0F 87` rel32) |
| opcode 读取 | — | `MOVZX ECX,[ESI+4]`(@0x41DD23);减 300(`ADD EAX,-0x12c`)、`CMP EAX,0x2bd`(@0x41DD35) |
| 超界 default 目标 | `jmp 0x4265f2`(函数尾) | **`0x00422a9b`**(超界 no-op 路径;cave 处理完跳这) |
| 取参函数 | `GameGetIntArg 0x428CC0` | `ecl_get_int_arg` @**0x473c90** / `ecl_get_float_arg` @**0x473d40** / `_arg_ptr`(`02`/`04`,thiscall ecx=enm) |
| 寄存器(进 cave 时) | edi=enm, edx=ins | **enm=ECX(=EDI,@0x41DCDD 存)**、**ins=ESI**(@0x41DD2F 存 `[EBP-0x42c]`) |
| INSTR 布局 | `INSTR` | `zEclRawInstructionHeader`(已建进 Ghidra) |
| 系统 opcode(<0x5d)派发 | — | `ecl_run` @**0x472030**(`04`);要加系统码则 hook 这里的 default 分支 |

---

## 3. 配方:加一条游戏指令(TH16)

1. **选 opcode 号**:用 **≥1002(出 `[300,1001]` 范围)**,例如 2000+。这样它天然命中 `0x41DD3A` 的"超界"分支,**不用动跳转表**。(也可占用区间内的空槽——但那要改 `0x422c44` 字节表,更麻烦。)
2. **建 code cave**:`VirtualAlloc` 一块可执行内存,写:`push ESI(ins); push EDI(enm); call <你的InsSwitch>; jmp 0x422a9b`(跳回 default 路径让 PC 正常推进)。
3. **打 hook**:把 `0x41DD3A` 的 `JA 0x422a9b`(6 字节 `0F 87 xx xx xx xx`)改成 `JA <cave>`(重算 rel32 = cave − (0x41DD40))。`VirtualProtect` 改可写。
4. **写 InsSwitch(enm, ins)**:按 `ins->id` 分发;参数用游戏的 `ecl_get_int_arg`(0x473c90,`__asm{ mov ecx,enm; push n; call 0x473c90 }`)/ `ecl_get_float_arg`(0x473d40,结果在 xmm0)/ `_arg_ptr` 取——**这样自动支持变量/字面量两种参数**(取参函数内部按 `paramMask` 解析,见 `04` §4)。字符串参数直接读 `ins->data`。
5. **栈纪律**:执行后引擎按 `instr+0xc`(`num_stack_refs`/popCnt)弹栈(`04` §2)。让你的 **eclmap 签名**正确(thecl 据签名算 popCnt),引擎就会替你平栈;或自己处理。
6. **注入**:写个 loader(`CreateProcess` 挂起 + 注入 DLL + 恢复)或挂 thcrap。
7. **工具链侧(让 thecl 编得出来)**:给你的 opcode 在一份 eclmap 里加 `名 签名`(`!ins_names`/`!ins_signatures`),并写一个 `.tecl` include 供脚本 `#include`——参考 ECLplus 的 `ECLinclude/ECLplus.eclm` + `ECLplus.tecl`。否则 `.ecl` 里没法写这条指令。

---

## 4. 自定义变量(负 id)— 同理

ECLplus 也 hook 了**变量 getter 的范围闸**(TH17 `0x427524` 取值 / `0x427Cf1` 取址)→ 转 `IntVarSwitch(enm,var,type)`。TH16 对应路径:负 id 变量在 `ecl_get_int_arg` 里走 `vm->vtable` → `Enemy::ecl_get_*_global`(0x423810/0x424110,`01`/`04` §4)。要加自定义变量就 hook 那条 global 解析的"未知 id"分支,转你自己的 var switch(返回值 / 返回地址两种 type)。

---

## 5. 注意事项(坑)

- **地址版本锁**:上述全是 **TH16 v1.00a**;换版本/作品,`ecl_run_over_300`/范围闸 `ja`/取参函数地址都会变,须用同套方法(我们的 `04`/`05`)重定位。ECLplus 也是每作单独做。
- **replay/版本不兼容**:加了 opcode = 改了模拟,**录像必然 desync**(见之前 replay 讨论);用 RNG/浮点的 handler 还要注意确定性(replay-safe 流见 `../shared/th16-engine-math.md`)。
- **别撞已有 opcode**:`[300,1001]` 内大量是 default 空槽、`<300` 基本没用,但仍以我们枚举的已用集为准(`05` §2);选 ≥2000 最稳。
- **code cave 要可执行**(`VirtualAlloc PAGE_EXECUTE_READWRITE`);patch 点要 `VirtualProtect` 开写再还原。
- **thiscall 调参**:`ecl_get_int_arg` 等是 `__thiscall`(ecx=enm),C 里要用内联汇编调(见 ECLplus `ECLplus.cpp` 的 `GetIntArg`)。

---

## 6. 与 THTK-Studio 的关系
- 这是**运行时 mod**(注入),与 thecl 的**编译期**(把 `.ecl` 反汇编/重编)是两回事:加指令要**两边都做**——运行时 hook(执行)+ eclmap/thecl(汇编)。
- IDE 若要支持"自定义指令"工作流,可在 eclmap 编辑 + opcode 空间提示 + 生成 loader/binhack 模板上发力(本文的 TH16 锚点可直接用)。

## 关联
- 派发器/取参:`04-ecl-vm-interpreter.md`(`ecl_run` + 参数三分支)、`05-fire-interface.md` §1(`ecl_run_over_300` 范围闸 + 跳转表 0x422c44)。
- 变量模型:`01-ecl-context-and-variables.md`。INSTR 结构已建进 Ghidra(`02` 末注)。
- 参考实现:`github.com/Priw8/ECLplus`(TH17;`binhack.cpp` 范围闸 hack、`ECLplus.cpp` InsSwitch、`ECLplus.h` INSTR)、`ECLplus.eclm`/`ECLplus.tecl`(工具链侧)。
- 纪律:本文为指南/推断(基于 ECLplus 真实代码 + 我们 TH16 反编译);具体字节 patch 未在本机实跑验证,实施时以 exe 实测为准。
