bin/th18_card_expand.dll   一份，配下面任何一套 patch。放 <thcrap>/bin。

patch-step1/   58 行，行为零变化。先跑这个。
               通过 = th18_card_expand.log 末尾 "OK: table filled (58 rows …), 100/100 sites verified"
               且游戏与香草无差别。
patch-step3/   255 行 + 分配器搬迁。step1 通过后，用它替换 step1 进栈。
patch-test/    验证钩子，叠在 step3 之上。卡组编成里把第一格清空，开一局。
               定论 = 日志里 "trace: allocate_new_card(id=58, mode=1)  <- NEW ID"
               ⚠️ 战线 C 之前只能测 id 58。
