# sht-webedit / shmupcc-sht 源码分析（面向 IDE 移植）

承接 [sht-format-research.md](./sht-format-research.md) 的高层调研，本文是对 Priw8 两个仓库的
**源码级**分析,目标是给 THTK-Studio 的 SHT 支持定一套可落地的架构。两个仓库都是 touhou modding
开源社区的公开资料,已确认可以合法研究和移植。

分析基于克隆到本地的源码(非本项目 git):

- `Priw8/sht-webedit`(浏览器编辑器,最近一次提交 2023-09-20,覆盖 TH07–TH19 + 外传)
- `Priw8/shmupcc-sht`(quickjs CLI 编译器,最近一次提交 2023-09-12,含 `feature/th19`)

> ⚠️ 许可证:两个仓库**都没有 LICENSE 文件**。按用户确认(社区公开资料、作者允许)进行移植,
> 但若日后正式发布,建议在 NOTICE / 致谢里注明来源,或邮件向 Priw8 确认授权。

## 0. 两个仓库的定位:互补,不是重复

| | sht-webedit | shmupcc-sht |
| --- | --- | --- |
| 语言 | 原生 JS(浏览器) | TypeScript → quickjs 单文件 CLI |
| 价值 | **真实东方各版本二进制 schema**(TH07–TH19 全覆盖) | **干净的"声明式 struct + 校验 + JSON 互转"架构** |
| 数据表示 | 小端、float32(真实游戏字节序) | 大端、float64(一个**归一化**的 `shmupcc` 格式) |
| 形态 | 与 HTML 表格 UI 强耦合,但 struct/import/export 可剥离 | 纯命令行 `compile/decompile`,JSON 作为文本中间表示 |
| 适合借鉴 | **逐版本字段表 + ZUN 解析器怪癖处理** | **整体工程架构 + JSON-as-source 思路** |

结论先行:**移植策略 = 拿 sht-webedit 的真实版本 schema + ZUN 怪癖处理逻辑,套进 shmupcc-sht
式的声明式架构,用 Rust 重写,JSON 作为"源表示"(类比 ECL 的 .decl)。**

## 1. sht-webedit:声明式 schema + 通用解析器

这是整个仓库最值得抄的设计:**每个版本一个 `struct_NN.js`,纯数据描述布局;`import.js` /
`export.js` 是与版本无关的通用 reader/writer,靠走 schema 完成解析和回写。**

### 1.1 schema 结构(以 TH19 为例)

每个 `struct_NN.js` 导出一个对象,含四段字段定义 + 一组元数据:

```js
window.struct_19 = {
  ver: 19, editorVer: "19",
  main: [ "字段名","类型", ... ],       // 文件头 + 三个特殊段的占位
  option_pos: [ "x","float", "y","float" ],   // 单个副机位置的结构
  sht_off:    [ "offset","uint32" ],          // 单条偏移表项的结构
  sht_arr:    [ "fire_rate","byte", ... ],     // 单个 shooter 的结构
  // —— 元数据(驱动通用解析器的行为)——
  sht_off_type: "rel",          // 偏移是相对(rel)还是绝对(abs)
  option_pos_len: 0xA0,         // option_pos 段总字节数
  max_opt: 0x04,                // 最大副机数(>TH12 用它,否则用 pwr_lvl_cnt)
  flags_len: 0x3c, flag_size: 4,// flags 段:总字节 / 每个 flag 的字节宽
  type: "maingame",             // maingame / photogame(见 §4)
  forced_shtoffarr_len: 0x28,   // ZUN 要求偏移表定长(见 §3.1)
  f_uf_shooter_split: true,     // shooterset 是否分聚焦/非聚焦
  dummy_offset_value: 0xffffffff// 偏移表填充/终止哨兵(逐版本不同!)
};
```

类型词汇很小:`byte / int16 / int32 / uint32 / float`(全部小端、float32),外加四个**特殊段**
`option_pos / sht_off / sht_arr / spellname_arr`,由通用解析器特判。`string@N` 是定长 Shift-JIS
(仅 PoFV 符卡名用)。

### 1.2 文件总体布局(TH10+)

```
[main 头部]
[option_pos 段]      ← 各 power 等级的副机坐标,三角填充
[sht_off 偏移表]      ← 每条 4 字节(>TH12)或 8 字节(≤TH12)
[sht_arr shooter 数组] ← 各 shooterset,之间用 4×0xFF 分隔
```

`import.js::readSht` 顺序走 `main` 数组,遇到特殊段名时调用对应的 `readOptionPos /
readShtOff / readShtArr`。`export.js::getExportArr` 是其逆运算,并在写完 shooter 数组后
**回填偏移表**(偏移自动重算,用户不手填)。

