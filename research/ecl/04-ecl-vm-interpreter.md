# 04 — ★ ECL 解释器循环 `EclRunContext::ecl_run`(0x472030)一手反编译

> **对象**:TH16 `th16.exe` `0x472030`(ExpHP=`EclRunContext::ecl_run`)。日期 2026-06-09。
> **方法**:主控一手反编译整函数 → 三方交叉验证:**thecl 指令号(`00-*`)+ ExpHP 结构体(`02-*`)+ expr.c 表达式表**。
> **可信度**:✅✅ —— 这是**社区未公开反编译**的 ECL 派发循环;循环结构 + 系统 opcode(0–0x5d)语义为一手实证,且与 thecl ins 号、ExpHP `zEclRunContext`/`zEclRawInstructionHeader` 字段偏移**逐项吻合**(已过四闸门:一手到底 + 与三个独立外部源对名 + 量纲关 + 主动找冲突)。仅 TH16。
>
> ⚠️ **"反超社区"声明**:本文给出了 thecl(格式侧)/ExpHP(仅结构与函数名)都**没有**的东西——**运行时每条系统 opcode 的实际行为 + 派发循环机制**。已尽力复核;高位游戏 opcode(default 分支)仍走 `ecl_run_over_300`,未在本函数展开。

---

## 0. 一句话

`ecl_run(runCtx, dt)` = 一条 ECL 调用栈的**每帧推进器**:从 PC 取指 → **time 门控**(指令 time ≤ ctx.time 才执行)→ **rank 过滤** → opcode 派发(系统码 0–0x5d 内联,其余走 VM vtable[0]=`ecl_run_over_300`)→ 按 `total_size` 进 PC → 按 `num_stack_refs` 弹栈 → 循环到遇到未来指令 → `ctx.time += dt` → 跑 8 路浮点插值器。

---

## 1. 上下文/取指(✅✅ 与 ExpHP `zEclRunContext` 对齐)

`param_1` = `zEclRunContext*`(以 float* 访问)。确认字段:
| 偏移 | 代码 | 字段(ExpHP) |
| --- | --- | --- |
| +0x0 | `*param_1` | `time`(float) |
| +0x4 | `param_1[1]` | `cur_location.subroutine_index` |
| +0x8 | `param_1[2]` | `cur_location.offset_from_first_instruction`(=PC) |
| +0xc.. | `param_1+3` | `stack`(zEclStack) |
| +0x100c | `param_1[0x403]` | `stack.stack_offset`(栈顶指针,字节) |
| +0x1018 | `param_1[0x406]` | owning **zEclVm/enemy 回指**(用其 vtable[0]/`+0x11f8`file_manager/`+0x1200`async_list)— ⚠️ ExpHP 标 "enemy",实际当 zEclVm 用(zEclVm 内嵌于 enemy+0,自洽) |
| +0x101c | (ins 20 写目标) | `__set_by_ins_20` |
| +0x1020 | `*(byte*)(param_1+0x408)` | `difficulty_mask`(rank 过滤) |
| +0x11e4 | (ins 18/19 写目标) | `__set_by_ins_18_19` |
| +0x1024.. | `param_1+0x409..` | `float_i[8]`(8 路 `zInterpFloat`,§5) |

**取指**(✅✅ 与 ExpHP `zEclFileManager`/`zEclSubroutinePtrs`/`zEclRawSubHeader` 对齐):
```
fm   = *(vm + 0x11f8)                       ; zEclFileManager
subs = *(fm + 0x8c)                          ; zEclSubroutinePtrs[]  (stride 8: {name@0, bytecode@4})
code = *(subs + 4 + sub_index*8)             ; 该 sub 的字节码基址(指向 ECLH)
instr = code + 0x10 + offset                 ; +0x10 跳过 ECLH 头;offset=PC
```

**指令头**(✅✅ = ExpHP `zEclRawInstructionHeader` 0x10 字节,亦 = thecl `th10_instr_t`):
`+0x0 time`(i32,门控)·`+0x4 opcode`(u16,switch)·`+0x6 total_size`(u16,PC 步进)·`+0x8 variable_mask`·`+0xa rank_mask`(u8,& difficulty_mask)·`+0xb param_count`·`+0xc num_stack_refs`(执行后弹栈量)。

---

## 2. ★ 主循环机制(✅)

