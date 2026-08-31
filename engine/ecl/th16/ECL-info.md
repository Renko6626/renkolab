# ECL脚本速查表

> 📌 **本仓库验证批注(2026-06-09,来自 th16.exe 逆向)**:本文档(thcrap 社区 Discord)的 **etEx 效果代号、EX_ANGLE 的 c 子模式、EX_SAVE 存档、EX_VEL/EX_VELTIME** 均与 **TH16** 反汇编**实测吻合**(见 `../bullets/01-core-engine.md` §8/§8.1)。但**两处对 TH16 不符**(疑跨版本/后作):① 下文 EX_ACCEL/EX_VELTIME 的**"大数阈值阶梯"**里 `1999990/2999990/3999990/4999990` 那几档(含 `*RANDF2`、`boss0 角`)**在 TH16 不存在**——TH16 只有 `±999990` 三分支(EX_STEP/EX_ANGLE 多 `9999990`→存档角一档);② EX_ANGLE `c==7` 的瞄准阈值实测是 **990.0**(非文中的 `999.0`)。**冲突以 TH16 exe 为准。**

这是常用的东方project弹幕脚本速查表
**注意**: 后面的global并没有在游戏脚本定义，你需要填原始数字
**注意**: 游戏帧率是60帧，你需要妥善计算时间差。
## 坐标系设置
- 屏幕上方中心为$x=0,\ y=0$, 右侧为$x$轴正方形, 下侧为$y$轴正方向, 屏幕总大小是384×448

- 对于角度, 右侧(x轴正方向)为极轴, 逆时针为角度的正方向
## 子弹相关的脚本

子弹通过"子弹发射器'进行发射
- **etNew(id)** 创建一个游戏内编号id的子弹发射器
-  **etOn(id)** 让编号为id的子弹发射器发射一波子弹

- **etSprite(id,type,color)** 让编号为id的子弹发射器的子弹Sprite类型变成type, 颜色变成color

- **etAim(id, mode)**:让编号为id的发射器的发射模式为**mode**, 其中mode的取值分别有以下意义:

0: 自机狙(中心方向朝向发射器和玩家连线)
1: 固定弹(中心方向固定)
2: 自机狙环形(同0, 但是子弹会排成一圈)
3: 固定弹环形(同1, 但是子弹会排斥一圈)
4: 偶数狙环形(中心子弹方向恰好不朝向玩家)
5：固定弹，但是稍微动一点保证不瞄准玩家的情况下
6: 固定弹+角度随机涨落
7: 环形固定弹+速度随机涨落;
8: 环形固定弹+角度随机涨落+速度随机涨落
9-12: 不常用, 建议不用


- **etCount(id, 路数, 层数)**: 设置子弹数目
。路数对应左右摇摆, 层数对应前后子弹同时发射了几层。对于自机狙(mode 0), 如果路数是奇数, 那么中间那一路将发射向玩家, 如果路数是偶数, 则是"偶数自机狙"(中间两路的中线指向玩家)

- **etSpeed(id, 第一层速度, 最后一层速度)**
不同层之间的速度是线性插值的，范围在这之间。
对随机子弹, 它的两个参数代表了子弹速度的涨落的中心和范围。

在设置了这些模式之后,这些模式内存在一个角度参数。
- **etAngle(id, ang1, ang2)**: 给id的子弹发生器设置参数ang1,ang2

对模式0(自机狙): ang1为中线在和玩家连线基础上, 额外的偏移量,ang2是相邻两路弹幕之间的夹角。

对模式1(固定弹): ang1是起始弹幕角度(x轴正方向为0), ang2是相邻两路弹幕的角度差

对圆形弹幕, ang1同样是角度偏移量, 但由于相邻两路的角度差已经为了铺满一圈算完了, ang2是相邻“层”之间的角度偏移量。

对mode6和所有有角度涨落的的随机弹, ang1是中心相对玩家的角度, ang2是涨落正负范围。

- **etEx(id, async, type, int a, int b, float r, float s)**: 给id的弹幕发射器的弹幕添加一个类型为type，传入参数为a,b,r,s的效果。如果async为0, 这个效果是同步执行的, 否则是异步的
- **etEx(id, index, async ,type, int a,int b, float r, float s)**:和上一个一样, 但这个相当于把弹幕发射器的效果池里面第index个效果修改成想要的

