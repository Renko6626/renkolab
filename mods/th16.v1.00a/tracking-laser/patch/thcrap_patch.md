# thcrap patch:注入「追踪+爆发激光」(重指 tick idx4)

> 把 `tick_tracking_burst_starter.asm` 编成 code cave,并用 binhack **重指 TH16 tick 表 idx4 槽**
> (`0x4919b0`,现 = `0x004470f0`)指向 cave。配套 `files/pl02_tracklaser.sht`(已生成)。
> ⚠️ thcrap 分发的是**补丁(二进制 diff + cave)**,不含版权 exe —— 合规。
>
> **★ 已对 thcrap 一手源码 + ExpHP 真实 th16.v1.00a 补丁核实(2026-06-11)**,见 §0/§7。
> 核实中**抓到并修正一个真 BUG**:表槽要写**绝对地址**,必须用 `<codecave:…>`(不是 `[codecave:…]`,后者是相对 rel32)。

## 0. 核实依据(为什么这套能被 thcrap 正确挂载)

- **机制**(`thcrap/docs/2_files.md`):thcrap_loader 挂起启动游戏→改入口 2 字节为死循环→等其跑到入口
  (Windows loader 初始化完)→在游戏进程分配可执行内存 + CreateThread `LoadLibrary thcrap.dll` 跑 init→恢复。
  即**远程线程 DLL 注入 + 运行时内存打补丁**。版本经 `base_tsa/versions.js` 的 exe 哈希匹配到 `th16.v1.00a`。
- **`[…]` vs `<…>`**(一手定论,`thcrap/src/binhack.cpp` L869–879):`[expr]`=**相对** patch value(渲染为相对
  patch 处的 DWORD 偏移,所以 `E9 [codecave:X]` 能当 jmp);`<expr>`=**绝对** patch value。codecave 名在表达式里写
  `codecave:NAME`(`binhack.cpp` L1599 `strdup_cat("codecave:", name)`)。→ **写函数指针表槽要绝对地址 = `<codecave:NAME>`**。
- **binhack 能写任意地址(含 .rdata 数据)**:apply 时 thcrap 把目标页设可写再写入,不限代码段;
  ExpHP 的补丁也往各处地址写。我们写 `.rdata` 的 `0x4919b0` 没问题。
- **对照 ExpHP 的真实 th16.v1.00a 补丁**(`ExpHP/thcrap-patches`:`bullet_cap/`、`anm_leak/`):结构=patch 根下
  `patch.js` + `files.js` + 逐版本 `th16.v1.00a.js`(+ `.asm`);顶层 `codecaves`/`binhacks`/`options` 对象;
  binhack 形如 `{"addr","expected","code":"E9 [codecave:of(...)]"}`;codecave 值**直接是 hex 串**。
  注:ExpHP **没有**我们这种"重指数据指针表槽"的用例(他都是 `E9/E8` 钩代码),所以绝对地址那条要靠 `<…>` 自己保证。

## 1. 补丁目录结构(对照 ExpHP 实际布局)

```
test-laser/                  ← patch 根(run config 的 archive 指向这里)
├── patch.js                 ← {"id":"test-laser","title":"TH16 tracking burst laser"}
├── files.js                 ← 文件名→CRC32 清单(thcrap 更新用;含 th16.v1.00a.js 等)
├── th16.v1.00a.js           ← ★本作本版的 binhacks + codecaves(§2)
└── pl02.sht                 ← 文件替换(= files/pl02_tracklaser.sht;§4)
```
(thcrap 按 exe 哈希解析出 `th16` + build `v1.00a` → 读 `th16.v1.00a.js`。)

## 2. `th16.v1.00a.js` —— binhack + codecave