```c
if (instr.time <= ctx.time) {
  do {
    if ((ctx.difficulty_mask & instr.rank_mask) == 0) goto advance;   // rank 过滤
    switch (instr.opcode) {
      // 系统 opcode 0..0x5d 内联(§3)
      default:                                                        // 游戏 opcode
        r = (*vm->vtable[0])();   // -> ecl_run_over_300 族
        if (r==-1) goto EXIT;     //   yield/wait(本帧停)
        if (r==1)  goto refetch;  //   发生跳转,重取不进 PC
        // r==0 正常继续
    }
    if (instr.num_stack_refs != 0) ctx.stack_offset -= num_stack_refs; // 弹掉本指令消费的参数
advance:
    ctx.offset += instr.total_size;  instr += instr.total_size;        // 进 PC
refetch:
  } while (instr.time <= ctx.time);
}
EXIT:
ctx.time += dt;                       // dt = XMM1 入参(帧增量/game speed)
run float_i[8] interpolators;         // §5
return 0;
```
- **time 门控**:本帧执行所有 `time ≤ ctx.time` 的指令,遇到未来指令(wait)即停;`ctx.time` 帧末 +dt → 下帧更多指令到期。这就是"wait/timeline"机制的本体。
- **RET_BIG(ins 1)/上下文结束**:`cur_location = (-NAN,-NAN)`,return -1。
- **段式派发**:系统码(变量/算术/跳转/调用/数学)在本函数;**游戏码(开火/敌机/移动/anm…)走 `vm->vtable[0]` = `ecl_run_over_300`**(`0x41dcb0`),返回 -1 停帧 / 0 继续 / 1 已跳转重取。

---

## 3. ★★ 系统 opcode 表(0–0x5d)运行时语义(✅ 一手 + thecl 对名)

> 类型标:栈元素 8 字节 = 类型标记('i'=0x69 / 'f'=0x66)+ 4 字节值;弹栈按标记决定 int/float 解释。

| op | thecl 助记 | 运行时行为(本函数实证) |
| --- | --- | --- |
| 0,0x16,0x1e,0x1f | nop 类 | 空操作(22/30/31 等;在别处处理) |
| 1 | **RET_BIG** | 置 PC=(-NAN,-NAN),return -1(结束本上下文) |
| 10 | **RET_NORMAL** | `ecl_return`;从栈恢复调用方 (time,offset,sub,stack_offset);栈空则结束 |
| 11 | **CALL** | `ecl_call_sub`(同步调用 sub,压返回帧) |
| 12 | **GOTO** | `ctx.time = param[5]`;`ctx.offset += param[4]`;跳转(format `ot`:o=param[4],t=param[5]) |
| 13 | **UNLESS** | 弹栈,==0 则同 GOTO |
| 14 | **IF** | 弹栈,!=0 则同 GOTO |
| 15 | **CALL_ASYNC** | `ecl_spawn_async(vm,-1,0)`(0x474430)新建异步上下文挂 async_list |
| 16 | **CALL_ASYNC_ID** | 取 id → `ecl_spawn_async(vm,id,1)` |
| 17 | (kill async id) | `lookup_async(vm,id)`(0x4744e0)→ 置其 +8=-1(杀) |
| 18 / 19 | (set/clr flag) | `lookup_async`→ 目标 `+0x11e4 |=1 / &=~1`(`__set_by_ins_18_19`) |
| 20 | (set field) | `lookup_async`→ 目标 `+0x101c = arg1`(`__set_by_ins_20`) |
| 21 | (kill all async) | 遍历 `vm+0x1200` async_list,全杀 |
| 23 / 24 | (rel wait) | `ctx.time -= int_arg / float_arg` |
| 40 | **STACK_ALLOC** | `ecl_stack_alloc(stack, n)`(0x474810)开栈帧 |
| 41 | (return-ish) | `ecl_return` |
| 42 | **LOADI/push i** | 压入 int(标 'i') |
| 43 | **SETI** | 弹栈 → int 变量(`get_int_arg0_ptr`) |
| 44 | **LOADF/push f** | 压入 float(标 'f') |
| 45 | **SETF** | 弹栈 → float 变量 |
| 0x32–0x3a (50–58) | **ADD/SUB/MUL/DIV/MOD** | 各 I/F 版:弹 2 压 1(50 ADDI,51 ADDF,52 SUBI,53 SUBF,54 MULI,55 MULF,56 DIVI,57 DIVF,58 MODI) |
| 0x3b–0x46 (59–70) | **比较** | EQ/NE/LT/LE/GT/GE 各 I/F 版(59 EQI…70 GEF),弹 2 压 1(int 结果) |
| 0x47/0x48 (71/72) | **NOTI/NOTF** | ==0 |
| 0x49/0x4a (73/74) | **OR/AND** | 逻辑 |
| 0x4b/0x4c/0x4d (75/76/77) | **XOR/B_OR/B_AND** | 位运算 |
| 0x4e (78) | **DEC** | 变量自减,压旧值(times 循环计数) |
| 0x4f/0x50 (79/80) | **SIN/COS** | |
| 0x51 (81) | (rotate) | normalize_angle + `cartesian_from_polar`(0x474510)→ 2 输出 |
| 0x52 (82) | (wrap angle) | `math_normalize_angle` |
| 0x53 (83) | **NEGI** | 整数取负 |
| 0x54 (84) | **NEGF** | `^ 0x80000000`(浮点取负) |
| 0x55 (85) | (len²) | `a²+b²` |
| 0x56 (86) | (hypot) | `sqrt(a²+b²)` |
| 0x57 (87) | (atan2) | `atan2(...)` |
| 0x58 (88) | **SQRT** | |
| 0x59 (89) | (angle delta) | 角差,归一化到 [-π,π](用 ±2π 常量) |
| 0x5a (90) | (rotate pt) | sin/cos 旋转点 → 2 输出 |
| 0x5b/0x5c (91/92) | (interp set) | 配置 `float_i[idx]` 插值器(0x5c 带贝塞尔附加参);用 `bullet_size_interp`/`FUN_00417180` |
| 0x5d (93) | (random pt) | `prng_randf_signed` → 随机点 2 输出 |

