# player 逆向 06:资源获得经济(命 / 炸 / power / 季节 的"涨"端)

> 方法:Ghidra(ghidra-re MCP)一手反编译 th16.exe(用户自有,ExpHP 符号 + struct 已套)。
> 日期 2026-06-13。分级 ✅一手 / 🟡推断或单点 / ❓未解。**仅 TH16 v1.00a**。
> 承接 `01`(生命系统的"失"端:扣命/掉 power/miss)。本篇补"得"端:道具拾取 + 分数续命。
> 纪律:`../sht/findings/00-METHOD`(发现→推测→验证→结论(可信度+版本)→证据)。

## 0. 一句话结论

道具在 `ItemManager__on_tick_1d__body @0x42f4e0` 里**按 item type(运行时槽 `+0x315`)switch 分派**到
各 `Globals__collect_*`。**命**=type5 满命道具(+1)或**分数续命**(`add_to_score` 越过档表);
**炸**=type7(+1)或 type6 碎片(5 碎=1 炸);**power**=type1(+1)/type3(+100)/type8(满);
**季节槽**=type16(+1)。**★ TH16 没有"命碎片"收集物**——`CURRENT_LIFE_FRAGMENTS` 无任何拾取写入点
(见 §4,负结论)。

## 1. item type → 资源 分派表(`ItemManager__on_tick_1d__body` 的 switch,一手 ✅)

收取判定:道具坐标进 `player.item_collect_box`(zPlayer)→ `switch(item->type @+0x315)`:

| type(+0x315)| 调用 | 资源效果 | 音效 |
| --- | --- | --- | --- |
| 1 | `Globals__collect_power_item` | **power +1**(满则转分/PIV)| 升档 0xd |
| 2 | `Globals__collect_point_item` | 点(分)| — |
| 3 | `Globals__collect_big_power` | **power +100(整档)**(满则 +20000 分)| 0xd |
| 5 | `Globals__collect_extend` | **命 +1**(成功再 SFX 0x11 + `Gui__sub_42bcf0(0,4)`)| 0x11 |
| 6 | `Globals__collect_bomb_fragment` | **炸弹碎片(5 碎=1 炸)** | (满 5 时)0x2e |
| 7 | `Globals__collect_bomb` | **炸 +1** | 0x2e |
| 8 | `Globals__collect_furu_powah` | **满 power**(已满则 +10000 PIV)| 0xd |
| 9,10,0xb,0xc,0xd,0xe | `Globals__collect_piv` + `add_to_score` | PIV/季节加成(还累加 `SUBSEASON_BOMB+0xdc`)| — |
| 0x10(16)| `item_collect_season` | **季节槽 +1**(见 `02`)| 0x3f |
| (所有)| 末尾 `SoundManager__play_sound_at_position(0x25)` + `Item__delete` | 收集通用音效 0x25 | 0x25 |

## 2. 命(life)的获得 ✅

**① 满命道具(type5)** `Globals__collect_extend @0x43df70`:
```c
if (CURRENT_LIVES > 7) return 0;          // 已 8 命则无效
CURRENT_LIVES += 1;  if (>8) =8;          // +1,封顶 8
Gui__update_lives(...);  return 1;
```

**② 分数续命** `add_to_score @0x43e080`(每次加分都查):
```c
CURRENT_SCORE += points/10;               // 分数内部存 ÷10
while (CURRENT_SCORE >= get_score_extend_quota()) {   // 越过下一档
   if (CURRENT_LIVES < 8) { CURRENT_LIVES++(封顶8); Gui__update_lives; SFX 0x11; Gui__sub_42bcf0(0,4); }
   NEXT_SCORE_EXTEND_INDEX++;              // 推进到下一档
}
CURRENT_SCORE 封顶 999999999;
```
`get_score_extend_quota @0x43ddd0`:按难度选表 `DIFFICULTY==4(Extra)?SCORE_EXTEND_QUOTAS_EXTRA:..STANDARD`,
按 `NEXT_SCORE_EXTEND_INDEX` 取档。**续命也封顶 8 命**。

**档表(从 .rdata 直读,CURRENT_SCORE 内部单位 = 显示分 ÷10)✅值**:
- **STANDARD `@0x491880`**:`{500000, 1000000, 2000000, 4000000, 7000000, 10000000, 15000000, 25000000, 50000000, 100000000}`,终止符 `999999999`。
- **EXTRA `@0x4917c4`**:`{1000000, 2000000, 4000000, 6000000, 8000000, 10000000}`,终止符 `999999999`。
- 🟡 **显示分换算**:`CURRENT_SCORE×10`(TH16 惯例;终止符 999999999=内部分数上限,×10=显示上限 9,999,999,990)
  → 显示分续命点 ≈ STANDARD {5M,10M,20M,40M,70M,100M,150M,250M,500M,1B}。该 ×10 换算未独立核死,标 🟡。

## 3. 炸弹(bomb)的获得 ✅

