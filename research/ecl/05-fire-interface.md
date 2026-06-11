# 05 — ECL 游戏 opcode 派发 + 开火接缝(ECL et* → 弹幕 fire 描述符)

> **对象**:TH16 `th16.exe`,imagebase 0x400000。日期 2026-06-10。
> **方法**:subagent 一手反编译 `ecl_run_over_300`(0x41dcb0)+ `bullet_spawn_wrapper`(0x414da0)+ `ecl_enm_create`(0x423050)+ PE 跳转表 `0x422c44`;与 Priw8 `vendor/th16.eclm`(命名层)对差,与 `../bullets/01` §6(spawn 读取侧)交叉印证。
> **provenance/可信度**:结论为 **subagent 一手反编译,地址可复核**;关键字段映射经 **写入侧(et* handler)与读取侧(bullet_spawn_wrapper)双向自洽** + 与我们独立做的 `../bullets/01` §6 一致 = 强。标 ✅一手 / 🟡推断 / ❓存疑。仅 TH16。

---

## 1. 游戏 opcode 派发结构(✅)

`ecl_run`(0x472030)对游戏 opcode 走 `vm->vtable[0]` = **`EnemyData::ecl_run_over_300`(0x41dcb0)**,后者:
- 取指同 `ecl_run`(file_manager+0x11f8 → subs+0x8c → bytecode;opcode=`*(u16*)(instr+4)`)。
- **范围闸**:仅 `[300, 1001]`(`(short)op - 300U ≤ 0x2bd`)进派发,其余(含所有 <300)落 default = no-op。
- **跳转表**:`switch(*(u8*)(0x422c44 + opcode))` —— `0x422c44`(.text,文件 off 0x22044)是按 raw opcode 索引的**压缩字节表**,选 174 个 case 之一(0..0xac + 0xad=default)。
- 处理 **224 个 opcode**(稀疏分布于 300..1001);多 opcode 共享一个 case(变体族)。

---

## 2. ★ "无未公开游戏 opcode"(对照 Priw8 eclmap,✅ 负结论)

- 引擎处理的 224 个 ≥300 opcode = Priw8 `th16.eclm`(230 个 ≥300 名)的**严格子集** → **≥300 无未公开 opcode**;Priw8 按名全覆盖 TH16 游戏 opcode。
- 反向:eclmap 有名、引擎无 case(落 default=no-op)的:`573 unknown573`、`900-904 debug900-904` = eclmap 自己的 debug/占位,引擎未实现。
- `27`(eclmap `unknown27`)= **确认 no-op**(<300,`ecl_run` 系统 switch 无 case → default → `ecl_run_over_300` 范围闸外 → no-op)。
- 对比 `04-*` §8 的**系统码(<256)**结论:那边有 4 个未公开(18/19/20/41,操作异步上下文,ExpHP 字段名佐证)。**所以 TH16 的"社区 eclmap 缺、exe 有"全部集中在低位系统码,游戏码无缺口。**

> 方法学:"引擎实现 opcode 集 vs 社区 eclmap" 是找未公开点的标准闸门;系统码 + 游戏码现已查全。

---

## 3. ★★ 开火接缝:发射器结构体 = fire 描述符(✅✅ 双向自洽)

**模型**:敌机/VM 对象内嵌**发射器(emitter)数组**,每个发射器 idx `i`(= 所有 et* 指令的 arg0)位于 `param_1 + i*0xe0 + 0x166`(dword 索引;**stride 0xe0 dword = 0x380 字节**,由 etCopy(op 614)的 `for(0xe0)` 拷贝循环坐实)。**这个发射器结构体就是传给 `bullet_spawn_wrapper`(0x414da0)的 fire 描述符**(= `../bullets/01` §6 的 `param_1`)。et* 指令是配置 setter,`etOn` 是触发。

### 3.1 et* opcode → 描述符字段(写入侧一手,desc 偏移相对发射器基 dword)

| op | 名 | case | 写入描述符字段 / 行为 | 可信 |
| --- | --- | --- | --- | --- |
| 600 | etNew | 0x72 | `memset(emitter,0,0x380)` + 默认值(`[0x16d?]`=2.0、packed 默认 `[0x23f..0x243]`) | ✅ |
| 601 | **etOn** | 0x73 | **开火**:由 et-offset(+0xf76 区)+ 敌机位置合成 pos 入 desc `[2][3][4]`;设 `g_bullet_mgr+0x44`(spawn 取消半径)= 敌机字段;调 **`bullet_spawn_wrapper(emitter+0x166)`** | ✅✅ |
| 602 | etSprite | 0x74 | desc **`[0]`=type**(arg1)、**`[1]`=subtype**(arg2) | ✅✅ |
| 603 | etOffset | 0x75 | et-offset x/y → 辅助区 `+0xf76/+0xf77`(etOn 时加进 pos) | ✅ |
| 604 | etAngle | 0x76 | desc **`[5]`=基准角**(arg1)、**`[6]`=散布步进**(arg2) | ✅✅ |
| 605 | etSpeed | 0x77 | desc **`[7]`=speed**、**`[8]`=speed2** | ✅✅ |
| 606 | etCount | 0x78 | desc **`[0xd9]` 低16=内层(路数)**、**高16=波数**(`desc+0x366`) | ✅✅ |
| 607 | etAim | 0x79 | desc **`[0xda]`=散布/瞄准模式**(u16) | ✅✅ |
| 608 | etSound | 0x7a | desc **`[0xdc]`=sfx id**、`[0xdd]`=第二音参 | ✅✅ |
| 609–612 | etEx/etEx2 | 0x7b | 写一条 **etEx 效果 = 11 dword(0x2c 字节)弹字节码指令** 入描述符字节码块 `[0x10 + n*0xb]`(stride 0xb dword = `../bullets/01` §3 弹 VM stride);按 raw opcode 0x262/0x263/0x264 变参数布局 | ✅ |