## 2. 高版本(TH15–TH19)shooter 结构演化

这是用户最关心的部分。**TH15/16/17 的 shooter 结构完全一致**,TH18 起开始变化:

| 字段 | TH15/16/17 | TH18 | TH19 |
| --- | --- | --- | --- |
| fire_rate | byte | byte | byte |
| start_delay | byte | byte | byte |
| dmg | int16 | int16 | int16 |
| off_x / off_y | float×2 | float×2 | float×2 |
| hitbox_x / hitbox_y | float×2 | float×2 | float×2 |
| angle | float | float | float |
| speed | float | float | float |
| (unknown) | int32 | int32 | **float**(`unknown_sht_float`) |
| option | byte | byte | byte |
| (unknown byte 0) | byte | byte | byte |
| anm / anm_hit | byte×2 | byte×2 | byte×2 |
| sfx_id | int16 | int16 | int16 |
| **new_th18_int32** | — | **int32(新增)** | 拆成 4×byte(`unknown_sht_byte_1..4`) |
| fire_rate2 / start_delay2 | byte×2 | byte×2 | byte×2 |
| 行为函数 | func_on_init / on_tick / _old_on_draw / on_hit(int32×4) | 同左 | **func_1?..func_4?(int16×4)** + `_old_on_draw`(int32) + `func_on_hit`(int32) |
| flags | 0x20 字节 | 0x20 字节 | **0x3c 字节** |
| flag_size | TH15=4, TH16/17=**2** | 4 | 4 |

要点:

- **fire_rate / start_delay 在高版本是 1 字节**(TH07 时代是 int16)。范围 0–255,UI 要按 byte 校验。
- TH15 与 TH16/17 的差别**只在 `flag_size`**(TH15 把 0x20 字节切成 8 个 int32;TH16/17 切成
  16 个 int16)。`flags` 段语义未知(README 的 TODO),先按"原样保留的整数数组"处理,不要丢。
- TH18 在 `sfx_id` 后插入一个 `new_th18_int32`,导致其后所有字段整体后移——**这正是"逐版本
  schema 不能复用"的典型例子**。
- TH19 重排了尾部:旧的具名行为函数变成 4 个 `func_?` int16(语义待考),且 `flags` 扩到 0x3c
  (15 个 int32)。
- `fire_rate2 / start_delay2`(LoLK 起)用 120 帧计时器,一旦设置就**覆盖**原 `fire_rate /
  start_delay`,且有"偶发卡住不发射"的著名 bug——编辑器应在该字段旁给警告。

### 2.1 main 头部(TH15–TH19 基本稳定)

`unknown_head` int16、`sht_off_cnt` int16、`hitbox_u/grazebox_u/itembox_u` float、四个移动速度
`move_{nf,f}_{str,dia}` float、`pwr_lvl_cnt` int16、`max_dmg_u` int16、`SA_power_divisor` int32
(只 SA 用)、`max_dmg` int32,再跟一串 `unknown_*` int32(TH19 比 TH15 多了 unknown_7..10)。
带 `_u` 后缀的是"旧版遗留/未用"字段,`export.js` 会在新旧版本互转时用 `prop+"_u"` 回退取值。

## 3. 必须复刻的 ZUN 解析器怪癖(移植的难点)

这些是"血泪逆向"出来的细节,自己从零写解析器最容易踩坑的地方:

### 3.1 偏移表定长(`forced_shtoffarr_len`)

ZUN 的解析器**假设 shooter 数组从一个固定偏移开始**,所以多数游戏的 `sht_off_cnt` 被强制成一个
定值(TH13=0x0B,TH14/15/16/17=0x0A,TH17=0x14,TH18/18.5/19=0x28)。导出时:

- `sht_off_cnt` 必须等于 `forced_shtoffarr_len`;
- 实际用到的 shooterset 数记在 `real_sht_off_cnt`,不足的用**空偏移(哨兵)补齐**;
- `real_sht_off_cnt` 可以比 `sht_off_cnt` 小,但不能更大。

### 3.2 哨兵值逐版本不同(`dummy_offset_value`)

偏移表的填充/终止哨兵**不是固定的**:TH18 用 `0x00000000`,TH18.5 / TH19 用 `0xffffffff`,更早
的版本不设(默认 0)。`readShtOff` 用它判断"提前结束偏移表"(`th18 jank`:第一项不算,之后遇到
哨兵就 `break`),从而支持变长偏移表。**移植时这个值必须按版本表查,不能写死。**

### 3.3 shooterset 之间用 4×0xFF 分隔

`readOneSht` 在每个 shooter 起始处检查前 4 字节是否全 `0xFF`,是则结束当前 shooterset。导出时
每个 shooterset 末尾补 `255,255,255,255`。

