# th18 移植/验证计划:TH16 结论 → TH18 待验假设 + 锚点
> **版本**：TH18 v1.00a（`th18.exe`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
>

> **怎么用本文**:左列是 TH16 已一手反出的**语义结论**(可复用的"概念");中列是**TH18 验证状态**;
> 右列是**TH18 锚点**(从哪查偏移 / 从哪起手验)。**所有 TH16 具体地址/偏移在此一律标 `(TH16)` = 仅参考,
> 不得当 TH18 事实**;TH18 偏移**查 ExpHP `data/th18.v1.00a` 结构体**,TH18 行为**到 th18.exe 一手验**。
> 状态记号:`待测`=未验 / `✅`=th18 一手验过 / `≠`=确认不同 / `不适用`=TH18 无此机制。

## 0. 总则(复用 vs 重取)

| 复用(搬概念/语义)| 重取(按 th18) |
| --- | --- |
| "自机有 5 态状态机""决死有窗口""5 碎=1 炸"这类**机制描述** | 状态机字段**偏移**(查 th18 `zPlayerInner`)|
| 字段**语义**(state/iframes/flags/hitbox 是什么)| 字段所在**地址/偏移**、函数**地址** |
| **方法论 + 工具 + 认知地图** | **func_* 表内容、数值表(档表/伤害/帧数)、特有机制** |

> ⚠️ 已知会变的硬证据:`zPlayer` th16=0x2c828 → **th18=0x479d4**;`zPlayerInner` th16=0x16090 → **th18=0x47304**。
> → **TH16 的 `+0x165a8=state` 等偏移在 TH18 全部移位**,但 ExpHP th18 `zPlayerInner` 已把 `state/iframes/flags/...`
> 命名好,直接拿 th18 偏移即可(用 `import_th_re_data_structs.py` 套进 Ghidra 后,反编译自动显示 `player->inner.state`)。

---

## 1. 共通引擎(大概率同形,逐条**验证**,非假设成立)

### 1a. 自机 中弹/生命(源:`engine/player/th16/01`)
- **可复用概念(TH18 待测)**:5 态状态机(出场/存活/死亡结算/决死窗口/…);中弹经碰撞判定族→死亡入口;
  无敌帧门控;commit 死亡=扣命+miss+掉资源+重置;复活有无敌期;命<0→GameOver/续关。
- **TH18 锚点**:`zPlayerInner.state / .iframes / .flags`(ExpHP 已命名,偏移按 th18 取);碰撞函数到 th18.exe 按
  "玩家坐标 vs 弹半径"模式定位。**决死窗口帧数、无敌帧数、复活炸库存——TH18 可能不同,逐个重测**。
- ~~**注意**:TH18 **无炸弹**(`zBomb` MISSING)~~ → ❌ **已证伪(2026-06-13)**:TH18 **保留 TH16 式炸弹(按 X)**,
  有 `BOMB_PTR`/`do_bomb`(`0x420360`)/`Bomb__operator_new`(`0x41FD40`)/`zVTableBomb`(角色专属 begin)。
  ExpHP 没命名 `zBomb` **数据结构** ≠ 没有炸弹机制。卡牌只取代了**季节释放(按 C)**,不是炸弹。
  决死窗口同时支持"X 炸救命"与"救命卡"两条路。证据/详见 `engine/card/th18/06-resource-economy.md` §1 与 `engine/card/th18/03-hooks.md` §4。
  教训:别把 "ExpHP 未命名某结构" 当 "该机制不存在"。

### 1b. 火力/输入/移动/聚焦(源:`engine/player/th16/03`)
- **可复用概念(待测)**:开火门控状态机(射击键→cadence)、9 向移动 + 4 档移速(直/聚直/斜/聚斜,√2 对角)、
  **聚焦=输入位**驱动。
- **TH18 锚点**:`zPlayerInner.is_focused / .shoot_key_*_timer / .regular_speed.. / .attempted_direction`;输入位掩码到
  `Supervisor::read_keyboard_input` 重解(位值由消费侧定;**TH16 聚焦=INPUT bit3,TH18 重验**)。

### 1c. option/子机(源:`engine/player/th16/04`)
- **可复用概念(待测)**:本体 option 数=火力档;option 位置取自 .sht option_pos(聚焦/非聚焦两段);option 既是显示也是发射点。
- **TH18 锚点**:`zPlayerOption`、`zPlayerInner.main_options[]`、`zShtRawOptionPos`(若 th18 有)。
  **TH16 的"季节子机"= TH18 无**(季节机制不存在)→ 第二组 option 在 TH18 是什么(卡牌相关?)需新查。

