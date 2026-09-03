/* engine.h —— 行为卡能碰的引擎地址 / 偏移。只放一手确认过的，每条带出处。
 *
 * 版本：TH18 v1.00a（imagebase 0x400000）。全是绝对地址（游戏 exe 不重定位：imagebase 固定，
 * 现有 100 处 binhack 也是这么写的）。出处缩写：
 *   OM  = engine/card/th18/01-object-model.md   SM = engine/card/th18/05-shop-and-money.md
 *   HK  = engine/card/th18/03-hooks.md          PL = engine/player/th18/01-position-and-state-timers.md
 *   SDK = ../SDK.md（本会话 Ghidra 一手，AUDIT §O）
 */
#pragma once
#include <stdint.h>

/* ---- 全局 ---- */
#define CE_ADDR_SCORE              0x4cccfc   /* int，封顶 999999999（SM §1）*/
#define CE_ADDR_MONEY              0x4ccd34   /* int（SM §1）*/
#define CE_ADDR_MONEY_TOTAL        0x4ccd30   /* int，只记收入（SM §1）*/
#define CE_ADDR_CARD_PRICE_BY_TIER 0x4b35c4   /* int[15]，price_tier → 金钱（SM §「价格表」一手 dump）*/
#define CE_ADDR_MONEY_ITEMS        0x4ccd20   /* int，吃到的金钱道具个数（collect_money_item 0x446d22 inc）*/
#define CE_ADDR_CURRENT_POWER      0x4ccd38   /* OM §7 */
#define CE_ADDR_MAX_POWER          0x4ccd3c
#define CE_ADDR_PLAYER_PTR         0x4cf410   /* zPlayer*（ExpHP statics；Nitori/Momoyo 都从这读）*/
#define CE_ADDR_ABILITY_MGR_PTR    0x4cf298   /* zAbilityManager*（OM §4）*/
#define CE_ADDR_BULLET_MGR_PTR     0x4cf2bc   /* zBulletManager*（ExpHP statics；cancel_all 0x4297a9 读）*/
#define CE_ADDR_GUI_PTR            0x4cf2e0   /* zGui*（ExpHP）；+0x1b0 = msg（对话 VM，非 0 = 对话中）。C 键门控 0x45c069、Tenshi state0 0x40ea0d 读它 */
#define CE_ADDR_ENEMY_MGR_PTR      0x4cf2d0   /* zEnemyManager*；+0x198 = enemy_count_real（ExpHP）。== 0 时 C 键与充能都停（0x45c07b / 0x40ea1f）*/
#define CE_ADDR_INPUT_PRESSED      0x4ca434   /* 本帧上升沿；bit 0x400 = C 键（0x45c084）*/

#define CE_SCORE()        (*(int32_t *)CE_ADDR_SCORE)
#define CE_MONEY()        (*(int32_t *)CE_ADDR_MONEY)
#define CE_MONEY_TOTAL()  (*(int32_t *)CE_ADDR_MONEY_TOTAL)
#define ce_price_for_tier(t)  (((t) >= 0 && (t) < 15) ? ((const int32_t *)CE_ADDR_CARD_PRICE_BY_TIER)[(t)] : 0)
#define CE_PLAYER()       (*(uint8_t **)CE_ADDR_PLAYER_PTR)
#define CE_ABILITY_MGR()  (*(uint8_t **)CE_ADDR_ABILITY_MGR_PTR)
#define CE_BULLET_MGR()   (*(uint8_t **)CE_ADDR_BULLET_MGR_PTR)
#define CE_GUI()          (*(uint8_t **)CE_ADDR_GUI_PTR)
#define CE_ENEMY_MGR()    (*(uint8_t **)CE_ADDR_ENEMY_MGR_PTR)
#define CE_GUI_MSG            0x1b0       /* zGui.msg：对话中 */
#define CE_EM_ENEMY_COUNT     0x198       /* zEnemyManager.enemy_count_real */

/* ---- zAbilityManager ---- */
#define CE_MGR_CARD_LIST_HEAD      0x18       /* 表头；首结点在 +0x1c（尾段 lea ecx,[edi+0x18]；on_tick 0x408683 读 +0x1c）*/
#define CE_MGR_CARD_LIST_FIRST     0x1c
#define CE_MGR_OWNED               0xd70      /* int[255]，本 mod 搬过来的（战线 C）*/
#define CE_MGR_RECHARGE_MULT       0xc58      /* float，reset 置 1.0（OM §5）*/
#define CE_MGR_SELECTED_ACTIVE     0x38       /* 选中的主动卡（C 键分派 0x45c090）*/
#define CE_MGR_ABILITY_ANM         0x0c       /* AnmLoaded*：ability.anm（场上特效）。ExpHP zAbilityManager +0x0c；CardTenshi__c_press 0x40ebf0 `mov ecx,[eax+0xc]` 取它起 script 0x1c。★ 第一版写成 0x10 拿到了 abcard，script68 越界成垃圾 VM（AUDIT O24′）*/
#define CE_MGR_ABCARD_ANM          0x10       /* AnmLoaded*：abcard.anm（卡图；HUD/编成/图鉴起脚本后 set_sprite）。ExpHP +0x10 */
#define CE_MGR_ABMENU_ANM          0x14       /* AnmLoaded*：abmenu.anm（编成 / 图鉴 UI）。ExpHP +0x14 */

