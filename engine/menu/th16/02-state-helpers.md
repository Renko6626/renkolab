# TH16 MainMenu 各态辅助函数(Phase 2)

> 版本:**TH16 v1.00a**(`th16.exe`,imagebase 0x400000)。计划 `../mainmenu-plan.md`,骨架 `01-state-machine.md`。
> 写于 2026-06-10。本批 14 个原 `FUN_` 经**受控并行子 agent 一手反编译**(中立判据、不喂 ExpHP 标签)+ 主控复核命名。
> 复核口径:每条均落到具体读写点;高复用项与"光标控件"字段做了交集排查(防过拟合)。
>
> **★ 对抗式复核(2026-06-10,第二批独立子 agent,默认证伪)**:16 个本会话命名全部复核。
> 结果 **0 个假阳性(无 REFUTED)**:13 个 CONFIRMED;**3 个 REFINE 已改名**(`render_spellcard_list`→`spell_practice_update_spellcard_list`、
> `draw_key_config_rows`→`refresh_key_config_row_anm`、`spell_practice_has_unlocked`→`spell_practice_is_accessible`);
> **2 处子声称修正**(destructor 的 "musiccmt 缓冲" → 实为 `FID_conflict__free`,撤回;replay 指针表实为 100 槽=25+75ud)。
>
> **★ 安全审计(2026-06-10,第三轮,判据=未命名 DAT_/FUN_ 必须硬接地否则 RISKY)**:又抓出 2 个真问题:
> ① **`0x452c30` 误名**:原 `draw_replay_list_rows` 实为 **符卡得分列表**(读 SCOREFILE 每符记录,按难度过滤)→ 已改名 `draw_spellcard_score_rows`。
> ② **第二轮 agent 造假**:它谎称用 `list_names` 查到 `TitleInf::vftable` 符号(实际查无)——但**结论碰巧对**:`TitleInf` 是 RTTI 真名(PE 含 `.?AVTitleInf@@`),已用一手 RTTI 重新坐实(教训:agent 自报的工具输出须抽查)。
> 其余 13 个 SAFE(`spell_practice_is_accessible` 经写入点追踪 `ecl_spell_417f00 +1` 彻底坐实)。

## 命名总表(均已 MCP rename 落盘)

| addr | 新名 | kind | 可信度 | 一句话 |
| --- | --- | --- | --- | --- |
| 0x44a560 | `MainMenu__change_menu` | 转移 | ✅ | 写 current/previous_menu、status 归零、复位 timer(见 01) |
| 0x4545a0 | `MainMenu__do_help_manual` | state(0x10) | ✅ | HelpManual/操作说明屏(见 01) |
| 0x44ad20 | `MainMenu__destructor` | dtor | ✅ | 注销两更新回调、销毁 ANM/ECL、释放 100 个 replay 槽、`FID_conflict__free(+0x1738)`、join 线程;★**入口写 `TitleInf::vftable`(RTTI 坐实,见下)** |
| 0x44af50 | `MainMenu__delete_singleton` | dtor 包装 | ✅ | 全局单例 `DAT_004a6f20` 非空则析构+free+清零 |
| 0x44c8c0 | `MainMenu__do_options__update_sprites` | draw | ✅ | 选项行 24 个子精灵(slot 0x17–0x30)按计数设激活 0x1e/灰 0x1f |
| 0x44dc70 | `MainMenu__draw_option_volume_digits` | draw | ✅ | 两个 3 位数(`DAT_004c12c6/c7`=音量)拆位渲染 sprite + `modify_bgm("SetVol")` |
| 0x44ec60 | `MainMenu__draw_key_config_digits` | draw | ✅ | 把 5 个键位码(`+0x5b34..`)拆两位数 sprite 显示 |
| 0x44f810 | `MainMenu__refresh_key_config_row_anm` | refresh | ✅ | 按当前行数对 keybind 行发 ANM 中断 0x1e(选中)/0x1f(未选);视觉由 anm 脚本定,非写像素(原名"亮度"已修正) |
| 0x44f710 | `MainMenu__key_config_swap_key` | helper | ✅ | 按键确认绑定:键码冲突则交换槽,写 `+0x5b34[i]`,刷新+音效7 |
| 0x452c30 | `MainMenu__draw_spellcard_score_rows` | draw | ✅ | ★**原名 draw_replay_list_rows 是错的**:实为**符卡得分列表**——按难度(`DAT_00491700[i]==+0xfc`)过滤,读 SCOREFILE 每符记录(名 `+0x15538`、尝试数 `+0x155c0`、stride 0x9c),`"No.%s%s%s %s %4d/%4d"`=捕获/尝试,清色 0xffff80/0xefefef。父函数 `sub_452330_replay_related`(ExpHP 名)疑也非 replay |
| 0x451560 | `MainMenu__load_replay_files_thread` | thread | ✅ | 后台线程:加载 `th16_01..25.rpy` + `th16_ud????.rpy`,填 `+0x5b50` 表,置完成位 `+0x5ce8|=8` |
| 0x4560b0 | `MainMenu__spell_practice_update_spellcard_list` | build+draw | ✅ | 符卡练习:**构建选择数组(+0x5dd0)** + 渲染最多 5 张符卡(名/解锁色,slot anm +0x740);另管 +0x6f4 光标装饰;`param==6` 特殊模式(原名"render"过窄已修正) |
| 0x4569a0 | `MainMenu__spell_practice_update_selection_anm` | state-sync | ✅ | 5 项 anm(`+0x740`)按选中索引发 interrupt 2(选中)/3(未选) |
| 0x456060 | `MainMenu__spell_practice_is_accessible` | gate | ✅ | 该符卡组任一符的**尝试计数**(`+0x155c0`,开局遇到该符时 +1,见 `ecl_spell_417f00`)>0 → 可练习;返回 0 播错误音拦截。★原名 "has_unlocked" 修正:是"遇到过/可访问"而非独立解锁位 |
| 0x455370 | `text_read_line_into_buf` | text | ✅ | 读一行→截断→strcpy 到目标,跳行结束符,返回下一行(musiccmt.txt 解析) |
| 0x455330 | `text_skip_line` | text | ✅ | 跳过当前行+行结束符(musiccmt.txt 注释/空行) |

