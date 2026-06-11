# 03 — TH16 激光子系统(EX_LASER)

> **对象**:TH16《鬼形兽》`th16.exe`,imagebase `0x400000`。日期 2026-06-09。
> 来源:主控 inline 钉锚点(构造器 + RTTI vtable 名)→ 子 agent 深挖 → 主控**一手复核碰撞几何**。
> 可信度 ✅一手 / 🟡 agent 单源未逐个亲反 / ❓存疑。仅 TH16。
>
> 激光由弹 VM 的 **opcode `0x8000000`(EX_LASER)** 生成(见 `01-core-engine.md` §3)。它不是弹池对象,
> 是**独立对象类**,住在**激光管理器 `DAT_004a6ee0`**(≠弹 `DAT_004a6dac`、≠敌 `DAT_004a6dc0`)。

## 0. 速览

- **5 个激光类**(名来自 exe 的 MSVC RTTI vtable,= 二进制自带,强证):`LaserLineInf`(线)、`LaserInfiniteInf`(无限/激光柱)、`LaserCurveInf`(曲线/蛇)、`LaserBeamInf`(粗 beam)、`LaserDataInf`(公共基类,全 stub)。
- **EX_LASER 只生成线(`a=0`)和无限(`a=1`)**;**曲线/beam 由别处生成**(未在弹 VM 的 0x8000000 里,待查 → 疑 ECL 直接生成)。
- **碰撞 = 旋转 OBB**(把自机转进激光局部系测长×宽盒),✅ 主控亲验,与弹的圆/矩形判定**不同**。命中调同一个 `player_on_death`(`0x443f10`)。
- vtable 驱动:每帧 tick / draw / collide / graze / split / death 各占一个槽。

## 1. 类 / vtable / 构造器(✅ RTTI 名 + 一手)

| 类 | vftable | 对象大小 | 构造器 | EX_LASER |
| --- | --- | --- | --- | --- |
| `LaserLineInf` | `0x492424` | `0x1b20` | `0x431130` | `a=0` 线激光 |
| `LaserInfiniteInf` | `0x4923b8` | `0x1548` | `0x431860` | `a=1` 无限激光柱 |
| `LaserCurveInf` | `0x4922e0` | `0x1b20` | `0x431900` | ❓ 非 0x8000000 生成 |
| `LaserBeamInf` | `0x49234c` | ~`0x1b20` | `0x4318c0` | ❓ 非 0x8000000 生成 |
| `LaserDataInf` | `0x492490` | — | — | 公共基类(vtable 全 stub) |

公共基类 ctor `0x430fc0`;ANM 子精灵 init `0x4093f0`(线 3 个子精灵 body/head/tail,无限 2 个)。

## 2. vtable 槽职能(🟡 agent 枚举,主控验了碰撞槽)

> 槽 N = vtable + N×4。下表以 LaserLine / LaserInfinite 为例。

| 槽 | 职能 | LaserLine | LaserInfinite |
| --- | --- | --- | --- |
| 1 | 每帧 UPDATE(跑自身 VM/移动) | `0x431fe0` | `0x436fd0` |
| 3 | INIT(= vtable+0xc,spawn 后调,灌帧字段) | `0x431b30` | `0x435050` |
| 4 | **每帧主调度**(调 update + 碰撞 + 状态机) | `0x432f40` | `0x4352f0` |
| 5 | DRAW | `0x433720` | `0x4357a0` |
| 7 | GRAZE 循环(逐段计擦弹) | `0x434010` | `0x436010` |
| 8 | 命中伤害派发 | `0x433860`(ret0) | `0x435880` |
| 13 | **玩家碰撞 hit-test**(→ `0x443af0`) | `0x433510` | `0x435610` |
| 10 | 死亡/清除特效 | `0x434cd0` | `0x436c70` |
| 20 | 线激光屏缘**分裂/绕环**(到屏边生子段) | `0x432620` | (stub) |

## 3. 对象结构(✅ 基类偏移一手;🟡 部分子类字段 agent)

**公共基类**(ctor `0x430fc0`):`+0x10` 状态(1 扩张/2 满/4 收缩/5 完)、`+0x14` 链表 next、`+0x54/58/5c` **起点 xyz**、`+0x60/64/68` 速度、`+0x6c` **角**、`+0x70` **当前长度**、`+0x74` **当前半宽**、`+0x78` 扩张速率、`+0x7c` 枢轴偏移、`+0x80` 句柄、`+0xb0` 擦弹计时。

**LaserInfinite 时序状态机**(✅ `0x4352f0`):`+0x181` start_time、`+0x182` expand_time、`+0x183` duration、`+0x184` stop_time、`+0x17c` 角速。状态 `3 等待→4 扩张(宽线性增)→2 满→5 收缩→free`。**碰撞只在 state 4/2 生效**(等待/收缩期无判定)。

## 4. ★ 玩家碰撞 = 旋转 OBB(✅ 主控一手复核 `0x443af0`)