/* 卡链表结点（= card+0xc）：{+0 card*, +4 next, +8 prev}（0x412e90 插入；0x408690 遍历 mov ecx,[edi]; mov edi,[edi+4]）*/
#define CE_NODE_CARD               0x0
#define CE_NODE_NEXT               0x4

/* ---- zCardBaseClass（0x54 字节；case 56 与尾段一手，SDK §2）---- */
#define CE_CARD_VTABLE             0x00
#define CE_CARD_ID                 0x04
#define CE_CARD_ARRAY_INDEX        0x08
#define CE_CARD_LIST_NODE          0x0c
#define CE_CARD_ELAPSED_TIMER      0x20       /* zTimer：激活经过帧（每帧 Timer__increment；OM §3 订正）*/
#define CE_CARD_RECHARGE_TIMER     0x34       /* zTimer：充能倒计时（空闲时 Timer__decrement；c_press 门控 +0x38 <= 0）*/
#define CE_CARD_RECHARGE_TIME      0x48
#define CE_FLAG_ACTIVE             0x08       /* flags bit3：主动卡（尾段按它入 selected / num_active）*/
#define CE_FLAG_FIRING             0x20       /* flags bit5：正在释放（HUD 配色，method_40）*/
#define CE_FLAG_ACTIVE_CLEAR       0x46       /* 主动卡 case 清的位（0x411d83 and ~0x46 | 8）*/
#define CE_CARD_TABLE_ENTRY        0x4c
#define CE_CARD_FLAGS              0x50       /* bit0 存档/replay 装载，bit3 主动，bit5 开火中，bit6 装备 */
#define CE_CARD_OBJECT_SIZE        0x54

/* 基类虚表（终值，case 56 写入）与 21 个槽的实现（本会话读 0x4b4c78，SDK §2）*/
#define CE_ADDR_BASE_VTABLE        0x4b4c78
#define CE_BASE_SLOT_CTOR          0x413010
#define CE_BASE_SLOT_C_PRESS       0x413030
#define CE_BASE_SLOT_METHOD_38     0x4130f0
#define CE_BASE_SLOT_METHOD_3C     0x413130
#define CE_BASE_SLOT_METHOD_40     0x413140
#define CE_BASE_SLOT_OPDELETE      0x411410   /* CardNull__operator_delete(this, flag)，thiscall + 1 栈参 */

/* ---- zPlayer ---- */
#define CE_PLAYER_X                0x620      /* float px（PL §1）*/
#define CE_PLAYER_Y                0x624
#define CE_PLAYER_STATE            0x476ac    /* PL §3 */
#define CE_PLAYER_FOCUSED          0x476cc    /* PL §3 */
#define CE_PLAYER_INVULN_TIMER     0x47774    /* zTimer{prev,cur,float}；复活 0x45c35e 置 {0x117,0x118,280.0}，决死救回 60，炸弹各自置（SDK）*/
#define CE_PLAYER_SPEED_MULT       0x477ec    /* float；Player tick 末尾 0x45c702 复位 1.0；移动 0x45b5b6 读。AbilityManager tick(0x16) 先于 Player(0x17) → on_tick_2 里写生效（SDK）*/
#define CE_PLAYER_SPEED_BASE       0x477f0    /* float×2，每帧从 0x5217dc 复制（0x45c717）*/
#define CE_PLAYER_SHT_PTR          0x47940
#define CE_PLAYER_DAMAGE_MULT      0x47980    /* float；EnemyManager tick 读后复位 1.0（0x42e02f）——别用，顺序不可控 */
#define CE_PLAYER_ITEM_ATTRACT_SPD 0x47988    /* float：Player__reset {5,30,70,70}，Nitori on_load {10,30,110,110}（ExpHP 名 + SDK）*/
#define CE_PLAYER_ITEM_COLLECT_R   0x4798c
#define CE_PLAYER_ITEM_ATTRACT_RF  0x47990    /* focused */
#define CE_PLAYER_ITEM_ATTRACT_RU  0x47994    /* unfocused */
#define CE_PLAYER_POC_HEIGHT       0x47998    /* Kanako 置 224.0 */

