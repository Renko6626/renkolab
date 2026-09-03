# AUDIT —— card-expand 对抗审计

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 姿态：**默认自己写错了，去二进制找证伪证据**。逐条给 CONFIRMED / REFUTED / OPEN。
> 清单来自 [`../../_template/AUDIT-checklist.md`](../../_template/AUDIT-checklist.md)。

## 0. 状态

**A–D + E 第一、二块全部实跑通过（2026-09-02，用户 Windows 实机，thcrap 2024-11-06 stable）。**

| 步 | patch | 日志关键行 | 游戏内 |
| --- | --- | --- | --- |
| 1 | `th18_card_expand` | `OK: table filled (58 rows @ 03850000), 100/100 sites verified` | 与香草无差别 |
| 2 | `th18_card_expand_255` | `jumptable: 255 entries … allocator bound = 254` → `OK … 255 rows … allocator relocated, 100/100` | 与香草无差别 |
| 3 | + `th18_card_expand_test` | `trace: allocate_new_card(id=58, mode=1)  <- NEW ID`（×4，两次 reset_cards 各两张）| 不崩；卡组编成选它时提示「未获取」——当时预期，D 已解 |
| C+D+E1 | `_255`（含 manager 扩容、影子存档、文案重定向）+ `_test` | 用户报告通过（2026-09-02 晚，日志未留档）| id 58 能获得、重启后仍解锁、名字「测试卡牌 58」 |

`gate: BP_ce_gate fired at ScoreFile__load` 每次都在——断点门成立。
第 3 步的 trace 里 `id=42` 是默认卡组的 KOZUCHI，`id=16 / 24` 是局中获得的卡，
`reset_cards` 每次过场跑两遍所以成对出现。

## A. ABI / 栈平衡

| # | claim | 结论 |
| --- | --- | --- |
| A1 | 初始化 codecave 不调用任何引擎函数 | **CONFIRMED** —— 全文只有 `cld/pushad/mov/rep movsd/popad/ret`，见 A5 反汇编 |
| A2 | 调用约定是 cdecl、调用方清栈，所以结尾用裸 `ret` | **CONFIRMED** —— `plugin.h:71` `typedef void (TH_CDECL *mod_call_type)(void *param)`；`plugin.cpp` 的 `mod_funcs_t::run` 直接 `func(param)` |
| A3 | cdecl 要求被调方保留的 `ebx/esi/edi/ebp` 都被保住 | **CONFIRMED** —— `pushad`/`popad` 覆盖全部 8 个通用寄存器 |
| A4 | `rep movsd` 依赖 DF=0 | **CONFIRMED** —— 入口显式 `cld`；且 `popad` 不恢复标志，返回时 DF 仍为 0，符合 ABI 要求 |
| A5 | 生成的机器码就是设计的那些指令 | **CONFIRMED** —— 见下 |
| A6 | FPU 栈平衡 | **CONFIRMED** —— 全程不碰 x87/SSE |

反汇编（`<…>` 表达式用 `deadbeef` 占位，每个恰好 4 字节）：

```
rows=58                          rows=255 追加的填充循环
 0: cld                          13: mov  ebx, 0xc5        ; 255-58 = 197
 1: pusha                        18: mov  esi, <新表+0xb60> ; 行 56 (NULL)
 2: mov  edi, <新表>             1d: mov  ecx, 0xd          ; 0x34/4 = 13
 7: mov  esi, <Rxc53c0>          22: rep  movsd
 c: mov  ecx, 0x2f2   ; 754      24: dec  ebx
11: rep  movsd                   25: jne  0x18              ; 回到 mov esi
13: popa
14: ret
```

`jne 0x18` 的目标正好落在循环体首指令上 —— **CONFIRMED**（rel8 = −15，体长 13 + 跳转 2）。

## B. 写入点

| # | claim | 结论 |
| --- | --- | --- |
| B1 | 100 处 `expected` 与 exe 实际字节逐字节一致 | **CONFIRMED** —— `make verify` 从**已生成的 patch 文件**回到 exe 重新比对，不是复用生成器的中间结果 |
| B2 | 只替换 4 字节常量，opcode 一字不动 | **CONFIRMED** —— `verify_patch` 第 ③ 项逐条比对 `code` 前缀与 `expected` 前缀 |
| B3 | `code` 与 `expected` **渲染后等长** | **CONFIRMED** —— 二者由同一条记录产出。⚠️ 这条不是形式主义：长度不等时 thcrap 会「记一行日志然后**跳过校验**」（`binhack.cpp:1264`），护栏白装 |
| B4 | 绝对 `<…>` 用对了，不该是相对 `[…]` | **CONFIRMED** —— 100 处全是 `mov r32, imm32` / `cmp r32, imm32` / `add`/`lea`，常量是**当值用的地址**，不是 rel32。（`tracking-laser` 的历史教训正相反：数据指针表槽误写成 `[…]`）|
| B5 | 目标落在 `.text`，thcrap apply 时会设页可写 | **CONFIRMED** —— `.text` VA `0x401000` 长 `0xab800`，100 处全在内 |
| B6 | 零售表本身不被写 | **CONFIRMED** —— 只在初始化时**读**它一次（`rep movsd` 的源） |

## C. 完整性 —— 「100 处就是全集」怎么证的

这是本 mod 最要紧的一条：**漏一处的后果远大于改错一处**。三层证据：

| # | 检查 | 结果 |
| --- | --- | --- |
| C1 | 骨架锚点（`add r32,0x34` 紧跟 `inc r32`）在全 `.text` 的出现次数 | **正好 25 处**，与 25 个内联查表一一对应 |
| C2 | 扫「表基 / 回退行 / 表尾」三段值，列出不在骨架里的 | 15 处，**全部**是 `0x4c5f88` / `0x4c5f8c` 那两个热全局 |
| C3 | 扫**整张表区间** `0x4c53c0`–`0x4c5f88` 的全部 4 字节引用 | `.text` **0 处**、数据节指针 **0 处** |

C3 是补的：C2 只扫三小段，扫不到「直接引用第 12 行」这种写法
（`0x4c53c0 + 12*0x34 = 0x4c56d0` 落在三段之外）。补扫后确认没有这种引用。

★ **C2 当场救回一个真站点**：`CardCollection__mark_obtained_and_notify` 的
`mov edx, 0x4c53c4` `0x418e0e` 是**表遍历**，按计数收尾（`cmp ecx, 0x38`）而不是按地址，
骨架不同，被 C1 漏掉。补进 `find_walks()` 后总数从 99 变 100。
**这条审计路径必须留着。**

## C′. 阶段性复审（2026-09-02）—— 「覆盖够不够」从四个方向攻

审计 C 证的是「表的每一处引用都在 100 处里」。但用户问的是另一件事：
**卡牌子系统有没有哪块逻辑绕过了这 100 处、仍然在读旧表？** 分四个方向攻：

### C′1. 从函数名单反推 —— 没有游离的读表者

卡牌子系统 51 个已命名函数里，**9 个**含站点；另有 **4 个**调用非内联的
`TableCardData__get` `0x407d70`（`allocate_new_card`、`AbilityMenu__on_tick`、
`CardShop__pick_weighted_random_offer`、`FUN_00419170`）——函数本体已 patch，等价覆盖。
其余 38 个不碰表：它们要么只用 `card->id` 与对象自身字段，要么用
**别处查表得到的指针**（`zAbilityMenu.__card_ptrs_0xfec`、商店 offer 数组）——
那些指针来自已 patch 的查表，指向新表，行为一致。

