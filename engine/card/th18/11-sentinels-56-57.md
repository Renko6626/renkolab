# TH18 id 56 / 57 —— 两个「哨兵」到底是什么，能不能让出来

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> **性质**：定点逆向。回答 [`10-extensibility-limits.md`](10-extensibility-limits.md) §7 留下的第一题——
> 「路线 B（吃掉哨兵）可不可行」。
> **可信度**：全篇 ✅ 为本次一手反汇编读出；🟡 处逐条注明。

## 0. 结论先行：路线 B 死了

**两个都不是空位，两个都在服役。**

| id | 真身 | 为什么让不出来 |
| --- | --- | --- |
| **56 `NULL`** | ①**全部内联查表（25 处）的「查不到」回退行**；②卡组编成菜单里的**「空槽」伪卡**；③一个**可分配**的无行为卡对象 | 拿它当新卡 = 任何一次查表失配都会返回你的新卡；且卡组编成的清空操作按 `id == 56` 判定，会连带失效 |
| **57 `BACK`** | 图鉴里**未解锁卡的「卡背」图**（唯一用途） | `allocate_new_card` 的 `cmp ebx,0x38; ja` 根本不放行 57，而跳转表 57 项紧接着就是代码，原地扩不了 |

顺带的收获比结论本身更有用：这一轮把**注册表的两个未命名字段反出来了**，
并把 [`10`](10-extensibility-limits.md) 的 12 处边界扩到 **27 处**，还给路线 C 算出了确切工价。

## 1. 两行的原始数据

`zTableCardData[]` `0x4c53c0`，stride `0x34`。两个哨兵**不在表尾**，
而是**表的第 56、57 行**——但表并不按 id 排序（见 §4），所以行号恰好等于 id 只是巧合。

| 字段 | 行 56（`0x4c5f20`） | 行 57（`0x4c5f54`） |
| --- | --- | --- |
| `+0x00` internal_name | `0x4b4c00` = `"NULL"` | `0x4b4c08` = `"BACK"` |
| `+0x04` id | 56 | 57 |
| `+0x08` | 1 | 1 |
| `+0x0c` 类别 | **4** | **4** |
| `+0x10` 价格档 / `+0x14` 权重 / `+0x18` dmode / `+0x1c` | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| `+0x20` ★菜单可见 | **1** | 0 |
| `+0x24` ★初期解禁 | **1** | **1** |
| `+0x2c` sprite_large | 116 | **2** |
| `+0x30` sprite_small | 117 | **3** |

### ★ 两个新反出来的字段

**`+0x24` = 初期解禁标志。**存档创建时逐 id 拷进 `unlocked_cards[]`：

```asm
0x463670  XOR EDX, EDX                      ; card_id = 0
loop:     ...内联 get(card_id)...           ; 找不到 → 0x4c5f44 (= 行56 的 +0x24)
0x4636D5  MOV AL, byte ptr [EAX]            ; entry->+0x24
0x4636D7  MOV byte ptr [EDI+EDX+0xd0], AL   ; obj+0xd0+card_id
0x4636DE  INC EDX
0x4636DF  CMP EDX, 0x39                     ; card_id < 57
0x4636E2  JL loop
```

判定为「就是 `unlocked_cards`」的依据是两条独立算式对上：`FUN_00463670` 由存档加载器
`FUN_004637d0` 以 `scorefile + 0x5f4b8` 为 `this` 调用，而 `0x5f4b8 + 0xd0 = 0x5f588`
——正是 `zScoreFile.unlocked_cards` 的偏移。✅

实读全表：`+0x24 == 1` 的只有 id 1–6（EXTEND/BOMB/两个掉落/PENDULUM/DANGO）、16、24、42、56、57。
即**新档一开局就解禁的是这 11 个 id**。

**`+0x20` = 卡组编成菜单可见。**`0x4149de` 处 `CMP dword ptr [EAX], 0x0; JZ 跳过`。
实读：id 8–54 与 **56** 为 1，id 0–7、55、57 为 0。

## 2. id 56（`NULL`）的四重身份

### 2.1 它是所有内联查表的「查不到」回退行 ✅

`TableCardData__get` `0x407d70` 被**大面积内联**。每个内联点长这样：

