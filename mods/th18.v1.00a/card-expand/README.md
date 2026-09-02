# card-expand —— TH18 卡表搬迁 / 扩容的基础设施

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。

把 `zTableCardData[]` 从 `.data` 搬进 codecave，为「加新卡」腾出行数。
方案全貌见 [`../card-rework/PLAN-255-ids.md`](../card-rework/PLAN-255-ids.md)，
边界依据见 [`engine/card/th18/11-sentinels-56-57.md`](../../../engine/card/th18/11-sentinels-56-57.md)。

**做到哪了**（下一步交接见 [`NEXT.md`](NEXT.md)）：

| 步 | 内容 | 状态 |
| --- | --- | --- |
| 1 | 只搬表，58 行，行为零变化（`make step1`） | ✅ **实跑通过**（2026-09-02）|
| 2 | 255 行，仍零变化 | ✅ **实跑通过** |
| 3 / 战线 B | 分配器搬迁 + 验证钩子（`make step3`） | ✅ **实跑通过**：`allocate_new_card(id=58)` 真的发到手上 |
| C | `zAbilityManager` 扩容，`owned[]` 255 项（并入 `_255`）| 静态审计通过，**待实跑** |
| D / E | 影子存档 / 图鉴文案图 | 未做。新卡目前「未获取」是 D 的事 |

第 1 步的价值不在功能，而在用「和香草没差别」这个最容易判定的标准，
一次性验证 100 处搬迁 + 生成器 + 对账器 + 开机自检。

## 这里没有手写的 patch

`patch/th18.v1.00a.js` 是 **`native/sites.py` 从真 exe 生成的**，不要手改。

```bash
cd native
make check          # 扫描 + 校验两条不变式
make list           # 25 个查表实例的全表
make gen            # 生成 patch（ROWS=58；ROWS=255 出扩容版）
make verify         # 把生成好的 patch 拿回真 exe 逐条对账
make files          # 刷新 files.js 的 crc32
```

理由：100 处 `expected` 手写等于必然出错，而 thcrap 对 `expected` 不匹配的处理是
**记一行日志然后跳过**（`binhack.cpp:1420`）——对整表搬迁来说，部分应用就是灾难。

死绑量（表基址 / stride / 行数 / 回退行 / RVA）与换 build 要重取的清单在 [`TARGET.md`](TARGET.md)；
对抗审计与实跑记录在 [`AUDIT.md`](AUDIT.md)。

## 三个文件各干什么

| 文件 | 角色 |
| --- | --- |
| `native/shape.py` | **权威站点来源**。整体匹配内联查表的骨架，每次命中自带「四条臂配套」的保证 |
| `native/x86imm.py` | **完整性审计**。扫出所有撞上这些值的地方，凡不在骨架里的都列出来人工过目 |
| `native/sites.py` | 串起来 + 两条不变式校验 + 生成 patch + 对账 |

### 为什么不是「找到 4 字节值就改」

因为那件事**天然有歧义**：`0x4c5f8c` 既是卡表的尾界立即数（`cmp eax, 0x4c5f8c`），
又是一个被 9 个函数读写的**热全局**的地址（`mov eax, [0x4c5f8c]`）。
更糟的是 `83 3D <K> 00`（`cmp dword [K], 0`）的第二个字节 `3D` 自己就是
`cmp eax, imm32` 的 opcode——两种读法都「自洽」。

**第一版就是这么写的，结果把 39 个 END 当成 25 个。**
改成匹配整段骨架之后，锚点（`add r32,0x34` 紧跟 `inc r32`）在整个 `.text` 里
**正好 25 处**，与 25 个内联点一一对应，没有歧义可言。

## 两条不变式 —— 安全性全压在这上面

`make check` 对 25 个实例逐个验：

1. **`END - 表尾 == LOOP_START - 表基`** —— 循环比较的字段和终止条件必须是同一个。
2. **`FALLBACK - 回退行 == HIT_ARM - 表基`** —— 两条臂必须取同一个字段。

★ 违反 ② 正是整表搬迁**唯一会静默算错**的失败模式：LOOP_START 指了新表、
HIT_ARM 还指旧表时，`下标 * 0x34 + 旧基址` 会返回**另一张卡的行**——不崩、不报错。
所以必须按实例校验，不能按站点。

## 「干净」的四个具体做法

**① 仓库不留一个版权字节。** 新表的内容不写进 patch（那是 ZUN 的数据），
改成开机时从**用户自己那份 exe** 里 `memcpy` 过来。patch 里只有地址、原字节和源码。

**② 原表不删不覆盖。** 新表是拷贝。任何漏改的站点仍然看到一张合法的（只是旧的）表，
失败模式从「内存腐败」降级为「新卡不出现」。第 1 步行数不变，两张表内容逐字节相同，
**连漏改都不会有可观察的后果**——这正是它适合当第一步的原因。

