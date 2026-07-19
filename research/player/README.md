# player/ — TH16 自机系统逆向(火力 / 生命 / 季节释放)

> 本目录承接 `../sht/`(SHT 字节布局 + func_* 行为 + 伤害管线)与 `../funcs/`(ExpHP th-re-data
> 符号),从**player 对象 + 引擎调度**的角度,把"自机作为一个运行时子系统"反完:它怎么动、怎么开火、
> 怎么中弹/死/复活,以及 TH16 招牌的**季节释放(按 C)**怎么工作。
>
> 仅 **TH16(天空璋)th16.exe v1.00a,imagebase 0x400000**。一手反编译用户自有 exe(版权不入库)。
> 可信度分级:✅一手实证 / 🟡推断或单点 / ❓未解。记录纪律见 `../sht/findings/00-METHOD-逆向记录纪律.md`。

## 这是什么 / 与 sht 的分工

| 工作区 | 关注 |
| --- | --- |
| `../sht/` | **.sht 文件**:字节布局、shooter 字段图、func_* 跳转表→行为、shooterset 组织、自机弹伤害管线 |
| **`player/`(本目录)** | **player 运行时对象**:状态机、输入/移动/聚焦、开火门控、**中弹/生命/死亡/复活**、**炸弹 & 季节释放(C)** |

两者互补:sht 解决"一发弹长什么样、怎么飞、怎么扣血";player 解决"自机这个对象每帧在干什么、玩家三大
资源(命/炸/季节)怎么涨怎么消耗"。**开火的下半段(do_shooting→spawn→伤害)在 `../sht/findings/07,08`,
本目录的 `03` 只补它的上半段(输入→门控)并交叉引用,不重复。**

## 文档索引

1. **`01-hit-life-system.md`** — ★ 中弹/生命系统:player 五态状态机(`+0x165a8`:0 出场 / 1 存活 /
   2 死亡结算 / 3 / 4 **决死(deathbomb)窗口**)、碰撞判定族(circle/rect/laser_obb)、无敌帧
   `+0x1663c`、决死 8 帧窗口、掉 power、扣命/miss、复活流程、Game Over。
2. **`02-season-release-and-bombs.md`** — ★★ TH16 双炸弹体系 + **季节释放(按 C)**:
   - **主炸(X)** = `BombMain{Reimu,Cirno,Aya,Marisa}`,按 `CHARACTER` 选,消耗 `CURRENT_BOMBS` 库存;
   - **季节释放(C)** = `BombSub{Spring,Summer,Fall,Winter,Doyou}`,按 `SUBSEASON` 选,消耗
     `CURRENT_SEASON_POWER`(季节槽,捡季节道具充能),释放强度随槽位档次,部分副季节只扣一档(可连放)。
   - 季节槽机制、`Bomb::can_bomb`/`activate_bomb`、释放冷却、释放=半径式清弹屏障 + 短无敌。
3. **`03-fire-input-movement.md`** — 开火/输入/移动:`tick_shooting_state`(射击键→cadence 门控)、
   `player_input_move`(9 向移动 + 4 档移速 + **聚焦 `+0x165c8`=输入 bit3**)、开火大门的前置条件;
   与 `../sht/findings/07,08` 的衔接。
4. **`04-options-subshot-system.md`** — ★ option/子机系统:`repopulate_options`——**本体子机**(数=火力档,≤4,
   主 .sht option_pos)+ **★季节子机**(数=季节槽档,≤8,副 .sht option_pos,精灵按 SUBSEASON);
   option_pos 拆 **非聚焦@+0x40 / 聚焦@+0xe8** 两段;与 shooterset `opt` 的关系。
6. **`06-resource-economy.md`** — ★ 资源获得("涨"端):item type→资源分派(命/炸/power/季节)、5 炸碎=1 炸、
   分数续命档表(STANDARD/EXTRA)、**命无碎片收集物(负结论)**、POC/自动回收(聚焦=INPUT&8 再证)。补 `01` 的"失"端。
5. **`05-object-field-maps.md`** — ★ 字段总账:player 对象(坐标/移速/判定盒/状态机/计时/`+0x1664c` 标志/射击计时)
   + **Bomb 对象 0x108 全字节字段图** + 伤害源创建(`create_damage_source` 交叉验 sht/08);含季节阈值常量来源、
   `player_shot_init` 初始化全景。每字段带读写点 + 可信度;诚实留白见其 §4。

## 锚点速查(本目录新坐实的 player 对象字段 / 全局)

> player 对象基址全局 **`PLAYER_PTR` = `DAT_004a6ef8`**(`operator_new(0x2c828)`)。
> 全局命名用 ExpHP th-re-data(已套进 Ghidra DB `th16`)。

| 符号 / 偏移 | 含义 | 见 |
| --- | --- | --- |
| `+0x165a8` | **主状态机**(0 出场/1 存活/2 死亡结算/3/4 决死窗口) | 01 |
| `+0x628`(及 `+0x624/62c`)| 当前状态的**帧计数器**(Timer:cur/prev/float) | 01 |
| `+0x1663c`(`+0x16640` float)| **无敌帧倒计时**(>0 不中弹) | 01 |
| `+0x165c8` | **聚焦(focus)标志** = `INPUT>>3 & 1` | 03(订正 sht/07 的 🟡) |
| `+0x16650/54/58/5c` | 4 档移速(直/聚直/斜/聚斜),源自 SHT header move_* | 03 |
| `+0x2c780` | 9 向移动方向(0..8) | 03 |
| `+0x2c788/78c` | 主/副 .sht 解析后基址 | sht/04 |
| `+0x165cc/d0`、`+0x165e0/e4` | 射击键短/长计时(开火 cadence) | 03 |
| `CURRENT_LIVES/BOMBS/SEASON_POWER` `@0x4a57f4/5800/5808` | 命 / 炸 / 季节槽 | 01,02 |
| `MAIN_BOMB_PTR/SUBSEASON_BOMB_PTR` `@0x4a6da8/6da4` | 主炸 / 季节释放对象 | 02 |
| `INPUT/INPUT_RISING_EDGE` `@0x4a52c8/52d4` | 帧按键位 / 上升沿;bit0=射击,bit1=主炸,bit3=聚焦,**bit0x800=季节释放** | 02,03 |

## Ghidra 里已写入(DB `th16`,已落盘)

- **9 个 struct 类型已建并套用**(来自 ExpHP th-re-data,见 `05` §0.5):`zPlayer`/`zPlayerInner`/`zBomb`/
  `zPlayerOption`/`zPlayerDamageSource94` + leaf(`zTimer`/`zFloat3`/`zInt2`/`zBoundingBox3`)。
  套到全局(`PLAYER_PTR`→`zPlayer*`、两个 BOMB_PTR→`zBomb*`)+ ~15 个核心函数签名 → 反编译已是具名字段
  (如 `(player->inner).state`、`bomb->is_season`)。
- 另有 ~20 处函数改名 + 注释(见各 finding 的"落盘"段)。⚠️ ExpHP `import_th_re_data.py` 只导 funcs/statics,
  **不导 struct**;上述 struct 是本工作区手建导入的(C 声明从 `type-structs-own.json` 生成)。

## 环境 / 复核

- Ghidra DB **`th16`**(MCP `ghidra-re`):`open_database files/th16.exe` 即复用已套 ExpHP 符号 + struct 的工程。
- 所有地址可在 DB `th16` 复核;常量/数据值多为**运行时填充**(静态镜像里是 0,见 02 季节槽注)。
- 纪律:`../sht/findings/00-METHOD-*`;memory `re-overclaim-guard` / `re-evidence-chain-discipline`。
