# 03 — 本仓库 RE vs ExpHP th-re-data 交叉验证(靠谱度审计)

> **目的**:把我们独立反出并命名的函数(`apply_th16_bullet/math/sht_names.py` = 我们 committed 的结论)
> 逐个对到 ExpHP `th-re-data`(`data/th16.v1.00a/funcs.json`,社区一手 RE 符号表)的命名,**检验我们靠不靠谱**。
> **方法**:脚本提取我们 111 个 (addr, name),查 ExpHP 同址名,并排比对 + 对真冲突就地反编译裁决。日期 2026-06-09。
> **结论(下面详述)**:**高度一致** —— 68 个双方都命名的函数里绝大多数语义吻合(连弹幕 step_ex_NN 的 EX 索引、PRNG 函数名都精确对上);真冲突仅 2 处,裁决为 **1 我们错 / 1 ExpHP 猜错**;另有一批我们做了而 ExpHP 留空(尤其整个 SHT 运行时)。

---

## 1. 统计

| | 数 | 说明 |
| --- | --- | --- |
| 我们命名的条目(含数据符号) | 111 | bullet 45 / math 47 / sht 19(去重后) |
| 双方都有真名(function) | 68 | 见 §2 大多语义吻合 |
| 我们命名、ExpHP 留 `sub_*` 占位 | 1+ | 我们更细(如 player_collide_rect) |
| 不在 ExpHP `funcs.json` | 42 | **多为数据符号**(f_* 常量 / g_* 全局,funcs.json 只收函数,它们在 statics.json)+ 我们原创的 SHT 表 |

> ⚠️ "不在 funcs.json" 对数据符号是**预期**(类别不符,非分歧);SHT 的 func_*/effect 表是我们原创(§4)。

---

## 2. 双方都命名:语义吻合度(抽样)

**精确/强吻合(独立印证我们没反错)**:
| 地址 | 我们 | ExpHP | |
| --- | --- | --- | --- |
| 0x413860 | bullet_vm_exec | `Bullet::run_ex` | ✅ run_ex = 跑 EX 效果 = 我们的运动 VM |
| 0x412cb0 | bullet_pool_spawn | `BulletManager::shoot_one` | ✅ |
| 0x411e70 | bullet_tick | `Bullet::on_tick` | ✅ |
| 0x4439e0 | player_collide_circle | `kill_player_in_circle` | ✅ |
| 0x443f10 | player_on_death | `Player::die` | ✅ |
| 0x417510 | vec2_from_polar | `cartesian_from_polar_417510` | ✅ |
| 0x402cb0 | prng_randf_signed | `Rng::randf_neg_1_to_1` | ✅✅ 精确 |
| 0x402c70 | prng_randf_unit | `randf_0_to_1` | ✅✅ |
| 0x402cf0 | prng_rand_angle | `randf_minus_pi_to_pi` | ✅✅ |
| 0x402be0 | prng_gameplay_draw | `rand_int` | ✅ |
| 0x403110 | motion_update_mode_full | `PosVel::step` | ✅ |
| 0x443790 | sht_parse_resolve_funcptrs | `read_sht_file_443790` | ✅ |
| 0x440fb0 | player_shot_init | `Player::initialize` | ✅ |

**★ 弹幕 10 个行为 handler —— 与 ExpHP 的 `step_ex_NN` 命名独立吻合(NN = EX 效果索引)**:
| 地址 | 我们(c68 位) | ExpHP | EX 索引核对 |
| --- | --- | --- | --- |
| 0x414fb0 | accel_vec (0x4) | `step_ex_02` | EX_ACCEL=2 ✅ |
| 0x4153e0 | turn_accel (0x8) | `step_ex_03` | EX_ANGLE_ACCEL=3 ✅ |
| 0x415570 | speed_angle_transition (0x10) | `step_ex_04` | EX_ANGLE=4 ✅ |
| 0x415bb0 | wall_bounce (0x40) | `step_ex_06` | EX_BOUNCE=6 ✅ |
| 0x4162d0 | offscreen (0x100) | `step_ex_08` | EX_OFFSCREEN=8 ✅ |
| 0x415d80 | wrap (0x1000) | `step_ex_12` | EX_WRAP=12 ✅ |
| 0x415f90 | move_to_point (0x20000) | `step_ex_17` | EX_MOVE=17 ✅ |
| 0x4161f0 | add_displacement (0x80000) | `step_ex_19` | EX_VELADD=19 ✅ |
| 0x4151e0 | speed_ramp (0x200000) | `step_ex_21` | EX_VELTIME=21 ✅ |
| 0x414ec0 | speed_boost (0x1) | `step_ex_00` | bit 0 ↔ index 0 ✅ |
> 我们按 **c68 位掩码** 命名、ExpHP 按 **EX 索引(位序号)** 命名,**两套独立体系逐一对齐**(bit 2^n ↔ index n)。这是对我们整张弹幕 opcode→行为表最强的外部确认。

