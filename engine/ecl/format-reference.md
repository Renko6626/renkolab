# 00 — thecl 格式参考(.ecl 二进制格式 + TH16 opcode 表 + ECS→opcode 降级)

> **来源**:`vendor/thtk/thecl/`(thtk @ `892114a0`,BSD 许可),由 thpatch 社区维护的 ECL 反汇编/重编译器。
> **可信度框架**:
> - ✅**格式侧**(文件布局 / id→参数格式 / ECS→opcode 降级):thecl 是 de-facto 标准工具、能 round-trip 真实游戏 .ecl,**单源但权威**。
> - 🟡**命名**:thtk **不附带任何 TH16 eclmap**;opcode/变量的**人类可读名**(enmCreate/etNew/movePos…)来自 `ECL-info.md` 及社区 eclmap,thecl 只给数字 id + 参数格式。
> - ✅**运行时语义(已做,更新 2026-06-10)**:thecl 只给参数形状(WHAT);运行时实现(HOW)已反编译——系统 opcode 见 `04-ecl-vm-interpreter.md`(`ecl_run` 0x472030),游戏 opcode 派发 + 开火接缝见 `05-fire-interface.md`(`ecl_run_over_300` 0x41dcb0)。⚠️ 旧注里的"派发表 0x4921b4"是误判,实为变量访问器表(已纠,见 `01`/`03`)。
> - **仅 TH16**(version 16);TH16.5=165 是独立变体,勿混。
>
> **本文件用途**:做 `th16.exe` ECL VM 逆向时的**外部锚点**——把运行时 opcode 派发表的每一项,对到下面 thecl 的"格式 id → 参数格式 / 语义类别"。

---

## 0. 速览:这份素材为什么对 exe 逆向关键

1. **补全了 VM 机器层**:`ECL-info.md` 全是高层命名指令(enmCreate/etNew…),但 thecl 暴露了**低位 opcode = VM 控制核**(RET/CALL/STACK_ALLOC/LOAD/SET/算术/比较/跳转)。这正是 exe 派发表 `0x4921b4` 里那些操作"每 sub 栈帧 + 表达式栈 + PC"的小 handler。已知 `FUN_00424110`=random handler 是表中一项。
2. **id 区段 ↔ ECL-info 分类吻合**(双向印证,见 §3):`300-340`敌人/ANM、`400-439`移动、`500-572`杂项,与 ECL-info 标注逐段对齐。
3. **TH16 ≈ TH13**:TH16 只改 6 个 opcode(337/338/339/340/572/1000),其余继承 TH13 → 社区 TH13-15 eclmap 命名基本可复用。

---

## 1. .ecl 二进制文件格式(TH10+ 引擎,thecl10.c)

> 来源:`thecl10.c:43-90`(packed 结构)+ `th10_open()` `thecl10.c:1212-1410`。**game exe 直接 mmap 并解释这套布局**,故偏移精确。

### 1.1 顶层布局(自顶向下)

```
偏移        大小              段
0x00        0x20             SCPT 头 (th10_header_t)
0x20        变长             ANIM 列表头 (th10_list_t) + anim 名(NUL 结尾串)
+           (4 字节对齐)      → ECLI 列表头 + ecli 名
+           (4 字节对齐)      sub 偏移数组 (uint32_t × sub_count, 绝对文件偏移)
+           变长             sub 名(每 sub 一个 NUL 结尾串,顺序同偏移数组)
+           (4 字节对齐)      各 sub:ECLH 头 + 指令流
```

### 1.2 关键结构

**SCPT 头** `th10_header_t`(0x20 字节,`thecl10.c:43-53`)
| 偏移 | 字段 | 说明 |
| --- | --- | --- |
| 0x00 | `magic[4]` | `"SCPT"` |
| 0x04 | `unknown1` u16 | 恒 1 |
| 0x06 | `include_length` u16 | ANIM+ECLI 段总长 |
| 0x08 | `include_offset` u32 | = 0x20(紧接头) |
| 0x10 | `sub_count` u32 | sub 数量 |
| 0x14 | `zero2[4]` | 保留 0 |

**ANIM/ECLI 列表** `th10_list_t`(8 字节头,`:55-61`):`magic[4]`(`"ANIM"`/`"ECLI"`)+ `count` u32 + 变长 NUL 串(CP932)。anim 名 = 引用的 .anm 文件名;ecli 名 = include 的其它 .ecl。

