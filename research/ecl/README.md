# research/ecl/ — TH16 ECL(敌机/弹幕脚本)VM 逆向(新会话入口)

> 本文件夹专做一件事:**逆向 TH16《鬼形兽》(`th16.exe`,imagebase `0x400000`)的 ECL 系统**——
> 即 `.ecl` 字节码的**虚拟机(VM)**与运行时:敌机/Boss/关卡脚本怎么被解释、**开火指令怎么把参数喂给
> 弹幕引擎**(`../bullets/`)。ECL 是东方 gameplay 逻辑的顶层脚本(enemy control language)。
> 你若是**新 Claude 会话**,读完这份 README 应知道目标、规范、环境、和**从哪一刀切**。
>
> ⚠️ **现状**:本文件夹**尚未系统开工**。下面的锚点是做弹幕引擎(`../bullets/`)时**顺到的边界**,
> 多为 🟡(xref 级 / 单源),**动手时务必自己反编译复核**,别当定论。

## 这是什么 / 三套 VM 的位置

TH16 运行时至少**三套字节码 VM**,别混:
1. **ECL VM**(本文件夹)= 顶层 gameplay 脚本:驱动敌机/Boss/关卡、**发出开火/移动/spawn 指令**。
2. **弹运动 VM**(`../bullets/` 已解,`0x413860`)= 每颗弹自带的小段运动脚本(加速/转向/反弹…)。
3. **ANM VM**(`../anm/`)= 显示/精灵动画脚本。

ECL 在最上层:**ECL 的"开火"指令 → 创建弹对象 + 灌运动字节码**,这就是 ECL↔弹幕的接缝(见 §A)。

## 目标

1. **ECL VM 主体**:opcode switch 解释器在哪、指令格式、PC/sub/timeline 机制、虚拟寄存器/变量。
2. **opcode 表**:逐 opcode → 行为(设变量/算术/跳转/wait/spawn 敌人/开火/设运动/调用 sub)。
3. **开火接口**:ECL 开火指令如何把参数(角/速/弹型/散布/anm)映射到弹对象字段(`../bullets/01` §5 字段图)。
4. **格式 ↔ 运行时**:把运行时 opcode 与 **`thecl.exe`(thtk)** 反汇编出的 ECL 指令号/语义对应,产出"指令号→行为"表。

## 规范(与父工作区一致)

- **五段证据链**(发现→推测→验证→结论(可信度+版本)→证据(地址/出处)):`../sht/findings/00-METHOD-逆向记录纪律.md`。
- **可信度** ✅一手实证 / 🟡单源或推断 / ❓存疑;**结论必注版本(仅 TH16,勿外推)**。
- **防过拟合**:派子 agent 命名给中立判据、不喂标签;"反超社区"自创结论按四闸门复核;验证前往下取整标 🟡。
  (memory `re-overclaim-guard` / `re-agent-no-hypothesis-priming` / `re-evidence-chain-discipline` / `re-workflow-fanout-cost`)
- **主仓库不留版权字节**:游戏 exe / .ecl 资产 / 大段反编译原文一律 gitignore;只提交脚本 + markdown。

## 环境(已就绪,与父工作区共用)