```asm
          XOR ECX, ECX
          MOV EAX, 0x4c53c4              ; &table[0].id
loop:     CMP dword ptr [EAX], <id>
          JZ  found
          ADD EAX, 0x34
          INC ECX
          CMP EAX, 0x4c5f8c              ; 表尾（= 表基 + 58*0x34 + 4）
          JL  loop
          MOV EAX, 0x4c5f20              ; ← 查不到:行 56，可带字段偏移
          JMP after
found:    IMUL EAX, ECX, 0x34
          ADD EAX, 0x4c53c0
after:
```

`0x4c5f20`（及其 `+0x0c` / `+0x10` / `+0x14` / `+0x1c` / `+0x20` / `+0x24` / `+0x30` 变体
`0x4c5f2c` `0x4c5f30` `0x4c5f34` `0x4c5f3c` `0x4c5f40` `0x4c5f44` `0x4c5f50`）在 `.text` 里
共 **24 处操作数，全部是回退臂**（按反汇编操作数实测，见 §6），横跨
`AbilityMenu__on_tick`、`AbilityShop__initialize`、`CardShop__pick_weighted_random_offer`、
`TableCardData__get`、`FUN_00409310`、`FUN_00416940`、`FUN_00463670`。

> **这就是「NULL」这个名字的含义**：它是查表失败的安全返回值，不是一张卡。
> 把它改成真卡 = 把「找不到」变成「找到了你的新卡」。

### 2.2 它是卡组编成里的「空槽」伪卡 ✅

**决定性证据是一处按值比较**，不是按地址：

```asm
0x415049  LEA EAX, [EDI + 0x304]           ; zAbilityMenu.__card_ids_0x304
          ...在其中定位当前光标项...
0x41506E  MOV EAX, dword ptr [EAX]         ; zTableCardData*
0x415070  CMP dword ptr [EAX + 0x4], 0x38  ; ★ entry->id == 56 ?
0x415074  JNZ 0x0041516f
```

`+0x04` 是 id 字段，`0x38` = 56。**游戏显式判断「选中的这项是不是 NULL」**——
这只有在 NULL 是一个可被光标选中的菜单项时才有意义。

配套证据三条：
- `+0x20 = 1`（菜单可见）且 `+0x24 = 1`（初期即解禁）→ 它**从一开始就出现在列表里**；
- **显示顺序表 `0x4b3600` 的第 57 项就是 56**，而遍历该表的循环上界是
  `0x414b54  CMP EAX, 0x4b36e4`（= 表基 + 57 项）→ **覆盖到它**；
- 它自带一对专属 sprite（116 / 117），不是复用别人的。

综合：**NULL 是初期卡组编辑器里那个「不装卡 / 清空此槽」的条目。**🟡
（判为 🟡 而非 ✅：链路完全成立，但没有游戏内实跑截图佐证 UI 长什么样。
证伪方法：进初期卡组编成界面，看列表末尾是否有一个可选的空白项。）

### 2.3 它是一个可分配的、无行为的卡对象 ✅

`AbilityManager__allocate_new_card` `0x411460` 的跳转表 `0x412dac` 共 **57 项、无重复目标**，
第 56 项指向 `0x411489`：

```asm
0x411489  PUSH 0x54
0x41148B  CALL 0x0048dc71          ; operator new(0x54)
0x411498  MOV dword ptr [ESI], 0x4b6010
          ...通用初始化...
0x4114D6  MOV dword ptr [ESI], 0x4b4c78   ; ← 最终虚表
0x4114DC  JMP 0x00412cd5
```

对比 id 0（`0x411f4b`）：多一步 `CALL 0x00407da0`（`AbilityManager__reset_cards`），
其余骨架相同。**即 `allocate_new_card(56)` 是合法的，产出一张挂着基类虚表 `0x4b4c78` 的空卡。**

> 这是唯一一处对路线 B 有利的事实：分配侧不用改。但另外三重身份把它抵消了。

### 2.4 它落在商店池之外 ✅

商店的三个遍历都以 `zAbilityManager` 的「本局是否拥有」数组为轴：

| 位置 | 起 | 止 | 覆盖 id |
| --- | --- | --- | --- |
| `CardShop__pick_weighted_random_offer` `0x416f8f` / `0x41716b` | `mgr+0xc84` | `< 0xd64` | 0–55 |
| `AbilityShop__initialize` `0x41744a` / `0x417527` | `mgr+0xc84` | `< 0xd64` | 0–55 |
| 同上第二轮 `0x417535` / `0x4175e7` | `mgr+0xc84` | `< 0xd64` | 0–55 |

