bin/th18_card_expand.dll   一份，配下面任何一套 patch。放 <thcrap>/bin。

patch-step1/   58 行，行为零变化。先跑这个。
               通过 = th18_card_expand.log 末尾 "OK: table filled (58 rows …), 100/100 sites verified"
               且游戏与香草无差别。
patch-step3/   255 行 + 分配器搬迁。step1 通过后，用它替换 step1 进栈。
               step3 自带本 mod 的卡池 th18/cards.js（黑桃 10/J/Q/K/A，id 58–62，各有行为，开局即解锁）。
               日志里应有 "cards: 5 registered from cards.js"；图鉴 / 编成 / 商店里都能看到，能买、能拿。
patch-test/    开发环境，叠在 step3 之上：th18/cards_dev.js 让起手卡组直接拿到 58–62 并追踪钩子。
               钩子部分：卡组编成里把第一格清空，开一局 →
               "trace: allocate_new_card(id=58, mode=1)  <- NEW ID"。