---

## 3. 真冲突(2 处)——已反编译裁决

**① `0x4313B0`:我们错了,ExpHP 对。**
- 我们:`laser_mgr_tick`(每帧 tick);ExpHP:`LaserManager::destructor`。
- 反编译裁决:函数释放 `mgr+4`/`mgr+8` 两个子对象、调 `FUN_0042cb00`、**末尾 `g_laser_mgr = 0`** + SEH 框架 → **析构无疑**(每帧 tick 不会把全局管理器置 0)。
- **行动**:已修 `../bullets/03-lasers.md`(0x4313B0 改注为析构;真正的激光每帧 tick 待重新定位)。

**② `0x445E20`:ExpHP 猜错(它自己标了 `i_think`),我们更靠谱。**
- 我们:`playershot_launch_shared`(shot 发射/特效收尾);ExpHP:`PlayerBullet::sub_445e20__collide__i_think`。
- 反编译裁决:**无任何距离/判定框比较**(不是碰撞);而是经我们识别的 `effect_behavior_dispatch_table`(0x491b0c)派发 + 设置 shot 特效对象(`+0x490=1`、缩放 `+0x60`、`+0x8c=2`)→ launch/特效收尾。**ExpHP 的 collide 猜测不成立**;我们的读法证据更足(🟡 精确角色仍可再挖,但"非碰撞"确定)。

---

## 4. 我们做了、ExpHP 留空的(我们的增量)

- **占位未命名**(ExpHP 留 `sub_*`,我们已定性):`0x4124b0` bullet_vs_player_collide、`0x412670` bullet_pool_free、`0x4438c0` player_collide_rect(ExpHP 只到 `sub_..._may_kill_player`)。
- **ExpHP funcs.json 没有**:`0x443af0` player_collide_laser_obb(旋转 OBB 激光判定,我们一手亲验)。
- **整个 SHT 运行时(原创,th-re-data 几乎零覆盖)**:`sht_func_init/tick/hit_table`(0x4919c0/9a0/980)、`effect_behavior_dispatch_table`(0x491b0c)、playershot 的 homing/laser/curve 分支(0x445ee0/446260/446e00)、`find_nearest_enemy`(0x425240)等——这些是本项目的核心产出,ExpHP 不含。
- **语义层全是我们的**:ExpHP 只给名,EX handler 每帧算什么、c68 位场、fire 描述符字段、SHT func_* 跳转表语义、与社区 etEx/Priw8 交叉验证——都是我们做的。

---

## 4b. 函数覆盖反向 diff(Ghidra 全量 vs funcs.json)

从 Ghidra 实际 DB 拉全部**非默认名函数 631 个**(总函数 1764),与 ExpHP 有意义命名 886 个 diff:
- **484 个不在 ExpHP 命名集**,但其中 **469 个是 CRT/MSVC 运行时**(`__scrt_*`/SEH/`FID_conflict`/`exception`…,Ghidra 签名库自动命名,非研究、ExpHP 也不标)。
- **真正"我们标了、ExpHP 没标"的游戏逻辑函数 ~10 个**(其余我们命名的都在 ExpHP 集里 = 大量重叠 = ExpHP 函数覆盖很广):

| 地址 | 我们 | 子系统 | ExpHP |
| --- | --- | --- | --- |
| 0x445D40 | playershot_hit_dispatch | SHT | 无 |
| 0x445EE0 | playershot_tick_homing_idx1 | SHT | 无 |
| 0x446260 | playershot_tick_laser_idx2 | SHT | 无 |
| 0x446E00 | playershot_tick_curve_idx3 | SHT | 无 |
| 0x425240 | find_nearest_enemy | ECL/瞄准 | 无 |
| 0x4438C0 | player_collide_rect | 碰撞 | 仅 `sub_..._may_kill_player` 占位 |
| 0x443AF0 | player_collide_laser_obb | 激光碰撞 | funcs.json 无 |
| 0x4052E0 | math_add_normalize_angle | 数学 | 无 |
| 0x449030 | prng_save_restore_replay_state | PRNG/replay | 无 |
| 0x458DB0 | prng_init_warm_stream_b | PRNG | 无 |

**解读**:① 我们的独有函数集中在 **SHT 自机射击系统**(ExpHP 几乎没碰的原创领域);② SHT 的主要"反超"在**数据符号**(`sht_func_init/tick/hit_table` 0x4919c0/9a0/980、`effect_behavior_dispatch_table` 0x491b0c),**不在函数对照里**(funcs.json 只收函数,要比须用 `statics.json`);③ 反向看,ExpHP 有意义命名的 886 个里**一大批我们还没研究** = 它指好路的待挖区。

