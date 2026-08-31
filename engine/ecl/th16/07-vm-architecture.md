# 07 — ECL 虚拟机整体机制(宏观总览 + 核心机制确定)

> **定位**:这是 ECL VM 的**capstone 总览**——把 `00`–`06` + `../shared/th16-main-loop.md` 的细节收束成一张宏观图,并把**核心机制逐条标注确定性**。要细节查对应专题文档;要全局看这篇。
> **对象**:TH16 `th16.exe`,imagebase 0x400000。日期 2026-06-10。
> **可信度**:本文骨架机制均 ✅**一手反编译**(`ecl_run` 0x472030 / `Enemy::ecl_run` 0x473bc0 / `call_sub` 0x471db0 / `ecl_run_over_300` 0x41dcb0 / `run_all_on_tick` 0x401460),并与 thecl 指令号、ExpHP 结构体、Priw8 eclmap **四源交叉印证**。仅 TH16。

---

## 0. 一句话

**ECL 是一台"每敌机一实例"的栈式字节码虚拟机**:每帧由主循环驱动每个敌机,敌机把自己的若干**调用栈(主 + 异步)**各推进一遍;每条栈是一台 `EclRunContext`,按 **time 门控 + rank 过滤**取指、派发——**低位 opcode(<300)是通用 VM 核心(算/跳/变量),高位(≥300)是经 vtable 派发的"宿主 syscall"(造敌/移动/开火/动画)**;开火 syscall 把参数灌进发射器描述符交给弹幕池。

---

## 1. 五层全景图

```
[主循环] Window::do_frame (0x45a8a0) ──每帧──▶ UpdateFuncRegistry::run_all_on_tick (0x401460)   〔../shared/th16-main-loop〕
            按优先级遍历子系统 on_tick:Stage(0x11) · EnemyManager(0x1a) · BulletManager(0x1c) · Effect(0x1f) · …
                                              │
[宿主] EnemyManager::on_tick_1a (0x41b3d0) ──┘ 遍历敌人链表 mgr+0x180,逐敌机:
            Enemy::on_tick (0x41d1e0) ─▶ Enemy::ecl_run (0x473bc0)
                                              │  〔§2 多调用栈调度〕
[VM 实例] EclRunContext::ecl_run (0x472030) ─┘ 推进一条调用栈一帧        〔§3 取指-派发循环 / 04〕
            ├ opcode < 300  ── 内联处理:控制流/变量/算术/数学/调用         〔§4 VM 核心 / 04〕
            └ opcode ≥ 300  ── vm->vtable[0] ─▶ EnemyData::ecl_run_over_300 (0x41dcb0)  〔§4 宿主 syscall / 05〕
                                              │
[引擎子系统] enmCreate→敌人管理器 · move→运动 · et*/etOn→─┐
                                              │           ▼
[下游 VM] 弹幕池 bullet_pool_spawn ◀── 发射器描述符 ◀── etOn 触发           〔开火接缝 / 05 §3,../bullets/01 §6〕
            每弹再跑弹运动 VM Bullet::run_ex (0x413860)
```

---

## 2. 执行模型:每敌机一解释器,多条并发调用栈 ✅

- **没有全局 VM**:每个敌机自带 ECL 解释状态;无敌机=无 ECL 运行(Priw8 + 本仓库一手)。
- **一个敌机 = 一条 main 调用栈 + 任意条 async 侧栈**。`Enemy::ecl_run`(0x473bc0,✅一手)每帧**遍历该敌机的运行上下文链表**,逐个调 `EclRunContext::ecl_run` 推进:
  - **首个 = main 栈**:其 `ecl_run` 返回非 0(= 整条栈跑完)→ `Enemy::ecl_run` 返回 -1 → **宿主据此删除该敌机**(= "main sub 结束,敌机消失")。
  - **其余 = async 栈**(由 `CALL_ASYNC` ins15/16 创建):跑完(返回非0)就**从链表解链 + 释放**(`FUN_004749df`),其余正常推进。
- 每条栈本身是一台 `EclRunContext`(§5)。**这就是 ECL 的"协程"模型**:async sub = 同一敌机上的并发协程。

---

## 3. 取指-解码-执行循环 `EclRunContext::ecl_run`(0x472030)✅(详见 `04`)

一条调用栈推进一帧:
1. **取指**:PC = `cur_location`(sub 索引 + 字节偏移)→ `vm->file_manager->subroutines[idx].bytecode + 0x10(ECLH) + offset`。
2. **time 门控**:执行所有 `instr.time ≤ ctx.time` 的指令,遇未来指令(wait)即停;帧末 `ctx.time += dt`。← timeline/wait 的本体。
3. **rank 过滤**:`ctx.difficulty_mask & instr.rank_mask == 0` → 跳过(难度裁剪)。
4. **派发**(§4)→ 执行。
5. **进 PC**:`offset += instr.total_size`。
6. **平栈**:按 `instr.num_stack_refs` 弹掉本指令消费的栈参。

---

## 4. opcode 两层(核心设计)✅

