# player 逆向 03:开火门控 / 输入 / 移动 / 聚焦
> **版本**：TH16 v1.00a（`th16.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th18:0x…`。
>

> 方法:Ghidra(ghidra-re MCP)一手反编译 th16.exe(用户自有,ExpHP th-re-data 符号已套)。
> 日期 2026-06-12。分级 ✅高 / 🟡中。**仅 TH16 v1.00a**。
> 本篇补"开火的**上半段**"(输入→门控→cadence)与移动/聚焦;开火**下半段**(do_shooting→shooterset→
> spawn→伤害)在 `engine/sht/th16/07`(shooterset)与 `08`(伤害管线),此处只衔接、不重复。

## 0. 一句话结论

存活态每帧 `player_input_move`(移动 + 聚焦 + 派发已存在弹的 tick),`player_update_perframe` 末尾在
**满足开火大门**时调 `Player__tick_shooting_state`(读射击键 → 推进短/长计时 → 调 `Player__do_shooting`
按 shooterset 发弹)。**聚焦 = `+0x165c8` = `INPUT bit3`**(一手坐实,订正 `engine/sht/th16/07` 的 🟡)。

## 1. 输入全局 ✅

`Supervisor__read_keyboard_input` `0x401d50` 把 DInput/键盘读成一个动作位掩码,经
`InputManager__detect_holds_and_repeats` 生成四个全局:

| 全局 | 地址 | 含义 |
| --- | --- | --- |
| `INPUT` | `0x4a52c8` | 本帧**按住**位 |
| `INPUT_PREV` | `0x4a52cc` | 上帧按住位 |
| `INPUT_RISING_EDGE` | `0x4a52d4` | 本帧**新按下**(上升沿)|
| `INPUT_FALLING_EDGE` | `0x4a52d8` | 本帧松开 |

**动作位**(由本篇各消费点反推,✅值/🟡键名):

| 位 | 动作 | 证据 |
| --- | --- | --- |
| 0x01 | **射击**(shot)| `tick_shooting_state` 读 `INPUT & 1` |
| 0x02 | **主炸**(spellcard bomb)| `player_update_perframe` `INPUT_RISING_EDGE & 2` → 主炸(见 `02`)|
| 0x08 | **聚焦**(focus/低速)| `player_input_move`:`+0x165c8 = INPUT>>3 & 1` |
| 0x10/0x20/0x40/0x80 | 上/下/左/右 | `player_input_move` 9 向(§3)|
| 0x800 | **季节释放**(Season Release)| `player_update_perframe` `INPUT_RISING_EDGE & 0x800`(见 `02`)|

> DInput 重映射的逐键→位映射在 `0x401d50` 内(位运算混淆,未逐键解);上表位值由**消费侧**坐实,够用。

## 2. 开火门控:`Player__tick_shooting_state` `0x4455d0` ✅

**前置大门**(在 `player_update_perframe` 末尾,全满足才调):
```
GUI 不在对话(GUI+0x1c8==0) && 场上有敌(ENEMY_MANAGER+0x18c!=0)
&& (GAME_THREAD+0x88 & 0x4000)==0 && player+0x650 > 0x13(19)
&& (player+0x1664c & 0x4)==0 && (player+0x1664c & 0x10)==0      // 两个"禁射"位(语义见 engine/player/th16/01 §7)
```
→ 否则把射击计时复位(不发弹)。注:`+0x650` 是一个进关后自增的帧计数,>19 才允许开火(开局/复活后的
短暂"不能射"缓冲)。

**函数体**(仅存活态 `+0x165a8==1` 执行):
```c
if (player+0x165d0 < 0)              // 短计时未启动
   if (INPUT & 1) {                  // 按住射击键
      Player__set_shoot_key_short_timer(player, 0);   // 启动短计时(见 §2b)
      ...启动长计时 +0x165e0...
   } else goto 长计时段;
if (player+0x165d0 != player+0x165cc)                 // 计时跨过节拍
   Player__do_shooting(player, player+0x165d0, player+0x165e4);   // ★ 实际发弹(→ ../sht/07)
// 短计时推进:<0xe(14)自增;到顶后松键复位 -1、按住则环绕到 0xe
// 长计时(+0x165e4):封顶 0x76(118)/0x77,管"长按"分支
```
- `+0x165cc/d0` = **短射击计时**(prev/cur);`+0x165e0/e4` = **长按计时**。两者一起决定**开火节拍 cadence** 与
  连射状态,然后把"当前计时值"传给 `Player__do_shooting` 当帧相位(对应 `engine/sht/th16/07` 里
  `frame_main % fire_rate == start_delay` 的 `frame`)。
- **`Player__set_shoot_key_short_timer` `0x440d50`**:把短计时初始化为给定值(`+0x165d0=v`、`+0x165cc=v-1`、
  `+0x165d4=(float)v`)——按下射击键瞬间归零起拍。

