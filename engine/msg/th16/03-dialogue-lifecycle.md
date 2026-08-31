# 03 · TH16 对话生命周期 + ECL↔MSG 协程握手(逐指令锁定)

> 适用:**TH16 `th16.exe` v1.00a**,关卡内对话(stage MSG / `GuiMsgVm`)。
> 本篇把 `01`/`02` 里标 🟡 的**握手机制**逐指令对死,升 ✅。可信度:全程一手反编译 + th-re-data 字段名印证。

## 1. 完整生命周期(谁创建 → 谁驱动 → 谁拆)

```
① 装载(stage 起):Gui::sub_426c10(0x426C10)按角色取 stXXy.msg 文件名 → THA1 归档读
   → malloc 缓冲 → 存 Gui+0x1cc(文件头=8 字节一条的入口表,第 id 条 +4=脚本偏移)。
② 触发(ECL 敌机脚本):ins 518 dialogRead(id) → Gui::start_dialogue(GUI_PTR, id):
     id>=0 : operator_new(0x1c8) → GuiMsgVm::initialize(vm, Gui+0x1cc[id] 脚本起点)
             → vm 存 Gui+0x1c8 ; vm[0]=id
     并(同 case 落空 fallthrough)清全场:BulletManager::clear_all + et_clear_all_special + EnemyManager::kill_all
     id=-1/-3 : boss 登场语音(.wav)+换 BGM(不建 VM) ; id=-2 : 符卡分支
③ 驱动(每帧):Gui::on_tick_20(0x427CF0,UpdateFunc 优先级 0x20):
     if (Gui+0x1c8 != 0) ret = GuiMsgVm::run(vm)
        ret==0          → 对话继续(推进 vm 计时/速度倍率)
        ret==0xffffffff → GuiMsgVm::destructor + free + Gui+0x1c8=0   ← 拆 VM
④ 渲染:run 逐 opcode 把文本/立绘喂 AnmManager VM(文本行/立绘/注音各一棵 anm 子树)。
⑤ 结束:脚本走到 opcode 0 end → run 返回 -1 → ③ 拆 VM → Gui+0x1c8 归零。
```

**门控**:`Gui+0x1c8 != 0`(对话活跃)期间,on_tick_20 抑制 boss 计时块与敌人血条/季节槽 UI(对话独占)。

## 2. ECL↔MSG 协程握手(★ 本篇核心,逐指令锁定 ✅)

东方的"对话穿插在 boss 战里"靠 **ECL 与 MSG 两个 VM 每帧交替跑 + 一个共享标志位**实现协程式让步。

**共享标志 = `GuiMsgVm + 0x18c`**(th-re-data 名 `__dword_incremented_by_enemyAppear`,与"boss 起飞"语义吻合)。

三个一手读写点:
| 角色 | 位置 | 代码 | 作用 |
| --- | --- | --- | --- |
| **每帧清** | `GuiMsgVm::run` 顶部 0x42A1D0 | `if (0 < vm[0x18c]) vm[0x18c] -= 1;` | 标志是**一帧脉冲**,跑完即自清 |
| **置位(MSG 侧)** | `run` case 0xc(**ins 12 ecl-resume**) | `vm[0x18c] = 1;` | 对话脚本主动"放行 ECL" |
| **读取(ECL 侧)** | `ecl_run_over_300` case 0x40(**ins 519 dialogWait**)@0x4216e0 | 见下 | ECL 据此决定阻塞/放行 |

`ins 519 dialogWait` 实现(一手):
```c
case 0x40:  // ECL opcode 519 dialogWait
  if ( *(int*)(GUI_PTR + 0x1c8) != 0           // ① 还有活动对话 VM
    && *(int*)(*(int*)(GUI_PTR+0x1c8) + 0x18c) == 0 )  // ② 且其 +0x18c == 0(未被 ecl-resume 脉冲)
      goto LAB_00422a9d;   // → 不推进 ECL 指针、本帧让步,下帧重跑同一条 = 阻塞
  break;                   // 否则:推进 ECL,继续敌机脚本
```

**完整时序**(每帧 on_tick_20 在 ECL 更新之前跑):
```
帧 N:
  on_tick_20 → GuiMsgVm::run:  run 顶部清 +0x18c;…演出…若执行到 ins 12 → +0x18c = 1
  ECL 更新   → 撞 ins 519 dialogWait:
       若 +0x18c==1(本帧 ecl-resume 了)→ 不阻塞 → ECL 越过 dialogWait 继续(boss 起飞等)
       否则 → 阻塞,停在 dialogWait
帧 N+1: run 顶部把 +0x18c 减回 0 → 若 ECL 又遇新的 dialogWait 则再次阻塞
```
→ **每个 `ins 12 ecl-resume` 恰好放行一个 `ins 519 dialogWait`**(一帧脉冲,不会连放)。
对话彻底结束(opcode 0 → 拆 VM → Gui+0x1c8=0)后,dialogWait 的条件①不成立 → ECL 也放行。
即 **dialogWait 释放有两个出口:被 ecl-resume 脉冲,或对话整体结束**。✅(三读写点全一手)

**典型用法**(对话脚本与 boss ECL 配合):
```
ECL:  518 dialogRead(0)   ; 起对话(并清屏 kill_all)
ECL:  519 dialogWait       ; 卡住,等对话演到某处
MSG:  …台词… 12 ecl-resume ; 通知"boss 该飞过来了"
ECL:  (越过 dialogWait) …boss 移动/发弹…
MSG:  …更多台词… 0 end     ; 对话结束,拆 VM
```

## 3. 由此回填/订正 `01`/`02`

- `02` 表 **ins 12 ecl-resume**:exe 信号链已锁(`vm[0x18c]` 脉冲 ↔ dialogWait)→ 升 **✅**(原 🟡)。
- `02` 表 **ins 11 pause / 0 end / 28 callout-pos / 25 y-offset / 32 / 33-35** 等均维持 ✅。
- `01` §2 dialogRead 行为补全:**ins 518 不止起对话,还(fallthrough)清子弹/特效/杀全部敌人**(case 0x3f→0x46
  `EnemyManager::kill_all`)。⚠️ 该 fallthrough 是 Ghidra 反编译所示、未单独验汇编,标 🟡(语义合理:对话起即清场)。

## 4. 仍待对死的 🟡(优先级低)

- `02` 表 ins **3 show-textbox / 22-24 shake / 27 music-fade-custom / 30 route-select**:exe case 尚未逐条核对名实。
- ins 17 文本内 `|x,y,文本` 定位语法(`FUN_0042bbe0` 取串、`FUN_00476c60` 切逗号)未精解 → 对 thcrap 译文相关。
- 这些不影响主链路与握手,留作后续。

## 证据指针

th16.exe v1.00a:`GuiMsgVm::run` 0x42A1D0(顶部 +0x18c 递减、case 0xc 置 1)、`ecl_run_over_300`
case 0x40 = ins 519 dialogWait @0x4216e0(读 `Gui+0x1c8 -> +0x18c`)、case 0x3f = ins 518 dialogRead @0x4216b3、
`Gui::start_dialogue` 0x429FF0、`Gui::on_tick_20` 0x427CF0。
th-re-data:`zGuiMsgVm` 字段 0x18c `__dword_incremented_by_enemyAppear`、0x1c8 size。
名/签名:ExpHP truth `core_mapfiles/msg.rs`、thpages `reference/msg.ts`(见 `02`)。