> 0–93 = **thecl `th10_fmts` 基表的指令号**,运行时语义与 `00-*` §2.1 的格式表 + expr.c 的 `th10_expressions` 表**逐条对上**(ADDI=50…SQRT=88 全中)。这是对格式侧的运行时确认。

---

## 4. 变量/栈模型(✅,补 `01-*`/`02-*`)

- **表达式/局部栈** = `zEclStack`(ctx+0xc),`stack_offset`(ctx+0x100c)为栈顶字节偏移;**8 字节/元素**:类型标记('i'/'f')+ 4 字节值。push:写标记→ +4 →写值→ +4;pop:-4(值)、-4(标记),按标记决定 int/float。
- **局部变量/参数访问** 走 `ecl_get_int/float_arg`(0x473c90/473d40)+ `get_*_arg_ptr`。**三分支解析**(2026-06-10 套结构体后读清):指令 `variable_mask`(instr+8)的对应位 = 0 → **字面量**(`instr+0x10+idx*4`);= 1 → **引用**,引用值 ≥0 → **栈局部**(`stack.data + stack.base_offset + 值`)、为特定负值 → **栈相对**(`stack_offset + 值*8`,带 'i'/'f' 标记)、其余负 id → **全局/特殊变量**(经 `vm->vtable` = get_*_global)。这正对上 thecl `param_mask`(`00-*` §1.3)的"位 i=引用 vs 字面"。
- **特殊/全局变量**(负 id:I0-3/F0-3/RNG/位置…)走 `Enemy::ecl_get_*_global`(`01-*`),存敌机字段。两套命名空间并存(见 `02-*` §5)。
- **调用栈**:CALL(11)由 `ecl_call_sub` 压 (time,offset,sub,stack_offset) 返回帧;RET(10)由 `ecl_return` 弹回;栈空 → 上下文结束(敌机 main sub 结束即敌机消失,印证 Priw8)。

---

## 5. 帧末浮点插值器(`float_i[8]`)

循环退出后遍历 8 路 `zInterpFloat`(ctx+0x1024,本函数里 `param_1+0x409` 起,stride 0xc):若激活则 `bullet_size_interp` 推进一帧,结果写回目标(可为负 id 全局,经 vm vtable 解析,或栈局部)。由 ins 91/92 配置。= ECL 的"定时插值变量"(平滑改某变量到目标值)。

---

## 6. 与外部源交叉验证小结(★ 四源独立印证)
- **thecl**:opcode 0–93 = `th10_fmts` 指令号;ADD/SUB/.../SQRT、CALL=11/CALL_ASYNC=15/16/STACK_ALLOC=40/SETI=43/SETF=45/RET=1,10 **全对上**(`00-*`)。
- **ExpHP th-re-data**:`zEclRunContext`/`zEclRawInstructionHeader`/`zEclFileManager`/`zEclSubroutinePtrs` 字段偏移**全对上**(`02-*`);helper `lookup_async`(0x4744e0)、`cartesian_from_polar`(0x474510)同名。
- **★ Priw8 th16.eclmap**(`vendor/th16.eclmap`,298 条):opcode→名 **逐条印证我的语义**——`10 return`/`11 call`/`12 jmp`/`13 jmpEq`/`14 jmpNeq`/`15 callAsync`/`16 callAsyncId`/`40 stackAlloc`/`42 push`/`43 set`/`44 pushf`/`45 setf`/`50 add`/`51 addf`/`58 mod`/`78 dec`/`79 Math_sin`/`88 Math_sqrt`… **全中**。这是第 4 个独立源。
- **一处精化 ExpHP**:ctx+0x1018(ExpHP="enemy")在本函数当 **zEclVm 回指**用(vtable[0]/file_manager/async_list)——与 zEclVm 内嵌敌机+0 自洽。
- **我们独有(行为层)**:`ecl_spawn_async`(0x474430)、`ecl_stack_alloc`(0x474810)无人命名;**全部 opcode 的运行时行为** thecl/ExpHP/Priw8 **均只给名/签名,无行为描述**(Priw8 `ins.js` 零条 desc)——exe 实证的行为是本仓库增量。

