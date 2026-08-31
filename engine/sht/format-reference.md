# SHT（自机 / shoot type）格式调研

本文整理 SHT（"shot type" / "shoot type"，自机射击类型）文件格式的调研结论，用于评估
THTK-Studio 是否以及如何把它接进 IDE。

与 ECL / ANM / MSG / STD 不同，**SHT 本质是一份纯二进制配置文件**（类似带版本差异的结构
化表格），不是一门带指令流和子程序的脚本语言。这决定了它在 IDE 里的形态更接近"结构化表单
/ 表格编辑器"，而不是 Monaco 文本编辑器 + 工具链编译。

> 可信度说明：SHT 是社区逆向出来的、官方从未公开的格式。本文结论主要来自 Priw8 的
> `sht-webedit`（作者本人的仓库 + 各版本 struct 源码），并由 en.touhouwiki.net 的 Mddass
> 规范页和 pytouhou 文档交叉印证。下文对每个结论尽量标注可信度，对存疑项单列"开放问题"。

## 0. 一句话结论

- SHT = 自机的"射击类型"定义：每个角色 / 每个 shottype 在各 **power 等级**、各 **focus（低速/
  高速）模式** 下发射哪些子弹、发射频率、判定箱、移动速度、副机（option）位置，以及引用的 ANM
  动画和音效。
- **官方 thtk 和 ExpHp 的 truth 都不支持 SHT**——它们只覆盖 ANM/DAT/ECL/MSG/STD。所以这块
  没有现成工具链可以包装，IDE 要支持就得**自己写 Rust 解析器 / 序列化器**。
- 唯一成体系、跨版本（TH07–TH18 及若干外传）的参考实现是 **Priw8 的浏览器版 `sht-webedit`**，
  它的各版本 struct 表 + 导出逻辑是目前最完整的逆向文档，可以直接移植。

## 1. SHT 代表什么（高可信度）

来源：Priw8 `sht-webedit` README、Mddass touhouwiki 规范页、pytouhou 文档（三方 3-0 印证）。

- SHT 定义"一个角色及其射击"（pytouhou 原文，针对 PCB）。
- 文件由若干 **shooter（射手）** 组成，每个 shooter 描述"自机 / 副机发射的一种子弹，以及发射
  频率"（Priw8 README 原文）。
- 数据按 **power 等级**组织；从 **TH10 起**额外按 **focus 模式**组织（低速聚焦 / 高速移动）。
  - TH07–TH08 没有 focus 维度的内嵌结构，而是**把聚焦 / 非聚焦拆成两个独立 .sht 文件**。
- "shoot type / shot type" 是东方里"可选自机武器"的惯用叫法。

### 与其他格式的关系

- SHT 引用 **ANM**：子弹精灵动画 + 命中动画（`anm` / `anm_hit` 字段是 ANM 脚本索引）。
- SHT 引用**音效 id**（`sfx_id`）。
- SHT 里有一组 **func_on_init / tick / draw / hit** 字段，是游戏 exe 里**硬编码行为函数的
  索引**（不是可编辑的脚本，只是选号）。这点对编辑器很关键：这些是"枚举/魔法数字"，需要每个
  版本一张名称表才能给用户友好显示。

## 2. 谁在处理它（高可信度）

| 工具 | 是否支持 SHT | 说明 |
| --- | --- | --- |
| **thtk**（thanm/thdat/thecl/thmsg/thstd） | ❌ 不解析 | 顶层目录只有上述五个；`thdat` 能从 DAT 包里**解出 `.sht` 二进制 blob**，但不解析其内部结构 |
| **ExpHp / truth**（trustd/truanm/trumsg） | ❌ 不支持 | `src/formats/` 只有 anm/ecl/mission/msg/std，没有 sht 模块 |
| **Priw8 / sht-webedit** | ✅ 事实标准 | 浏览器内编辑 .sht，覆盖 TH07–TH18 + TH12.8/14.3/16.5 + 黄昏酒場 Uwabami Breakers |
| **Priw8 / shmupcc-sht** | ❓ 推测相关 | TypeScript 仓库，名字暗示与 SHT 有关，但无 README，用途未确认（见开放问题） |
| **pytouhou** | 📖 文档/实现参考 | 有 PCB(TH07) 的 SHT 结构文档，可交叉印证 |

- Priw8 是 thpatch 组织成员、thtk 贡献者；`sht-webedit` 托管在 `priw8.github.io/sht-webedit/`，
  是**目前唯一维护中、跨版本、源码里带各版本二进制 schema** 的 SHT 工具。
- ⚠️ 网上有"thsht 存储符卡名称"之类的说法，是**错误的**（符卡名称属于 MSG/thmsg）。不存在
  名为 `thsht` 的官方工具。

## 3. 二进制结构

> 强调：**布局逐版本差异很大**，不要假设一套 schema 通吃。下面分代说明。

### 3.1 TH07（PCB）布局（高可信度，已对 `struct_07.js` 核对）

来源：Priw8 `js/struct/struct_07.js`（一手）、Mddass wiki、pytouhou `doc/07/sht.xhtml`。