**结论：CONFIRMED** —— 不存在「既不含站点、又不调 get、却读表」的函数，
因为 C3 已证 `.text` 里对表区间的引用只有那 100 处。

### C′2. 三种「不经查表也会碰表」的写法 —— 都不存在

| 写法 | 长什么样 | 会落在哪段 | 实测 |
| --- | --- | --- | --- |
| 指针 → 下标 | `sub reg, 0x4c53c0` / `imul`+`div` | 表基段的**非 mov/add/lea** 立即数 | **0 处** |
| 与 NULL 行指针比较 | `cmp reg, 0x4c5f20` | 回退段的 **cmp** | **0 处**（25 处全是 `mov`）|
| 静态存的行指针 | `.data` 里的 `zTableCardData*` | 数据节 4 字节对齐指向表内 | **0 处** |

第二条顺带说明游戏判「查不到」靠的是 `entry->id == 56` 或 `entry->+0x0c == 4`
（[`engine/card/th18/11`](../../../engine/card/th18/11-sentinels-56-57.md) §2），
**不是**比较指针。搬表不会改变这个判定。

### C′3. 有符号比较的隐患 —— 不成立

25 处 END 之后都是 **`jl`（有符号）**。codecave 若落在 ≥ `0x80000000`，
`cmp p, END; jl` 会翻转。核对 PE：`Characteristics = 0x0103`，
**无 LARGEADDRESSAWARE** → 32 位进程用户空间 < `0x80000000`，`VirtualAlloc` 给不出高地址。
**REFUTED（不构成问题）**，但换 build 若加了 LAA 要重看。

### C′4. 与其它 patch 撞车 —— vendor 内 0 处，`base_tsa` 待用户实测

100 处 5–7 字节写入点，任何一处被别的 binhack/breakpoint 覆盖，后应用的那个会
「expected 不匹配 → 静默跳过」。新增 `sites.py conflicts <其它.js>` 做区间交集。

- vendor 里的 ExpHP 5 个 th18 patch（9 个 hackpoint）：**0 处重叠**。
- **`base_tsa`：已实测 —— CONFIRMED，0 重叠。**发布仓库 `th18_modkit` 自带
  thcrap 2024-11-06 及其 `base_tsa/th18.js` + `th18.v1.00a.js`（`addr` 与 `cavesize`
  分在两个文件、地址用 `Rx` 记法——`conflicts` 已改为认这两样）。
  对 base_tsa 70 处 + `th18_mouse_control` + `renko`：**0 重叠**。
  顺带：base_tsa 在 `0x41669c` / `0x4167b0` 挂了卡牌文案（`gentext#card_name/desc`）的
  翻译钩子，紧邻 `imul $0x1c0` 的文案读取——**战线 E 搬文案缓冲时要与它对账**。

### C′5. 第 1 步刻意**不**覆盖的（这不是漏）

行数仍 58，所以 [`11`](../../../engine/card/th18/11-sentinels-56-57.md) §5 的另外 33 处
边界（字面 56/57、`mgr+0xc84` 数组、`zAbilityMenu.__card_ids`、存档数组）**一处不动**，
它们的语义在 58 行下与香草完全相同。这些是战线 B–E 的事，见
[`../card-rework/PLAN-255-ids.md`](../card-rework/PLAN-255-ids.md)。

## D. 量纲 / 算术

| # | claim | 结论 |
| --- | --- | --- |
| D1 | `58 * 0x34 = 3016`，`3016 / 4 = 754 = 0x2f2` 整除 | **CONFIRMED**（`0x34` 可被 4 整除，`rep movsd` 不会剩尾巴）|
| D2 | 拷贝 3016 字节 = 读 `0x4c53c0`–`0x4c5f88`，**不碰**那两个热全局 | **CONFIRMED** —— 末字节是 `0x4c5f87`，`0x4c5f88` 是全局的第一个字节 |
| D3 | rows=255 时 cave 尺寸 = 拷贝量 + 填充量，不多不少 | **CONFIRMED** —— `3016 + 197 × 52 = 13260 = 0x33cc` = 声明的 `size` |
| D4 | 回退行偏移 `56 × 0x34 = 0xb60` | **CONFIRMED** —— 与 `0x4c5f20 − 0x4c53c0 = 0xb60` 一致 |
| D5 | `<codecave:NAME+OFF>` 的 OFF 是**十六进制** | **CONFIRMED** —— `expression.cpp` `GetCodecaveAddress` → `strtouz(…, 16)`。⚠️ 写成看着像十进制的 `+58` 会被当成 `0x58`。生成器一律输出裸十六进制 |

## E. thcrap 行为核对（都是从源码读的，不是记忆）

| # | claim | 结论 |
| --- | --- | --- |
| E1 | `size` 而无 `code` 的 codecave 合法，默认 READWRITE | **CONFIRMED** —— `binhack.cpp:1594` 只在两者皆无时忽略；access 默认见 `codecave_from_json` 尾部 |
| E2 | `export` 要求 access 是 EXECUTE 或 EXECUTE_READ | **CONFIRMED** —— `binhack.cpp:1544`。所以 init cave 声明 `"access": "RX"` |
| E3 | codecave 之间可互相引用 | **CONFIRMED** —— 第二遍先 `func_add` 记录全部地址，第三遍才渲染 `code` |
| E4 | `*_patch_init` 会被调用 | **CONFIRMED** —— `binhack.cpp:1724` → `plugin.cpp:304` `patch_func_init`；`mod_funcs_t::build` 取 `_patch_` 之后的后缀作 key，`th18_card_table_patch_init` → `init` |
| E5 | ⚠️ `*_patch_init` **早于** binhack 应用 | **CONFIRMED** —— `patch_func_init` 在 `codecaves_apply` 末尾，而 `runconfig.cpp:655-656` 是先 codecaves 后 binhacks。**所以它能用来预填新表，但不能用来验证 binhack 是否都打上了** |
| E6 | 页保护在 `patch_func_init` 之后才设 | **CONFIRMED** —— `codecaves_apply` 的 `VirtualProtect` 循环在 `patch_func_init` 之后，所以初始化时整块还是 `PAGE_EXECUTE_READWRITE`，写得进去 |

## F. 仓库纪律

| # | claim | 结论 |
| --- | --- | --- |
| F1 | 不分发游戏字节 | **CONFIRMED** —— 新表内容**运行时**从用户自己的 exe `memcpy`，patch 里只有地址、原字节和源码 |
| F2 | 不写死 `0x400000` | **CONFIRMED** —— 零售表地址用 thcrap 的 `Rx` 记法（`<Rxc53c0>`，`expression.h:310`：相对模块基址）|
| F3 | 可回滚 | **CONFIRMED** —— 从 run config 的 patch 栈里移除即可；不写存档、不改磁盘上的任何游戏文件 |

## H. 全有或全无的门（`th18_card_expand.dll`）

**起因（用户复审）**：`*_patch_init` codecave 是否被自动调用取决于 thcrap 版本；
没被调用时新表全零、100 处 binhack 指向空表，**而日志一切正常**。
E5 已经说明它验不了 binhack；这一条说明它连「表填了没」都给不出证据。

