# card-expand —— TH18 卡表搬迁 / 扩容的基础设施

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。

把 `zTableCardData[]` 从 `.data` 搬进 codecave，为「加新卡」腾出行数。
方案全貌见 [`../card-rework/PLAN-255-ids.md`](../card-rework/PLAN-255-ids.md)，
边界依据见 [`engine/card/th18/11-sentinels-56-57.md`](../../../engine/card/th18/11-sentinels-56-57.md)。

**当前只做到第 1 步：行数仍是 58，行为应当零变化。** 这一步的价值不在功能，
而在用「和香草没差别」这个最容易判定的标准，一次性验证 100 处搬迁 + 生成器 + 对账器。

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

## 装法

| 放哪 | 什么 |
| --- | --- |
| patch 栈里加上 `patch/` 这个目录 | codecave 声明 + 100 条 binhack |

不需要 DLL。本地测试见 [`../../thcrap-platform.md`](../../thcrap-platform.md) §6.2。

## 怎么算通过（第 1 步）

thcrap 日志里找这一行：

```
[th18_card_expand] OK: table filled (58 rows @ 0x…), 100/100 sites verified
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
│   ├── selfcheck.c    ★ 自检②:post_init 填表 + 回读 100 处
│   ├── th18_card_expand.def
│   └── Makefile
└── patch/
    ├── patch.js
    ├── files.js
    └── th18.v1.00a.js  ★ 生成物,不要手改
```