固定头部（偏移以字节计）：

| 偏移 | 类型 | 含义 |
| --- | --- | --- |
| 0x02 | Int16 | power 等级 / shot 偏移表 的条目数 |
| 0x04 | Float | bomb 数 |
| 0x08 | Int32 | 死亡 bomb（deathbomb）时间窗 |
| 0x0C | Float | 判定箱（hitbox） |
| 0x10 | Float | 擦弹箱（grazebox） |
| … | … | item 相关参数 |
| 0x24/0x28/0x2C/0x30 | Float×4 | 移动速度（直行/斜行 等） |
| 0x34 起 | offset 表 | 每条 8 字节：`uint32 offset` + `uint32 power`，条目数 = 头部 count |

- offset 表之后（`0x34 + 8*count`）是 shooter 结构数组。
- **终止判定**：当某条 shooter 的前 4 字节 == `0xFFFFFFFF` 时，停止解析。
- TH07 单条 shooter（高可信度，部分字段曾 2-1，但偏移已对一手 struct 核对）：

| 偏移 | 类型 | 字段 |
| --- | --- | --- |
| 0x00 | Int16 | fire_rate（发射频率） |
| 0x02 | Int16 | start_delay（起始延迟） |
| 0x04 | Float | off_x（相对副机的生成偏移 X） |
| 0x08 | Float | off_y |
| 0x0C | Float | hitbox_x |
| 0x10 | Float | hitbox_y |
| 0x14 | Float | angle（弧度） |
| 0x18 | Float | speed |
| 0x1C | Int16 | dmg（伤害） |
| 0x1E | Byte | option（副机分配，0 = 自机本体） |
| 0x20 | Int16 | anm（子弹 ANM 脚本索引） |
| 0x22 | Int16 | sfx_id（音效） |
| 0x24–0x30 | Int32×4 | func_on_init / tick / draw / hit（硬编码行为函数索引） |

> ⚠️ TH07 **没有独立的 "flags" 字段**；尾部四个 Int32 是函数指针索引，不是位标志。曾有一个
> "16 字段、含 homing flag 和 uint8 orb(0=本体/1=左/2=右)、以 interval+unknown1 全 0xffff
> 终止"的说法被**对抗验证否决（1-2）**，不要采用。

### 3.2 TH07–TH08 的共性（高可信度）

- **没有 option 表**（副机位置疑似硬编码在 exe 里）。
- 聚焦 / 非聚焦 = **两个独立 .sht 文件**（每个 shottype 两份）。
- power 等级最多 **129 级（0–128）**。

### 3.3 TH10+ 布局（高可信度）

来源：Priw8 README（TH10+ 段）、Mddass wiki。

顺序为：

1. **头部（"main" 表）**：`sht_off_cnt`、`pwr_lvl_cnt`（最大 power 等级）、`max_dmg`，以及
   聚焦/非聚焦 × 直行/斜行 的移动速度。
2. **option positions（副机位置块）**：按每个 power 等级排列（详见 3.4 各版本差异）。
3. **shooterset 偏移数组**：存放各 shooterset 在 shooterset 数组中的偏移。
4. **shooterset 数组**：紧随其后，**各 shooterset 之间用 4 个 `0xFF` 字节分隔**。
   - 注意分隔的是 **shooterset 之间**，不是单个 shooter 之间。
   - 例：`pwr_lvl_cnt = 4` 时应有 **10 个 shooterset**（非聚焦 5 个 power 级 + 聚焦 5 个）。
- 导出时偏移数组**自动重算**（offset 由结构推导，不手填）。

### 3.4 版本差异要点（高可信度，已对 struct 源码核对）

| 版本 | option_pos 块大小 | 最大 power 级 | 未用槽哨兵值 | 备注 |
| --- | --- | --- | --- | --- |
| TH07–TH08 | 无 option 表 | 129 (0–128) | — | 聚焦/非聚焦分两个文件 |
| TH12（UFO） | 0x240 = 576 B | 8 | `-999.0f`（字节 `00 C0 79 C4`） | 半径式单 float 的 hit/graze/item 箱；shooter 结构尺寸不同 |
| TH13（TD） | 0xA0 = 160 B | 4 | `0x00000000`（**不是** -999.0f） | 与 TH12 明显不同，别套用 |
| LoLK 起 | — | — | — | 新增 `fire_rate2`/`start_delay2`，用 **120 帧**计时器（原 `fire_rate`/`start_delay` 是 15 帧）；`fire_rate2` 一旦设置就忽略原字段 |

- **LoLK 的 120 帧计时器有个著名 bug**：用该计时器的射击在极少数情况下会"卡住不再发射"。
  这是格式语义层面的坑，编辑器在该字段旁应给提示。
- option positions 采用"三角数填充 + 哨兵"逻辑（不同 power 级用到的副机数不同，多出来的槽用
  哨兵值填）。⚠️ Mddass wiki 自己给的尺寸公式 `pwr_lvl_cnt(pwr_lvl_cnt+1)/2*2*4` 在 n=8 时
  算出 288 而非 576，疑似源里漏了一个 X/Y 的 ×2 因子——**以 struct 源码实测尺寸为准**。