**③ 生成器与对账器分开。** `gen` 产出，`verify` 把产物拿回真 exe 重新核对
（`expected` == exe 字节、`code` 与 `expected` 等长、只换常量不换 opcode）。
只信生成器等于没查。

**④ 完整性审计留档。** `make check` 会列出所有撞上这些值但不在骨架里的位置
（当前 15 处，全部是那两个热全局），让人确认「漏掉的都是该漏的」。
`CardCollection__mark_obtained_and_notify` 的表遍历就是被这条路径捞回来的——
它按计数收尾（`cmp ecx, 0x38`）而不是按地址，骨架不同，差点漏掉。

## 战线 B —— 分配器（`make step3`）

让 `allocate_new_card(id ≥ 57)` 合法地产出一张卡。**没有手写一个字节的构造器**：

| 改什么 | 怎么改 |
| --- | --- |
| 跳转表 `0x412dac`（57 项） | 搬进 codecave `th18_card_jumptable`（255 项）：0–56 原样拷，**57–254 全指向 case 56 的函数体 `0x411489`** |
| `0x411479` `cmp ebx, 0x38` | → `cmp ebx, 0xfe`（3 字节，同长）|
| `0x411482` `jmp [0x412dac+ebx*4]` | → `jmp [新表+ebx*4]`（7 字节，同长）|

为什么指向 case 56 就够：它的函数体做 `new(0x54)` → memset → 挂基类虚表 `0x4b4c78`
（22 槽全是 `xor eax,eax; ret` 之类的空函数，无空槽）→ `jmp 0x412cd5`；
公共尾段再把 **`card->id` 写成 `ebx` 里的真实 id**（`0x412cec`）。
于是任何未注册的 id 都得到一张挂着**自己的 id**的无行为卡——「克隆现有卡」最干净的形式，
而 [`AUDIT.md`](AUDIT.md) §A 里那条 `0x412cd5` 的栈契约根本不用碰，因为我们复用的是原装的 case。

## 战线 C —— `zAbilityManager` 扩容（并入 `_255`）

12 处，全部同长：3 处 `push 0xd70`（`operator_new` / 它的 memset / sized delete）→ `0x116c`；
`owned[]` 从 `+0xc84` 搬到 `+0xd70`（`reset_cards` 的 `lea` + `rep stosd` 项数 56→255、
`allocate_new_card` 尾段的 `owned[id]=1`、商店三处循环起点）。

★ **商店三处循环的上界只跟到 56**（`+0xe50`），不跟到 255。原因是筛选链：
第一轮要的是 `owned==0` → `is_available_at_stage==1` → **`+0x14==0`**（固定商品），
而 NULL 行 `+0x14=0`、`unlocked[56]=1`——**它能过**；id 58–254 查表落到回退行（也是 NULL）→ 全过
→ 约 198 个候选写进 57 槽的栈数组 `[ebp-0xe4]`。所以新卡进商店池不是把上界抬高就行，
要在 E 里加「查表命中才算」（`entry->id == esi`）的 codecave 筛选，那不是同长改写。

DLL 的 `check_grow` 按运行时 rows 现算这 12 处的改后字节逐一核对。

### 验证钩子 `patch-test/`（只在测试时进栈）

| 钩子 | 干什么 |
| --- | --- |
| `0x407ee3` binhack → `th18_ce_test_deck58` | `reset_cards` 读初始卡组时，**空槽(56) 改发 id 58**。不写存档、不改文件 |
| `0x411469` 断点 → `BP_ce_trace_alloc` | 每次 `allocate_new_card(id, mode)` 记进日志 |

**流程**：`make step3` → `patch/` 进栈（DLL 不用换），再把 `patch-test/` 叠在上面 →
卡组编成里把**第一格清空**（选那个空白项）→ 开一局。日志里应出现：

```
jumptable: 255 entries at 0x… (57 retail + 198 -> case56 @ 0x00411489); allocator bound = 254
OK: table filled (255 rows @ 0x…), allocator relocated, 100/100 sites verified
trace: allocate_new_card(id=58, mode=1)  <- NEW ID
```

第三行是定论：香草会在这里分配 id 56 然后被 `FUN_00407f10` 按 `id==56` 摘掉；
我们的 58 不会被摘，会以 NULL 的图标留在卡列表里（sprite 116 长什么样还没看过）。

战线 C 并入 `_255` 后 59–254 都合法（`owned[]` 已扩到 255 项）。

## 发布 —— 一条命令，Windows 只负责拉