`zAbilityManager` 实测大小 `0xd70`（`operator new` 的实参），数组止于 `0xd64`
→ **对象内还剩 12 字节 = 3 个 dword 的余量**，把上界改成 `0xd68` 在结构体内是放得下的。✅

> ⚠️ ExpHP 的 `zAbilityManager` 在这一带**有偏差**：它把 `0xc68` 起 32 字节标成 `__thread`、
> `0xc88` 起 232 字节标成 `field_c88`，而一手代码明确以 `0xc84` 为数组基址、`0xd64` 为止。
> 两者在 `0xc84`–`0xc88` 重叠。以一手为准。

## 3. id 57（`BACK`）：卡背

**它在整个 `.text` 里没有任何一处按地址引用**（`get_xrefs_to 0x4c5f54` 返回 0），
只被两处**按 id 字面量 `0x39`** 查到，两处都在 `AbilityMenu__on_tick`、
且都挂在「这张卡没解锁」的分支上：

```asm
0x414401  MOV EDX, dword ptr [EDX*0x4 + 0x4b3600]   ; card_id = 显示顺序表[i]
0x41440B  CMP byte ptr [EAX + EDX*0x1 + 0x5f588], CL ; unlocked_cards[card_id] == 0 ?
0x414417  JZ  0x00414494                             ; ← 未解锁,跳去查 id 0x39
...
0x414494  CMP dword ptr [EAX], 0x39                  ; 线性查 id == 57
0x4144D0  CMP dword ptr [EAX], 0x39                  ; 同一帧的第二个 sprite 槽
```

两处随后都把查到的行交给 `FUN_004091a0`，后者用行的 `+0x2c` 当 sprite 建 ANM VM：

```c
AnmLoaded__instantiate_vm_to_ui_list_front(ABILITY_MANAGER_PTR->abcard_anm, ..., script, ...);
AnmLoaded__set_sprite(..., *(int *)(entry + 0x2c));
```

行 57 的 sprite 是 **2 / 3**（整个表里最小的一对，其余卡从 4 起步）
→ **`BACK` 就是图鉴里未解锁卡显示的那张「背面 / ？」图。**✅
名字读作**卡背**（card back），不是「返回按钮」。

**为什么连改都难：**

| 障碍 | 事实 |
| --- | --- |
| 分配不放行 | `0x411460  cmp ebx, 0x38; ja 失败` —— 57 在跳转表之前就被挡掉 |
| 跳转表扩不了 | 表 `0x412dac` 恰好 57 项，止于 `0x412e90`，而 `0x412e90` 的字节是 `55 8b ec …` = **下一个函数的序言**。原地加一项就是覆盖代码 |
| 它不在显示顺序表里 | `0x4b3600` 的 57 项是 id 0–56 的重排，**不含 57** → 它永远不是菜单项 |
| 它也不进 `unlocked_cards` | 初期解禁循环上界 `CMP EDX, 0x39` = id 0–56，写不到 57 |
| 改了就丢卡背 | 那是图鉴里所有未解锁卡的显示依据 |

## 4. 顺带反出来的三件事

### 4.1 注册表**不按 id 排序** ✅

实读行号 → id：行 0–7 是 id 0–7，**行 8 是 id 38**，行 13 是 id 16，行 41 是 id 42……
这解释了为什么 `TableCardData__get` 要做线性查找而不是 `table[id]`——
**它没法直接索引**。同时也说明：想加新 id，往表尾追加一行在语义上是够的（顺序无所谓），
问题全在「表尾在哪」和「谁知道表尾」。

### 4.2 显示顺序表 `0x4b3600` ✅

57 个 dword，`0x4b3600`–`0x4b36e3`，内容是 id 0–56 的一个重排：

```
0..20, 51, 21..40, 54, 41..50, 52, 53, 55, 56
```

即把 MAGATAMA(51)、MUKADE(54) 插到分类中间，NULL(56) 压在最后。

### 4.3 菜单有**两个上界不同**的遍历 ✅

| 循环 | 位置 | 上界 | 覆盖 | 是什么 |
| --- | --- | --- | --- | --- |
| 图鉴 | `0x4143c0`–`0x4145e5` | `CMP EAX, 0x38` = 56 | 顺序表前 56 项（id 0–55） | 固定 56 格；未解锁的画卡背（§3） |
| 卡组编成 | `0x4149b0`–`0x414b59` | `CMP EAX, 0x4b36e4` = 顺序表尾 | 全 57 项（含 NULL） | 按 `+0x20 != 0` 且已解锁筛选，条目数写回 `menu+0x300` / `+0x1c4` |