**sub 偏移数组**(`:1285`):4 字节对齐(`(4 - addr) % 4` 修正),`sub_count` 个 u32,各为该 sub 的 **ECLH 绝对文件偏移**。

**ECLH sub 头** `th10_sub_t`(0x10 字节,`:63-70`):`magic[4]`(`"ECLH"`)+ `data_offset` u32(恒 8)+ `zero[2]`;指令流从 ECLH+0x10 起。sub 边界 = 下一个 sub 偏移(或文件尾)。

### 1.3 指令记录 `th10_instr_t`(0x10 字节头,`thecl10.c:72-90`)

| 偏移 | 字段 | 说明 |
| --- | --- | --- |
| 0x00 | `time` u32 | 指令的时间戳(帧)。同 time 成组,**VM 按 time 门控执行** |
| 0x04 | `id` u16 | **opcode**(查 §2 格式表) |
| 0x06 | `size` u16 | 整条记录字节数(含头),用于跳到下一条 |
| 0x08 | `param_mask` u16 | **位 i=1 → 第 i 个参数是栈/变量引用,=0 字面量**(`:1348-1390`) |
| 0x0A | `rank_mask` u8 | 难度位 `1111LHNE`(E/N/H/L 低 4 位;TH13+ 加 Extra/Overdrive)。0xFF=全难度 |
| 0x0B | `param_count` u8 | TH10-12=参数个数;**TH13+=参数里栈引用的个数** |
| 0x0C | `zero` u32 | TH13+:栈引用计数相关(序列化时 `<<3`) |
| 0x10 | `data[]` | 参数数据,按格式串 + param_mask 解码 |

> **跳转/时间偏移基准**:`o`(跳转)偏移相对**当前指令在 sub 内的偏移**;指令的 `offset` = 相对 ECLH 起点;`address` = `offset + sub_offsets[i]`(绝对)。runtime 解析 goto 即按 sub 内相对偏移。

### 1.4 参数线上编码(`th10_value_from_data` `thecl10.c:92-123`)

| 格式字符 | 类型 | 字节 | 编码 |
| --- | --- | --- | --- |
| `S` | int32 | 4 | 小端有符号 |
| `f` | float | 4 | IEEE754 |
| `o` | 跳转偏移 | 4 | int32,相对当前指令偏移(label 目标) |
| `t` | 时间目标 | 4 | int32(帧 time) |
| `m` | 字符串/blob | 变长 | 4 字节长度前缀 + 数据 |
| `x` | 加密串 | 变长 | 同 `m`,数据再 **XOR 0x77**(`util_xor(...,0x77,7,16)`) |
| `D`/`H` | 转换参数 | 8 | `thecl_sub_param_t`:`from` 字符 + `to` 字符 + u16 零 + 4 字节值联合。`H` 在 mask 里占 2 位 |
| `*` 前缀 | 重复 | — | `*S` = 余下数据反复按 S 读(可变参数,如 CALL 的参数表) |

`thecl_sub_param_t`(`thecl.h:80-90`):调用/赋值时携带源类型→目标类型(int↔float)+ 值,实现调用边界类型转换。

---

## 2. TH16 opcode → 参数格式表(thecl10.c)

> **继承链**(`th10_find_format()` `thecl10.c:1114-1174`,后者覆盖前者):
> `th16` → `th15` → `th143` → `th14` → `th13` → `th128` → `th125` → `th12` → `th11` → `alcostg` → `th10`(兜底)。
> 即:绝大多数 TH16 指令实际来自 **th13_fmts**;TH16 自己只覆盖/新增 6 条(下表标 ★TH16)。

### 2.1 ★ VM 机器核(低位 opcode)— 对 exe 逆向最关键

> 这些是 `ECL-info.md` **没有**记录的底层指令(它只记高层命名指令)。exe 派发表 `0x4921b4` 的低位项应对应这些。来自 `th10_fmts`(`:167-348`)+ `expr.c:88-143` 表达式表 + `thecl.h:66-78`。