| | <300(实际 0–93) | ≥300(300–1001) |
| --- | --- | --- |
| **本质** | **通用脚本 VM 核心**(语言基础设施) | **宿主 syscall**(对引擎子系统的副作用) |
| **内容** | ret/call/jmp/if、push/set/load、算术/比较/逻辑、sin/cos/sqrt/atan2、wait | enmCreate/move*/et*开火/anm*/playSound/spell/lifeSet… |
| **在哪处理** | **内联在 `ecl_run`** 的大 switch | `ecl_run` default → **`vm->vtable[0]` 虚派发** → `ecl_run_over_300`(字节跳转表 0x422c44) |
| **对世界** | 纯计算 + 控制;**只能经变量"读"世界** | **"写"世界**(spawn/move/fire/改状态) |
| **可扩展性** | 固定 | vtable 虚派发 = 宿主专属/可 hook(自定义指令钩这里,`06`) |
| 94–299 | — | 空(留白,落 default no-op) |

> 类比:**<300 = CPU 指令集,≥300 = OS syscall**。两层用 OOP 虚函数分层,不是 if-else。

---

## 5. 状态与栈模型 ✅(详见 `04`/`02`)

- **`zEclRunContext`**(一条调用栈的全部状态):`time`(+0)、`cur_location`=PC(sub+offset,+4)、`stack`(+0xc)、`difficulty_mask`(+0x1020)、`vm` 回指(+0x1018)、8 路浮点插值器(+0x1024)。
- **`zEclStack`**(操作数栈 + 局部变量):**8 字节/槽 = 类型标记('i'/'f')+ 值**;`stack_offset`(栈顶)、`base_offset`(当前帧基址)。
- **调用/返回 `call_sub`(0x471db0)✅一手**:CALL(ins 11)① 把实参拷进新栈帧;② **压返回帧 =(time, PC.offset, PC.sub)**;③ `find_sub_by_name(instr+0x14)` **按名解析被调 sub**(动态链接);④ 跳到新 sub(offset 0)。RET(ins 10,case 10)弹回这三者;栈空 → 本栈结束(§2)。async 调用(ins15/16)则新建一条独立 `EclRunContext` 挂上敌机的上下文链表。
- **变量三命名空间**(取参函数按指令 `variable_mask` 位决定):**字面量** / **栈局部**(`base_offset`+偏移)/ **全局·特殊变量**(负 id,经 `vm->vtable`→`ecl_get_*_global`,如 RNG/玩家位/I0-3/F0-3/难度,见 `01`)。

---

## 6. 核心机制确定性一览

| 机制 | 状态 | 证据 |
| --- | --- | --- |
| 每敌机一解释器 / main+async 多栈调度 | ✅一手 | `Enemy::ecl_run` 0x473bc0(§2) |
| 取指 + time 门控 + rank 过滤 + 进 PC + 平栈 | ✅一手 | `ecl_run` 0x472030(§3,`04`) |
| <300 系统 opcode 全表行为 | ✅一手 + thecl/Priw8 对名 | `04` §3 |
| ≥300 经 vtable 虚派发 / 字节跳转表 | ✅一手 | `ecl_run_over_300` 0x41dcb0(`05`) |
| CALL 压帧(time/PC/sub)+ 按名解析 sub | ✅一手 | `call_sub` 0x471db0(§5) |
| 变量三分支(字面/栈/全局) | ✅一手 | `ecl_get_int_arg` 0x473c90(`04` §4) |
| 主循环 → 敌机 → ecl 驱动链 | ✅一手 | `run_all_on_tick` 0x401460 + 敌机 body(`../shared/th16-main-loop`) |
| 开火接缝(et*→描述符→弹池) | ✅一手(写/读双向) | `05` §3 |
| RNG / 数学原语(确定性回放) | ✅一手 | `../shared/th16-engine-math` |

---

## 7. 开放(宏观层面已闭环,余为细节/边角)
- `Enemy::on_tick`(0x41d1e0)内部 → `ecl_run` 的确切调用点未逐行(已知它驱动 ECL)。
- `Window::do_frame` 内部(WinMain 泵 / 帧率节流)未一手。
- ✅ **async 已闭环**:创建(`ecl_spawn_async` 0x474430)、调度(`Enemy::ecl_run`)、按 id 管理(`lookup_async`)全反清。**ins18/19/20 写的控制标志(`+0x11e4`/`+0x101c`)= TH16 里只写不读**(全 .text disp32 扫描 + 函数归位:无任何读取点;唯一命中均为写入/初始化或弹对象同偏移假阳性)→ **TH16 无可观测效果,疑跨版本遗留**(故 eclmap 不收、ExpHP 只按"谁写"命名字段)。🟡 属"未发现读取点",非标准寻址读取若现可推翻。
- 未公开系统码 41(0x29)用途(疑栈帧清理)。
- ≥300 各 handler 行为多数未逐条反(Priw8 eclmap 命名 + ECL-info 行为已覆盖,故意取舍,`05` §2)。

## 关联
- 格式/opcode 表 `00` · 变量/上下文 `01` · 运行时结构/函数地图 `02` · ExpHP 对照 `03` · **解释循环 `04`** · **游戏派发+开火 `05`** · 自定义指令 `06` · 主循环 `../shared/th16-main-loop.md` · 数学/RNG `../shared/th16-engine-math.md` · 弹幕 `../bullets/01`。
- 纪律 `../sht/findings/00-METHOD-逆向记录纪律.md`。