```json
{
  "codecaves": {
    "tracking_burst_laser": "<<< nasm 出的 cave 字节 hex(见 §3);codecave 值直接是 hex 串 >>>"
  },
  "binhacks": {
    "repoint_tick_idx4_to_cave": {
      "addr": "0x4919b0",
      "expected": "f0704400",
      "code": "<codecave:tracking_burst_laser>"
    }
  }
}
```
- `addr 0x4919b0` = tick 表第 4 项(`0x4919a0 + 4*4`);`expected f0704400` = 原指针 `0x004470f0`(小端)。
  thcrap 校验原字节,不匹配则跳过,防误伤改版。
- **`code: "<codecave:tracking_burst_laser>"`** —— `<…>`=绝对地址(★ 修正:原写 `[…]` 是相对 rel32,会写错指针崩)。
  渲染为 cave 的绝对 4 字节地址,正好覆盖 4 字节表槽。
- binhack 的 key(`repoint_tick_idx4_to_cave`)即其标识,`title` 字段可省(ExpHP 不用)。
- codecave 默认 access = execute-read-write(可执行),符合我们放代码的需求。
- cave 函数 **__fastcall**(self 在 ECX)、普通 `ret`,内部调引擎函数走绝对地址(见 .asm)。

## 3. 怎么得到 cave 字节(必须的构建步)

起步版已写成 position-independent 汇编(`tick_tracking_burst_starter.asm`,所有外调用 `mov eax,ABS/call eax`,
数据全绝对引用 → 放哪都能跑):
```
nasm -f bin tick_tracking_burst_starter.asm -o cave.bin
xxd -p cave.bin                       # 取 hex,贴进 codecave.code
```
- 所有引擎函数地址已填实(见 .asm / starter.c):find_nearest 0x425240、is_enemy_alive 0x41a980、
  handle_to_enemy 0x41b540、crt_atan2 0x487aaa、anm_unload 0x46f1c0。半径 256 = `[0x494680]`。
- ★ 手写汇编必须**汇编后比对 + 游戏内验证**(尤其 FPU 栈平衡、find_nearest 参数顺序、frame 平衡)。

## 4. .sht 侧(配套)—— 起步版已生成 ✅

- **`files/pl02_tracklaser.sht`(已生成)**:子机弹 `func_on_init=3, func_on_tick=4, func_on_hit=0`,dmg=30;主弹保留直线。
  (起步版用 init=3:清 +0x90 目标槽 + flag&0x3c,正是 targeting 前置。完整激光版才需 init=2。)
- 打包进 `th16.dat`(thdat)或用散文件覆盖让游戏读到 pl02.sht。

## 5. 测试 / 观察清单(回填 NOTES)

进游戏选琪露诺,看子机弹:
1. **会不会瞄敌**(束朝最近敌人转)?—— 验"追踪"。
2. **是不是脉冲**(发一下→约 24 帧→灭→再发)?—— 验 BURST_FRAMES + fire_rate。
3. **★ 有没有伤害**(敌人掉血)?—— 验 PLAN §3 开放项 1。**这条最关键**:若无伤,说明激光池对象/
   伤害路径没接上,要回去反伤害路径,别下"成功"结论。
4. **会不会崩**(空指针/坏 vm)?记下崩溃点。

## 6. 诚实状态

- ✅ **thcrap 机制已对一手源码 + ExpHP 实补丁核实**(§0):binhack 写数据槽可行、`<codecave:>` 绝对地址正确、
  文件结构对齐 ExpHP `th16.v1.00a.js`、注入方式确认。核实中修正了 `[…]`→`<…>` 的真 BUG。
- ✅ 伤害路径已反(`findings/08`,经对抗审计):伤害自动,cave 不写伤害代码。
- ✅ cave 逻辑/ABI/偏移经对抗审计(`NOTES.md`):修了 stdcall 误当 cdecl 的崩溃 BUG;hit=0 证安全。
- ⏳ **唯一剩下的**:把 `tick_tracking_burst_starter.asm` 用 nasm 汇编成字节、组 thcrap patch、**进游戏验**
  (手写 asm 仍需汇编后比对 + 实跑确认不崩、追踪/脉冲/伤害符合预期)。
- 即:从"设计"到"可跑"只差**汇编 + 实测**两步;静态层面已尽可能核实。
