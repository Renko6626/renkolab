# english_pattern — 标准英式牌面（黑桃 10/J/Q/K/A、方片 2）

来源：Wikimedia Commons「English pattern playing cards」系列，作者 Dmitry Fomin，**CC0 公有领域**。
文件 `English_pattern_{10,jack,queen,king,ace}_of_spades.svg`、`English_pattern_2_of_diamonds.svg`（`Special:FilePath` 取回，2026-09-04）。

处理：`rsvg-convert -h 640` → `fit_card.py <NAME> <png> --no-detect --trim 0 --bg '#ffffff' --margin 8`
（牌面 214:320，等比缩到高 304，白底居中、两侧白色填充；不做去白边，否则白牌面会被当边裁掉）。