- **ghidra-re MCP**,database `th16`(已分析,含 SHT/数学/**弹幕**模块命名)。MCP rename+comment+save 跨会话可靠落盘;数据符号真改名走 headless `apply_*.py`。
- 常量/字节可直读 PE:`../files/th16.exe`。
- 落盘:命名脚本 `../sht/disasm/scripts/apply_th16_ecl_names.py`(建议,待建);文档 → 本文件夹。

## 起步锚点(starting points)— 来自 `../bullets/01-core-engine.md`(2026-06-09)

### A. ★ ECL → 弹幕 开火接缝(🟡 xref 级,最佳第一刀)
- 弹 spawn `FUN_00412cb0`(从池取槽 + 灌 `obj+0xc88` 字节码)**唯一**被 `FUN_00414da0` 调。
- `FUN_00414da0`(弹 spawn 包装)的调用方 4 个:
  - `FUN_00413860`(弹 VM 自身,opcode 0x2000 子弹分裂——内部,**不是** ECL)。
  - **`FUN_0041dcb0`**(@0x420aa0)、**`FUN_00431fe0`**(@0x432465)、**`FUN_00438cb0`**(@0x4391b0)= bullet_spawn_wrapper 的外部调用方。⚠️ **更正(ExpHP 对照)**:只有 **`0x41dcb0` 是 ECL**(`EnemyData::ecl_run_over_300`,游戏 opcode 派发,开火接缝见 `05`);**`0x431fe0`=`LaserLine::method_4`、`0x438cb0`=`LaserCurve::method_4`(激光的 et_ex 方法,非 ECL handler)**。早期"3 个都疑 ECL 开火 handler"的猜测有误。
- **第一刀**:反这 3 个外部调用方——它们读什么参数(角/速/弹型/anm)灌进 spawn 描述符 `param_2`(`+0x28` 起是弹字节码、`+0x378` 是初始 PC)。
- ✅ **`FUN_0041dcb0` 身份已定**(ExpHP th-re-data + deep research,2026-06-09)= **`EnemyData::ecl_run_over_300`** = ECL **opcode ≥300(enmCreate/move/anm/et*…)处理器**,正是 fire/spawn handoff 入口;enmCreate=`0x423050 ecl_enm_create`、激光=`0x4319e0 ecl_545`。详见 **`02-runtime-vm.md`** §3。

### B. ~~ECL opcode 派发表~~ → 实为**变量访问器表**(已纠正,见 `01-ecl-context-and-variables.md`)
- ❌ **旧假设推翻**:`0x4921b4` **不是** opcode 派发表。一手反 `FUN_00424110` + Priw8 双证(2026-06-09):它是 **ECL 变量访问器表**(`0x4921ac..` 一族:读特殊变量 / 取左值地址)。
- ✅ **由此坐实**:`FUN_00424110`=按负 id 读 ECL 特殊变量;**ECL 上下文结构(=敌机对象)字段图**已解一大片(I0-3=`ctx+0x1498..`、F0-3=`ctx+0x14a8..`、移动态 `+0x125x..+0x12fx`);玩家 `DAT_004a6ef8+0x610/614`、难度 `DAT_004a57b4`、管理器 `DAT_004a6dc0` 字段。**详见 `01-*`。**
- ✅ **opcode 解释循环已反编译**:`EclRunContext::ecl_run`(`0x472030`)—— 全部系统 opcode(0–0x5d:RET/CALL/CALL_ASYNC/GOTO/IF/算术/比较/栈/数学)运行时语义 + time 门控 + rank 过滤 + 段式派发(游戏码走 vtable[0]=`ecl_run_over_300`)。**详见 `04-ecl-vm-interpreter.md`**(社区未公开过这块;且 Priw8 eclmap 第 4 源印证 opcode 名)。
  - ⚠️ 游戏 opcode 名+签名已被 **Priw8 `vendor/th16.eclmap`(298 条)** 全覆盖,行为多在 `ECL-info.md` → 全反 `ecl_run_over_300` 边际价值有限。**下一刀选择性挖**:ECL 开火 opcode(Et_* 600 区 / `ecl_enm_create`)→ 弹幕 fire 描述符字段映射(接 `../bullets/01` §6,exe 才有的接缝)。

### C. 敌机侧(ECL 的宿主,🟡 继承旧文档)
- 敌人管理器 `DAT_004a6dc0`(+0x180 链表头 / +0x18c 计数 / +0x15c 游标)。
- 敌人对象 ~`0x574c`(独立 `operator_new`),`FUN_0041aa70` spawn 进敌人链;每帧更新疑 `FUN_0041c330`(findings/06 §4)。
- 敌机大概率是 **ECL 脚本的宿主**(每个敌机跑一段 ECL sub);确认"敌机结构里的 ECL PC/脚本指针"是关键。
- ⚠️ **别和弹搞混**:弹管理器 `DAT_004a6dac`(差一位!),弹对象 `0x1478`、池内嵌;敌机 `DAT_004a6dc0`、`0x574c`、堆分配。

## ★ ECL-info.md(社区 etEx 速查,已与本仓库 VM 交叉验证)

- **`ECL-info.md`**(本目录,来自 thcrap 社区 Discord)= ECL 指令速查 + **`etEx` 子弹效果表**(EX_* 代号 + 参数语义)+ 子弹 Sprite/颜色表 + 敌人指令(enmCreate/move*/anm*)。
- **已确立的桥梁**(见 `../bullets/01-core-engine.md` §8,2026-06-09):**`etEx` 的效果 = 弹运动 VM(`bullet_vm_exec` 0x413860)的 opcode**;`obj+0xc68` == etEx 效果位场;社区"旧 etEx"位值 == 我反出的 opcode 整数,**~28/28 吻合**。即:**一颗弹的字节码(`obj+0xc88`)= 发射器编译好的一串 etEx 效果**。`etEx(id,...,type,a,b,r,s)` 的 `type`=EX_=opcode,`a/b/r/s`=指令字段。
- **由它解开的**:`+0x141c`=EX_SIZE 尺寸、`+0x24`=EX_INVULN、`0x8000000`=**EX_LASER**(子对象其实是激光,线/无限两型)。
- ✅ **参数分支已二次验证**(2026-06-09,见 `../bullets/01-core-engine.md` §8.1):EX_ANGLE 的 c 子模式、EX_SAVE 存档机制、EX_VEL/VELTIME、基础角阈值——**TH16 实测吻合**。但 ❌ **两处 ECL-info 对 TH16 是错的**(像是后作文档):① 所谓 EX_ACCEL/VELTIME 的"7 档角度阶梯"(`1999990/2999990/...` 配 RANDF2/boss 角)**在 TH16 不存在**(常量全文搜不到,只有 ±999990 与 9999990);② EX_ANGLE c=7 阈值实测是 `990` 不是 `999`。**ECL-info 是社区单源(Discord)、跨版本**,冲突以 TH16 exe 为准。
- **et* 发射器指令**(etNew/etOn/etAim/etCount/etSpeed/etAngle/etEx/etSprite…)= 配置发射器→`bullet_pool_spawn` 的 fire 描述符(`../bullets/01` §6 已逐字段解);**第一刀**可对着 ECL-info 的 etAim mode 0-12 / etCount 路数·层数,去 exe 里核 spawn 描述符 `[0xda]`散布模式 / `[0xd9]`数量的对应。