- **etClearAll()**: 消除平面所有弹幕
- **etCancel(r)**: 消除调用者(一般为敌人)自身中心半径$r$的弹幕, 被消除的弹幕会变成得分道具
- **etClear(r)**: 同上, 但是不掉落道具

- **angleToPlayer(var,x,y)**: 计算(x,y)到玩家位置夹角并存储到var里面

- **etDist(id, dist)**: 让id的弹幕发射器发射的弹幕方向不变, 但是初始和发射器有dist的距离

- **etOffSetRad(id, angle, radius)**: 让id的弹幕发射器发射的弹幕初始有一个方向angle和半径radius的额外偏移量, 这和etOffset对应同一个弹幕

- etOffsetAbs(id ,x, y): 让子弹的偏移量设置成偏移到绝对位置的x和y

- **fog(r, color)**: 让发射器发射子弹产生的雾气特效半径为r，颜色(BGR格式)为color
根据提供的东方Project游戏脚本文档，以下是相对重要指令的总结性速查表：

## 敌人创建和ANM脚本管理 (300-340)

- **enmCreate(string sub, float x, float y, int hp, int score, int item)**：在相对坐标(x,y)创建敌人，使用子程序sub，指定生命值、分数和掉落物品。注意：这里的item参数指的是掉落的物品，而不是传入参数。对于传入的参数，你可以在创建前用I0(整数)或者F0（浮点数）设置，这个变量会被创造的敌人继承。
- **enmCreateA(string sub, float x, float y, int hp, int score, int item)**：在绝对坐标(x,y)创建敌人
- **anmSelect(int anmIndex)**：选择ANM文件供其他指令使用
- **anmSetSprite(int slot, int script)**：在指定槽位加载ANM脚本
- **anmSetMain(int slot, int script)**：设置主ANM脚本，根据移动方向自动切换不同脚本
- **anmPlay(int anmIndex, int script)**：在调用者当前位置播放独立的ANM脚本
- **deathAnm(int anmIndex, int script)**：设置敌人死亡时播放的动画
- **anmColor(int slot, int R, int G, int B)**：修改ANM脚本颜色
- **anmAlpha(int slot, int alpha)**：设置ANM脚本透明度
- **anmScale(int slot, float w, float h)**：设置ANM脚本缩放
- **anmScale2(int slot, float w, float h)**：乘性缩放ANM脚本（不覆盖原缩放）
- **enmDelete(int id)**：删除指定ID的敌人

## 移动管理 (400-447)

- **movePos(float x, float y)**：设置绝对位置
- **movePosTime(int time, int mode, float x, float y)**：在指定时间内移动到绝对位置
- **movePosRel(float x, float y)**：设置相对位置
- **movePosRelTime(int time, int mode, float x, float y)**：在指定时间内移动到相对位置
- **moveVel(float r, float spd)**：设置绝对移动角度和速度
- **moveVelRel(float r, float spd)**：设置相对移动角度和速度
- **moveCircle(float θ, float spd, float rad, float radInc)**：设置绝对圆周运动
- **moveCircleRel(float θ, float spd, float rad, float radInc)**：设置相对圆周运动
- **moveEllipse(float θ, float spd, float rad, float radInc, float ellDir, float ellRatio)**：设置绝对椭圆运动
- **moveSetMirror(int state)**：设置镜像标志
- **moveBezier(int time, float x1, float y1, float x2, float y2, float x3, float y3)**：贝塞尔曲线移动
- **moveAngle(float r)**：设置绝对移动角度
- **moveSpeed(float spd)**：设置绝对移动速度
- **moveEnm(int id)**：移动到指定ID敌人的位置

## 敌人属性管理和杂项 (500-572)

- **setHurtbox(float w, float h)**：设置受伤判定框
- **setHitbox(float w, float h)**：设置攻击判定框
- **flagSet(int n)**：设置标志位
- **flagClear(int n)**：清除标志位
- **moveLimit(float x, float y, float w, float h)**：设置移动限制区域
- **	dropExtra(type, amount)**: 给调用者的掉落物额外增加amount量的type类型掉了
- **dropItems()**：掉落所有物品
- **lifeSet(int hp)**：设置当前和最大生命值
- **setBoss(int a)**：设置boss模式
- **setInterrupt(int slot, int hp, int time, string sub)**：设置中断（生命值或时间触发）
- **setInvuln(int time)**：设置无敌时间
- **playSound(int id)**：播放音效
- **setScreenShake(int time, int startIntensity, int endIntensity)**：设置屏幕震动
- **enmKillAll()**：杀死所有其他敌人
- **spell(int id, int time, int mode, string name)**：声明符卡
- **spellEnd()**：结束当前符卡
- **gameSpeed(float s)**：设置游戏速度
- **hitSound(int id)**：设置受击音效
- **enmAlive(int var, int id)**：检查敌人是否存活
- **setDeath(string sub)**：设置死亡时执行的子程序
- **die()**：立即执行死亡子程序或死亡