### 1d. 字段总账(源:`engine/player/th16/05`)
- **直接用 ExpHP th18 结构体**:`zPlayer/zPlayerInner/zBomb(无)/zPlayerOption/zPlayerDamageSource94?`——
  **偏移全部以 th18 struct 为准**,TH16 的字段图只作"该有哪些字段"的清单。
- 伤害源池、判定盒(hurtbox/attractbox)等概念同;**偏移/数值重取**。

### 1e. 资源经济(源:`engine/player/th16/06`)
- **可复用概念(待测)**:道具按 type switch 分派到 collect_*;命=满命道具+分数续命(档表);power 多档;
  **5 炸碎=1 炸(TH18 无炸→不适用)**;分数续命有 per-难度档表。
- **TH18 锚点**:`ItemManager` 的 item-tick dispatch、`Globals__collect_*`(th18 funcs.json 里找)、
  `SCORE_EXTEND_QUOTAS_*`(**th18 自己的档值,重读**)、`zItem`、卡牌购买可能用"金钱"资源(查 `zAbility*`/money 全局)。
- **不适用/换形**:炸弹碎片;季节道具(type0x10)→ TH18 换成卡牌/金钱掉落。

### 1f. SHT 格式 + 自机弹语义(源:`engine/sht/th16/03,05,07,08`)
- **★ 这是最该先验的"共通假设"**:`zShtShooter` th18 在(同 0x58),字段名同。
- **待验假设(TH16→TH18)**:func_* 跳转表机制(load-time 索引→指针)、**flags 段运行时是否仍不读**、
  shooterset 组织(火力×聚焦)、自机弹伤害管线(spawn→伤害源→敌人)。
  → 正是 `engine/sht/th16/01` / `../README` 标的开放问题 **"TH16↔TH18/19 func_* 编号是否共用"**。
- **重取**:func 表地址与内容、各 idx 行为、`flags` 分布、`max_dmg` 等数值。

---

## 2. TH18 特有机制(不适用 TH16 结论,**从零反**,有 ExpHP 锚点)

| TH16 机制(`engine/player/th16/02,04`)| TH18 对应 | 起手锚点(ExpHP th18)|
| --- | --- | --- |
| 季节释放(按键技能)+ 双炸弹 | **卡牌/能力系统**(完全不同)| `zCardBaseClass / zVTableCard / zTableCardData / zCardEquipmentSingle / zCardList / zCardMomoyo` |
| 季节槽充能 + 档位 | **能力/金钱 经济**(疑)| `zAbilityManager / zAbilityMenu / zAbilityText`;商店/金钱全局待查 |
| 季节子机 | (TH18 无季节)| —— 按卡牌效果重查 option 第二组来源 |

→ 像我们反 TH16 季节那样:从 vtable(`zVTableCard`)+ 数据表(`zTableCardData`)+ 管理器(`zAbilityManager`)
入手,反 begin/on_tick/激活路径,落 `th18/findings/`。**这是 TH18 的"原创增量",ExpHP 只给了结构没给语义。**

---

## 3. 注定会变 / 易踩坑(警示清单)

- **地址**:全部。别用任何 TH16 地址。
- **偏移**:结构体长大(`zPlayer` +0x1d1ac 字节)→ TH16 偏移全错;用 th18 struct。
- **数值表**:分数续命档(TH16 STANDARD `{500k..}`)、伤害上限、决死/无敌帧数、POC 线、power 档数——**逐个重读 th18**。
- **func_* 表**:地址 + 内容 + idx→行为,全可能不同(连"共用编号"都是待验假设,不是已知)。
- **输入位**:键→位映射可能变;位值由消费侧重定。
- **特有机制**:季节/炸弹相关结论(`engine/player/th16/02`、`engine/player/th16/04` 季节子机、`engine/player/th16/06` 炸碎)在 TH18 **不适用**。

---

## 4. 建议验证顺序(性价比)

1. **套 ExpHP th18 符号 + 结构体**(两个 import 脚本)→ 立刻可读。
2. **先验 1f(SHT/func 表)**:回答开放问题"func_* 是否跨作共用",一手 diff TH16↔TH18,收益最高。
3. **再验 1a/1b(生命/开火)**:结构同形,验证快,顺带确认 TH18 决死/无敌/聚焦的具体数值。
4. **最后新反第 2 节(卡牌/能力)**:TH18 的真正特色,从 `zCard*/zAbility*` 锚点进语义层。

> 每验完一块 → 在 `th18/` 下建对应 finding(如 `th18/player/01-...`、`th18/sht/...`、`th18/cards/...`),
> **只写 th18 一手结论**,引用 TH16 时标 "(TH16, 待验/已验)"。