### 3.2 spawn 读取侧确认(`bullet_spawn_wrapper` 0x414da0,✅✅)

- 外层循环 `wave` 跑 `*(short*)(desc+0x366)`(= etCount 高16);内层 `spread_i` 跑 `(short)desc[0xd9]`(= etCount 低16)。
- 每颗 `bullet_pool_spawn(g_bullet_mgr, desc, spread_i, wave, baseAngle)`。
- `baseAngle`:若 desc `[2]/[3]` ≠ 玩家位 → `atan2` 朝玩家(自机狙),否则 `DAT_00494534`。
- SFX:`if (desc[0xdb] & 0x20) FUN_0045e1f0(desc[0xdc])` → desc **`[0xdb]` bit 0x20 = 播音标志**、**`[0xdc]` = sfx id**。

> **双向印证**:`../bullets/01` §6 从 spawn **读取侧**独立推出的字段([0]type/[1]subtype/[2..4]pos/[5]angle/[6]spread/[7]speed/[8]speed2/[0xd9]count/[0xda]mode/sfx),现由 et* **写入侧**逐一确认 = 这条 ECL→弹幕接缝在 exe 层钉死(社区 ECL-info/eclmap 未在 exe 层给)。
> **修正 `../bullets/01` §6**:sfx 是 **`[0xdc]`(非 [0xdd])**;`[0xdb]` bit 0x20=播音标志;`[0xd9]` 高16=波数(原文未拆分 count 高低16)。

---

## 4. enmCreate(`ecl_enm_create` 0x423050,op 300/301/304/305/309/311/312/321)✅

- float arg1/arg2 = spawn x/y;int arg3/4/5 = 额外参(life/anim/score,默认取指令立即数字段)。
- op 300/0x135/0x141/0x137/0x130:加**父敌机位置**(`param_1+0x44/+0x48`)→ 相对 spawn;"M"/相对变体置标志;mirror 标志 `0x80000` 翻 x 符号。
- 拷 0x54 字节参数块(敌机模板字段 `param_1+0x28c..+0x2b8` + `+0x5740`)→ 调 **`FUN_0041aa70(DAT_004a6dc0 敌人管理器, instr+0x14 sub名指针, &params)`** = **在敌人管理器里分配新 zEnemy 并按名启动一段新 ECL sub**;受容量闸 `enemy_mgr+0x18c < +0x8c` 限。
- ❓ 不在当前上下文起 sub,而是把命名 sub 交给新建敌机 → 印证 `02-*` §1"每敌机一个解释器"。

---

## 5. 开放 / 待挖
- 散布模式 `[0xda]` 的 0..0xc 各模式精确几何在 `bullet_pool_spawn`(0x412cb0)内,本轮未展开(🟡;接 `ECL-info.md` etAim 0-12 对照)。
- 发射器辅助区:et-offset `+0xf76..`、`+0xfa6..`(第二/"冻结"位,etOn 在 `+0xfa8 > 常量` 时用)、per-emitter 计数 `+0xf66`(etEx 自增)——存在 ✅,`+0xfa6` 分支用途 🟡。
- etEx 写入的弹字节码块 = `../bullets/01` §3 弹 VM 程序;ECL `etEx(type,a,b,r,s)` 的 type→opcode、a/b/r/s→指令字段已在 `ECL-info.md`/`../bullets/01` §8 交叉验证。

## 关联
- 解释器循环 `04-ecl-vm-interpreter.md`;运行时结构 `02-runtime-vm.md`;格式 `00-*`;变量 `01-*`。
- 弹幕引擎(下游):`../bullets/01-core-engine.md` §6(fire 描述符,本文已精修)、§3(弹 VM)、§8(etEx 交叉验证)。
- 命名层:`vendor/th16.eclm`(Priw8)。纪律:`../sht/findings/00-METHOD-逆向记录纪律.md`。
- ⚠️ 本文为 subagent 一手反编译,地址均可在 Ghidra `th16` 复核;主控未逐行复跑,但关键字段映射已由写/读双向 + bullets/01 三方自洽。