| # | claim | 结论 |
| --- | --- | --- |
| H1 | ~~`*_mod_post_init` 会被调用~~ | **REFUTED（实跑）** —— 日志停在 `plugin_init`。根因见 §H′；改为断点 `ce_gate`（H15）|
| H2 | 名字匹配：`th18_card_expand_mod_post_init` → 后缀 `post_init` | **CONFIRMED** —— `mod_funcs_t::build` 用 `strstr(name, "_mod_")`，只有一处 `_mod_` |
| H3 | 签名 `void (TH_CDECL*)(void*)` | **CONFIRMED** —— `plugin.h:71`；DLL 里声明为 `void __cdecl f(void*)` |
| H4 | `func_get` / `log_printf` 是 C 链接导出，可 `GetProcAddress` | **CONFIRMED** —— `thcrap.h:57 extern "C"`；`plugin.h:24`、`log.h:36` 皆 `THCRAP_API` |
| H5 | codecave 在 post_init 时可写 | **CONFIRMED** —— `access: "RW"` → `PAGE_READWRITE`（E1）|
| H6 | 验证算式：改后 4 字节 = `cave + 类别基偏移 + 字段`，前缀不变 | **CONFIRMED** —— `sites_gen.h` 与行数无关（58/255 逐字节相同）；rows 由第一处 END 站点已写入的尾界反推（`derive_rows`：必须 ≥ cave、整除 `0x34`、落在 58–255），反推失败即 FAIL |
| H7 | 填表的最小自证 | 行 0 的 id == 0、行 56 的 id == 56，任一不符即 FAIL 并停手 |
| H8 | 导出无装饰名 / 32 位 / 只依赖 kernel32+msvcrt / 自身零 x87 | **CONFIRMED** —— `make dllverify dllx87`；x87 只查我们自己的目标文件（整个 DLL 的 42 条来自 static-libgcc 运行时）|
| H10 | 自检①：`thcrap_plugin_init` 验零售表签名（行 0 id==0、行 56 id==56、名字 `"NULL"`），不符则返回 1 自卸载 | **CONFIRMED** —— `dll_main.c`；`IsBadReadPtr` 兜住名字指针非法的情况 |
| H9 | 拿不到 thcrap 导出时的行为 | 降级：写 `th18_card_expand.log`，**不填表**并明说 —— 宁可不装，不静默 |
| H11 | 发布仓库那份 thcrap（2024-11-06 stable）支持本 mod 用到的三样 | **CONFIRMED** —— 拉 GitHub 同日提交 `aeb9155` 的源码核对：`GetCodecaveAddress` 有 `+` 偏移解析、`binhack.cpp` 有 `patch_func_init`、`init.cpp:416` 有 `post_init`；DLL 里 `strings` 也见 `_patch_` 与 `func_get`/`log_printf` |
| H12 | 两个行数的 patch 同时进栈 | **兜住** —— 搬表只有先到者生效，但分配器上界 binhack 两边都能打上；DLL 检出 `rows` 与上界不符即 FAIL 并把 `0x411479` 写回 `0x38`（`restore_alloc_bound`） |
| H14 | 日志落在游戏 exe 目录而不是 CWD | **CONFIRMED（修过一次）** —— 注入期间 CWD 是 `thcrap/bin`（`inject.cpp:355` 设、`:384` 才恢复），`plugin_init`/`post_init` 都在其间；第一版用相对路径把日志写进了 `thcrap/bin/`。现从 `GetModuleFileNameA(NULL)` 拼绝对路径，与 mouse-control 一致 |
| H15 | 自检门改为断点 `ce_gate` @ `ScoreFile__load` `0x4637d0`，`cavesize` 5 | **CONFIRMED** —— 见 §H′ |
| H13 | DLL 构建可复现 | **CONFIRMED** —— `-Wl,--no-insert-timestamp`，两次构建 md5 相同；否则每次 `release` 都会产生只差时间戳的假提交 |

**这一节把「表空」「binhack 漏了」两种静默失败都变成了日志里的一行红字。**

### H′. 为什么 `post_init` 没跑、为什么换成断点

**实跑现象**：`th18_card_expand.log` 停在 `guard: retail table signature ok`，`post_init` 一行没有。

**根因**（`plugin.cpp:301-308`，2024-11-06 与 master 同）：`mod_funcs.merge(mod_funcs_new)` 是
`std::unordered_map::merge`，**不合并目标里已存在的 key**；`init.cpp:327` 先 `plugin_init(hThcrap)`
把 thcrap.dll 自己的 `steam_mod_post_init` / `motd_mod_post_init` 注册进去，`post_init` 已被占，
插件的被静默丢弃。`init` / `detour` 之所以能跑，是因为它们「直接在新表上 `run`」再合并。
另：`post_init` 每个 init stage 结束各跑一次，base_tsa th18 有 3 个 stage。升级 thcrap 无用。

**断点 `ce_gate`** @ `ScoreFile__load` `0x4637d0`，`cavesize` 5：

- 原字节 `55 8b ec 6a ff` = 三条完整指令、无相对寻址；
- 该函数只被 `0x452cde` 调一次，且是**最早碰卡表**的函数（两次调 `init_unlocked_cards_from_table`）；
- 断点声明在本 patch = 最后一个 init stage，**能触发即证明全部 stage 已应用**；
- 与 base_tsa 70 处 + 另两个 patch：0 重叠；`BP_ce_gate` 用 static 只跑一次；
- 启动器底部的交叉检查看得见 `ce_gate` ↔ `BP_ce_gate`。

## I. 战线 B —— 分配器搬迁

| # | claim | 结论 |
| --- | --- | --- |
| I1 | 两处 binhack 同长 | **CONFIRMED** —— `83 fb 38`→`83 fb fe`（3）；`ff 24 9d <disp32>`（7），只换 disp32 |
| I2 | `cmp ebx, rows-1; ja` 的语义 = 允许 id 0..rows-1 | **CONFIRMED** —— 无符号 `ja`，与原 `0x38` 同构 |
| I3 | 跳转表项 57..254 指向 case 56 函数体是安全的 | **CONFIRMED** —— case 56 的序列以 `jmp 0x412cd5` 收尾，栈上正好留 memset 的 `0xc` 字节（§A 已审）；**我们没写任何新的 case，栈契约由原代码自己满足** |
| I4 | 公共尾段把 `card->id` 写成真实 id 而不是 56 | **CONFIRMED** —— `0x412cec mov [esi+4], ebx`，`ebx` = `[ebp+8]` 即调用者给的 id |
| I5 | 基类虚表 `0x4b4c78` 无空槽 | **CONFIRMED** —— 22 项全非零，实读函数体全是 `xor eax,eax; ret[ imm]` / `ret` / 三个读字段的小函数 |
| I6 | id 58 的 `owned[id]` 写不越界 | **CONFIRMED（仅 58）** —— `0x412d42` 写 `mgr+0xc84+id*4`；58 → `+0xd6c`，对象止于 `0xd70`。**59 起越界**，战线 C 之前禁止 |
| I7 | 跳转表全零时的后果 | **REFUTED（已兜住）** —— 那是 `jmp [0]` 必崩，比表空更糟。所以跳转表拷贝**同时**放在 `_patch_init` 保险和 DLL 权威两处；DLL 还核对项 56 == case56、两处 binhack 已生效，不符即 FAIL |
| I8 | 有符号 `jl` 对 255 行的新表尾界 | **CONFIRMED** —— 同 C′3，无 LAA，codecave < `0x80000000` |
| I9 | 测试 cave 的 flags | **CONFIRMED** —— 原 `movzx` 不设 flags；cave 里 `cmp` 设了；返回后紧接 `push eax; call`，无人读 flags（`0x407eeb`/`0x407eec`）|
| I10 | 测试 cave 的栈 | **CONFIRMED** —— `call` 压 4 字节、`ret` 弹回，cave 内不动栈；只写 `eax`，与原指令的目的寄存器相同 |
| I11 | 追踪断点只读 | **CONFIRMED** —— 读 `[ebp+8]`/`[ebp+0xc]`（序言 `push ebp; mov ebp,esp` 已执行），返回 1 照常执行；不调 thcrap API，零 x87 |
| I12 | `0x407ee3` 与 `0x411469` 不与正式 patch 的站点重叠 | **CONFIRMED** —— 前者在 `reset_cards`（无站点），后者在 `0x411479` 之前 7 字节，不相交 |