### 3.4 相对 vs 绝对偏移(`sht_off_type`)

TH07–TH12 是 `abs`(绝对文件偏移),TH13+ 是 `rel`(相对 sht_off 段)。回写时:
`rel` 直接写 `offsets[j]`;`abs` 写 `offsets[j] + sht_off_off + offsets.length*entrysize`。

### 3.5 ≤TH12 偏移表是 8 字节项,带 power / 魔法数

`>TH12` 偏移表每项 4 字节(纯 offset);`≤TH12` 每项 8 字节(offset + 附加 4 字节)。附加 4 字节
在 MoF–UFO(`f_uf_shooter_split`)里是 `0x08`(每组第一项)或 `999`(`0x03E7`,其余项);在 <MoF
里是 `power` 值。alcostg(ver 10.3)又是特例。

### 3.6 option_pos 三角填充 + TH10 的额外 padding

副机位置按"power 等级 p 对应 p 个副机"的**三角数**排布,聚焦/非聚焦各一遍;`>TH12` 用定长
`option_pos_len` + `max_opt`,`≤TH12` 用运行时 `pwr_lvl_cnt`。**TH10 / alcostg** 每个副机坐标后
多 4 字节 padding。未用槽的填充值也分版本:`≤TH12` 填 `999.0f`(`00 C0 79 C4`),`>TH12` 填 0。

### 3.7 photogame 与 0-power shooterset

`type: "photogame"`(TH12.8 / TH14.3 / TH16-sub / alcostg)结构不同:没有正常的聚焦/非聚焦分裂,
shooter 全进 `extra`。另外 `pwr_lvl_cnt=4` 时有 **10 个 shooterset(含 0 power 那组)**,0 power
组在 HSiFS Okina 终符里真的会用到——别当成可删的冗余。TD(TH13)还多一个 trance 专用 shooterset。

## 4. shmupcc-sht:值得借鉴的工程架构

shmupcc-sht 是一个 quickjs 单文件 CLI:`shmupcc [-c|-d] VERSION INPUT OUTPUT`。

- `-d`(decompile):二进制 → JSON(`ShtReaders[version]` → `.toJSON()`)
- `-c`(compile):JSON → 二进制(`ShtWriters[version]` → `.toBuffer()`)

**这正是 ECL 那套 `.decl ↔ .ecl` 的 SHT 版**——JSON 当人类可读的"源",这回答了上一篇的开放问题
("shmupcc-sht 是不是把 SHT 编译成可读文本?"):**是,JSON 就是它的文本表示。**

它的架构比 sht-webedit 干净得多,几个值得抄的点:

1. **声明式 `Struct` 类**(`struct.ts`):字段定义 `{name, type, count?}`,`type` 可以是基本类型
   或**嵌套 Struct**(组合)。一套 `readFrom / writeTo / validate` 通吃。
2. **内建校验**:`validate` 按类型做范围检查(BYTE 0–255、INT16 等),返回结构化
   `{field, message}` 错误——天然契合本项目"结构化 diagnostics"模式。
3. **下划线前缀 = 未用字段**:`_unused1` 这类字段读时不进 JSON、写时补 0,JSON 保持干净。
4. **版本注册表**(`versions.ts`):`ShtReaders / ShtWriters` 按版本字符串映射 reader/writer 类——
   和本项目 `TOOLCHAIN_REGISTRY` / `WORKBENCH_EDITOR_VIEWS` 的注册式扩展思路一致。

⚠️ **但要注意它的局限**:当前 `versions.ts` 只注册了 **`"shmupcc"` 一个格式**,而且
`shmupcc.ts` 里那个格式是**大端 + float64 的归一化结构**(`version_num / dmg_cap_type /
hitbox/grazebox/itembox 都是 FLOAT64`),**不是任何真实东方游戏的字节序**。也就是说:

- shmupcc-sht 提供的是**架构骨架 + 一个示范格式**(很可能对应 "Shmup Creator" 引擎或一个统一中间
  表示),**不含真实东方各版本的 schema**;
- 真实东方逐版本 schema 仍要从 **sht-webedit 的 `struct_NN.js`** 取。
- 仓库虽然合并过 `feature/th19`,但克隆到的 `versions.ts` 并未注册 th 版本,真实游戏 reader 尚未
  在此实现——**不要误以为它能直接编译真实东方 .sht**。

## 5. 给 THTK-Studio 的 Rust 设计建议

综合两者,推荐如下(遵循本项目分层:解析逻辑在 Rust 宿主,前端只做结构化视图):

### 5.1 数据模型:声明式版本 schema