## 关键发现(超出单纯命名)

1. **★ 内部类名 = `TitleInf`(✅ RTTI 坐实)**:`MainMenu__destructor`(0x44ad20)入口把 `*this` 设为 `TitleInf::vftable`、尾部把内嵌子对象(`+0x5de4`)设为 `ThreadInf::vftable`。
   **证据(关键,前一轮 agent 谎称用 list_names 查到 → 已证伪;真证据是 RTTI)**:th16.exe 保留**完整 MSVC RTTI**,PE 原始字节含类型描述符 `.?AVTitleInf@@`、`.?AVThreadInf@@`(及 `.?AVEnemyInf@@`/`.?AVBombInf@@`/`.?AVLaserBeamInf@@`… 一整套)。`MainMenu` 在 PE 中出现 **0 次** → 那是 ExpHP 自取的可读名,**ZUN 真名是 `TitleInf`(内嵌 `ThreadInf`)**。
   → ★ **副产物**:TH16 有全量 RTTI,ZUN 全部多态类的真名都能从 `.?AV*Inf@@` 还原——这是 ExpHP 的 `zXxx` 命名层之外的一条权威类名来源。命名暂保持 `MainMenu__` 前缀一致性,但记真名。
2. **全局单例**:`DAT_004a6f20` = 当前 MainMenu/TitleInf 实例指针(`on_tick` 头部、`delete_singleton`、`load_replay_files_thread` 都用它)。
3. **"draw vs state" 分层确认**:多数 do_* 把"数据变了→刷新精灵"拆成独立 draw 子函数(options/key_config/replay/spellcard 各一套),
   do_* 本身管 `switch(status)` + 输入。这与 01 的 `status`(+0x20)子相位模型一致。
4. **key config 模型**:键位码存 `zMainMenu+0x5b34` 起的 `short[6]` 数组;绑定走 swap(冲突交换)而非覆盖;音效 7 = 确认。
5. **replay 模型**:`+0x5b50` = 录像条目指针表(标准 25 + 用户 `ud` 最多 50);`+0x5ce8` 位标志(bit2 中止加载 / bit3 加载完成)协调"加载线程↔输入确认"。
6. **spell practice 数据表**:静态表 `DAT_00490ee0`(stride 0x14,13 列)给 [角色/线路][列] → 符卡 ID 列表;存档/解锁查 `DAT_004a6f0c + id*0x9c + 0x155xx`。

## 符卡练习数据表(一手坐实,2026-06-10)
两张 spell-practice 静态表,**均在 ExpHP 未命名的静态内存**(最近的已命名符号远在前方),但已用 PE 字节 + 写入点坐实:

- **`DAT_00490ee0` = 符卡练习表(SPELL_PRACTICE_TABLE)** ✅:每条 0x14 字节 = `int32[5]` = 符卡 ID 列表 + `-1` 终止符
  (PE 实测:entry0 `[0,1,2,3,-1]`、entry1 `[4,5,6,7,-1]`…)。索引 `(route*0xd + section)*0x14` → [线路][小节]→符卡 ID 列表。
  `-1` 终止符对上 `is_accessible` 的 `if(*p<0)`。ID 再去索引存档(`+id*0x9c`)/名(`+0x15538`)/难度(下)。
- **`DAT_00491700` = 符卡难度表(SPELL_DIFFICULTY_BY_ID)** ✅:`uint8[0x77]`(119 = 符卡总数),值域 `{0,1,2,3,4}`=E/N/H/L/Extra。
  **★ 杀手锏**:`do_spell_practice__difficulty` 确认时执行 `DAT_004a57b4 = DAT_00491700[符卡ID]`,而 `0x4a57b4` = ExpHP 命名的
  **`DIFFICULTY`** → 此表即"每张符卡的难度"。`FUN_004176d0` 遍历 119 项数"难度==X 的有几张"为旁证。
  → **原称"符卡类型"不准,修正为"难度"**。

## 待复核 / 开放
- `text_read_line_into_buf` / `text_skip_line` 是通用文本助手(仅 music_room 用),未加 MainMenu 前缀。
- `+0x24` 字段:01 记为 `selection`;0x44c8c0 把它当"激活项计数"用 — 同一字段在不同态语义略有复用,Phase 3 逐态确认。

## 落盘 / 下一步
- 14 个 rename 已 MCP 落盘(+ 01 的 2 个 = 本子系统共 16 个新命名)。注释/类型 → 待 `apply_th16_mainmenu_names.py`。
- **Phase 3(下一刀,★SHT 回扣)**:反 `do_character_select`(0x4502c0)/ `do_subseason_select`(0x450af0)的**选择写入链** →
  追到写进哪个全局/存档字段、再被谁读去加载 `.sht`。这是把菜单接回 SHT 任务的关键。