## 社区对照(关键:有 thecl 可交叉印证)

- **`thecl`**(thtk,`thpatch/thtk` @ `892114a0`,BSD):ECL 的反汇编/重编译器,**有完整 opcode 表与格式定义**(C 源)。
  把"运行时 opcode"对到"格式指令号"的**权威外部锚点**——逆向时**先看 thecl 的 ins_ 表**,再去 exe 核对实现。
  - ★ **已克隆 + 消化** → `vendor/thtk/`(gitignore,可重克隆)+ **`00-thecl-format-reference.md`**(.ecl 二进制格式 / TH16 opcode→参数格式全表 / VM 机器核低位 opcode / ECS→opcode 降级 / eclmap 命名层 / 怎么驱动 exe 逆向)。**动手反 exe 前先读 `00-*`。**
- **父仓库已有现成资源**:`../../src-tauri/src/modules/ecl/`(THTK-Studio 自己的 thecl 封装/error_parser/eclmap),`../../tools/thecl.exe_ghidra/`(thecl.exe 的 Ghidra 工程,理解 .ecl 格式编译侧)。
- **★★ ExpHP `exphp-share/th-re-data`**(已克隆 `vendor/th-re-data`):**TH16 专属(`data/th16.v1.00a/`)结构体 + 命名 VM 函数地址表**——`zEclVm`/`zEclRunContext`/`zEclStack`/`zEclLocation` 布局 + `ecl_run`(0x472030)/`call_sub`/`ecl_run_over_300`(0x41dcb0)等 45 个 ECL 函数地址。**可直接导进 Ghidra**(下一步 `apply_th16_ecl_names.py`)。**当前最硬的 TH16 运行时一手源。** 详见 `02-runtime-vm.md`。
  - ⚠️ **粒度 = 仅符号名 + 结构体偏移,无语义注释**(932/1930 函数命名,`comment` 字段 0 条):它给"叫什么/字段在哪",**不给"干什么/参数含义/opcode→行为"**。覆盖重 ANM/laser/ecl/bullet,**SHT 几乎为零**。已验证:我们深挖的弹幕函数它都命名了(身份对上),但语义层(EX handler 每帧算什么、c68 位场、SHT 全部)仍是我们的原创产出。**当命名层用,语义层自己做。**