> 衔接:`do_shooting` 之后的"选 shooterset(火力×聚焦)→ 遍历 shooter → `shoot_one_bullet` → spawn 灌字段
> → 建伤害源"全在 `engine/sht/th16/07`(组织)+ `08`(伤害)+ `03/04`(func_* 行为),本篇不再展开。

## 3. 移动 + 聚焦:`player_input_move` `0x441cf0` ✅

每帧(存活态,由 `player_update_perframe` 状态 1 调)。

**9 向方向 `+0x2c780`**(0..8)由方向位组合得出:`0x10=上 0x20=下 0x40=左 0x80=右`,对角线取组合
(如上+左→5、下+左→7、上+右→6、下+右→8;纯方向 1=上/2=下/3=左/4=右;无=0)。

**聚焦 `+0x165c8`** ✅(★订正 `engine/sht/th16/07` §4 的 🟡):
```c
if (场上有敌 && player+0x63c >= 4)  player+0x165c8 = INPUT>>3 & 1;   // = 聚焦键(bit3)是否按住
else { player+0x165c8 = 0; player+0x16680 = 0x1e; }                  // 无敌/开局强制非聚焦
```
→ **聚焦标志直接来自输入 bit3**,不是别的。它驱动:① shooterset 选 set 0–4(非聚焦)/5–9(聚焦)
(`../sht/07`);② 激光收拢(`../sht/03` §6.7);③ 判定/移速缩放;④ 显示判定点指示(anm 0x1a @ `+0x165ac`)。

**移速**:从 4 档里按"聚焦 × 直/斜"选:
```
非聚焦·直 = +0x16650   聚焦·直 = +0x16654
非聚焦·斜 = +0x16658   聚焦·斜 = +0x1665c
```
这 4 档进关时从主 .sht header 的 `move_*`(`+0x10/14/18/1c`,见 `../sht/05` §2b)× 缩放装入。
→ **移速是真·数据驱动**(改 .sht 有效)。

**位置积分 + 边界钳制** ✅:
```c
player+0x61c(定点 x) += vx;  player+0x620(定点 y) += vy;
clamp x ∈ [-0x5c00, 0x5c00];  clamp y ∈ [0x1000, 0xd800];     // 定点(×1/128)
player+0x610(float x) = x/128;  player+0x614 = y/128;
```
→ **游玩区边界**(屏幕坐标):x ∈ [−184, +184],y ∈ [+8, +432](= 定点 /128)。

**末尾派发已存在的弹**(每帧让 shot 槽自己 tick,见 `../sht/04`):
```c
playershot_tick_dispatch(player, player+0x660, 4);   // 主弹槽 ×4
playershot_tick_dispatch(player, player+0x9f0, 8);   // 子机/option 槽 ×8
```
并维护聚焦判定点指示(anm 0x1a `+0x165ac`)与聚焦光环(anm 0x1b `+0x165b0`)两个特效。

## 4. 一帧自机时序(整合 `engine/player/th16/01` + `../sht/04`)

```
player 任务 0x443720
  └─ player_update_perframe 0x442560  (switch +0x165a8)
       case1 存活:
         ├─ 按炸/季节释放(INPUT_RISING_EDGE&2 / &0x800)→ Bomb::activate(见 02)
         └─ player_input_move 0x441cf0:9 向移动 + 聚焦(+0x165c8) + 边界钳制
                                         + playershot_tick_dispatch(已存在弹 tick)
       …(状态无关下半段)…
         ├─ 伤害源池 256 更新(../sht/08)、无敌帧倒计时 + 闪烁(engine/player/th16/01 §3)
         ├─ 判定矩形世界角点重算、帧计数自增
         ├─ 满足开火大门 → Player__tick_shooting_state 0x4455d0
         │      └─ 读 INPUT&1 → 推进短/长计时 → Player__do_shooting 0x445470
         │            └─ 选 shooterset → shoot_one_bullet → spawn → 建伤害源(../sht/07,08)
         └─ Player__tick_bullets 0x4456d0(逐弹 func_on_tick 派发 + 伤害源刷位置,../sht/04,08)
```

## 5. 可信度 / 复核

- ✅ 一手:`Player__tick_shooting_state`(`0x4455d0`)、`Player__set_shoot_key_short_timer`(`0x440d50`)、
  `player_input_move`(`0x441cf0`)、`Supervisor__read_keyboard_input`(`0x401d50`)本会话反编译;开火大门来自
  `player_update_perframe`(`0x442560`)调用点。
- ✅ **聚焦 = `+0x165c8` = INPUT bit3** 一手坐实 → 把 `engine/sht/th16/07` §4 的 🟡 升 ✅。
- 🟡 DInput 逐键→位映射未解(位值由消费侧坐实);`+0x650/+0x63c` 计数的精确语义只取了"门控阈值"。
- 复核入口:Ghidra DB `th16`,地址见上。开火下半段交叉 `engine/sht/th16/07,08`。