**上界不同不是笔误**：图鉴要展示「共 56 张」这个固定盘面，所以连未解锁的都占格；
卡组编成只列你能装的，所以要动态计数，并且要把「空槽」（NULL）也列进去。

## 5. 边界表增补

[`10-extensibility-limits.md`](10-extensibility-limits.md) §2 记了 12 处。本轮又坐实 15 处，
且把其中 4 条 🟡 转成 ✅：

| # | 位置 | 边界 | 含义 |
| --- | --- | --- | --- |
| 13 | `0x4145e2` | `CMP EAX, 0x38` | 图鉴填充循环 = 56 格 |
| 14 | `0x414394` | `MOV [EDI+0x300], 0x38` | 图鉴条目数 |
| 15 | `0x41439e` | `MOV [EDI+0x1c4], 0x38` | 图鉴 `zMenuSelect` 项数 |
| 16 | `AbilityMenu__initialize` `0x413650` | `this+0x1c4 = 0x38` | 同上，初始化时先设一次 |
| 17 | `0x41570d` | `MOV EAX, 0x38` → `IDIV [0x5704bc]` | 图鉴**翻页行数**由 56÷列数 算 |
| 18 | `0x4157cb` | `CMP EDX, 0x38` | 图鉴光标高亮遍历 |
| 19 | `0x415817` | `MOV EDI, 0x38` | 图鉴 ANM 清理循环 |
| 20 | `0x41495c` | `MOV EDI, 0x38` | 卡组编成 ANM 清理循环 |
| 21 | `0x414b54` | `CMP EAX, 0x4b36e4` | 卡组编成循环 = 顺序表 57 项 |
| 22 | 顺序表 `0x4b3600` | 57 dword | 新 id 不在里面就不显示 |
| 23 | `0x415070` | `CMP [EAX+4], 0x38` | **id 56 当哨兵值**：清空槽判定 |
| 24 | `0x414494` / `0x4144d0` | `CMP [EAX], 0x39` | **id 57 当哨兵值**：卡背查表 |
| 25 | `0x4636df` | `CMP EDX, 0x39` | 存档初期解禁写入 = id 0–56 |
| 26 | `0x46d8ec` | `CMP EAX, 0x39` | 成就菜单里 `0x570980` 字节数组遍历（起点 32） |
| 27 | `zAbilityMenu.__card_ids_0x304` | `int[56]`，紧跟 `num_total_cards` | **写第 57 项会踩到计数字段** 🟡（尺寸来自 ExpHP；「紧跟」由 `0x4145d2  MOV [ESI-0x4e8], EAX` 的落址一手佐证） |

**转正的 🟡**：

- #10 `unlocked_cards` 在 `+0x5f588`、按 card_id 索引的 `uint8_t` 数组，长度 ≥ 57
  —— 三处独立一手（`0x418df6` 读写、`0x4636d7` 初始化写、`0x41440b`/`0x41694e` 读）✅。
- #12 全收集成就：`CardCollection__mark_obtained_and_notify` `0x418de0` 遍历**表的前 56 行**
  查 `unlocked_cards[row.id]`，全非零才发成就 `0x1d`。前 56 行的 id 恰为 0–55
  → **NULL/BACK 不参与全收集** ✅。
- #8 `zAbilityManager` 数组 `0xc84`–`0xd64`、对象大小 `0xd70` ✅（见 §2.4）。
- #7 商店池三个遍历的起止 ✅（见 §2.4 表）。

## 6. 路线判据更新

| 路线 | 状态 |
| --- | --- |
| **A. 换皮** | 不变。仍是唯一零边界成本的做法 |
| **B. 吃掉哨兵** | ❌ **判死**。56 是查表回退 + 空槽哨兵，57 连分配都进不去 |
| **C. 整体搬迁** | 工价现在算得出来了，见下 |

### 路线 C 的确切工价

搬表要改的立即数，按**反汇编操作数实测**（不是 xref 计数——xref 会把常量装载和随后的
使用各算一次，早先我按 xref 得出的数字偏大）：