在 `src-tauri/src/modules/sht/` 下,把 sht-webedit 的逐版本 schema 转写成 Rust 的声明式表
(借 shmupcc 的 `Struct` 思路):

```rust
enum FieldType { Byte, I16, I32, U32, F32, OptionPos, ShtOff, ShtArr, Flags }
struct FieldDef { name: &'static str, ty: FieldType }
struct VersionSchema {
    ver: f32,                 // 7.0 / 12.8 / 14.3 / 18.5 / 19.0
    main: &'static [FieldDef],
    shooter: &'static [FieldDef],
    sht_off_type: OffsetType, // Rel | Abs
    option_pos_len: usize, max_opt: usize,
    flags_len: usize, flag_size: usize,
    kind: ShtKind,            // MainGame | PhotoGame
    forced_shtoffarr_len: Option<usize>,
    f_uf_shooter_split: bool,
    dummy_offset_value: u32,
}
```

通用 `read_sht(bytes, &schema) -> ShtDocument` / `write_sht(&doc, &schema) -> Vec<u8>`,把
§3 的所有怪癖集中在这两个函数里。**逐版本差异只体现在 schema 表,不分散到 if-else。**

### 5.2 源表示:JSON(`.sht.json`),对齐 ECL 的 .decl 模型

- decompile:`.sht`(二进制)→ `.sht.json`(结构化、人类可读、可 diff)
- compile:`.sht.json` → `.sht`,导出时**自动重算偏移表**(用户永不手填 offset)
- 这样 SHT 也能复用本项目"源文件 ↔ 二进制"的工作流心智模型,只是无外部 exe,解析器内建。

### 5.3 前端:结构化表单/表格视图,不是 Monaco 文本

- 在 `services/workbench/editorViews.js` 的 `WORKBENCH_EDITOR_VIEWS` 注册一个 SHT 视图(类似
  `binary-script` 思路):main 头部一张表,option_pos 一张表,每个 shooterset 一张表。
- 校验直接用 §4.2 的范围检查产出结构化 diagnostics,接现有 Output/Problems 面板。
- `func_*` / `anm` / `sfx_id` 这些是**枚举/索引**,需要每版本一张名称映射表才能友好显示——可借鉴
  ECL 的 eclmap 语义层(外部数据驱动),后续补。

### 5.4 实施顺序(高版本优先,贴合用户偏好)

1. **先做 TH18/TH19 的只读 decompile**(用户偏好新作;且 TH18/19 的偏移表哨兵/变长逻辑最复杂,
   先啃下来后面都简单)。返回结构化 JSON,前端只读表格视图。
2. 补 TH15/16/17(三者 shooter 结构相同,一次搞定),再回填 TH13/14。
3. 实现 compile(写回 + 偏移重算 + `forced_shtoffarr_len` 校验)。
4. 补 TH07–TH12 旧格式(8 字节偏移表、abs 偏移、option 硬编码、双文件聚焦/非聚焦)。
5. 接入 `func_*/anm/sfx` 名称映射的语义层。

## 6. 仍待解决的问题

- `flags` 段(各版本 0x20 / 0x3c 字节)的语义完全未知(sht-webedit README 自己列为 TODO)。先
  无损保留为整数数组,不要尝试解释。
- TH19 尾部 `func_1?..func_4?`(int16×4)与早期 `func_on_init/tick/draw/hit`(int32×4)的对应
  关系待考——跨版本互转时这块需要小心。
- `unknown_head`、main 里的 `unknown_2..10`、shooter 里的 `unknown_sht_*` 含义未知,保留原值。
- shmupcc-sht 的 `"shmupcc"` 格式到底对应哪个引擎/中间表示?是否值得把它作为我们 IDE 的**统一
  归一化中间层**(各版本东方 → 统一 JSON → 各版本东方),以简化跨版本互转?
- 各版本 `func_*` / `anm` / `sfx_id` 的名称表从哪来(社区是否已有整理)?这是语义层的数据源。

## 7. 源码位置速查(本地克隆,便于二次核对)

- 通用 reader:`sht-webedit/js/import.js`(`readSht / readShtArr / readOneSht / readShtOff /
  readOptionPos`)
- 通用 writer:`sht-webedit/js/export.js`(`getExportArr / getExportShtArr /
  getExportOneShooter / getExportOptPos`,含偏移回填与 ZUN 怪癖)
- 类型读写原语:`sht-webedit/js/vartypes.js`
- 逐版本 schema:`sht-webedit/js/struct/struct_{07,08,09,10,12,12.8,13,14,14.3,15,16,16-sub,17,18,18.5,19,alcostg}.js`
- shmupcc 架构:`shmupcc-sht/src/{struct,versions,shmupcc,binary-types,binary-reader,binary-writer,main}.ts`