## 额外常用语法

- 声明变量可以用 var A, 这种声明方法在之后调用A时，如果A是整数需要用$A，浮点数需要用%A标记
- 声明变量也可以用int A或者float A, 这种声明方法直接调用就可以

- 我们可以用goto循环, 但也可以使用while循环:
int a = 30;
 while(a--) {
     // assume that the bullet manager was properly initialized beforehand
     etOn(0);
     wait(30);
 }

 同样，使用continue来跳转到下一个循环是可以的

 ## 子弹样式和颜色表

 这个表格是子弹样式和颜色的对照，在Sprite里面你需要用整数指定它，这是不同数对应的样式和颜色：
 /* th16 bullet types for Et_setSprite */
/// Bullet sprites
// 16 colors
global Pellet = 0;
global Pellet2 = 1;
global InvertPopcorn = 2;
global Popcorn = 3;
global Ball = 4;
global Ball2 = 5;
global RingBall = 6;
global RingBall2 = 7;
global Rice = 8; //米弹
global Kunai = 9; //苦无
global Shard = 10;
global Talisman = 11;
global Arrowhead = 12; //箭
global Bullet = 13;
global LumpyBall = 14;
global InvertRice = 15;
global StarR = 16;
global Droplet = 34;
global SpinRice = 35;
global SpinShard = 36;
global StarL = 37;
global LaserChunk = 38;
// 8 colors
global BigBall = 18; //大玉
global BigBall2 = 19;
global Oval = 20; //椭圆弹
global Dagger = 21; //刀弹
global Butterfly = 22;
global BigStarR = 23;
global BigStarL = 24;
global Heart = 29;
global PulseBall = 30;
global Arrow = 31;
global GlowBall = 33;
global Rest = 43;
global YinYangR = 44; //
global YinYangL = 45;
global Diamond = 48;
global Tear = 49;
// 4 colors
global Bubble = 32;
global BigYinYangR = 46;
global BigYinYangL = 47;
// Special colors
global Coin = 17;
global FireballRed = 25;
global FireballPurple = 26;
global FireballBlue = 27;
global FireballYellow = 28;
global NoteRed = 39;
global NoteBlue = 40;
global NoteYellow = 41;
global NotePurple = 42;
/* th16 bullet colors for Et_setSprite */

global COLOR16_BLACK = 0;
global COLOR16_DARKRED = 1;
global COLOR16_RED = 2;
global COLOR16_PURPLE = 3;
global COLOR16_PINK = 4;
global COLOR16_DARKBLUE = 5;
global COLOR16_BLUE = 6;
global COLOR16_DARKCYAN = 7;
global COLOR16_CYAN = 8;
global COLOR16_DARKGREEN = 9;
global COLOR16_GREEN = 10;
global COLOR16_LIME = 11;
global COLOR16_DARKYELLOW = 12;
global COLOR16_YELLOW = 13;
global COLOR16_ORANGE = 14;
global COLOR16_WHITE = 15;
global COLOR16_SPECIAL = 15; /* Kunais are weird */

global COLOR_COIN_GOLD = 0;
global COLOR_COIN_SILVER = 1;
global COLOR_COIN_BRONZE = 2;

global COLOR8_BLACK = 0;
global COLOR8_RED = 1;
global COLOR8_PINK = 2;
global COLOR8_BLUE = 3;
global COLOR8_CYAN = 4;
global COLOR8_GREEN = 5;
global COLOR8_YELLOW = 6;
global COLOR8_WHITE = 7;

global COLOR4_RED = 0;
global COLOR4_BLUE = 1;
global COLOR4_GREEN = 2;
global COLOR4_YELLOW = 3;

global COLOR_NEG = 0;

## 子弹效果表

