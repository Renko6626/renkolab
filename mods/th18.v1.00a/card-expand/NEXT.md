# NEXT —— 下一个会话从这里开始：先验收 D，再开战线 E

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 交接文档。写给**没有本会话上下文**的下一个会话；读完这一页应该能直接动手。

## 0. 现状一句话

A（搬表）、B（分配器）实跑通过；C（`zAbilityManager` 扩容）、**D（存档影子数组 + side-car）静态审计通过、
已发布、待实跑**。新卡现在能被分配、能被「获得」、解锁状态能持久化——但它还没有名字、说明、图鉴位、
商店位，所以**解锁后名字栏是乱码**（`zAbilityText` 只有 57 张的文案缓冲），这是 E。

| 战线 | 状态 |
| --- | --- |
| A 搬表 | ✅ 实跑 |
| B 分配器 | ✅ 实跑 |
| C `zAbilityManager` 扩容 | 🔧 静态审计通过，已发布未实跑 |
| D 存档 | 🔧 静态审计通过（[`AUDIT.md`](AUDIT.md) §K），已发布未实跑 |
| **E** 图鉴 / 顺序表 / 文案 / 图 / 商店筛选 | ← **这里** |

## 1. 先做：把 C + D 的实跑记录收回来

用户 Windows 上 `git pull` 后按 [`README.md`](README.md)「战线 D → 验收」跑一遍，把
`th18_card_expand.log` 贴回来。要看的行（顺序）：

```
gate: BP_ce_gate fired at ScoreFile__load
grow: zAbilityManager 0xd70 -> 0x116c, owned[] at +0xd70 (255 entries), shop loops still 56
unlocked: shadow @ …, 9 read sites + 3 breakpoints verified; side-car = C:\Users\…\AppData\Roaming\ShanghaiAlice\th18\th18_card_expand.sav
OK: table filled (255 rows @ …), allocator relocated, manager grown, unlocked shadowed, 100/100 sites verified
unlocked: shadow @ …, 57 retail (N set) + side-car (0 new ids set) from …
trace: allocate_new_card(id=58, mode=1)  <- NEW ID
test: calling mark_obtained(id=58, notify=1) to exercise the unlock path
unlock: id=58 (NEW; shadow + side-car saved)
```

第二次启动 `side-car (1 new ids set)`。任何一行缺失 / FAIL / `mitigation:` 都先处理再往下。
通过后把 [`AUDIT.md`](AUDIT.md) §0 的表补上 C、D 两行，§K 末尾「未实跑」改掉。

⚠️ 一个可能的坑：解锁后 `FUN_00416540` 读 `zAbilityText + 58*0x1c0`，越过对象末尾 `0x160` 字节。
只读不写，大概率是乱码 / 空白；**若崩在这里**，那是 E 的文案缓冲问题提前暴露，不是 D 的错——
临时绕法是把 patch-test 的 `th18_ce_test_id` 留 `0x3a`、但先不进卡组编成看它。

## 2. E 要做什么（PLAN §2 战线 E 的量化，本会话补的在 ★）

| 块 | 处数 | 备注 |
| --- | --- | --- |
| 图鉴上界 `0x38` → `0xff` | 8 | 全同长：`0x4137bb` `0x414394` `0x41439e` `0x4145e2` `0x41495c` `0x41570d` `0x4157cb` `0x415817` |
| 显示顺序表 `0x4b3600`（57 dword）→ codecave | 7 引用 + 1 尾界 `0x4b36e4` | ⚠️ `0x4b36e4` 紧接另一张表（`0x4337f4`），不能就地加长 |
| 文案缓冲 `zAbilityText` `0x63e0` → `0x1be00` | 1 写 `0x41623d` + 3 读 `0x416694` `0x416779` `0x41926a` | ⏳ 尾部字段 `+0x63c0..+0x63dc`（vm id ×7，`FUN_00416540` 里就在用）的**全部访问点还没数全**——扩容会把它们顶走，先数清 |
| ★ 商店筛选 | 3 处循环（`0x416f8f` `0x41744a` `0x417535` 起点，上界现留 56）| 抬上界前要加「查表命中才算」（`entry->id == esi`）的 codecave 筛选，否则 ~198 个 NULL 副本涌进 57 槽的栈数组 `[ebp-0xe4]`（AUDIT §J4、边界 #34）|
| ★ `zAbilityMenu.__card_ids` | 与顺序表耦合 | AUDIT G3 |
| 图 | `abcard_anm` 加 sprite | thanm/truanm；sprite 索引余量 ⏳ 未查（已知用到 116/117）|
| ★ 新卡数据激活 | — | 现在 58..254 行全是 NULL 副本（`+0x24=1` 初期解禁、`+0x20=1` 菜单可见），真正的新卡行由谁、何时写进 codecave 还没定。建议：DLL 在 `ce_selfcheck` 通过后从一个 JSON/文本读行数据填表（仓库不留版权字节的原则同样适用：只放**新**卡的数据）|

建议顺序：**先数文案缓冲尾部字段**（唯一没量化的），再做顺序表 + 图鉴 8 处（都是同长/搬表，工具链现成），
最后商店筛选（第一段需要新 cave 逻辑的活）。

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