- **★ Priw8 ECL 文档站**(`priw8.github.io`,源码 `github.com/Priw8/priw8.github.io`):**特殊变量全表**(`js/ecl/vars.js`,逐作负 id + rw/scope)、`content/modding/ins.md`、**`eclmap-16.md`(TH16 指令名)**、`transforms.md`(etEx)、`ecl-tutorial/`(每敌机解释器模型)。已与本仓库 exe **逐项吻合**(见 `01-*`)。
- 速查 `../shared/touhou-modding-sources.md`;参考仓库克隆走 `vendor/`(gitignore)。
- ⚠️ thecl 给**格式**语义;**运行时**实现(VM 怎么解释、各 opcode 在 exe 里干啥)仍须在 th16.exe 自证。
  且 TH16 是新作,opcode 集与老作有别,以 thecl 对 TH16 的支持为准。

## 产出(现状 2026-06-10)

- ✅ `00-thecl-format-reference.md`(格式/opcode 表)· `01-ecl-context-and-variables.md`(变量/上下文)· `02-runtime-vm.md`(运行时结构+函数地图)· `03-thredata-crosscheck.md`(vs ExpHP 审计)· **`04-ecl-vm-interpreter.md`**(★ `ecl_run` 派发循环一手)· **`05-fire-interface.md`**(★ 游戏 opcode 派发 + ECL et*→弹幕 fire 描述符接缝)· **`06-adding-custom-instructions.md`**(★ 如何加自定义 ECL 指令:参考 ECLplus + TH16 钩点 0x41DD3A)· **`07-vm-architecture.md`**(★★ 宏观总览 + 核心机制确定性表,先读这篇看全局)。
- ✅ `../sht/disasm/scripts/apply_th16_ecl_names.py`(ECL 函数命名,MCP 已落盘)。
- **VM 核心已基本通**:格式↔运行时、解释循环、变量模型、ECL→弹幕接缝全打通;未公开 opcode 仅低位系统码 18/19/20/41。
- **下一步选项**:① 回填 `../../docs/`(驱动 IDE);② ExpHP 指路的待挖区(敌人 tick/spell/anm VM);③ 18/19/20/41 异步语义细挖。

## 关联

- ★ 接缝来源:`../bullets/01-core-engine.md` §6(spawn `FUN_00412cb0` / 字节码源)、§7 开放问题 1。
- 弹运动 VM(ECL 下游):`../bullets/01-core-engine.md` §3(opcode 表)。
- ANM 显示 VM(另一独立 VM):`../anm/README.md`。
- PRNG/数学(ECL random opcode 用):`../shared/th16-engine-math.md` §3。
- 旧切口(二手,待复核):`../sht/findings/06-th16-engine-incisions.md`(§4 敌人);自机弹 ECL 锚点 `../sht/findings/03/04`。
- 纪律:`../sht/findings/00-METHOD-逆向记录纪律.md`;memory `re-overclaim-guard` / `re-agent-no-hypothesis-priming` / `re-evidence-chain-discipline` / `re-workflow-fanout-cost`。
</content>