对于**etEx**指令, 它需要用type传入子弹变换效果代号和对应的参数，下表是所有变换的编号：
global EX_DIST = 0; // (broken)
global EX_ANIM = 1;
（子弹加速）global EX_ACCEL = 2;
（子弹）global EX_ANGLE_ACCEL = 3;
global EX_ANGLE = 4;
global EX_SPAWNSOUND = 5; // not a real ex anymore
global EX_BOUNCE = 6;
global EX_INVULN = 7;
global EX_OFFSCREEN = 8;
global EX_SETSPRITE = 9;
global EX_DELETE = 10;
global EX_PLAYSOUND = 11;
global EX_WRAP = 12;
global EX_SHOOT = 13;
global EX_SHOOT_DATA = 14; // Does nothing
global EX_REACT = 15;
global EX_LOOP = 16;
global EX_MOVE = 17;
global EX_VEL = 18;
global EX_VELADD = 19;
global EX_BRIGHT = 20;
global EX_VELTIME = 21;
global EX_SIZE = 22;
global EX_SAVEANGLE = 23;
global EX_ENEMY = 24;
global EX_LAYER = 25;
global EX_DELAY = 26;
global EX_LASER = 27;
global EX_LASER_DATA = 28; // Does nothing for bullets. Changes ID of some lasers
global EX_HITBOX = 29;
global EX_WAIT = 30;
global EX_HOMING = 31;
global EX_ACCEL_2 = 32;
global EX_NO_GRAZE_EFFECT = 33;

----

下面是这些效果的代码和参数含义
EX_ANIM:
    runs interrupt 7 + a on the bullet vm

EX_ACCEL:
    duration = a
    acceleration = r

    s <= -999990.0                          : angle = current_angle
    s > -999990.0 && s < 999990.0           : angle = s
    s >= 999990.0 && s < 1999990.0          : angle = angle_to_player_from_current_position + m
    s >= 1999990.0 && s < 2999990.0         : angle = s
    s >= 2999990.0 && s < 3999990.0         : angle = angle_to_player_from_current_position + m * RANDF2
    s >= 3999990.0 && s < 4999990.0         : angle = current_angle + m * RANDF2
    s >= 4999990.0                          : angle = angle_from_boss0_to_current_position

EX_ANGLE_ACCEL:
    duration = a
    acceleration = r
    angle = s

EX_ANGLE:
    duration = a
    max_count = b
    type = c
    __int_44 = d

    s <= -999990.0  : speed = current_speed
    s > -999990.0   : speed = s
    c == 7          : speed = current_speed + s * RANDF2

    r <= -999990.0                          : angle_arg = current_angle
    r > -999990.0 && r < 999990.0           : angle_arg = r
    r >= 999990.0 && r < 1999990.0          : angle_arg = angle_to_player_from_current_position + m
    r >= 1999990.0 && r < 2999990.0         : angle_arg = r
    r >= 2999990.0 && r < 3999990.0         : angle_arg = angle_to_player_from_current_position + m * RANDF2
    r >= 3999990.0 && r < 4999990.0         : angle_arg = current_angle + m * RANDF2
    r >= 4999990.0                          : angle_arg = angle_from_boss0_to_current_position

    c == 0 || c == 1 || c == 4              : angle = angle_arg
    c == 2                                  : angle = angle_to_player_from_saved_position + angle_arg
    c == 3                                  : angle = saved_angle + angle_arg
    c == 5 || c == 6                        : angle = r * RANDF2
    c == 7 && r <= -999990.0                : angle = current_angle
    c == 7 && r > -999990.0 && r < 990.0    : angle = r
    c == 7 && r >= 999.0                    : angle = angle_to_player_from_current_position

EX_BOUNCE:
    max_count = a
    type = b
    speed = r
    
    b & 0x20    : size_x = s, size_y = m
    !(b & 0x20) : size_x = 384.0, size_y = 448.0

EX_INVULN:
    duration = a

EX_OFFSCREEN:
    max_time = a
    unknown = b

EX_SETSPRITE:
    sprite = a
    color = b

    c & 0x8000 : runs interrupt 2 on the bullet vm

EX_DELETE:
    a == 1 : cancel_script = -1

EX_PLAYSOUND:
    sound_id = a

EX_WRAP:
    max_count = a
    walls = b