- **整炸道具(type7)** `Globals__collect_bomb @0x43dfb0`:`CURRENT_BOMBS += 1`,**封顶 8**,SFX 0x2e。
- **碎片(type6)** `Globals__collect_bomb_fragment @0x43dff0`:
  ```c
  if (CURRENT_BOMBS > 7) { CURRENT_BOMB_FRAGMENTS = 0; return; }   // 满炸则碎片清零
  CURRENT_BOMB_FRAGMENTS += 1;
  if (CURRENT_BOMB_FRAGMENTS > 4) {        // ★ 满 5 碎
     CURRENT_BOMBS += 1(封顶8); CURRENT_BOMB_FRAGMENTS = 0; SFX 0x2e;
  }
  ```
  → **5 个炸弹碎片 = 1 颗炸弹**(✅)。炸弹满 8 时碎片不累积。
- 复活/决死 commit 时 `CURRENT_BOMBS=3`(见 `01` §4/§5)是另一条路径(重置非拾取)。

## 4. ★ 命碎片(life fragment)= 无拾取来源(负结论,evidence-complete)✅

`CURRENT_LIFE_FRAGMENTS @0x4a57f8` 的**全部 xref(共 7 条,无遗漏)**:
- **WRITE 仅 1 处**:`PauseMenu__on_tick_in_pause_menu @0x440A0E`(暂停/续关菜单状态,非游戏内拾取)。
- READ:`add_to_score`、`Gui`(HUD 显示)、`Player__destroy`、`collect_extend`、`commit_death`。

且 §1 的 item-type switch **无任何分支增加命碎片**(type5 直接 +1 满命,无碎片累积)。→ **结论:本 th16.exe 里
玩家在关内无法"收集命碎片"**;命只来自 ① type5 满命道具、② 分数续命。可信度 **HIGH(xref 完整闭合 + 分派
switch 全覆盖)**,版本 TH16 v1.00a。

> 🟡 **与"东方常见命片"直觉相悖,留作交叉核**:HUD 仍显示 `CURRENT_LIFE_FRAGMENTS`(`Gui__update_lives`
> 第二参),但关内无拾取写入 → 可能 TH16 本就用"满命道具 + 分数续命"而非碎片制,该字段或为存档/续关延续或
> 余留 HUD 元素。**未当定论:仅报代码事实(无拾取写入点),不否认可能有非道具来源(如符卡奖励)未被本次 xref 命中**——
> 但 0x4a57f8 是定址全局,任何 `MOV/INC [0x4a57f8]` 都会 xref,故"无关内拾取增量"较硬。

## 5. power / point / 季节 的获得(✅,旁证收集机制)

- **power**:type1 `collect_power_item`(+1,跨档 `repopulate_options`+SFX 0xd;满则按 PIV/POC 转分)、
  type3 `collect_big_power`(+`POWER_PER_LEVEL`=100=整档;满则 +20000 分)、type8 `collect_furu_powah`
  (未满→灌满;已满→+10000 PIV)。`__CURRENT_POWER_COPY`=power 上限(`shot_init` 算,见 `05`)。
- **point/PIV**:type2/9-0xe;9-0xe 还把值累加进 `SUBSEASON_BOMB->__field_dc`(季节×分联动,🟡 下游未追)。
- **季节**:type16 `item_collect_season`(槽 +1,跨档触发 repopulate + SFX 0x3f),见 `02` §2。

## 6. 收集 / POC / 自动回收(✅,交叉印证 `03`/`05`)

- **收集框** = `player.item_collect_box`(zPlayer,= `05` 的 itembox);道具进框 → §1 switch 收取。
- **自动回收**:道具进 `item_attract_box_{focused/unfocused}` → 置 state5 飞向自机;**聚焦选哪个框 = `INPUT & 8`**
  (= INPUT bit3,**再证 `03` 的聚焦=bit3**);type 9-0xe(季节加成)不自动回收。
- **POC 线(全屏满额收取)**:自机 `pos.y ≤ 0x80(128)`,**`CHARACTER==3`(魔理沙)= `0x94(148)`**(角色差,一手)。
- 自机死亡(state2)时不收取(item tick 跳过收集分支)。

## 7. 可信度 / 复核

- ✅ 一手(本会话反编译):`ItemManager__on_tick_1d__body`(0x42f4e0 分派 switch)、`Globals__collect_extend`
  (0x43df70)、`collect_bomb`(0x43dfb0)、`collect_bomb_fragment`(0x43dff0)、`add_to_score`(0x43e080)、
  `get_score_extend_quota`(0x43ddd0)、`collect_power_item/big_power/furu_powah`(0x430100/0x4304a0/0x4303a0)。
- ✅ 档表值 = .rdata 静态字节直读;命碎片负结论 = `CURRENT_LIFE_FRAGMENTS` 全 xref(7 条)+ 分派 switch 全覆盖。
- 🟡 显示分 ×10 换算、type 9-0xe 的 PIV/季节下游、`Gui__sub_42bcf0` 参数语义未追。
- 复核入口:Ghidra DB `th16`,地址见上。全局:`CURRENT_LIVES@0x4a57f4`、`CURRENT_LIFE_FRAGMENTS@0x4a57f8`、
  `CURRENT_BOMBS@0x4a5800`、`CURRENT_BOMB_FRAGMENTS@0x4a5804`、`NEXT_SCORE_EXTEND_INDEX@0x4a57fc`、
  `SCORE_EXTEND_QUOTAS_{STANDARD@0x491880,EXTRA@0x4917c4}`、`CURRENT_POWER@0x4a57e4`、`POWER_PER_LEVEL@0x4a57ec`。
