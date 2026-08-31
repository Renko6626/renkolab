# th18/ — TH18(東方虹龍洞 / Unconnected Marketeers)逆向工作区

> **独立于 th16 的工作区**,避免结论混淆。本目录放 **TH18 自己一手验证过的结论**;
> TH16 的成果只作**方法论 + 认知地图 + 待验假设**来源,**地址/偏移一律按 th18.exe 重取**(见 `00-port-plan.md`)。
> 新会话先读本 README,再读 `00-port-plan.md`。纪律:`../sht/findings/00-METHOD-逆向记录纪律.md`。

## 当前状态:✅ 基础建设与卡牌主线已完成(2026-06-14)，可开展定点验证/改造

> 新会话**无需重做导入**,`open_database`(`file_path=th18/th18-files/th18.exe`,`database_id=th18`)即用。若目标是协作制作运行时卡牌改造，先读 [COLLABORATION.md](COLLABORATION.md)：现有结论可指导 TH18 v1.00a 的定点实验，但尚无已实跑的 TH18 注入补丁。
- ✅ **th18.exe 已全量分析**(Ghidra headless,函数 **2447** 个)并落盘。
- ✅ **ExpHP th18 名字已套**(`import_th_re_data.py`:applied=715 / skipped=97 / missing=63)——含**完整卡牌/能力系统**
  (`AbilityManager__*`/`AbilityMenu__*`/`AbilityShop__*`,卡牌 `CardLife/CardBomb/CardLifeFragment/CardBombFragment/CardMokou/CardNarumi/...`,共 ~295 函数)。
- ✅ **157 个结构体已建**(`import_th_re_data_structs.py`,failed=0;`zPlayer/zPlayerInner/zAbilityManager/zCardBaseClass/zEnemyData/...`)。
- ✅ **卡牌主线已一手反出**:核心架构/调用接缝、资源经济、58 项注册表、商店规则与卡牌目录见 `findings/cards-01` 至 `cards-06`。
- ⏳ **仍未做**:已实跑的 TH18 thcrap/DLL 改造样例；装备卡 shooter 数据存储与少数标 🟡 的字段/参数仍待验证。
- 工程位置见下表 / `th18-files/README.md`。

## 这是什么 / 目标

TH18 = **東方虹龍洞**(Unconnected Marketeers),特有机制是**卡牌/能力(card/ability)系统**(取代了 TH16 的季节系统/炸弹)。
目标同 TH16 路线:**搞懂引擎运行时语义**(自机/弹幕/敌人/道具…),为 IDE 的多作支持铺路。分两步:
1. **验证共通引擎**:TH16 已反的引擎子系统(自机状态机/碰撞/开火/option/伤害管线/资源经济/SHT 格式)在 TH18 大概率**结构同形**——快速**验证**(不是假设成立)。
2. **新反特有机制**:卡牌/能力系统(`zCard*`/`zAbility*`)是 TH18 独有,**从零(但有 ExpHP 结构锚点)反**,像 TH16 反季节那样直接进语义层。

## 与 th16 的关系(★复用什么 / 不复用什么)

| 复用 ✅ | 不复用 ❌(必须按 th18 重取)|
| --- | --- |
| 方法论(锚点常量、func 表、ExpHP 命名、证据链纪律)| **所有函数/全局地址**(th18.exe 重新编译,全变)|
| 工具(`../funcs/import_th_re_data*.py` 直接指向 `data/th18.v1.00a`)| **结构体字段偏移**(th18 结构体长大了,例:`zPlayer` th16=0x2c828 / **th18=0x479d4**)|
| 认知地图(知道该找哪些子系统/字段语义)| **特有机制**(TH16 季节/炸弹 ≠ TH18 卡牌/能力,代码不同)|
| 字段的**语义含义**(state/iframes/flags/hitbox… 是什么)| **func_* 跳转表内容、玩法数值**(逐作不同)|

→ 一句话:**搬"概念和语义",查 ExpHP th18 结构体拿"新偏移",到 th18.exe 验"新地址/新行为"。**

### ★ 强烈鼓励:先读 TH16 的结论和 Ghidra 工程(但只"参考逻辑",不照抄)

开工前**务必先翻 TH16 的成果当地图**——它们告诉你"该找什么、长什么样、坑在哪",能省掉大量探索:
- **TH16 findings**:`../player/01-06`(自机生命/季节释放/火力/option/字段图/资源经济)、`../sht/findings/03,05,07,08`
  (SHT func 表/字段/shooterset/伤害管线)、`../shared/`(引擎数学/主循环/归档)。
- **TH16 Ghidra 工程**:可同时 `open_database files/th16.exe`(database_id `th16`)与 th18 **并排对照**——
  对同名函数(ExpHP 命名一致)看 TH16 已反清楚的版本,理解逻辑后**再去 th18.exe 重新定位/验证**。
  (MCP 支持多库;`decompile_function` 指定不同 `database` 即可左右对照。)

**但只能"参考逻辑",不得直接搬运**:
- ✅ 可借:控制流/状态机形状、字段的**含义**、"该有哪些步骤"、命名、踩过的坑(见各 finding 的 🟡/❓/纠错段)。
- ❌ 不可抄:任何**地址、偏移、func 表内容、数值、帧数**——这些是 TH16 的,th18 必须**自己一手取/验**。
- 落笔规矩:从 TH16 借来的判断在 th18 文档里写成"**(TH16 如此,th18 待验)**",**在 th18.exe 验证通过后**才去掉"待验"。
- 一句话:**拿 TH16 当"已解出的参考答案"对照思路,但每一步都要在 th18 上重新算一遍、对得上才算数。**