## 4. 对 IDE 的可借鉴点（中可信度，属综合建议）

`sht-webedit` 是唯一值得直接借鉴的资产。具体可移植的部分：

1. **各版本 struct schema**（`js/struct/struct_07..struct_19.js`）：逐版本的字段名 / 类型 /
   偏移表。这正好对应本项目"解析逻辑放 Rust 宿主"的分层原则——把这些表转写成 Rust 的版本化
   结构定义。
2. **读写 / 导出逻辑**（`export.js`）：`0xFFFFFFFF`（shooter 终止）、`4×0xFF`（shooterset
   分隔）的探测；导出时 shooterset 偏移数组的自动重算；option-position 的三角填充 + 哨兵
   （`-999.0f` / 0）处理。
3. 因为 thtk/truth 都不支持 SHT，这块在本项目里是**全新模块**，应照搬 `modules/ecl/` 的模块
   形态，并复用结构化结果（`{ success, ..., diagnostics }`）模式。
4. 前端接入点同样复用既有扩展位：
   - `services/toolchains/registry.js` 的 `TOOLCHAIN_REGISTRY`（但 SHT 没有外部编译器，
     descriptor 更像"内建解析器"而非"exe 包装"，可能需要扩展 registry 语义）。
   - `services/workbench/editorViews.js` 的 `WORKBENCH_EDITOR_VIEWS`：SHT 应注册一个
     **结构化表单/表格视图**（类似 `binary-script` 的思路），而不是 Monaco 文本视图。

### 与 ECL 路线的关键差异

| 维度 | ECL/MSG/ANM/STD | SHT |
| --- | --- | --- |
| 外部工具链 | 有（thecl/thmsg/…） | 无，需自研解析 |
| 源表示 | 文本（.decl 等） + 编译 | 纯二进制，需结构化编辑或自定义文本投影 |
| IDE 视图 | Monaco + 诊断 | 表单/表格 + 字段级校验 |
| 跨版本 | 指令集差异 | 二进制 schema 整体差异（更碎） |

> ⚠️ 移植前必须确认 `sht-webedit` 的开源许可证，评估其 struct schema / 导出逻辑能否合法
> 移植进本项目（见开放问题）。

## 5. 建议的下一步（不是立刻实现）

1. **先不写代码**，先把 `sht-webedit` 的 `js/struct/struct_*.js` 和 `export.js` 抓下来，
   逐版本整理成一张"字段 / 类型 / 偏移 / 哨兵"对照表（本文是起点，但只精确到 TH07/12/13）。
2. 确认许可证后，从 **TH07（结构最简单、已被一手核对）** 起做一个 Rust 只读解析器，返回
   结构化 JSON，前端先做**只读结构化视图**。
3. 再补 TH10+ 的 shooterset/offset 模型与导出（偏移重算是写回的难点）。
4. 行为函数索引 / ANM 索引 / 音效 id 需要**每版本一张名称映射表**才能做到友好显示，这部分
   可借鉴 ECL 的 eclmap 语义层思路（外部数据驱动 provider）。

## 6. 开放问题

- TH14–TH18 及外传（TH12.8/14.3/16.5、Uwabami Breakers）的精确逐版本 schema（即
  `struct_14..struct_19.js` 的确切字段表），本文未覆盖，需后续逐个抓取整理。
- `sht-webedit` 的开源许可证是什么？struct schema / 导出逻辑能否合法移植？
- `shmupcc-sht` 到底是什么？是否是一个把 SHT 编译/反编译成**人类可读文本表示**（类似 ECL 的
  .decl）的工具？若是，IDE 也许可以采用它的文本格式作为"源表示"，从而复用 Monaco 路线。
- SHT 在游戏 DAT 包里如何定位 / 打包（经 thdat 解出），又如何与 ANM 子弹精灵、ECL 交叉引用？
  这关系到能否做"完整 modding 工作流"而不只是孤立的二进制编辑器。

## 7. 主要来源

- Priw8 `sht-webedit`（一手，事实标准）：
  - <https://github.com/Priw8/sht-webedit>
  - README：<https://github.com/Priw8/sht-webedit/blob/master/README.md>
  - 各版本 struct：`https://raw.githubusercontent.com/Priw8/sht-webedit/master/js/struct/struct_NN.js`
- thtk（确认不支持 SHT）：<https://github.com/thpatch/thtk>
- ExpHp / truth（确认不支持 SHT）：<https://github.com/ExpHP/truth>
- Mddass 东方文件格式规范 - SHT（二手，自动抓取常被 Cloudflare 418 挡，结论已尽量对一手
  struct 核对）：<https://en.touhouwiki.net/wiki/User:Mddass/Touhou_File_Format_Specification/SHT>
- pytouhou 文档（PCB SHT 实现参考）：<https://pytouhou.linkmauve.fr/doc/>