typedef struct { int32_t prev; int32_t cur; float cur_f; } ce_timer_t;   /* zTimer 前三个字段（Bomb / Card 的写法一致）*/
#define CE_PLAYER_INVULN()   ((ce_timer_t *)(CE_PLAYER() + CE_PLAYER_INVULN_TIMER))
#define CE_RESPAWN_INVULN_FRAMES   0x118      /* 280 */

/* ---- 可从卡里调的引擎函数（调用约定一手：SDK.md / AUDIT §O16）---- */
#define CE_FN_ALLOCATE_NEW_CARD    0x411460   /* thiscall(mgr; id, mode)：mode 0 道具 / 1 存档 / 2 购买 / 3 replay；返回 num_total，-1 = 拒 */
#define CE_FN_MARK_OBTAINED        0x418de0   /* fastcall(id, notify)：置解锁位（本 mod 的断点把新 id 转进影子 + side-car）*/
#define CE_FN_TABLE_GET            0x407d70   /* fastcall(id) → zTableCardData*；未命中回落 NULL 行 */
#define CE_FN_SHOP_PICK_RANDOM     0x416f50   /* fastcall(out*, tier_lo; tier_hi, exclude[], n)：商店随机池抽一张（未拥有、本关可用、按权重、游戏 RNG）；返回非 0 = 抽到，*out = 表行 */
#define CE_FN_TIMER_DECREMENT      0x409750   /* thiscall(zTimer*; 一个未用栈参) ret 4：prev = cur, cur_f -= 游戏速度, cur = (int)cur_f */
#define CE_FN_TIMER_INCREMENT      0x405990   /* thiscall(zTimer*; 一个未用栈参) ret 4：同上方向相反。★ 调用方必须压那 4 字节 */
#define CE_FN_PLAY_SOUND           0x476c70   /* stdcall(id) + xmm2 = 世界 x（声像）；ret 4 */
#define CE_FN_ANM_INSTANTIATE_WORLD_BACK 0x405bf0 /* AnmLoaded__instantiate_vm_to_world_list_back：thiscall(AnmLoaded*; int* out_id, int script, int layer, void** out_vm) ret 0x10。建 VM、实体坐标 (0,0,0)、layer<0x18 时写 vm+0x18、AnmVm__run 一帧、挂 world 列表尾；内部自己进临界区。AUDIT O24 */
#define CE_FN_ANM_SET_SPRITE       0x477b00   /* AnmLoaded__set_sprite：thiscall(AnmLoaded*; vm, sprite_idx) ret 8（备查，特效脚本自己 sprite() 就不用）*/
#define CE_FN_ANM_DELETE_BY_ID     0x488cf0   /* stdcall(anm_id) ret 4：按 id 标记删除 VM 及其子树（Tenshi 收尾用；一次性脚本自 delete() 就不用）*/
#define CE_MODE_ITEM    0
#define CE_MODE_SAVE    1
#define CE_MODE_SHOP    2
#define CE_MODE_REPLAY  3

/* ---- zTimer（20 字节；Tenshi case 0x411d9c.. 的初始化；Timer__decrement 读 +0xc 当游戏速度源索引）---- */
typedef struct { int32_t prev; int32_t cur; float cur_f; int32_t speed_src; uint32_t control; } ce_ztimer_t;

/* ---- zBulletManager / zBullet（ExpHP 结构 + cancel_all 0x4297a0 的扫描：起点 mgr+0xec，2000 张，stride 0xfa0）---- */
#define CE_BM_BULLETS              0xec       /* 第 0 张（ExpHP 叫 list_0_tail_dummy_bullet；cancel_all 从它起扫 0x7d0 张）*/
#define CE_BM_BULLET_COUNT         0x7d0
#define CE_BULLET_STRIDE           0xfa0
#define CE_BULLET_FLAGS            0x20
#define CE_BULLET_POS              0x638      /* float3 */
#define CE_BULLET_VELOCITY         0x644      /* float3；普通子弹每帧 pos += velocity（0x423f1f..）*/
#define CE_BULLET_SPEED            0x650      /* float；ex 状态改速时从 speed/angle 重算 velocity（0x429bc0）*/
#define CE_BULLET_ANGLE            0x654      /* float；tick 里归一到 (-π, π]（0x4241b8..）*/
#define CE_BULLET_STATE            0xf68      /* uint16：0 = 空槽，3 = 消弹中（cancel_all 都跳过）*/

/* ---- zPlayerBullet ---- */
#define CE_BULLET_DAMAGE           0x9c       /* int；PlayerBullet__create 0x45e396 写、0x45e7f5 调槽 +0x28、0x45e837 用；Momoyo 覆写（SDK）*/
