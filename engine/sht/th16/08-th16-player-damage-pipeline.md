# 逆向工程发现 08:TH16 自机弹**伤害管线**(spawn→伤害源池→敌人扣血)

> 方法:Ghidra(ghidra-re MCP)一手反编译 th16.exe(用户自有)。日期 2026-06-11。
> 分级:✅高 / 🟡中。**仅 TH16 v1.00a**。承接 03(func_*)、05(字段图)、07(shooterset)。
> 触发:`test-laser` 实验需确认"自定义激光的伤害怎么生效"——结论是**伤害与子弹行为解耦,自动处理**。

## 0. 一句话结论

TH16 自机弹的**伤害不在 `func_on_*` 行为里算**,而是走一条独立管线:**每发弹 spawn 时创建一个
"伤害源"对象(挂在 `slot+0xb0`,dmg 取自 .sht `dmg` 字段),每帧把弹的位置拷进去;敌人在自己的
step 里遍历全部伤害源、判重叠、累加 dmg(按 .sht `max_dmg` 封顶)并扣血。** → 任何会移动+有伤害源
的弹都自动造成伤害,**行为函数(homing/laser/…)只管"怎么动",不管"怎么扣血"**。

## 1. 管线全景(全部一手)

```
[spawn] PlayerBullet__create @0x444e10
  slot+0x9c  = (short)shooter[+0x02]          // 弹伤害 = .sht 的 dmg 字段
  slot+0xb0  = sub_444b20_create_dmgsrc(pos, angle, 9999999, slot+0x9c)   // 建伤害源,返回 1-based idx
  dmgsrc = PLAYER+0xd080 + (slot+0xb0)*0x94    // 伤害源对象
        ↓ 每帧
[update] Player__tick_bullets @0x4456d0        // 逐弹派发 func_on_tick(见 03),然后:
  dmgsrc.pos(obj+0x1c)  = slot 位置(+0x48)
  dmgsrc.dmg(obj+0x74)  = slot+0x9c            // 把弹的当前 dmg 拷进伤害源
  (player_update_perframe @0x442560 另有一遍:更新伤害源运动 + 倒计时寿命,到 0 清 active)
        ↓ 每帧,敌人侧
[apply] EnemyData__step_logic @0x41c3xx → enm_compute_damage_sources_445a30 @0x445a30
  遍历 256 个伤害源(PLAYER+0xd114,stride 0x94):
    active(bit0) 且 计时未过 且 (timer % obj+0x80 == 0)  // obj+0x80=命中间隔,普通弹=1=每帧
    bit1=0 → collision_test_circle_rect(用 obj+0x0c 半径)   // 点/圆伤害源
    bit1=1 → 矩形/OBB 测试(用 obj+0x04 宽、obj+0x1c/0x20 端点) // 激光/线伤害源
    重叠 → total += obj+0x74(dmg);obj+0x78 += dmg(累计);达 obj+0x7c 上限则停用
  total 封顶 = *(主 .sht header + 0x28) = max_dmg(05 §2b)   // ★ .sht 的 max_dmg 是每次结算的伤害上限
  return total;  add_to_score(total/10+10)
        ↓ 调用方(敌人)拿 total
EnemyLife__receive_damage @0x41a6d0:  HP(this[0]) -= dmg
  (多血条 boss:this+0x18 & 1 → this+0xc(总HP) -= dmg,重算当前条 this[0])
```

## 2. 伤害源对象布局(PLAYER+0xd080 池,stride 0x94,256 个)✅

> 1-based 索引:`obj = PLAYER + 0xd080 + link*0x94`(link = slot+0xb0)。0-based flag 在 `+0xd114`。
> 偏移以 obj 基址(=flag 所在)为 0。

| obj 偏移 | 含义 | 来源/证据 |
| --- | --- | --- |
| +0x00 | flag:bit0=active、bit1=激光/线形(否则点/圆)、bit2=… | create/tick 置位 |
| +0x04 | 线宽 / 半径参数(in_XMM2) | create_damage_source |
| +0x0c | 圆半径(点伤害源碰撞用) | enm_compute (bit1=0 分支) |
| +0x1c/0x20 | 位置 x/y(每帧由 tick_bullets 从弹 +0x48 拷入;激光=端点) | tick_bullets / 激光 tick |
| +0x60 | 寿命 timer.prev | create:param_2−1 |
| +0x64 | 寿命 timer.cur(player_update_perframe 每帧 −1,<1 停用) | create:param_2 |
| +0x74 | **dmg(每次重叠扣这么多)** | create:param_3;tick_bullets 每帧从 slot+0x9c 刷新 |
| +0x78 | 累计已造成伤害 | enm_compute += |
| +0x7c | 伤害上限(达到则停用;普通弹=10000000≈无限) | create:9999999 / spawn:10000000 |
| +0x80 | 命中间隔(timer % 它 ==0 才结算;普通弹=1) | create:1 |
| +0x90 | 特殊伤害 handler 索引(≠0 走表 `&DAT_004919dc + idx*4`) | enm_compute |

## 3. EnemyLife 结构(this = enemy life 子对象)🟡

| 偏移 | 含义 |
| --- | --- |
| +0x00 | 当前 HP(扣血直接减这里;多血条时为当前条剩余) |
| +0x0c | 总 HP(多血条 boss) |
| +0x10 | 每血条 HP |
| +0x14 | 累计受伤(统计) |
| +0x18 | flag:bit0=多血条模式 |

## 4. 对"自定义弹/扩展"的关键含义 ✅

1. **伤害与行为解耦**:写新 `func_on_tick`(如追踪激光)**完全不用碰伤害**——只要弹是正常 .sht 发射的
   (spawn 自动建 +0xb0 伤害源)且 cave 里保持 `slot+0x48` 位置更新,伤害自动生效。
2. **伤害数值 = .sht 的 `dmg`(shooter +0x02)**;**每帧对单敌的伤害上限 = .sht 的 `max_dmg`(header +0x28)**。
   → 这两个 .sht 字段是"可编辑且有效"的真数据(呼应 05 §5)。
3. **点 vs 线**:伤害源 bit1 决定圆点还是线/OBB。普通弹=点(覆盖弹身);激光=线(覆盖整条束)。
   即便束形没配好,**点在敌人身上的伤害源照样掉血**——所以追踪弹只要飞到敌人身上就有伤害。
4. **命中间隔 obj+0x80**:普通弹每帧结算(=1)。若想做"低频脉冲伤害",这是个旋钮(但它由 create 设、
   非 .sht 直配,要改得在 cave/补丁里动)。

## 5. 可信度 / 复核

- ✅ 一手:spawn 建源+dmg(`0x444e10`)、tick_bullets 拷位置/dmg(`0x4456d0`)、enm_compute 遍历+封顶
  (`0x445a30`,调用方 `EnemyData__step_logic`)、receive_damage 扣血(`0x41a6d0`)。
- ✅(2026-06-11 对抗审计补实,原 🟡):`enm_compute_damage_sources` 返回 total,**`EnemyData__step_logic`
  在 `0x41c5c5` 调它拿返回值、过分数/倍率后在 `0x41c71c` 调 `EnemyLife__receive_damage((enemy+0x3f74), dmg)`
  扣血** —— 链条一手坐实。注:另一处调用方(`0x41c443`,param_6=1)是炸弹/特殊预扫(只探伤触发击杀,不走 receive_damage)。
- 🟡 EnemyLife 偏移由 receive_damage 单函数推,未交叉其他读点。
- 复核入口:Ghidra DB `th16`,地址见上。