## J. 战线 C —— `zAbilityManager` 扩容

| # | claim | 结论 |
| --- | --- | --- |
| J1 | 12 处全部同长 | **CONFIRMED** —— `push imm32`×3、`lea r,[r+disp32]`、`mov r,imm32`×4、`mov [r+r*4+disp32],imm32`、`cmp r,imm32`×3；`make verify` 逐条核对原字节 |
| J2 | `0xd70` 在 `.text` 只有这 3 处与本对象有关 | **CONFIRMED** —— 全二进制扫 `$0xd70`：另一处在 CRT 的 `parse_integer`，无关 |
| J3 | 没有代码用 `+0xd6c`（旧余量）或旧区 `0xc84`–`0xd64` 以外的偏移 | **CONFIRMED** —— `0xd6c(` 的两处在 `Bullet__*`，别的对象；`0xc84(` 的 5 处在 `ItemManager`，别的对象 |
| J4 | 商店循环上界抬到 255 会崩 | **REFUTED（所以没抬）** —— 第一轮筛选 `owned==0 → is_available==1 → +0x14==0`；NULL 行与全部 NULL 副本（回退到同一行，`is_available` 读的是**回退行的 id 56**）都能过，候选数 ~198 > 栈数组 `[ebp-0xe4]` 的 57 槽。上界保持 56 项（`+0xe50`），与香草等价 |
| J5 | `reset_cards` 清 255 项不越界 | **CONFIRMED** —— `rep stosd` 写 `+0xd70`..`+0x116c` = 新对象末尾 |
| J6 | 旧区 `0xc84`–`0xd64` 留着不用是否有害 | **CONFIRMED 无害** —— 无人再读写；ExpHP 把 `0xc68` 起 32 字节标成 `__thread`，与 `0xc84` 重叠是它的标注误差，不是我们的写入 |
| J7 | DLL 核对 | **CONFIRMED** —— `check_grow` 按运行时 rows 算改后字节逐条比对，任一不符 FAIL 并还原分配器上界 |

**新登记的边界（#34）**：商店候选数组 `[ebp-0xe4]`（`AbilityShop__initialize`）57 槽、
`pick_weighted_random_offer` 的 `0x8c0` 局部缓冲——**同时可进商店的卡 ≤ 57**，是栈帧大小，
战线 E 让新卡进商店池时必须一并处理。

## K. 战线 D —— unlocked_cards 影子数组 + side-car

**没有一个字节手写机器码**：9 处读由生成器改写 ModRM（去 SIB），写入点与两处同步点走 thcrap 断点，
逻辑全在 C（`native/unlocked.c`）。审计重点因此落在「改写留对了寄存器」和「断点语义」上。

