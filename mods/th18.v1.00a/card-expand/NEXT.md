# NEXT —— 下一个会话从这里开始：战线 E

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 交接文档。写给**没有本会话上下文**的下一个会话；读完这一页应该能直接动手。

## 0. 现状一句话

A（搬表）、B（分配器）、C（`zAbilityManager` 扩容）、D（存档影子数组 + side-car）**全部实跑通过**。
新卡现在能被分配、能被「获得」、解锁状态能持久化、名字显示「测试卡牌 58」（E 第一块：文案重定向，
[`AUDIT.md`](AUDIT.md) §L）——但它还没有图鉴位、商店位、真实数据、图。

| 战线 | 状态 |
| --- | --- |
| A 搬表 | ✅ 实跑 |
| B 分配器 | ✅ 实跑 |
| C `zAbilityManager` 扩容 | ✅ 实跑 |
| D 存档 | ✅ 实跑（[`AUDIT.md`](AUDIT.md) §K）|
| **E** 图鉴 / 顺序表 / 文案 / 图 / 商店筛选 | 文案重定向 ✅（§L）；图鉴 + 编成 🔧 待实跑（§M）；← **其余从这里** |

## 0.5 先读什么

[`README.md`](README.md)（是什么、怎么发布）→ [`MAP.md`](MAP.md)（**一张卡要经过的 10 段路，每条 binhack / 断点 / codecave 的出处；改了什么就在那里补一行**）→ [`AUDIT.md`](AUDIT.md) 对应小节。

## 1. 参考：一次正常启动的日志长什么样

（C+D+E1 已由用户实跑通过。以后改了东西，回归就看这些行还在不在。）

```
gate: BP_ce_gate fired at ScoreFile__load
grow: zAbilityManager 0xd70 -> 0x116c, owned[] at +0xd70 (255 entries), shop loops still 56
unlocked: shadow @ …, 9 read sites + 3 breakpoints verified; side-car = C:\Users\…\AppData\Roaming\ShanghaiAlice\th18\th18_card_expand.sav
text: ids 57..254 redirected to ext buffer @ … (198 entries x 0x1c0), 3 breakpoints verified
menu: order table @ … rebuilt (56 retail + 1 new + NULL, rest BACK); encyclopedia entries = 57; __card_ids at +0x13fc
OK: table filled (255 rows @ …), allocator relocated, manager grown, unlocked shadowed, text redirected, menu extended, 100/100 sites verified
unlocked: shadow @ …, 57 retail (N set) + side-car (0 new ids set) from …
trace: allocate_new_card(id=58, mode=1)  <- NEW ID
test: calling mark_obtained(id=58, notify=1) to exercise the unlock path
unlock: id=58 (NEW; shadow + side-car saved)
```

第二次启动 `side-car (1 new ids set)`。任何一行缺失 / FAIL / `mitigation:` 都是回归。

## 2. E 要做什么（PLAN §2 战线 E 的量化，本会话补的在 ★）

| 块 | 处数 | 备注 |
| --- | --- | --- |
| ~~图鉴上界 / 顺序表 / `__card_ids`~~（已做，`menu.c`，待实跑）| 27 binhack + 7 处运行时立即数 | AUDIT §M。条目数 ≤ 127（两处 imm8）；图鉴最后一行非整行是否可达 = M9，实跑看 |
| ~~文案缓冲扩容~~ → **重定向**（已做，`text.c`）| 3 读挂断点 | 对象不扩，尾部字段不用数了。写入点 `0x41623d`（文案文件解析器）仍只写零售 id；新卡的文案由 DLL 直接填进 ext 缓冲（现在是占位「测试卡牌 N」）|
| ★ 商店筛选 | 3 处循环（`0x416f8f` `0x41744a` `0x417535` 起点，上界现留 56）| 抬上界前要加「查表命中才算」（`entry->id == esi`）的 codecave 筛选，否则 ~198 个 NULL 副本涌进 57 槽的栈数组 `[ebp-0xe4]`（AUDIT §J4、边界 #34）|
| 图 | `abcard_anm` 加 sprite | thanm/truanm；sprite 索引余量 ⏳ 未查（已知用到 116/117）|
| ★ 新卡数据激活 | — | 现在 58..254 行全是 NULL 副本（`+0x24=1` 初期解禁、`+0x20=1` 菜单可见），真正的新卡行由谁、何时写进 codecave 还没定。建议：DLL 在 `ce_selfcheck` 通过后从一个 JSON/文本读行数据填表（仓库不留版权字节的原则同样适用：只放**新**卡的数据）|

建议顺序：新卡数据的来源与激活（把 `cards.c` 的注册表换成文件，同时装卡表行 + 文案）→ 商店筛选 → 图 → 行为。

## 3. 工具链与验收（照旧）

```bash
cd native
make check          # 站点扫描 + 不变式 + 战线 D 的 9 处读全集断言
make step3          # 255 行全套（含 C、D）+ patch-test
make dllverify dllx87
make conflicts OTHERS="<modkit>/thcrap/repos/nmlgc/base_tsa/th18.v1.00a.js …"
make release PUSH=1 # 同步进发布仓库 th18_modkit，Windows 只 git pull
```

## 4. 别忘了

- 自检门是断点 `ce_gate`，**不要用 `*_mod_post_init`**（AUDIT §H′）。D 又加了三个断点，都在 `unlocked.c`。
- **凡是「编译器把什么放在哪一格」的假设都要从上下文重取**——D 的改写表 3/9 留错了寄存器（AUDIT §K2），
  生成器现在从 `mov r32,[SCOREFILE_PTR]` 反推。E 搬顺序表时同样别信 PLAN 里手写的形态。
- `sites_gen.h` 与行数无关，DLL 一份配所有 patch；E 的站点也按这个原则做。
- 日志路径 / side-car 路径都是绝对路径（AUDIT H14、K13）。
- `make release` 只覆盖生成物；modkit 里的 `patch.js` / 侧车 `.json` / README 是手工文案，改了要在那边单独提交。
  本会话改了 `_test` 的语义（新 id 自动 mark_obtained），modkit 那边的文案已同步。
- 每条新写入点过 [`../../_template/AUDIT-checklist.md`](../../_template/AUDIT-checklist.md)，追加到 `AUDIT.md` 新一节。