EX_SHOOT:
    aim_mode = a
    effect_index = b
    count1 = c
    count2 = d
    sprite = a2
    color = b2

    r <= -999990.0                          : angle = current_angle
    r > -999990.0 && r <= 999990.0          : angle = r
    r > 999990.0 && r < 1999990.0           : angle = angle_to_player_from_current_position
    r >= 1999990.0                          : angle = r

    angle2 = s

    m <= -999990.0  : speed1 = current_speed
    m > -999990.0   : speed1 = m
    
    speed2 = n

EX_REACT:
    __ex_func_a = a

EX_LOOP:
    index = a
    count = b

EX_MOVE:
    duration = a
    mode = b
    target_x = r
    target_y = s
    
    b & 0x100 : target_x += current_x, target_y += current_y
    
EX_VEL:
    r >= 990.0                  : angle = angle_to_player_from_current_position + r - 999.0
    r >= -990.0 && r < 990.0    : angle = r
    r < -990.0                  : angle = current_angle
    
    s < -990.0  : speed = current_speed
    s >= -990.0 : speed = s

EX_VELADD:
    duration = a
    angle = r
    speed = s

EX_BRIGHT:
    a == 1              : blend_mode = 1
    a == 2              : blend_mode = 2
    a != 1 && a != 2    : blend_mode = 0

EX_VELTIME:
    duration = a
    speed = (r - current_speed) / a

    s <= -999990.0                          : angle = current_angle
    s > -999990.0 && s < 999990.0           : angle = s
    s >= 999990.0 && s < 1999990.0          : angle = angle_to_player_from_current_position + m
    s >= 1999990.0 && s < 2999990.0         : angle = s
    s >= 2999990.0 && s < 3999990.0         : angle = angle_to_player_from_current_position + m * RANDF2
    s >= 3999990.0 && s < 4999990.0         : angle = current_angle + m * RANDF2
    s >= 4999990.0                          : angle = angle_from_boss0_to_current_position

EX_SIZE:
    end_time = a
    mode = b
    initial_size = r
    final_size = s

EX_SAVEANGLE:
    this saves position, angle, and speed

EX_ENEMY:
    I0 = a
    I1 = b
    I2 = c
    I3 = d
    F0 = r
    F1 = s
    F2 = m
    F3 = n

EX_LAYER:
    layer = a

EX_DELAY:
    duration = a

EX_LASER:
    a == 0 : line laser

    sprite = b
    color = c
    delete_current_bullet = d
    shot_sound = a2
    transform_sound = b2
    effect_index = c2
    flags = 0

    r <= -999990.0                          : angle = current_angle
    r > -999990.0 && r <= 999990.0          : angle = r
    r > 999990.0 && r < 1999990.0           : angle = angle_to_player_from_current_position
    r >= 1999990.0                          : angle = r

    s <= -999990.0  : speed = current_speed
    s > -999990.0   : speed = s

    length = m
    __length_related = n
    __float_18 = r2
    width = s2
    distance = m2


    a == 1 : infinite laser

    sprite = b
    color = c
    flags = (d & 0xFD) | 0x02
    effect_index = (d & 0xFF00) >> 8
    delete_current_bullet = (d & 0x10000) >> 16
    start_time = a2
    expand_time = b2
    duration = c2
    stop_time = d2
    shot_sound = 18
    transform_sound = -1

    r <= -999990.0                          : angle = current_angle
    r > -999990.0 && r <= 999990.0          : angle = r
    r > 999990.0 && r < 1999990.0           : angle = angle_to_player_from_current_position
    r >= 1999990.0                          : angle = r

    s <= -999990.0  : speed = current_speed
    s > -999990.0   : speed = s

    __float_24 = m
    length = n
    width = r2
    distance = s2

EX_HITBOX:
    r < 0.0f    : hitbox_radius = original_hitbox
    r >= 0.0f   : hitbox_radius = r

EX_HOMING:
    duration = a
    speed = r
    angle = s
    target_x = m

EX_WAIT:
    duration = a

## 敌人的sprite编号表
global ENM_GIRL_S_BLUE = 0;
global ENM_GIRL_S_RED = 5;
global ENM_GIRL_S_GREEN = 10;
global ENM_GIRL_S_YELLOW = 15;
global ENM_GIRL_S_BLUE_ALT = 20;
global ENM_GIRL_S_RED_ALT = 25;
global ENM_GIRL_M_RED = 30;
global ENM_GIRL_M_BLUE = 35;
global ENM_GIRL_L = 40;