| # | claim | 结论 |
| --- | --- | --- |
| K1 | `.text` 里 imm32 == `0x5f588` 恰好 11 处 = 9 读 + 1 写 + 1 `lea` | **CONFIRMED** —— 全 `.text` 扫描；`make check` 现在断言 9 处读且无未解释命中，多一处少一处都停 |
| K2 | ~~9 处读的 SIB **index 就是 id**，改成 `[index+SHADOW]`~~（NEXT.md / PLAN 的表）| **REFUTED（3/9）** —— 见 §K′ |
| K3 | 「最近一条装载」到站点之间没有改写被留下的寄存器 | **CONFIRMED（人工，9 处逐条）** —— 见 §K′；换 build 必须重看 |
| K4 | 改写后指令 = 同 opcode、同 reg 字段、`[留下的寄存器+disp32]`、同 imm8、nop 补位 | **CONFIRMED** —— 9 处新旧字节各喂 GNU objdump（`-b binary -m i386`）反汇编比对：如 `cmp BYTE PTR [esi+eax*1+0x5f588],0x0` → `cmp BYTE PTR [esi+SHADOW],0x0 ; nop` |
| K5 | 没有寄存器落在 ModRM 的 rm=100/101（esp/ebp 需要 SIB / 无 base）| **CONFIRMED** —— 留下的是 edx/esi/ebx/edx/edx/esi/ecx/edi/eax；`decode_disp32_op` 对 rm∈{4,5} 直接报错 |
| K6 | 断点返回 0 = 跳过原指令、从 `addr+5` 继续，且 `+5..+cavesize` 是 nop | **CONFIRMED** —— `breakpoint.cpp`：`asm_buf[0]=CALL_NEAR_REL32`，其后 `memset(…, x86_NOP, cavesize-5)`；`bp_entry.asm`：返回 0 时不改 `[ebp+0x24]`（retaddr），`popa; ret` 回到 `addr+5` |
| K7 | `0x418e04` `mov byte [esi+edi+0x5f588],1` 处 edi = id、esi = 存档 | **CONFIRMED** —— `0x418de8 mov esi,[0x4cf41c]`；`0x418df1 mov edi,ecx`（fastcall 第一参）；同函数 `0x418df6` 的读也是 `[esi+edi]` |
| K8 | id < 57 放行原指令 ⇒ 零售数组照常写、存档格式不变 | **CONFIRMED** —— 原指令在 thcrap sourcecave 里原样执行；存档序列化只读 `+0x5f4b8` 子对象（`FUN_00463b30`），我们从不写它 |
| K9 | id ≥ 57 跳过原指令 ⇒ 不再写 `unlocked_cards[57..]` 之后的未知区 | **CONFIRMED** —— 返回 0；影子数组 256 字节，`id >= 255` 另有守卫 |
| K10 | `0x46398a` 时 ebx = 存档且零售数组已是最终值 | **CONFIRMED** —— `0x463984 mov [0x4cf41c],ebx` 前一条；`FUN_004639b0(_Dst)`（解析主存档）在 `0x463965` 已跑完；断点里再与全局比对，不等则用全局并记日志 |
| K11 | 三个断点站点无相对寻址、落在指令边界 | **CONFIRMED** —— `c6 84 3e 88 f5 05 00 01`（8）、`8d b3 b8 f4 05 00`（6）、`8d 83 88 f5 05 00`（6），Ghidra 反汇编各为一条完整指令；`expected` 由生成器从 exe 现取 |
| K12 | `unlock_all` 只有作弊菜单调 | **CONFIRMED** —— xref 仅 `MainMenu__tick_menu_0b_score_ranking` `0x469259`、`MainMenu__tick_menu_17_achievement` `0x46d869`；断点镜像 `memset(…,1,0x38)` 的范围 = 影子[0..55] |
| K13 | side-car 路径：游戏存档目录缓冲 `0x568c61` 尾带 `\` | **CONFIRMED** —— `Window__sub_4726a0`：`GetEnvironmentVariableA("APPDATA")` + `\ShanghaiAlice` + `\th18` + `\`；WinMain 退出时直接拼 `"th18.cfg"`。DLL 校验 `X:` 或 `\` 开头、尾 `\`，否则退到 exe 目录 |
| K14 | 断点里做文件 I/O 安全 | **CONFIRMED** —— 游戏线程、绝对路径（不受 thcrap 注入期 CWD 影响，H14）；`fopen/fwrite/MoveFileExA` 无 x87；`make dllx87` = 0 |
| K15 | 与其它 patch 撞车 | **CONFIRMED 0 处** —— `make conflicts` 对 base_tsa（70 hackpoint）+ mouse_control + renko |
| K16 | 测试钩子从断点里调 `mark_obtained(id,1)` | **CONFIRMED** —— `__fastcall`（ecx=id, edx=notify），无栈参数，自己 `push ebx/esi/edi`，`ret` 收尾，无浮点；objdump 见 `mov ecx,esi; mov edx,1; call eax`。只在 patch-test 进栈时存在 |
| K17 | 影子[57] 之后 vs 零售 `uint8_t[0x39]` | **CONFIRMED** —— ExpHP `type-structs-own.json`：`0x5f588 unlocked_cards uint8_t[0x39]`，正好 0..56；`init_from_table` 循环 `cmp edx,0x39; jl` 也止于 56 |
| K18 | 没有 DLL 时 D 的 patch 会怎样 | **已知退化** —— 影子全零 ⇒ 所有卡「未获取」。`_255` 本来就要 DLL（B 的兜底也在 DLL），README 明写 |

### K′. K2 / K3 —— 存档指针在 SIB 的哪一格是随机的

`[base+index*1+disp32]` 在语义上对称，编译器把存档指针放 base 还是 index 没有规律。
9 处里 **3 处放在 index**，按 NEXT.md 那张表改会用存档指针去下标影子数组——不崩、全错：

| 站点 | 原 | 前面那条装载 | 存档在 | 该留 | NEXT.md 表里留的 |
| --- | --- | --- | --- | --- | --- |
| `0x4149ec` | `[esi+eax]` | `0x4149e7 mov eax,[0x4cf41c]` | **index** | esi | eax ✗ |
| `0x416e3d` | `[edx+ecx]` | `0x416e37 mov ecx,[0x4cf41c]` | **index** | edx | ecx ✗ |
| `0x417ea3` | `[ecx+eax]` | `0x417e9e mov eax,[0x4cf41c]` | **index** | ecx | eax ✗ |

其余 6 处存档在 base，表是对的。生成器现在从站点前 48 字节内最近一条 `mov r32,[SCOREFILE_PTR]`
决定丢哪个寄存器，对账器独立再算一遍；找不到装载或装载的寄存器不在 base/index 里就拒绝生成。

**K3 的人工核对**（objdump 看每处前 8 条，中间有没有改写被留下的寄存器）：

| 站点 | 留 | 装载与站点之间的指令 | 结论 |
| --- | --- | --- | --- |
| `0x41440b` | edx | `mov [esi],0`；`mov edx,[edx*4+0x4b3600]`（顺序表 → id，正是要留的值）| ✅ |
| `0x4149ec` | esi | 无 | ✅ |
| `0x416590` | ebx | `addss xmm0,xmm1` | ✅ |
| `0x41694e` | edx | `push esi`；`mov esi,ecx` | ✅ |
| `0x416e3d` | edx | 无 | ✅ |
| `0x417125` | esi | `mov ebx,[ebp+0x10]` | ✅ |
| `0x417ea3` | ecx | 无（`mov ecx,[eax+4]` 在装载**之前**，取的就是 id）| ✅ |
| `0x418df6` | edi | `mov ebx,edx`；`push edi`；`mov edi,ecx`；`mov [ebp-4],edi` | ✅ |
| `0x418e15` | eax | 45 字节：`mov ebx,edx` … `xor ecx,ecx`；`mov edx,0x4c53c4`；`mov eax,[edx]`（表行 id）| ✅ |

**REFUTED 的那条（K2）是本战线最值得记的**：NEXT.md 那张「已算好长度」的改写表里三行留错了寄存器。
教训写进 `sites.py`：任何依赖「编译器把什么放在哪一格」的假设都要从上下文重取，不能从指令形态推。

**实跑通过**（2026-09-02，用户报告；见 §0）。

## L. 战线 E 第一块 —— id ≥ 57 的文案重定向

三处 `imul r, id, 0x1c0` 挂断点，把 r 改成「加上基址后落进 DLL 缓冲」的偏移。对象不扩。

| # | claim | 结论 |
| --- | --- | --- |
| L1 | `zAbilityText` 按 id 取文案的读只有这 3 处 | **CONFIRMED** —— `.text` 里 imm32 `0x1c0` 共 37 处，其余是别的对象的 `+0x1c0` 字段（`8b 8f c0 01 00 00` 形态）、`ScoreFile` 的 `0x463708`、CRT；PLAN §2 E 同结论。写入点 `0x41623d`（文案文件解析器）只写零售 id，不动 |
| L2 | 三处 imul 后紧跟 `add r, 基址`，中间无人读 flags | **CONFIRMED** —— `0x41669a add ecx,edi`；`0x416780 add edi,0x40 … 0x416797 add edi,eax`（中间是 mov/movss）；`0x419270 add eax,[0x4cf29c]` |
| L3 | 三处的基址都是 `ABILITY_TXT_PTR` 那个对象 | **CONFIRMED** —— `0x41655d mov edi,[0x4cf29c]`（FUN_00416540 全程不改 edi 直到 `0x416780`）；`0x419270` 直接读全局。所以 `ext - [0x4cf29c]` 这个相对偏移对三处都对 |
| L4 | `0x416779` 时 `[ebp+0xc]` 是 id | **CONFIRMED** —— 序言 `push ebp; mov ebp,esp; and esp,-8`，`ret 0x10` 四个栈参，`0x416550 mov ebx,[ebp+0xc]` 同一个值；此时 ebx 已被 `0x4166b8` 改写，所以不能用 ebx |
| L5 | 零售 57 张 = `0x63c0`，第 57 张的位置就是尾部字段 | **CONFIRMED** —— `0x4165ae mov eax,[edi+0x63c0]`、`0x41676b lea esi,[edi+0x63c4]`；57 × 0x1c0 = 0x63c0。阈值取 57：id 57（BACK）也重定向，零售从不为它渲染文案，无观察差异 |
| L6 | 名字被当作格式串 | **CONFIRMED** —— `FUN_004873f0` 先 `FUN_00404e40(param_7, …)`（vsprintf 类）再渲染；占位文案不含 `%` |
| L7 | UTF-8 能显示 | **CONFIRMED（源码）** —— win32_utf8 `MultiByteToWideCharU`：先 `CP_UTF8 + MB_ERR_INVALID_CHARS`，失败退 `fallback_codepage`；base_tsa 是依赖，textdisp 一定在。字宽算式用 `strlen`，3 字节/字比 Shift-JIS 多，字会略挤——外观问题，不是安全问题 |
| L8 | 断点里 `GetModuleHandleA` / 读全局 | **CONFIRMED** —— 无 x87、无 thcrap API；`make dllx87` = 0 |

**实跑通过**（2026-09-02，用户报告；见 §0）。

## M. 战线 E 第二块 —— 图鉴 / 编成（顺序表搬迁 + `zAbilityMenu` 扩容 + 条目数）

| # | claim | 结论 |
| --- | --- | --- |
| M1 | 顺序表 `0x4b3600` 的引用 = 6 处 + 尾界 1 处 | **CONFIRMED** —— 见 §M′ |
| M2 | 图鉴条目数的 7 处 `0x38` 都是「条目数」语义 | **CONFIRMED** —— 见 §M′ |
| M3 | ~~PLAN：8 处 `0x38 → 0xff`~~ | **REFUTED** —— 两处 `cmp r,imm8` 符号扩展，`0xff` = −1 → `jl` 永不成立；且图鉴只该列已注册的新卡。见 §M′ |
| M4 | 另两处 `cmp [eax+4],0x38`（`0x415070` `0x415e63`）不是条目数 | **CONFIRMED** —— `eax` 来自 `+0xfec` 卡指针数组，`[eax+4]` = `card->id`，比较的是「是不是空槽 56」。不动 |
| M5 | `0x41495c mov edi,0x38` 是编成前清理 anm id 数组的循环上界 | **CONFIRMED** —— 清 `[esi-0x400]`/`[esi]`（`+0x7ec`/`+0xbec`）各 56 项；数组本来就是 `[0x100]`（ExpHP 结构体）；抬到 255 只多清 199 个本来就是 0 的槽（`0x488cf0` 对 id 0 无事）|
| M6 | `__card_ids` 的访问 = 14 直接 + 2 游标相对 | **CONFIRMED** —— 见 §M′ |
| M7 | `zAbilityMenu` 大小 `0x13fc` 只有 3 处 | **CONFIRMED** —— operator new `0x413817`、memset `0x413831`、sized delete `0x413abb`（`call 0x48dca1`）；全 `.text` 的 `0x13fc` 只有这 3 处。新大小 `0x17f8`，`__card_ids` 搬到 `+0x13fc`（255 项）|
| M8 | 顺序表填充值 57（BACK）在两个菜单里都不可见 | **CONFIRMED** —— 编成循环先查 `+0x20`（`0x4149de cmp [eax],0`），BACK 行 `+0x20 = 0` → 跳过；图鉴按条目数 56+N 走，填充在 NULL(56) 之后走不到 |
| M9 | 图鉴条目非 7 的倍数（56+N）时最后一行能到 | **CONFIRMED（实跑，2026-09-02）** —— 57 条目，图鉴里第 57 项「测试卡牌 58」可达可选；编成里也能选进卡组。翻页代码 `sub_415b70` 对非整行无特殊处理 |
| M10 | 门里写代码段的时机 | **CONFIRMED** —— `ce_gate` 在 `ScoreFile__load` 入口，主菜单 / 任何 `zAbilityMenu` 都还没创建；`VirtualProtect` 与 `restore_alloc_bound` 同一做法；写之前核对该处仍是 `0x38` |
| M11 | 新增 27 处 binhack 全同长、只换常量 | **CONFIRMED** —— `make verify`；新旧字节各喂 objdump 逐条比对（`push 0x13fc→0x17f8`、`[edi+eax*4+0x304]→[…+0x13fc]`、`[esi-0x4e8]→[esi+0xc10]`、顺序表 6 处 `[r*4+T]→[r*4+cave]`、尾界 `cmp eax,T_END→cave+0x3fc`）|


### M′. M1 / M2 / M3 / M6 的证据

**M1 顺序表引用**：全 `.text` 扫 `[0x4b3600, 0x4b36e4]` 的 imm32，命中 8 处：
`0x414401` `0x4145f8` `0x414639` `0x41499f` `0x415681` `0x4156b6`（引用）、`0x414b54`（尾界）、
**`0x4337f7 mov eax,[eax*4+0x4b36e4]`——紧邻的另一张表的基址，值相同，显式排除**；生成器要求它必须被扫到且不改。

**M2 七处 `0x38` 的语义**：

| 站点 | 指令 | 语义 |
| --- | --- | --- |
| `0x4137bb` | `mov [this+0x1c4],0x38` | initialize：MenuSelect 项数 |
| `0x414394` / `0x41439e` | `mov [this+0x300],0x38` / `[this+0x1c4]` | 图鉴 fill：当前项数 |
| `0x4145e2` | `cmp eax,0x38`（imm8） | 图鉴 fill 循环上界 |
| `0x41570d` | `mov eax,0x38; idiv [0x5704bc]` | 行数 = 条目数 ÷ 列数（图鉴 7 列 / 编成 10 列） |
| `0x4157cb` | `cmp edx,0x38`（imm8） | 高亮循环上界 |
| `0x415817` | `mov edi,0x38` | 退出时遍历 vm 数组 |

后三处在 `0x415660..` 的图鉴分支里（用顺序表 + `+0x1bc` 直接取 id，不经 `__card_ids`）。

**M3 为什么不是 `0xff`**：两处 imm8 符号扩展；且条目数 = 56 + 已注册新卡数，不是 255（否则图鉴列出 198 个 NULL 副本）。
改为 DLL 在门里现写 7 处，上限 127。

**M6 `__card_ids` 访问点**：AbilityMenu 全部函数（`0x413470..0x4160b0`）objdump 过滤位移 ∈ [0x304,0x3e4) 与负位移：
直接 `+0x304` 14 处；`0x4145d2 [esi-0x4e8]`（esi 走 `+0x7ec`）、`0x414b3f [eax-0x8e8]`（eax 走 `+0xbec`）→
改成 `+0xc10` / `+0x810`，`0x7ec+0xc10 = 0xbec+0x810 = 0x13fc`。全二进制 `+0x304` 的其它 6 处在
`0x405e21..0x406349`（另一类对象）与 CRT `0x491b26`，不是菜单。

**实跑通过**（2026-09-02，用户报告；见 §0）。

## N. 战线 E 第 7 段（商店）+ 第 10 段（JSON 装载器）

商店三处循环上界从 56 抬到 rows；幻影 id（查表回落到 NULL 行 56）与 BACK（57）靠 cave 里这两行的
`+0x14`（权重）改成 6 排除：随机池要 `≠0 && ≠6`、保证 loop1 要 `==0`、loop2 要 `is_available==2`（dmode 1–5）。
**没有新的机器码 / 断点**；成立的前提是 `+0x14` 除商店外无人读——N1。

| # | claim | 结论 |
| --- | --- | --- |
| N1 | 表行 `+0x14` 只被商店读 | **CONFIRMED** —— 三路穷举，见下「N1 证据」 |
| N2 | 随机池缓冲 = 560 个 dword，无越界检查 | **CONFIRMED** —— 见下「N2 证据」 |

**N1 证据**（`+0x14` 的读者）：

- (a) 25 个内联查表实例（`sites.py list`，锚点扫描是全集）里返回 `+0x14` 的只有 `0x417085` `0x4170b4`
  （`pick_weighted_random_offer`）与 `0x4174c5`（`AbilityShop__initialize` loop1）。
- (b) `TableCardData__get` `0x407d70` 的 6 个调用者（`get_xrefs_to`）：`0x4170f9 mov ebx,[edx+0x14]` 是同一商店函数的压入份数；
  `allocate_new_card` 把指针存进 `card+0x4c`，函数内 57 处 `[esi+0x14]` 全是卡**对象**的字段清零；
  `FUN_00419170`（获得通知）只读 `+0x2c`；`AbilityMenu__on_tick` 三处只读 `+0x0c` / 传给绘制，
  其两处 `[ecx+0x14]` 的 ecx 来自全局 `0x4cf298`，不是表行。
- (c) 全二进制 2333 个函数反汇编扫 `mov r,[r+0x4c]` 后 10 条内 `[r+0x14]`（`card->entry->weight` 形态）：0 命中。

**N2 证据**：`0x416f53 sub esp,0x8d4`；`0x416f6e push 0x8c0` memset 清 `[ebp-0x8c4]`；压入用 `rep stosd`
（`0x41710d`，eax = 表行指针，ecx = 权重）与 `mov [ebp+edi*4-0x8c4],edx`（`0x41712f`，从没拿过再压），
计数在 `[ebp-0x8c8]`；循环里没有与 `0x8c0` 的比较。`0x8c0/4` = **560**，装载器按 `Σ(weight+5)` 保守核对。

**装载器（`cards.c`）**：

| # | claim | 结论 |
| --- | --- | --- |
| N3 | 装载器只写数据 codecave，不写代码段 | **CONFIRMED** —— 写入点：cave 第 `id` 行（`id ∈ [58, rows)`，rows 从 patch 反推）与 DLL 自己的 `s_ext` 文案缓冲；56 / 57 行 `+0x14 := 6` 在 `fill_table`（紧跟拷表，**任何后续 FAIL 都不影响它**，否则上界已是 255 的商店会被幻影灌爆）。代码段立即数仍只有 `menu.c` 写 |
| N4 | `internal_name` 指针不会把 `ability.txt` 的解析器引到新 id | **CONFIRMED（修过）** —— 见下「N4 证据」 |
| N5 | 把零售 NULL / BACK 行的 `+0x14` 从 0 改成 6 只影响商店 | **CONFIRMED** —— N1 穷举；商店里 NULL 零售本就到不了（上界 56），BACK 同 |
| N6 | 商店上界 = rows 后每次开店多扫 199 个 id | **CONFIRMED 可忽略** —— 每个 id 一次线性查表（255 行）× 3 循环，只在 `AbilityShop__initialize` 跑一次 |
| N7 | jansson `json_t` 布局假设失效时不会误读 | **CONFIRMED** —— 只读 `->type`；根的 `type != 0`（OBJECT）直接 FAIL；每个字段再各查一次类型，类型不符 FAIL |
| N8 | 全有或全无 | **CONFIRMED** —— 任一张卡出错就 `s_count = 0`、返回 0 → `restore_alloc_bound`；但**已写进 cave 的行留着**（幻影：`+0x04` 是新 id 但分配器上界已回 56，谁也分配不到；图鉴按注册表 0 张不显示）|

**N4 证据**：`AbilityText__parse_ability_txt` `0x4160b0` 对每个 `@NAME` token 扫全表（`0x41612f` 起，尾界已是 cave+255 行）
逐字节比对 `row+0x00` 指向的串（`0x416140..0x41615a`），命中则 `ebx = &row->id`（`0x41617c`），随后按
`txt + (id*7+line)*0x40` 写 7 行（`0x41622f..0x41624f`）。id ≥ 57 落在 `zAbilityText`（`0x63e0`）之外。
修法：DLL 存的名字带 `'\n'` 前缀（`cards.c`），token 由行解析而来不可能含换行 → 永不命中。
零售 NULL 副本行的 `+0x00` 仍指零售 "NULL"，扫描先命中第 56 行，副本永不被选中。

## O. 行为 SDK（第 9 段）—— 断点换虚表 + `__thiscall` 桩

设计见 [`SDK.md`](SDK.md)。**没有手写机器码**：两个断点 + 编译器生成的 `thiscall` 桩；对象由游戏分配 / 释放。

| # | claim | 结论 |
| --- | --- | --- |
| O1 | `0x412cec` 处 esi = 卡对象、ebx = id；断点 cavesize 6 盖住的两条指令无相对寻址 | **CONFIRMED** —— 见下「O1 证据」 |
| O2 | 换完虚表后 ctor 槽仍会被按零售语义调用 | **CONFIRMED** —— ctor 调用在 `0x412d11`，晚于 `0x412cec`；`mode&1` 判定（`0x412cf9..0x412d0b`）与 dtor（`0x412d35`）不动 |
| O3 | 基类 21 槽的签名 = `ret N`；桩的 ABI 与之一致 | **CONFIRMED** —— 见下「O3 证据」 |
| O4 | 桩不用的槽透传基类实现是安全的 | **CONFIRMED** —— +0x08/+0x38/+0x3c/+0x40 直接填基类地址；门里 `ce_sdk_setup` 把 `0x4b4c78` 的 0/2/14/15/16/20 槽与 `engine.h` 常量比对，不符 FAIL（布局守卫）|
| O5 | +0x50 桩的尾跳 | **CONFIRMED** —— `ce_state_free(this)` 后 `jmp 0x411410`，ecx 重新装 this，栈上的 flag 参数原样留给基类的 `ret 4`（objdump：`mov ecx,esi; pop esi; jmp eax`）|
| O6 | 私有状态不会泄漏 | **CONFIRMED** —— 所有销毁路径都走 +0x50 槽（`reset_cards` / `recount` / 即时卡当场删 `0x412d1d`），SDK 在那释放；256 槽 = 一局卡数上限（`0x411469`）|
| O7 | 移速倍率在 `on_tick_2` 里写才生效 | **CONFIRMED** —— 见下「O7 证据」 |
| O8 | `player+0x47774` 是复活无敌计时器，`{0x117,0x118}` 只在刚置好那一帧出现 | **CONFIRMED（推断链）** —— 见下「O8 证据」，实跑看 A♠ |
| O9 | `bullet+0x9c` 在 +0x28 槽被调时已是最终基础伤害 | **CONFIRMED** —— `PlayerBullet__create` `0x45e396` 写、`0x45e7f5` 调槽、`0x45e837` 取用；`CardMomoyo__on_bullet_init` `0x411083` 同一字段覆写 |
| O10 | `0x446cf6` 处 esi = 道具身价且改它同时影响弹窗与计分 | **CONFIRMED** —— `0x446cf3 cmovle esi,eax`（钳 ≥10）之后；`0x446cfc push esi` 给弹窗 `0x4645f0`，`0x446d0d mul esi` → `SCORE += esi/10`；`lea eax,[edi+0xc2c]` 6 字节不含相对寻址 |
| O11 | 测试卡组断点复刻原 movzx 语义 | **CONFIRMED** —— 原指令 `movzx eax, byte [eax+esi+0x5f608]`；断点读同一字节，写 eax，返回 0 跳过；不设 flags（原指令也不设，后随 `push eax; call`）；esi 是槽序号（循环 `0x407ed4..0x407f05` 里 `inc esi`），esi==0 时游标归零 |
| O12 | 事件断点里遍历卡链表安全 | **CONFIRMED** —— 表头 `mgr+0x18`、首结点 `[mgr+0x1c]`、结点 `{card,next,prev}`（`0x412e90` / `0x408690`）；`AbilityManager__on_tick` 用同一走法；加 256 步护栏 |
| O13 | 对账方向 | **CONFIRMED** —— C 有行为 JSON 无 → FAIL（有行为却不可见是 bug）；JSON 有 C 无 → 允许（开发期正常，日志计数）|
| O14 | `0x446d28` 处加钱与零售路径一致 | **CONFIRMED** —— 见下「O14 证据」 |
| O15 | 10♠ 不引入 replay 失同步 | **CONFIRMED** —— 用私有状态计数（每第 10 个），不用任何 RNG；replay 重放同样的拾取序列得到同样的加钱 |
| O16 | `sdk.h` 四个引擎调用的约定 | **CONFIRMED** —— 见下「O16 证据」 |
| O17 | 在 ctor 里再调 `allocate_new_card` 是安全的（强欲之壶）| **CONFIRMED** —— 见下「O17 证据」 |
| O18 | 壶不会抽到自己 / 无限递归 | **CONFIRMED** —— 排除表里放自己的表行（`pick` 按 `entry->id` 排除，`0x4170e6`）；再加静态深度护栏（嵌套 > 0 直接返回 1）；随机走商店自己的 `pick`，RNG 与商店同源 |

**O1 证据**：尾段 `0x412cec mov [esi+4],ebx`（`89 5e 04`）紧接 `0x412cef mov eax,[edi+0x28]`（`8b 47 28`），都无相对寻址。
ebx 自 `0x411479 cmp ebx,0x38` 起就是 id；esi 自各 case 的 `mov esi,eax`（`new` 的返回）起是对象；
`0x412ce4 test esi,esi; jz` 在前，断点里再判 esi≠0。

**O3 证据**：读 `0x4b4c78` 的 21 个指针逐个反汇编，带栈参的只有 +0x0c(`ret 4`)、+0x1c(`ret 8`)、+0x28(`ret 4`)、
+0x30(`ret 8`)、+0x44(`ret 4`)，其余裸 `ret`。桩用 `__attribute__((thiscall))`，objdump 确认 this 在 ecx、
一参桩 `ret 4`、二参 `ret 8`（checklist 的 ABI 项）。

**O7 证据**：`player+0x477ec` 由移动函数 `0x45b5b6` 读、Player tick 末尾 `0x45c702` 复位 1.0。UpdateFunc 优先级
AbilityManager 0x16 < Player 0x17（注册点 `0x40847f` / `0x45a8b4`，同一注册函数 `0x401180`）→ 管理器 tick 里的写
在同一帧被移动读到；`on_tick`（+0x24，`0x45c0e5`）在复位之前，白写。BombMarisa（0x19）写 0.5 是同一字段。

**O8 证据**：写入者穷举（全二进制扫 `0x47774/78/7c`）：复活 `0x45c35e`（280）、决死救回两处（60）、四个角色炸弹
（40 / 120 / 110 …）、ECL `515 setInvuln`；zTimer `{prev,cur,float}` 布局与 `CardAya__on_tick` 的读写一致。
置值时 prev = cur−1，之后每帧 prev = 上一帧 cur，(280, 279) 不会再现。

**O14 证据**：`collect_money_item` 尾部依次 `0x446d22 inc [0x4ccd20]`（道具计数）、`0x446d28 inc [MONEY_TOTAL]`、
`0x446d2e inc [MONEY]`、`0x446d34 mov [SCORE],eax`。断点盖 `0x446d28` 一条（6 字节，无相对寻址），在它之前把
`MONEY` / `MONEY_TOTAL` 各 += bonus，原两条 `inc` 照常，两个全局始终同步（帝的回填与「累计收集」统计不受影响）；不碰 eax（分数）。

**O16 证据**：`allocate_new_card` `0x411460`：ecx = mgr（`0x4185c1 mov ecx,[0x4cf298]`），`push 2; push id`，尾 `ret 8` → thiscall 两栈参。
`mark_obtained` `0x418de0`：`mov ecx,id; xor edx,edx; call`，尾裸 `ret` → fastcall 无栈参。`TableCardData__get` `0x407d70`：
`cmp [eax],ecx` 用 ecx 当 id，裸 `ret` → fastcall。`pick_weighted_random_offer` `0x416f50`：调用点 `mov ecx,eax(out); mov edx,0xa; push 0; push eax(excl); push 0xe`，
尾 `ret 0xc` → fastcall(ecx, edx) + 三栈参（hi, exclude, n），返回 eax 非 0 = 抽到。`pot.o` 的 objdump：ecx/edx 装法与压栈顺序逐条对上，
调用后无 `add esp`（被调方清栈）。

**O17 证据**：外层分配在 `0x412d11` 调 ctor 时，只写过卡对象自己的字段（`+0x04/+0x08/+0x50`），还没动 `mgr`（计数 `+0x28`、链表 `+0x18`、`owned[]`）。
内层 `allocate_new_card(mode 2)` 完整走一遍尾段（入链、计数、HUD 重建）。回到外层：ctor 返回非 0 → `0x412d17` 删自己 → `0x412d20 mov eax,[edi+0x28]` 取**当前**计数返回；
edi/esi 由我们的 thiscall 桩按 ABI 保住。外层不再使用任何在 ctor 之前读取的 mgr 状态。零售的 `CardNazrin__constructor` 也在 ctor 里改全局（`MONEY`），只是没重入分配器。

**未实跑。** 各卡的验收在 [`NEXT.md`](NEXT.md) §1。

## G. OPEN —— 还没解决的

| # | 事项 | 说明 |
| --- | --- | --- |
| G1 | ~~游戏内未实跑~~ | **三步实跑通过**，见 §0 |
| G2 | ~~全有或全无的门还没做~~ **已做**（2026-09-02） | 见 §H。触发原因是用户复审指出的一种「日志一切正常」的静默失败 |
| G3 | 扩容还要动的东西 | B（§I）、C（§J，manager 部分）、D（§K）已做；`zAbilityMenu` 的 `__card_ids` 扩容与顺序表耦合，归 E；E 未做 |
| G5 | ~~新卡在卡组编成里「未获取」~~ | 战线 D 已做（§K，待实跑）。原因是 `unlocked_cards` 是 `uint8_t[57]`，`[58]` 落在未知区读出 0 |
| G6 | ~~新卡解锁后名字 / 说明是乱码~~ | **已做**（§L，待实跑）——三处读重定向到 DLL 缓冲，占位「测试卡牌 N」。原因：`zAbilityText` 只有 57 张，id 58 落在对象之外 |
| G4 | MSVC 换 build 后骨架是否仍然一致 | 未验证。`make check` 的锚点数会立刻暴露（不是 25 就停） |