| 立即数 | 含义 | 处数 |
| --- | --- | --- |
| `0x4c53c4` | 内联查表的**起点**（`&table[0].id`） | 25 |
| `0x4c53c0` | 表基（`found` 臂算行地址用） | 13 |
| `0x4c53cc` `0x4c53d0` `0x4c53d4` `0x4c53dc` `0x4c53e0` `0x4c53e4` `0x4c53f0` | 表基 + 字段偏移的 7 个变体 | 12 |
| `0x4c5f8c` / `0x4c5f88` | 表**尾界** | 24 / 1 |
| `0x4c5f20` + 6 个字段变体 | 查不到的回退行 | 24 |
| — | **合计** | **99** |

分布很集中——**只有 9 个函数**：

| 函数 | 处数 |
| --- | --- |
| `AbilityShop__initialize` `0x4171b0` | 28 |
| `AbilityMenu__on_tick` `0x413af0` | 27 |
| `CardShop__pick_weighted_random_offer` `0x416f50` | 24 |
| `TableCardData__get` `0x407d70` / `FUN_00409310` `0x409310` / `FUN_00416940` `0x416940` / `FUN_00463670` `0x463670` | 4 each |
| `FUN_004160b0` `0x4160b0`（`ability.txt` 解析） | 3 |
| `CardCollection__mark_obtained_and_notify` `0x418de0` | 1 |

99 处机械替换，每处都是 5 字节的 `mov r32, imm32` / `cmp r32, imm32`，
**thcrap 的 binhack 逐条写 `expected` 就能做**。但这只解决了**表**；
§5 的 27 处按 id 索引的数组边界、以及 `zScoreFile` 的存档格式，一条都没动。

### ⚠️ 表尾之后不是空白 —— 是两个热全局

原始字节 `0x4c5f88: FF FF FF FF FF FF FF FF` 看着像填充，**不是**。
它们是两个各自独立、被大量读写的 `int` 全局：

**`0x4c5f88`** —— `Ending__initialize` `0x42b735` 读、`0x42b751` 写 −1；
`MainMenu__tick_menu_17_achievement` `0x46d532` 写。

**`0x4c5f8c`** —— 12 处读写，横跨 9 个函数：

- 卡牌侧：`AbilityShop__on_tick` `0x417cc7`
- 关卡流程：`GameThread__end_stage` `0x444b97`（读）/ `0x444baa`（写 −1）、
  `GameThread__thread_start` `0x4429ff`、`FUN_00457a60` `0x457af1` `0x457b25` `0x457b4c`
- ECL：`Enemy__ecl_get_int_global` `0x437956`、`Enemy__ecl_get_float_global` `0x43860d`
- 主菜单：`MainMenu__thread_start` `0x464c10`、`MainMenu__tick_menu_08_stage_select` `0x46769d`、
  `MainMenu__tick_menu_17_achievement` `0x46d9cb`

**巧合是双重的**：`0x4c5f8c` 既是卡表的尾界立即数，又是一个 ECL 全局变量的地址。
两种用法在反汇编里长得一样（`CMP EAX, 0x4c5f8c` vs `MOV EAX, [0x004c5f8c]`），
**动手时必须按寻址方式区分，不能按地址一把梭**——这是本轮最容易埋雷的地方。

结论：**表原地向后长这条路是堵死的**，不是「搬走邻表就行」。真要长表，
只能整表搬进 codecave，付上面那 99 处的工价。

## 7. 本次未查

- 卡组编成界面里 NULL 条目的**实际观感**（§2.2 的 🟡 只差一次游戏内确认）。
- `0x4c5f88` / `0x4c5f8c` 这两个全局各是什么语义（`Enemy__ecl_get_int_global` 会读它，
  说明至少 `0x4c5f8c` 是一个 ECL 可见的全局；搬表时要一起挪，所以得先知道它是什么）。
- 三个卡牌 ANM（`abcard_anm` / `ability_anm` / `abmenu_anm`）的 sprite 索引余量
  —— 行 57 只用到 sprite 2/3，行 56 用 116/117，说明 `abcard_anm` 至少有 118 个 sprite，
  但**上限未知**，要解包 ANM 才能答。
- `zScoreFile` 中 `0x5f5c1`–`0x5f608` 那 71 字节未知区是否空闲（`unlocked_cards` 后紧跟的空档，
  是唯一可能不改存档尺寸就扩解锁位的地方）。
- replay 里卡组的存储格式与长度上限。