| id | 助记符 | 格式 | 语义(thecl 侧) | 栈 |
| --- | --- | --- | --- | --- |
| 1 | RET_BIG | `""` | 返回(大 sub) | — |
| 10 | RET_NORMAL | `""` | 返回(普通 sub) | — |
| 11 | CALL | `m*D` | 同步调用 sub(名 + 可变参数) | — |
| 12 | GOTO | `ot` | 无条件跳转到 label@time | — |
| 13 | UNLESS | `ot` | 栈顶为假则跳转 | pop1 |
| 14 | IF | `ot` | 栈顶为真则跳转 | pop1 |
| 15 | CALL_ASYNC | `m*D` | 异步调用(并行协程) | — |
| 16 | CALL_ASYNC_ID | `mS*D` | 带 slot id 的异步调用 | — |
| 17 | kill async by id | `S` | ✅ 确认(`04` §3:`lookup_async`→置 +8=-1 杀) | ✅ |
| 40 | STACK_ALLOC | `S` | sub 入口分配栈帧(字节数) | — |
| 42 | LOADI | `S` | 压入 int(变量或字面) | push1 |
| 43 | SETI | `S` | 弹栈赋给 int 变量 | pop1 |
| 44 | LOADF | `f` | 压入 float | push1 |
| 45 | SETF | `f` | 弹栈赋给 float 变量 | pop1 |
| 50/51 | ADDI/ADDF | `""` | 加 | pop2 push1 |
| 52/53 | SUBI/SUBF | `""` | 减 | pop2 push1 |
| 54/55 | MULI/MULF | `""` | 乘 | pop2 push1 |
| 56/57 | DIVI/DIVF | `""` | 除 | pop2 push1 |
| 58 | MODULO | `""` | 取模 | pop2 push1 |
| 59/60 | EQI/EQF | `""` | == | pop2 push1 |
| 61/62 | NEQI/NEQF | `""` | != | pop2 push1 |
| 63/64 | LTI/LTF | `""` | < | pop2 push1 |
| 65/66 | LTEQI/LTEQF | `""` | <= | pop2 push1 |
| 67/68 | GTI/GTF | `""` | > | pop2 push1 |
| 69/70 | GTEQI/GTEQF | `""` | >= | pop2 push1 |
| 71/72 | NOTI/NOTF | `""` | 逻辑非 | pop1 push1 |
| 73 | OR | `""` | \|\| | pop2 push1 |
| 74 | AND | `""` | && | pop2 push1 |
| 75 | XOR | `""` | 逻辑异或 | pop2 push1 |
| 76 | B_OR | `""` | 位或 | pop2 push1 |
| 77 | B_AND | `""` | 位与 | pop2 push1 |
| 78 | DEC | `S` | 变量自减并压结果(times 循环用) | push1 |
| 79/80 | SIN/COS | `""` | 三角 | pop1 push1 |
| 81-93 | (各种 float 数学/向量) | 见 §2.2 | — | — |

> 返回寄存器(`thecl.h:77-78`):**I3 = `-9982`**(int 返回)、**F3 = `-9978.0`**(float 返回)。非 inline 调用后用 `LOADI -9982` 取返回值。NEGI/NEGF/SQRT 的具体 id 随版本(`is_post_th125`/`is_post_th13`)变动,TH16 见 expr.c 版本分支。

### 2.2 高层命名指令区(id ≥ 300,继承 th13_fmts,与 ECL-info 分类对齐)

> 格式串列全,**命名见 ECL-info.md / 社区 eclmap**(thtk 不附带)。区段对应 ECL-info 标注。

**敌人创建 / ANM(300-340)** — ECL-info「enmCreate/anm*」区:
`300 mffSSS`·`301 mffSSS`·`302 S`·`303 SS`·`304 mffSSS`·`305 mffSSS`·`306 SS`·`307 SS`·`308 SS`·`309-312 mffSSS`·`313 S`·`314 SS`·`315 SSf`·`316 SS`·`317 SS`·`318 ""`·`319 Sf`·`320 Sff`·`321 mSSSSS`·`322 SS`·`323 SS`·`324 S`·`325 SSSS`·`326 SSSSSS`·`327 SS`·`328 SSSS`·`329 Sff`·`330 SSSff`·`331 SS`·`332 SSSS`·`333 SSSff`·`334 S`·`335 Sff`·**`336 SS`★(th14 覆盖,原 th13=SSSm)**·**`337 SSfff`★TH16(原 th14=SSS)**·**`338 SSfff`★TH16 新**·**`339 SSS`★TH16 新**·**`340 S`★TH16 新**