## 7. 开放(及优先级调整)
- ⚠️ **游戏 opcode 的"名+签名"已被 Priw8 eclmap 全覆盖**(298 条:300=Enm_create / 400=Move_pos / 545=resetBoss / 600=Et_create…),**行为**多在 `ECL-info.md`(et*/move/enm,已交叉验证)。故全反 `ecl_run_over_300`(0x41dcb0)**边际价值有限**——大多是复述已知名/行为。
- ✅ **已完成**:ECL 开火 opcode(Et_* 600 区)→ fire 描述符字段映射 + enmCreate → **`05-fire-interface.md`**(et* 写入侧逐字段确认,接缝钉死)。
- ins 81/85/86/87/89/90/93 的精确参数布局(用 `ecl_get_*_arg` 索引)可按需细化。

## 8. ★ 未文档化 opcode(eclmap 没有、引擎却实现)— 对照 Priw8 `th16.eclm`(296 条,最新)

`ecl_run` 实处理、**Priw8 eclmap(新旧两版)均未命名**的系统 opcode:

| op | `ecl_run` 行为(一手) | 佐证 / 备注 | 可信 |
| --- | --- | --- | --- |
| **18** (0x12) | `lookup_async(arg0)` → 目标 `+0x11e4 \|= 1` | ExpHP 结构体字段 `__set_by_ins_18_19` 佐证存在 | ✅ |
| **19** (0x13) | `lookup_async(arg0)` → 目标 `+0x11e4 &= ~1` | 同上(成对:18 置位 / 19 清位) | ✅ |
| **20** (0x14) | `lookup_async(arg0)` → 目标 `+0x101c = arg1` | ExpHP 字段 `__set_by_ins_20` 佐证 | ✅ |
| **41** (0x29) | `EclStack__ecl_return(stack)` 后 `break`(**不**恢复调用帧,与 10 不同) | 疑栈帧清理/inline 收尾,角色待定 | ✅行为/🟡用途 |

> 即 **18/19/20 = 按 id 给另一条异步上下文写标志/字段**(`+0x11e4` 标志、`+0x101c` 字段)。
> ★ **消费者已查(2026-06-10):TH16 里这俩字段只写不读**——全 .text 扫 disp32 `[reg+0x11e4]`/`[reg+0x101c]` + 函数归位:除 ins18/19/20 自身的写、`reset_run_context` 的零初始化、和弹/玩家对象同偏移假阳性外,**无任何读取点**。→ **ins18/19/20 在 TH16 无可观测效果**(疑跨版本遗留/保留),这正解释了为何 eclmap 不收、ExpHP 只按"谁写"命名(`__set_by_ins_18_19`/`__set_by_ins_20`)却不给语义。🟡 "未发现读取点"(非标准寻址读取若现可推翻)。
> 另:`27`(Priw8 `unknown27`)→ 我的系统 switch 无此 case,落 default → 经 `vm->vtable[0]`=`ecl_run_over_300` 当**游戏 opcode** 处理(<300 却走游戏分支,异常,值得反);`22/30/31`(Priw8 `debug22`/`unknown30`/`unknown31`)在 `ecl_run` 里是**显式 nop**(case→break,系统循环内无副作用)。

> **方法学**:这条对照(引擎实现 opcode 集 vs 社区 eclmap)是找"未公开点"的好闸门——系统码已查完(上表 4 个);**高位游戏码(300+)已查**(`05-fire-interface.md` §2):224 个全是 eclmap 子集,**无未公开**。故 TH16 的"社区 eclmap 缺、exe 有"全部集中在低位系统码 18/19/20/41。

## 关联
- 格式表 `00-thecl-format-reference.md`;运行时结构/函数地图 `02-runtime-vm.md`;变量/上下文 `01-*`。
- 命名脚本:`../sht/disasm/scripts/apply_th16_ecl_names.py`(已加本轮 helper)。
- 纪律 `../sht/findings/00-METHOD-逆向记录纪律.md`;memory `re-overclaim-guard`/`re-evidence-chain-discipline`。
