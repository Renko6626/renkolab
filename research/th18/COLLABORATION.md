# TH18 卡牌改造协作指南

> 目标：让协作者以**合法自有的 TH18 v1.00a**为样本，通过 thcrap 的运行时加载/内存补丁能力，做可复现、可审计的卡牌系统实验。
> 本文不是可直接分发的 TH18 DLL 或补丁。仓库不含游戏二进制、Ghidra 项目或可复用的 TH18 注入地址。

## 现有材料能支持什么

卡牌系统的**架构、注册表、主要 vtable 接缝、商店/资源路径和 58 张卡的效果目录**已足以支持“从已有卡切入”的定点研究与设计讨论；它们均限定于 **TH18 v1.00a**，并标注一手/社区证据与未决项。

当前**没有**已在游戏内跑过的 TH18 thcrap patch、codecave 或 DLL，也没有可跨版本使用的地址、字节模式或 hook 模板。这不是把目标收缩为“只改已有卡”的理由；它说明完整卡牌重做必须先建立一个经过实跑验证的 TH18 运行时补丁底座。

加载层优先使用 thcrap；“DLL 注入”在这里是 thcrap 所采用的运行时加载机制。除非任务本身研究加载器，协作者无需另写裸 loader。

## 版本与边界

- 仅以 **TH18 v1.00a** 为事实目标。地址、`expected` 字节和结构偏移均绑定该版本；不匹配时必须停止，不能强行应用。
- 仅使用协作者自己合法持有的 `th18.exe`。二进制、解包资产、Ghidra 数据库、反编译全文不得提交。
- 补丁只分发 thcrap 元数据、源码/汇编、预期原字节和文档；不分发游戏字节。
- 不把 TH16 地址、ABI 或机器码套到 TH18。TH16 材料只证明方法和审计流程可行。

## 最终目标与实施路线

目标是同时做到：替换零售卡的效果、定义新的卡牌运行时行为，并让新卡进入获取、显示、存档和回放链路。建议按下列阶段推进；每一阶段都产出可独立验证的补丁，避免把新的注册表、UI、序列化和玩法逻辑一次性混在同一个 codecave 里。

| 阶段 | 目标 | 已有依据 | 尚需确认/实现 |
| --- | --- | --- |
| 0. 运行时底座 | 确认 thcrap 能对 TH18 v1.00a 安全加载、写入并卸载最小观测逻辑。 | TH16 thcrap 文档/审计。 | TH18 目标点、原字节、ABI 与游戏内实跑。 |
| 1. 替换零售卡 | 将一个既有卡的效果转交给我们的逻辑；先主动卡，再被动/装备卡。 | `cards-01` 的 vtable 调用点、`cards-05` 的逐卡目录。 | 每个目标函数的 TH18 机器码级复核和稳定的自定义状态管理。 |
| 2. 自定义卡运行时 | 用自定义对象/vtable 或统一 dispatcher 承载新行为，并与 AbilityManager 卡链表兼容。 | 基类 `zCardBaseClass`、22 槽 `zVTableCard`、链表和分类 flags 已定位。 | 自定义对象内存布局/析构、完整必需 vtable 槽、与 HUD/option 的生命周期。 |
| 3. 注册与获得 | 让新 ID 被查找、分配、商店/掉落逻辑选择，并配置价格、权重和关卡可用性。 | `zTableCardData[]`、`allocate_new_card`、商店筛选/购买路径已定位。 | 静态表的迭代边界、未知 ID 的 allocator fallback、所有 ID 范围检查与掉落/图鉴入口。 |
| 4. 呈现与持久化 | 显示名称/图标/说明，支持初始卡组、解锁、存档与 replay。 | 表中 sprite 字段；存档和 replay 都保存 card-id 字节数组。 | 文本/ANM 资源来源与加载路径、存档/解锁数组的可扩范围和完整 UI 消费点。 |