## ExpHP th18 盘点(实测 `data/th18.v1.00a/`,2026-06-13)

ExpHP 对 TH18 积累与 TH16 同量级,引擎结构体填得很满,**卡牌系统也已结构化映射**:

- 命名函数 **729**、statics 154、结构体(own)**157**。
- **引擎结构体(共通,可直接套)**:`zEnemyData 71/71`、`zEclVm 9/9`、`zBullet 48/56`、`zPlayer 18/22`、
  `zPlayerInner 9/14`、`zAnmVm`、`zSupervisor 34/46`、**`zShtShooter 16/19`(同 th16,size 0x58)**、`zItem`、`zGui`。
- **TH18 特有(卡牌/能力,新反锚点)**:`zCardBaseClass`、`zCardEquipmentSingle`、`zCardList`、`zCardMomoyo`、
  `zVTableCard`、`zTableCardData`、`zAbilityManager`、`zAbilityMenu`、`zAbilityText`。
- **注意缺失**:`zBomb` **MISSING**(TH18 无炸弹对象,卡牌/能力取代)、`zShtRawFile` 未命名(`zShtShooter` 在,
  SHT 格式应仍在,只是 ExpHP 没标完整文件结构)。

## 环境(工具与 th16 共用,但**工程/文件独立**,无 sudo)

- Ghidra 12.1.2 + conda env `ghidra`(同 `../sht/disasm/README.md`)。MCP `ghidra-re` 同一套工具。
- **★ TH18 是独立的一套文件 + Ghidra 工程,不与 th16 共用**(不同 exe → 不同 project)。位置对照:

  | 作品 | exe | MCP `database_id` | headless project-dir / project / program |
  | --- | --- | --- | --- |
  | TH16 | `../files/th16.exe` | `th16` | `../files/ghidra_projects` / `th16.exe` / `/th16.exe` |
  | **TH18** | **`th18-files/th18.exe`** | **`th18`** | **`th18/th18-files/ghidra_projects`** / `th18.exe` / `/th18.exe` |

  详见 `th18-files/README.md`。**可同时开 `th16` 与 `th18` 两库并排对照**(`decompile_function` 指定 `database`),
  结论各写各的。
- **样本**:`th18.exe`(32 位 PE)由用户放进 **`th18/th18-files/`**(gitignored),**没有就先问用户、不要下载**。
- **导入 ExpHP th18 符号 + 结构体**(开工第一件事,headless driver,先 `MCP close_database` 释放锁,env 见 `../funcs/README.md`):
  ```bash
  # 名字(funcs/statics)
  python funcs/import_th_re_data.py        ecl/vendor/th-re-data/data/th18.v1.00a \
      --project-dir th18/th18-files/ghidra_projects --project th18.exe --program /th18.exe
  # 类型(157 structs) —— programmatic build(★CParser 不可靠落盘,见 funcs/README)
  python funcs/import_th_re_data_structs.py ecl/vendor/th-re-data/data/th18.v1.00a \
      --project-dir th18/th18-files/ghidra_projects --project th18.exe --program /th18.exe
  ```
  之后把 `zPlayer*/zEnemyData*/zBullet*` 套到对应全局 → 反编译即具名字段(同 th16 做法,见 `../player/05` §0.5)。

## 怎么开干(给新会话)

1. 确认有 `th18/th18-files/th18.exe`;没有先问用户。
2. `open_database`(`file_path=th18/th18-files/th18.exe`,`database_id=th18`)→ 跑上面两个 import 脚本 → 得 729 名 + 157 结构体。
3. 读 `00-port-plan.md`:挑一个**共通子系统**(如自机生命/碰撞)→ 用 ExpHP th18 `zPlayerInner` 偏移定位 → **到 th18.exe 一手验证**行为是否与 TH16 同形 → 写进 `th18/findings/`(或 `th18/player/`)。
4. 或挑**特有的卡牌/能力系统**(`zCard*`/`zAbility*`)从锚点新反。
5. **每条结论**都按证据链纪律落到 **th18 自己的地址 + 读写点 + 可信度**;**严禁把 TH16 地址/偏移写成 TH18 事实**。

## 纪律(本工作区红线)

- **TH16 的一切结论在这里都是"假设",未在 th18.exe 一手验证前不得当事实**(CLAUDE.md 明写"别外推到 TH15-19")。
- **地址/偏移一律重取**;引用 TH16 时显式标 "(TH16)" 以免混入。
- 主仓库不留版权字节:`samples/ ghidra projects/ exports/` gitignore。

## 目录

```
th18/
├── README.md          # ← 你在这
├── 00-port-plan.md    # ★ TH16 结论→TH18 待验假设 + 锚点 + "会变"警示(复用内容的核心)
├── findings/          # TH18 一手验证结论(已含 cards-01~06；后续可建 player/ sht/ 等)
└── th18-files/        # ★ th18.exe + 它自己的 Ghidra 工程(独立于 th16;内容 gitignore,仅 README 入库)
    └── README.md      #    位置对照表(th16 vs th18 工程位置)+ 开工命令
```
