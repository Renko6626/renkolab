# mods/ — 产物层

**版本为主，死绑 build。** 一个 mod 的每个写入点都是「某个 exe 的某个地址上的某几个字节」——
换一个 build 就全部作废。所以目录第一层是版本，不是 mod 名：

```
mods/<版本>/<mod名>/
  README.md      这是什么 / 怎么装 / 版本约束
  TARGET.md      ★ 死绑登记:exe 哈希 + 每个写入点的 addr / expected / 调用约定
  native/        codecave 源码(.asm / .c)
  assets/        成品脚本资产(.ecl / .anm / .sht) —— 用 THTK-Studio 编辑,这里存源
  patch/         thcrap patch 目录(patch.js / files.js / <版本>.js)
  AUDIT.md       对抗审计记录
```

## 为什么 `TARGET.md` 是一等公民

没有它的话，「这个 mod 绑死了什么」会散落在 patch 的 `expected` 字段和 AUDIT 的行文里。
提成一份显式登记后，**换版本时一眼知道要重取哪些量**。新建 mod 时从
[`_template/TARGET.md`](_template/TARGET.md) 拷一份填。

## 纪律

- **只分发 thcrap 元数据、源码/汇编、预期原字节和文档；不分发游戏字节。**
- 地址只写入该版本文件；`expected` 不匹配必须停止，不能强行应用。
- **不把某作的地址/ABI/机器码套到另一作。** 跨作只能借方法论。
- ★ 涉及手写机器码 / ABI 的产出，**必须过
  [`_template/AUDIT-checklist.md`](_template/AUDIT-checklist.md)**——
  这不是形式主义，见下。
- 加载层统一用 thcrap（它的运行时加载机制就是 DLL 注入），除非任务本身研究加载器。

## ★ 为什么强制对抗审计

`tracking-laser` 的静态审计抓到过一个**肉眼和单人复核极易漏**的 BLOCKER：
引擎内部大量函数是 **stdcall（callee 清栈，`RET imm`）**，按 cdecl 写了 `add esp` 会抬高 ESP，
`pop esi/edi` 读到栈帧里的局部值 → esi/edi 被破坏 → `tick_bullets` 崩。
逻辑全对、只错栈平衡，靠「默认自己写错、去二进制证伪」的独立 agent 才抓出来。

同一轮还抓到第二个真 BUG：thcrap 的 `[expr]` 是**相对**地址、`<expr>` 才是**绝对**地址，
重指数据指针表槽写成 `[codecave:…]` 会把相对偏移当指针用 → 跳错地址崩。

## 现有 mod

| mod | 目标 | 状态 |
| --- | --- | --- |
| [`th16.v1.00a/tracking-laser`](th16.v1.00a/tracking-laser/README.md) | 重指 SHT tick 槽注入追踪激光 | 静态审计通过，**未实跑** |
| [`th18.v1.00a/card-rework`](th18.v1.00a/card-rework/ROADMAP.md) | 卡牌系统改造 | 路线图，**无已实跑补丁** |