**关键判断：**新增卡不能只“往 `zTableCardData[]` 后面写一项”。零售表是静态的，现有 `allocate_new_card` 的 ID→类分派、商店的表遍历、UI、解锁位、存档/replay 都可能各自假设零售卡集合。阶段 2–4 必须以同一套新 ID/元数据模型一起设计和验证。

阶段 1 仍是必要起点：它用于验证 TH18 的加载方式、调用约定和回滚机制，不是最终功能的限制。最适合作为第一个垂直切片的是“替换一张主动卡的效果，同时保留零售 ID、图标和商店入口”；成功后再把同一套 dispatcher 扩展到新 ID。

## 新增卡前必须补齐的研究

- `AbilityManager__allocate_new_card` 的完整 switch/default：未知 ID 当前如何处理，以及在哪个点接入自定义分配。
- `TableCardData__get` 和所有商店/菜单遍历的确切表边界：如何让外部表参与查询，而不覆写零售 `.rdata`。
- 卡牌文本、图标和 HUD 精灵的资源加载链；目前只确认表内 `sprite_large/sprite_small` 字段，尚未形成可替换的资产管线。
- `SCOREFILE` 解锁位、初始卡组的 16 个 ID 字节、replay 数组以及任何按 `card_id` 索引的数组：逐处确认上限与兼容策略。
- 装备卡的 shooter 数据来源；若新卡要发射新弹型，`cards-OPEN-passive-shooter-data.md` 是硬性前置。

不要从 `cards-DEEPRESEARCH-salvage.md` 直接抄实现结论；它是未合并原始素材。标为 🟡/⏳ 的字段可成为专项研究任务，但不能作为未经验证的新卡框架前提。

## 开工顺序

1. 读 [README.md](README.md) 和 [findings/README.md](findings/README.md)，确认样本和证据纪律。
2. 按任务阅读：架构 [cards-01-system-architecture.md](findings/cards-01-system-architecture.md)，卡效果 [cards-05-card-catalog.md](findings/cards-05-card-catalog.md)，商店 [cards-04-card-shop.md](findings/cards-04-card-shop.md)。
3. 在本地、忽略的 `th18-files/` 中打开 TH18 数据库；以函数语义和控制流复核目标点，记录 EXE 的版本/哈希和原始字节。
4. 用 thcrap patch 组织实验：逐版本脚本、`expected` 原字节校验、最小 codecave/binhack；地址只写入该版本文件。
5. 先做无行为改动的加载验证，再一次只加入一个行为变化；保留可还原补丁和游戏内验证记录。
6. 把已验证的地址、原字节、调用约定、测试步骤和结果写回 `findings/`；猜测只能留在开放问题。

## 可复用资料（仅流程，不是 TH18 地址）

- [../sht/test-laser/thcrap_patch.md](../sht/test-laser/thcrap_patch.md)：thcrap patch 目录、`binhack`/`codecave`、`expected` 校验及相对 `[…]`、绝对 `<…>` 表达式。
- [../sht/test-laser/NOTES.md](../sht/test-laser/NOTES.md)：ABI/栈平衡审计；按目标函数 `RET` 和游戏调用点确认调用约定。
- [../sht/disasm/README.md](../sht/disasm/README.md)：本地 Ghidra/PyGhidra 环境和样本边界。
- [../sht/findings/00-METHOD-逆向记录纪律.md](../sht/findings/00-METHOD-逆向记录纪律.md)：可复查结论的证据标准。

TH16 `test-laser` 尚未完成游戏内实跑，因此它是**经过静态审计的流程参考**，不是可照搬到 TH18 的生产模板。

## 合作者交付清单

- 目标版本和 EXE 哈希/版本识别方式；
- 目标卡、文档依据和目标函数的本地复核证据；
- patch 源文件（不含游戏文件）及每个写入点的 `expected` 原字节；
- codecave 的调用约定、保存/恢复的寄存器和栈说明；
- 最小复现步骤、预期游戏表现、实际结果及失败/崩溃记录；
- 对 `research/th18/findings/` 的增补：结论、置信度、适用版本和未验证假设。
