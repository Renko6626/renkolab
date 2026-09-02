# TARGET —— card-expand 死绑登记

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。

**这份文件回答一个问题：换一个 exe build，我要重取哪些量？**

对账脚本：`native/sites.py`（`make check` / `make verify`）。**换 build 后先过这一关。**

## 目标二进制

| 项 | 值 |
| --- | --- |
| 游戏 / 版本 | th18 v1.00a |
| exe md5 | `9969cac756098c1da05a81de45437a70` |
| imagebase | `0x400000`（无 DYNAMICBASE） |

⚠️ codecave 里取零售表地址用的是 thcrap 的 **`Rx` 记法**（`<Rxc53c0>`，
`expression.h:310`：相对模块基址的十六进制），**不写死 `0x400000`**。

## 死绑量（只有五个数）

| 量 | 值 | 出处 |
| --- | --- | --- |
| 注册表基址 | `0x4c53c0` | [`engine/card/th18/07-registry.md`](../../../engine/card/th18/07-registry.md) |
| 行长 stride | `0x34` | 同上 |
| 零售行数 | 58 | 同上 |
| 回退行号 | 56（`NULL`） | [`engine/card/th18/11-sentinels-56-57.md`](../../../engine/card/th18/11-sentinels-56-57.md) §2.1 |
| 表的 RVA | `0xc53c0` | = 基址 − imagebase |

**其余 100 个地址全部是算出来的，不是抄来的。**这就是为什么这个 mod 的
`TARGET.md` 比 [`../mouse-control/TARGET.md`](../mouse-control/TARGET.md) 短得多——
写入点由扫描器从二进制里现找。

## 写入点：100 处，全部同长

扫描器保证每一处都只替换 4 字节常量，**opcode 一个字节都不动**（`make verify` 第 ③ 项）。

| 类 | 处数 | 原形态 | 改成 |
| --- | --- | --- | --- |
| `start`（内联查表起点） | 24 | `mov <r>, 表基+f` | `mov <r>, 新表+f` |
| `end`（尾界） | 25 | `cmp <r>, 表尾+f` | `cmp <r>, 新表+行数*0x34+f` |
| `fallback`（查不到的回退臂） | 25 | `mov <r>, 回退行+g` | `mov <r>, 新表+56*0x34+g` |
| `hit`（命中臂） | 25 | `add`/`lea <r>, 表基+g` | `add`/`lea <r>, 新表+g` |
| `start`（表遍历，按计数收尾） | 1 | `mov edx, 表基+4` @ `0x418e0e` | 同 start |

`start` 是 24 而不是 25：`0x414412` 的 `mov eax, 0x4c53c4` 被编译器提到分支之前，
**由 `0x414420` 和 `0x414494` 两个循环共用**。扫描器显式支持这种共享。

## hook 点

**没有 hook 点。**本 mod 不挂断点、不写 `.text` 以外的东西，
只做两件事：申请一块 codecave，改 100 个 4 字节常量。

DLL 只有一个被 thcrap 调用的入口 `th18_card_expand_mod_post_init`
（`init.cpp:420` `mod_func_run_all("post_init")`），跑在 thcrap 初始化线程上、
游戏代码开始之前；它**不注入任何游戏函数**。

## codecave

| 名字 | 大小 | 权限 | 内容 |
| --- | --- | --- | --- |
| `th18_card_table` | 行数 × `0x34` | RW | 开机时从零售表拷贝而来 |
| `th18_card_table_patch_init` | 20 或 35 字节 | RX + export | 那段拷贝代码 |

`*_patch_init` 由 `patch_func_init` 调用（`binhack.cpp:1724` → `plugin.cpp:304`），
签名 `void (TH_CDECL *)(void *param)`（`plugin.h:71`）。

⚠️ **它跑在 `codecaves_apply` 末尾，早于 `binhacks_apply`**（`runconfig.cpp:655-656`），
且是否被调用取决于 thcrap 版本。所以它只是保险；**填表与验证的权威是 DLL 的
`post_init`**，见 [`README.md`](README.md)。DLL 从 `func_get("codecave:th18_card_table")`
（`plugin.h:24`，`THCRAP_API`）取地址，从 `GetModuleHandleA(NULL) + 0xc53c0` 读零售表。

## 换版本时必须重取

- [ ] 注册表基址 / stride / 行数（`sites.py` 顶部的五个常量）
- [ ] 表的 RVA
- [ ] 确认查表骨架没变（MSVC 换版本可能生成不同形状）——`make check` 的锚点数会立刻告诉你
- [ ] 确认那两条不变式仍然成立

可以借的只有：方法论、骨架的**形状**、两条不变式的**定义**。