global ENM_GIRL_S_DARK_BLUE = 147;
global ENM_GIRL_S_DARK_RED = 152;
global ENM_GIRL_S_DARK_YELLOW = 157;
global ENM_GIRL_S_PURPLE = 162;
global ENM_GIRL_L_DARK = 167;

global ENM_CIR_RED = 53;
global ENM_CIR_GREEN = 56;
global ENM_CIR_BLUE = 59;
global ENM_CIR_PURPLE = 62;

global ENM_CIR_RED_FADE = 65;
global ENM_CIR_GREEN_FADE = 68;
global ENM_CIR_BLUE_FADE = 71;
global ENM_CIR_PURPLE_FADE = 74;

global ENM_PHANTOM_RED = 79;
global ENM_PHANTOM_RED_FLIP = 80;
global ENM_PHANTOM_GREEN = 83;
global ENM_PHANTOM_GREEN_FLIP = 84;
global ENM_PHANTOM_BLUE = 87;
global ENM_PHANTOM_BLUE_FLIP = 88;
global ENM_PHANTOM_YELLOW = 91;
global ENM_PHANTOM_YELLOW_FLIP = 92;

## 示例代码:

这是游戏道中一个阶段的代码:
```
void MainSub01()
{
    var A, B, C;
    $A = 10;
    goto MainSub01_336 @ 0;
MainSub01_100:
    enmCreateM("GirlRedA02", 100.0f, -32.0f, 160, 10, 1);
    enmCreate("GirlBlueA02", -100.0f, -32.0f, 160, 10, 1);
    wait(20);
MainSub01_336:
    if ($A--) goto MainSub01_100 @ 0;
    $B = 10;
    goto MainSub01_680 @ 0;
MainSub01_444:
    enmCreate("GirlRedA02", 150.0f, -32.0f, 160, 10, 2);
    enmCreateM("GirlBlueA02", -150.0f, -32.0f, 160, 10, 2);
    wait(20);
MainSub01_680:
    if ($B--) goto MainSub01_444 @ 0;
    $C = 30;
    goto MainSub01_1024 @ 0;
MainSub01_788:
    enmCreateM("GirlBlueA02", 100.0f, -32.0f, 160, 10, 1);
    enmCreate("GirlBlueA02", -100.0f, -32.0f, 160, 10, 1);
    wait(5);
MainSub01_1024:
    if ($C--) goto MainSub01_788 @ 0;
    enmCreateM("GirlRedA02", 200.0f, -32.0f, 160, 10, 1);
    enmCreate("GirlRedA02", -200.0f, -32.0f, 160, 10, 1);
    return;
}
void GirlRedA02()
{
    //创建红色小怪
    anmSelect(2);
    anmSetMain(0, 5);
    anmSetSprite(1, 323);
    @GirlA02(1); //调用GirlA02的通用行为模式
    delete();
}
void GirlA02(var A)
{
    //一类小怪的通用逻辑1
    setHurtbox(24.0f, 24.0f);
    setHitbox(16.0f, 16.0f);
    moveVel(1.9634954f + (%RANDF2 * 0.34906584f), 3.0f);
    moveCircleRel(%RANDRAD, 0.017453292f, 32.0f, 0.0f);
    moveVelTime(60, 1, 0.3926991f + (%RANDF2 * 0.17453292f), 1.0f);
!NHL67
    //这代表只有在NHL难度下才会调用攻击脚本
    @GirlA02_at() async;
!*
    wait(120);
    moveSpeedTime(60, 1, 2.0f);
    goto GirlA02_480 @ 0;
GirlA02_460:
    wait(1000);
GirlA02_480:
    if (1) goto GirlA02_460 @ 0;
    return;
}
void GirlA02_at()
{
    //攻击脚本
    var A,B,C,D;
    etNew(0);
    etAim(0, 3);
    $B = $RAND % 8;
    $C = $RAND % 4;
    etSprite(0, $B, $C);
    $D = $RAND % 3+1;
    etCount(0, 6, $D);
    etAngle(0, 0.0f, 0.1f);
    etSpeed(0, 2.0f, 3.0f);
    etEx(0, 0, 1, 1, -9999994, -9999994.0f, -9999994.0f);
!E67
    0;
!N67
    $RAND % 300;
!H67
    $RAND % 60;
!L67
    $RAND % 30;
!*
    //这里的[-1]代表按照前面不同难度的场合取数
    wait([-1]);
    $A = 100;
    goto GirlA02_at_708 @ 0;
GirlA02_at_588:
    etOn(0);

    wait(30);
GirlA02_at_708:
    if ($A--) goto GirlA02_at_588 @ 0;
    return;
}
```
### 旧的etEx