## 4c. 数据符号对比(我们 32 个 vs statics.json 424 条)

statics.json 仅 **209/424 有意义命名**(其余是 `float(...)` 自动标签)→ **ExpHP 在数据符号上明显弱于函数,数据层是我们更突出的地方。**

**both named 11(全确认 + 增强)**:
- `g_rng_state_a`/`g_rng_state_b` = ExpHP **`REPLAY_SAFE_RNG`/`REPLAY_UNSAFE_RNG`** → **强互证**我们的双 RNG 流,并补上 replay-safe/unsafe 语义(接 `prng_save_restore_replay_state`)。
- `g_bullet_mgr`=`BULLET_MANGER_PTR`、`g_laser_mgr`=`LASER_MANAGER_PTR`、`g_rng_critsec`=`CRIT_SECTION_W`、`g_frame_dt`=`GAME_SPEED` 全对上。
- SHT 四表:我们 `init/tick/hit/draw`(0x4919c0/9a0/980/0x4a6f04)= ExpHP `SHT_FUNC_28/2c/34/SHOOTER_30_TABLE`(它按**结构偏移** 0x28/2c/34/30 命名、无语义;**我们的 init/tick/hit 语义是增量**。⚠️ 0x4a6f04 我们标 draw_UNUSED,ExpHP 标 SHOOTER_30,"unused" 待复核)。

**ExpHP 自动标签、我们给语义名 13(浮点常量,自动值反证我们对)**:`f_PI`=`float(PI)`、`f_2PI`=`float(2*PI)`、`f_rng_2pow_m32`=`float(2**-32)`… ExpHP 的自动值即我们命名依据。

**ExpHP 完全没有 8(纯原创)**:`g_bullet_type_table`、`g_bullet_render_desc`、RNG 内部(`g_rng_counter_a/b`、`g_rng_threadsafe_flag`、`g_rng_in_critsec_depth`、`g_rng_seed_timeGetTime`)、`d_rng_unsigned_fixup_tbl`。

**✅ 已结案(原待复核 1 处)**:`0x491b0c` —— **ExpHP 对,我们错了**。dump 表项 + 反编译裁决:它是 **`ANM_ON_SWITCH_FUNCS`**,`void*[4]`={null, `0x407900`, `0x405f20`, `0x406920`} = `AnmVm::on_switch__1/2/3`(操作 AnmVm 顶点数组 `+0x5b8`、设渲染/混合模式 `+0x534`/`+0x18`)——**ANM VM 的 on-switch 渲染状态切换回调,归 `../anm/`,不是 SHT 特效/敌弹派发**。属一整族 ANM 事件表(`0x491b0c`..`0x491b58`:on_switch/sprite_set/draw/copy/delete)。我们的 `effect_behavior_dispatch_table` 命名**作废** → 改 `anm_on_switch_funcs`。`playershot_launch_shared`(0x445e20)那处 = 发射时触发 shot 的 ANM 对象切换渲染态(仍非碰撞,ExpHP 的 collide 猜测依旧不成立)。已修:sht 脚本、`sht/findings/04`/`06`、`anm/README`。

## 5. 命名差异备记(非冲突,供统一口径时参考)

ExpHP 用 `Class::method` C++ 风格 + 偏程序员(constructor/on_tick/step);我们偏语义(bullet_pool_spawn/beh_*)。少量我们可借 ExpHP 更准的措辞:
- `0x4171c0` 我们 `bullet_size_interp` → ExpHP `InterpFloat::step`(**通用浮点插值器**,EX_SIZE 只是调用方之一;我们的名偏窄)。
- `0x442380` 我们 `playershot_tick_dispatch` → ExpHP `Player::update_options_position`(更具体)。
- `0x4173c0` 我们 `bullet_run_anm_interrupt` → ExpHP `AnmVm::sub_4173c0`(留空,我们更细)。

---

## 6. 结论

**我们靠谱。** 在 68 个可比对函数上与社区一手 RE **绝大多数语义吻合**,且多处独立体系(c68 位 vs EX 索引、PRNG 命名)精确对齐 = 强互证。真冲突仅 2 处,各打一手(我们 1 错、ExpHP 1 猜错),已就地裁决并修正。**把 th-re-data 当命名底图白嫖,语义层与 SHT 仍是我们的原创价值。**

## 关联
- ECL 函数已导入(本会话 MCP rename+save):脚本 `../sht/disasm/scripts/apply_th16_ecl_names.py`。
- 运行时 VM 结构/函数地图:`02-runtime-vm.md`。变量/上下文:`01-*`。
- 弹幕(含已修的 0x4313B0):`../bullets/01`/`03`。数学/PRNG:`../shared/th16-engine-math.md`。
- 纪律:`../sht/findings/00-METHOD-逆向记录纪律.md`;memory `re-overclaim-guard`。