renkolab 是**开发仓库**，[`Renko6626/th18_modkit`](https://github.com/Renko6626/th18_modkit)
是**发布仓库**（自带 thcrap 2024-11-06 + 勾选式启动器，朋友 clone 下来放好 exe 就能一键启动）。
它的克隆在 `local/vendor/th18_modkit`。

```bash
cd native
make release          # 构建 dist（DLL 可复现,无时间戳）→ 同步进 modkit → 在那边提交
make release PUSH=1   # 再 push
```

`release.py` 只覆盖**生成物**（三个 patch 的 `th18.v1.00a.js`、`files.js`、DLL）；
`patch.js`、侧车 `.json`、README 是 modkit 里手工维护的文案，**不碰**。
发布仓库不干净或落后于远端时它会拒绝/先快进。幂等：没变化就不提交。

modkit 里的对应关系：

| renkolab `dist/` | modkit |
| --- | --- |
| `patch-step1/` | `thcrap/repos/Renko_1055/th18_card_expand/` |
| `patch-step3/` | `thcrap/repos/Renko_1055/th18_card_expand_255/` |
| `patch-test/`  | `thcrap/repos/Renko_1055/th18_card_expand_test/` |
| `bin/th18_card_expand.dll` | `mods/th18_card_expand.dll` |

启动器里：**步骤 1 与步骤 3 二选一，DLL 必勾**；`_test` 只在验证战线 B 时叠上。
两个 patch 同时勾了也不会崩——DLL 会检出来、把分配器上界还原回零售值并记 `mitigation:`。

## 装法（不用 modkit 时）

| 放哪 | 什么 |
| --- | --- |
| patch 栈里加上 `patch/` 这个目录 | codecave 声明 + 100 条 binhack |

不需要 DLL。本地测试见 [`../../thcrap-platform.md`](../../thcrap-platform.md) §6.2。

## 日志

DLL 写**自己的**日志：`<游戏 exe 所在目录>/th18_card_expand.log`（写不了退到 `%TEMP%`），
每次启动新开一份，第一行是时间戳。路径从 `GetModuleFileNameA(NULL)` 拼**绝对**路径——
⚠️ 不能用相对路径：thcrap 注入时先 `SetCurrentDirectory(thcrap/bin)`，跑完整个 init
（含 `plugin_init` 与 `post_init`）才恢复 CWD（`inject.cpp:355-390`），
相对路径会把日志写进 `thcrap/bin/`。第一版就是这么丢的。thcrap 自己的日志里只镜像
**结论那一行**（`[th18_card_expand] OK/FAIL …`），不刷屏。

## 怎么算通过（第 1 步）

`th18_card_expand.log` 末尾（或 thcrap 日志里）找这一行：

```
OK: table filled (58 rows @ 0x…), 100/100 sites verified
```

**没有这一行就是没通过**，不管前面的 binhack 日志多整齐。可能的红字：

| 日志 | 意思 |
| --- | --- |
| `FAIL: func_get unavailable` | thcrap 太老，拿不到 codecave 地址；表**没填** |
| `FAIL: codecave:th18_card_table not found` | patch 没进栈，只放了 DLL |
| `FAIL: table sanity …` | 零售表地址错了（换 build？）|
| `FAIL: N/100 sites verified … partial application, DO NOT PLAY` | 有 binhack 没打上（`expected` 不匹配被跳过），第一处的实际字节已打出来 |

然后进游戏，**商店、图鉴、卡组编成、局内用卡全部与香草无差别**。

任何一处表现异常都说明搬迁不完整——这一步的全部意义就是让「不完整」变得可观测。

## 目录

```
card-expand/
├── README.md          # 你在这
├── NEXT.md            # ★ 下一个会话从这里开始（战线 D）
├── TARGET.md          # ★ 死绑登记
├── AUDIT.md           # 对抗审计
├── native/
│   ├── shape.py       ★ 查表骨架匹配器(权威站点来源)
│   ├── x86imm.py      x86 常量定位器(完整性审计用)
│   ├── sites.py       ★ 扫描 / 校验 / 生成 / 对账
│   ├── mkfiles.py     刷新 files.js
│   ├── sites_gen.h    生成物:DLL 用的站点表
│   ├── card_expand.h  DLL 内部共用声明
│   ├── dll_main.c     入口 / 日志 / thcrap API / 自检①(零售表签名)
│   ├── selfcheck.c    ★ 自检②:post_init 填表(+跳转表) + 回读站点
│   ├── bp_trace.c     测试断点:记录 allocate_new_card(id, mode)
│   ├── thcrap_bp.h    断点 ABI(与 mouse-control 同一份)
│   ├── th18_card_expand.def
│   └── Makefile
├── patch/
│   ├── patch.js
│   ├── files.js
│   └── th18.v1.00a.js  ★ 生成物,不要手改(仓库里是 ROWS=58)
└── patch-test/         只在验证战线 B 时叠上
    ├── patch.js        依赖 th18_card_expand
    ├── files.js
    └── th18.v1.00a.js  ★ 生成物:空槽→58 + 分配追踪断点
```