**移动(400-439)** — ECL-info「movePos/moveVel/moveCircle…」区:
`400 ff`·`401 SSff`·`402 ff`·`403 SSff`·`404 ff`·`405 SSff`·`406 ff`·`407 SSff`·`408 ffff`·`409 SSfff`·`410 ffff`·`411 SSfff`·`412 SSf`·`413 SSf`·`414 ""`·`415 ""`·`416 fff`·`417 fff`·`418 ff`·`419 ff`·`420 ffffff`·`421 SSfffff`·`422 ffffff`·`423 SSfffff`·`424 S`·`425 Sffffff`·`426 Sffffff`·`427 ""`·`428 ff`·`429 SSff`·`430 ff`·`431 SSff`·`432 S`·`433 S`·`434-435 SSSff`·`436-437 SSff`·`438-439 SSSff`

**敌人属性 / 杂项(500-572)** — ECL-info「setHurtbox/spell/playSound…」区:
`500 ff`·`501 ff`·`502 S`·`503 S`·`504 ffff`·`507 SS`·`508 ff`·`510-512 S`·`514 SSSm`·`515-516 S`·`517 SSS`·`518 S`·`521 Sm`·`522 SSSx`·`524 S`·`526 f`·`527 SfS`·`528 SSSx`·`529 ffff`·`530 ffffff`·`531 fff`·`532 SSSS`·`533 SSSSSS`·`534 SSS`·`535 SSSSS`·`536 fffff`·`537-539 SSSx`·`540-541 S`·`544 S`·`546 SS`·`547 f`·`548 SSSS`·`549-553 S`·`555 SS`·`556 m`·`557 SSSff`·`558-559 S`·`560 ff`·**`572 S`★TH16 新**

**其它区**:`600-640`(子弹/激光相关?`609 SSSSSSff`·`610 SSSSSSSSffff` 等多参数)、`700-714`、`800-802`、`900`、`1000-1003`(**`1000 SSS`★TH16,原 th13=S**)。完整逐 id 见 `thecl10.c` th13_fmts(`:667-936`)。

---

## 3. ECS 源语言 → opcode 降级(控制流 / 变量 / 调用)

> 来源:`ecsparse.y`(bison 文法)+ `ecsscan.l`(词法)+ `expr.c`。揭示 VM 的栈帧/变量/调用机制,exe 侧应能对上。

### 3.1 控制流构造 → opcode
- `goto L @ t` → **GOTO(12)** `ot`。
- `if (c) goto` / `if (c){}` → 条件入栈后 **UNLESS(13)**(条件假则跳过);`unless` 用 IF(14)。
- `while(c){}` → label_st → eval c → UNLESS→end → body → GOTO st → label_end。
- `do{}while(c)` → label_st → body → eval c → IF(14)→st。
- `times(n){}` → 局部计数器 → **DEC(78)** 自减 → UNLESS 退出。
- `loop{}` → label_st → body → GOTO st(无限)。
- `break`→`GOTO {block}_end`;`continue`→`GOTO {block}_st`。
- `switch` → 求值入局部变量 → 逐 case LOAD+EQ(59)+IF(14) 跳转。
- `return expr` → eval → **SETI(43)/SETF(45)** 写 I3/F3 → **RET_NORMAL(10)**;无值直接 RET_NORMAL。

### 3.2 变量 / 栈模型
- 局部变量声明 `var/int/float A` → 4 字节对齐分配栈偏移(0,4,8…);sub 入口插 **STACK_ALLOC(40)** = 总栈字节。
- sub 参数 = 前 N 个变量(偏移 0,4,…N*4);`arity = stack/4`;每参数类型记进 `sub->format`。
- 取值 sigil:`$A`=按 int 读(`LOADI`)、`%A`=按 float 读(`LOADF`);无类型变量必须带 sigil。
- 全局变量优先(`seqmap_find(gvar_names)` 命中则用其 id,如 `$I0`/`%F0`),否则解析为局部栈偏移。
- 作用域:scope 栈;变量记 scope id,出作用域不可见,偏移可复用。

### 3.3 调用约定
- 同步 `@sub(args)` → **CALL(11)** `m*D`:参数 0 = sub 名(`m` 串),后续 `*D` = 类型转换参数(`thecl_sub_param_t`:from→to + 值)。
- 异步 `@sub() async` → **CALL_ASYNC(15)**;带 slot:`async id` → **CALL_ASYNC_ID(16)** `mS*D`(多实例并发)。
- 表达式里调用非 inline sub:CALL 后 `LOADI/LOADF I3/F3` 取返回值。
- inline sub:指令就地展开(变量/标签重命名防冲突),返回值直接留栈,不用 I3/F3。
- 表达式 = 栈机器:递归输出子节点(LOAD…)再输出运算符(无参 opcode,pop2 push1)。编译期常量折叠(`2+3`→`LOADI 5`)。