```c
// player_collide_laser_obb(this, laser_origin_xy, half_len_bound(param_2), invuln(param_3)), 角∈XMM2, 半宽∈XMM3
dx = player_x(+0x610) - origin_x;  dy = player_y(+0x614) - origin_y;
s = sin(-angle); c = cos(-angle);                 // crt_sinf/crt_cosf(角取反 ^DAT_00494890)
along = dy*s + dx*c;   perp = dx*s - dy*c;         // 把自机转进激光局部系
if ( perp - hitX·K <= half_len  &&  along - hitY·K <= width·0.5
  && 0 <= perp + hitX·K        &&  width·(-1) <= hitY·K + along ) {   // 命中盒(自机判定框 +0x2c748/+0x2c74c 撑大)
   if (落在外圈带) return 2;                        // 擦弹
   if (非安全 && param_3==0 && 自机非死/复活(+0x165a8∉{2,3,4}) && 非无敌(+0x1663c<1))
       { player_on_death(player); return 1; }        // 命中 → 自机死(同弹的死亡函数!)
}
return 0;
```

→ 这是把自机平移差**旋转进激光局部坐标**后,对 `[0,长度]×[-宽,+宽]` 盒做判定的 **OBB**;命中/擦弹/未中三态,命中调 `player_on_death`,无敌/状态门与弹判定**逐项一致**。**与弹的圆(`0x4439e0`)/矩形(`0x4438c0`)判定是不同算法。** ✅

- 线激光 wrapper `0x433510`:据 `+0x608&2` 选"中点"或"原点"为判定中心;命中每 3 帧调一次 `FUN_00444cf0`(擦弹计分)。
- 无限 wrapper `0x435610`:state∈{4,2} 且长度>0 才判;半宽传 `+0x70 × ~0.5`。

## 5. 线 vs 无限(✅/🟡)

| | LaserLine `0x1b20` | LaserInfinite `0x1548` |
| --- | --- | --- |
| 生命周期 | 定长段,匀速增长到 `length=m` | 4 段状态机(等待/扩张/满/收缩) |
| 时序参数 | 无 | start/expand/duration/stop_time |
| 子精灵 | 3(body/head/tail) | 2(body/head) |
| 屏缘 | 槽20:出屏+对侧重入,边界处生新段 | 无 |
| shot/transform 音 | 来自 ECL 参数 `a2`/`b2` | **硬编码 18 / −1**(spawn 里 `0x12`/`0xffffffff`) |
| 宽度 | 固定 `s2` | 0→`r2` 扩张再收缩 |

## 6. EX_LASER 参数布局交叉验证(✅✅ 与 `../ecl/ECL-info.md` 逐位吻合)

无限激光(`a=1`)spawn 帧(弹 VM `0x413860` 的 `0x8000000` 分支)**逐位实测吻合社区**:`flags=(d&0xFD)|2`(`instr[7]`)、`effect_index=(d&0xFF00)>>8`、`delete_current=(d&0x10000)>>16`、`start/expand/duration/stop=instr[5/6/0xf/0x10]`、`shot_sound=18`、`transform_sound=-1`。线激光(`a=0`):`sprite/color/delete=instr[4]` 字节、`shot_sound=instr[5]`、`transform_sound=instr[6]`、角/速走 ±999990 阈值族。**这是 EX_LASER 在 exe 里的强佐证。**

## 7. 管理器(🟡 agent)

`DAT_004a6ee0`:`+0x14` 活动链、`+0x5e0` ring 头、`+0x5e4` 计数(cap `0x200`=512)、`+0x5e8` 句柄序(起 `0x10000`)、`+0x608` 擦弹累计。
> ⚠️ **更正(2026-06-09;th-re-data 对照 + 反编译裁决,见 `../ecl/03-thredata-crosscheck.md` §3)**:`FUN_004313b0` **不是**每帧 tick,实为 **`LaserManager::destructor`**(释放 `+4`/`+8` 子链 + `FUN_0042cb00` + 末尾 `g_laser_mgr=0`)。先前"game loop `FUN_0042d200`→0x4313b0 tick"标注**双重有误**:`0x4313b0` 是析构;`FUN_0042d200` 也**不是 game loop**(ExpHP=`GameThread::destructor`)。真主循环=`Window::do_frame`→`run_all_on_tick`(`../shared/th16-main-loop.md`);真正的激光每帧 tick 待重新定位(应是某 `on_tick_NN` 回调)。

## 8. 开放 / 待挖

1. **LaserCurveInf / LaserBeamInf**:曲线/beam 激光本体只读了 vtable,**生成路径未找到**(非 0x8000000)→ 疑 ECL 直接生成,留 `../ecl/`。曲线段更新链 `0x437ee0/0x438370` 未反。
2. **graze 计分公式**(`0x434010`):增量 `+0x608` 的具体算法(随宽/色/缩放)未化简。🟡
3. **`0x443af0` 里 `DAT_004945e0/0049449c/0049471c`** 撑大自机判定框的标量未 PE 实测(≈1/1/−1)。🟡
4. **`playershot_tick_laser_idx2`(`0x446260`)** 是**自机激光**,与敌激光是两套,未碰。

## 关联
- 生成来源:`01-core-engine.md` §3 opcode `0x8000000` + §8 EX_LASER。
- 弹 VM 模型(激光是其 spawn 的产物):`02-bullet-vm-model.md`。
- ECL 参数:`../ecl/ECL-info.md`(EX_LASER 段,已交叉验证)。
- 落盘脚本:`../sht/disasm/scripts/apply_th16_bullet_names.py`。
</content>