global EX_SPEEDUP = 1; // Note: formerly EX_DIST
global EX_ANIM = 2;
global EX_ACCEL = 4;
global EX_ANGLE_ACCEL = 8;
global EX_STEP = 16; // Note: formerly EX_ANGLE
/* 32 is not used */
global EX_BOUNCE = 64;
global EX_INVULN = 128;
global EX_OFFSCREEN = 256;
global EX_SETSPRITE = 512;
global EX_DELETE = 1024;
global EX_PLAYSOUND = 2048;
global EX_WRAP = 4096;
global EX_SHOOTPREP = 8192;
global EX_SHOOT = 16384;
global EX_REACT = 32768;
global EX_GOTO = 65536;
global EX_MOVE = 131072;
global EX_VEL = 262144;
global EX_VELADD = 524288;
global EX_BRIGHT = 1048576;
global EX_ACCELWEIRD = 2097152; // Note: formerly EX_VELTIME
global EX_SIZE = 4194304;
global EX_SAVE = 8388608; // Note: formerly EX_SAVEANGLE
global EX_ENMCREATE = 16777216; // Note: formerly EX_SPECIAL
global EX_LAYER = 33554432;
global EX_DELAY = 67108864;
global EX_LASER = 134217728;
/* 268435456 unused */
global EX_HITBOX = 536870912;
/* 1073741824 unused */ 
global EX_WAIT = -2147483648;

/* modes for EX_STEP (argument c)*/
global ANGLE_NORMAL = 0; /* angle smoothly changes to r, speed changes to s (s can be NEGF too use original speed) */
global ANGLE_AIMED = 1; /* angle becomes current angle to the player + r, speed same as above */
global ANGLE_SAVED = 2; /* angle becomes angle saved with EX_SAVEANGLE + r, speed same as above */
/* I don't understand how 3 works, so there's no constant for it (idk how to name it) */
global ANGLE_INSTANT = 4; /* same as 0, except angle changes instantly and not smoothly */
global ANGLE_RANDOM = 5; /* angle becomes current angle + r*%RANDFS, speed same as above */
global ANGLE_RANDOM_AIMED = 6; /* same as above, except it's current angle to the player + r*%RANDFS */
global ANGLE_RANDOM_SPEED = 7; /* angle = NEGF, bullet speed = current speed + s*%RANDFS (in this case, s can't be NEGF) */

/* values for bouncing */
/* UDLR - up, down, left, right - allowed  bouncing directions */
global BOUNCE_CUSTOM_UDLR = 47; /* CUSTOM = 5th byte set, so it uses custom wall locations, use with Et_exBounceCustom only (or manually with transformSet/Push) */
global BOUNCE_CUSTOM_UDL = 39;
global BOUNCE_CUSTOM_UDR = 43;
global BOUNCE_CUSTOM_UD = 35;
global BOUNCE_CUSTOM_ULR = 45;
global BOUNCE_CUSTOM_UL = 37;
global BOUNCE_CUSTOM_UR = 41;
global BOUNCE_CUSTOM_U = 33;
global BOUNCE_CUSTOM_DLR = 46;
global BOUNCE_CUSTOM_DL = 38;
global BOUNCE_CUSTOM_DR = 42;
global BOUNCE_CUSTOM_D = 34;
global BOUNCE_CUSTOM_LR = 44;
global BOUNCE_CUSTOM_L = 36;
global BOUNCE_CUSTOM_R = 40;
global BOUNCE_CUSTOM = 32;
global BOUNCE_UDLR = 15;
global BOUNCE_UDL = 7;
global BOUNCE_UDR = 11;
global BOUNCE_UD = 3;
global BOUNCE_ULR = 13;
global BOUNCE_UL = 5;
global BOUNCE_UR = 9;
global BOUNCE_U = 1;
global BOUNCE_DLR = 14;
global BOUNCE_DL = 6;
global BOUNCE_DR = 10;
global BOUNCE_D = 2;
global BOUNCE_LR = 12;
global BOUNCE_L = 4;
global BOUNCE_R = 8;
global BOUNCE_NONE = 0;