### 3.4 难度 / 时间门控(VM 行为线索)
- 每条指令带 `time`(帧)+ `rank_mask`(难度位)。**VM 只在 当前 time ≥ 指令 time 且 当前难度 ∈ rank_mask 时执行该指令** → exe 侧应有"按 time 推进 PC + rank 过滤"的主循环。
- `!E/!N/!H/!L/!*` 难度标签 → 给随后指令打 rank_mask 位;`a:b:c` 难度三元 → 按难度选值。

---

## 4. eclmap(命名层)与 thtk 的关系

- eclmap = 文本映射文件,段:`!ins_names`(id→名)、`!ins_signatures`(id→格式串)、`!gvar_names`(变量 id→名)、`!gvar_types`(`$`int/`%`float/`?`)、`!timeline_ins_names/signatures`。解析 `eclmap.c:80-224`。
- 反汇编时 `seqmap_get(g_eclmap->ins_names, id)` 命中→输出名,否则 `ins_NN`(`thecl10.c:1833`);变量同理(`:1701`)。
- **⚠️ thtk 不附带任何 eclmap 数据文件**(只有解析器 + `contrib/eclmapcvt.awk` 转换脚本)。TH16 的 opcode/变量名须用 `-m` 加载社区 eclmap(thcrap / 逆向项目);**本仓库的命名来源 = `ECL-info.md`**。
- → **行动项**:可据 §2 + ECL-info 自建一份 TH16 eclmap(`!ins_names` 把 300-340/400-439/500-572 对到 ECL-info 名),既能用 thecl 反汇编真 .ecl 做 ground-truth,也能反过来核对 exe handler。

---

## 5. 怎么用它驱动 exe 逆向(衔接 README §A/§B)

1. **派发表对名**:dump exe `0x4921b4` 指针表 → 表索引 i 大概率 = opcode id。先核**低位(§2.1 VM 核)**:找到只操作"栈/变量/PC/time"的小 handler 应是 LOAD/SET/算术/GOTO/CALL;`FUN_00424110`(random)已知是一项,定位它在表中的索引可校准整张表的 id 基准。
2. **CALL/STACK_ALLOC 验栈帧模型**:在 exe 找 STACK_ALLOC(40)handler → 它怎么给敌机/sub 开栈帧 → 坐实"敌机结构里的 ECL PC/栈指针"(README §C 的关键假设)。
3. **开火指令落位**:§2.2 里 et*/开火相关高层 opcode(疑在 600 区或独立)→ 对到 README §A 的外部开火点 `FUN_0041dcb0`/`FUN_00431fe0`/`FUN_00438cb0`,看它们对应哪个 opcode id、怎么把参数灌进 fire 描述符(`bullets/01` §6)。
4. **time/rank 门控**:exe 的 ECL 主循环按 time 推进 + rank_mask 过滤——✅ **已定位 = `EclRunContext::ecl_run`(0x472030,见 `04`)**。⚠️ 早期"疑 VM 主体 `FUN_0044c8c0`"的猜测**错了**(ExpHP:`0x44c8c0` 被 `MainMenu::do_options` 0x44c570 调 → 菜单逻辑,非 ECL VM),勿再追。

---

## 关联
- exe 侧锚点 / 派发表 `0x4921b4` / 开火点:`README.md` §A/§B/§C。
- 高层命名 + etEx 效果:`ECL-info.md`(已与弹运动 VM 交叉验证,见 `../bullets/01` §8)。
- 弹运动 VM(ECL 下游,opcode 0x2000/EX_SHOOT 创建):`../bullets/01-core-engine.md` §3/§6。
- 来源 commit:thtk `892114a0`(`vendor/` 已 gitignore,按本记录可重克隆)。
- 纪律:`../sht/findings/00-METHOD-逆向记录纪律.md`。**本文件 = 格式侧(thecl 权威);运行时语义已在 `04`/`05` 反编译完成(系统 opcode + 游戏 opcode 派发 + 开火接缝)。**
