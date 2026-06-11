# TH16 主循环 / 每帧更新调度(引擎主干)

> **对象**:TH16 `th16.exe`,imagebase 0x400000。日期 2026-06-10。
> **方法**:ExpHP th-re-data 命名 + 本仓库一手反编译 `run_all_on_tick`(0x401460)与 `EnemyManager::on_tick_1a__body`(0x41b3d0)双重坐实;xref 追到顶层 `Window::do_frame`。
> **可信度**:派发器机制 + 敌机/弹幕驱动链 = ✅一手;子系统命名/优先级 = ExpHP(✅✅,与本仓库吻合)。仅 TH16。
> 这补上了 `../bullets/01-core-engine.md` §6 标 🟡 的"调度器顶层 runner 未反"。

---

## 1. 架构:优先级更新表 `UpdateFuncRegistry`

引擎没有手写的大主循环;每帧靠一个**优先级回调表** `UpdateFuncRegistry` 驱动所有子系统。

- 子系统启动时把自己的 `on_tick`/`on_draw` 回调用 `register__on_tick`(0x401300)/`register__on_draw`(0x4013b0)注册进表(节点 `UpdateFunc`,`operator new` 0x401730);带**优先级**(决定遍历顺序)。
- 每帧 `run_all_on_tick`(0x401460)遍历表、按序调每个回调;`run_all_on_draw`(0x4015a0)同构跑渲染。

**`run_all_on_tick`(0x401460)机制(✅一手)**:遍历 `registry+0x18` 链表(游标存 `+0x50`,节点 `[1]`=next);每节点取 `UpdateFunc` 对象 `obj`,若 `obj+8`(on_tick 指针)非空且 `obj+4 & 2`(启用位)→ 调 `(*obj+8)()`。**回调返回码驱动生命周期**:`0`→注销(`unregister` 0x4017a0)、`3`→停止本帧返回 1、`5`→返回 -1、`6`→重头遍历、`7`→继续、其它→下一项;另在某些码下调 `obj+0x10`(第二回调)。临界区保护(`DAT_004c0f58`)。
> 这套 0/3/5/6 返回码 = 我们在 ECL/弹幕 handler 见过的 -1/0/1 生命周期约定的同源。

---

## 2. 每帧链(顶层 → 子系统 → VM)

```
Window::do_frame__normal_version (0x45a8a0)              ← 顶层帧驱动(另有 frameskip 0x45ac50 / 变体 0x45ae70)
 └ UpdateFuncRegistry::run_all_on_tick (0x401460) ✅      ← 按优先级遍历
    ├ Stage::on_tick_11            (0x409e50, prio 0x11)  → 关卡/STD/背景
    ├ EnemyManager::on_tick_1a     (0x41b4f0 / body 0x41b3d0, prio 0x1a) ✅一手
    │    └ 遍历敌人链表 mgr+0x180;每敌机 Enemy::on_tick (0x41d1e0)
    │         └ Enemy::ecl_run (0x473bc0) → EclRunContext::ecl_run (0x472030)   【ECL VM,见 ../ecl/04】
    ├ BulletManager::on_tick_1c    (0x412c50 / body 0x412860, prio 0x1c) ✅一手
    │    └ 遍历弹池活动链 mgr+0x70;每弹 Bullet::on_tick (0x411e70)
    │         └ Bullet::run_ex (0x413860)   【弹运动 VM,见 ../bullets/01 §3】
    ├ EffectManager::on_tick_1f    (0x418ab0, prio 0x1f)
    ├ Spellcard::on_tick (0x417930) · Bomb::on_tick (各机体) · Ending::on_tick_23 (0x4199f0) · AsciiManager::on_tick (0x408fb0) …
 └ UpdateFuncRegistry::run_all_on_draw (0x4015a0)          ← 渲染遍(各子系统 on_draw,按渲染层)
```

- **优先级即顺序**:名字里的十六进制(`_11`/`_1a`/`_1c`/`_1f`/`_23`)就是注册优先级 → tick 先后(Stage→Enemy→Bullet→Effect→…)。
- **两条 VM 的入口都在这条链上**:ECL VM 经 EnemyManager(0x1a)→Enemy::on_tick→ecl_run;弹运动 VM 经 BulletManager(0x1c)→Bullet::on_tick→run_ex。我们之前一手反的子系统,现在挂到了主干上。
- **`Supervisor`**(顶层游戏主管):`read_joypad_input`(0x4018e0)/`read_keyboard`(0x401d50)/`on_registration`(0x43b520,也是 PRNG 播种点,见 `th16-engine-math.md` §3.4)。输入采集在帧驱动里,先于 tick。

---

## 3. 开放
- `Window::do_frame`(0x45a8a0)内部(WinMain 消息泵 / 计时 / 帧率节流 / frameskip 三变体差异)未一手反。
- `Enemy::on_tick`(0x41d1e0)内部→`ecl_run` 的确切调用点未逐行反(已确认它遍历敌机 + 调 per-enemy 更新 + vtable[0x14];ECL 驱动在其内)。
- 各子系统注册的**完整优先级表**(谁在 0x11..0x23 之间)可枚举 `register__on_tick` 调用方补全。

## 关联
- ECL VM:`../ecl/04-ecl-vm-interpreter.md`(`ecl_run`)、`../ecl/02-runtime-vm.md`(每敌机一解释器)。
- 弹运动 VM / 弹池 tick:`../bullets/01-core-engine.md` §1/§3/§6(本文补其 §6 的 🟡 调度器 runner)。
- 子系统切口:`../sht/findings/06-th16-engine-incisions.md`(敌人/道具/图形…)。
- 命名来源:ExpHP `../ecl/vendor/th-re-data`(`UpdateFuncRegistry`/`Window::do_frame`/各 `on_tick_NN`);纪律 `../sht/findings/00-METHOD-逆向记录纪律.md`。
