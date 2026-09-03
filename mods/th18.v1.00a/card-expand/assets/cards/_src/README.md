# _src — 卡图用到的第三方 / 原始素材（原件 + 出处）

| 文件 | 用在 | 来源 | 处理 |
| --- | --- | --- | --- |
| `reverse_card.png` | REVERSE（反转牌，id 64） | 用户提供（UNO 反转牌图，2304×3500） | `fit_card.py REVERSE cards/_src/reverse_card.png`：去白边、上下各修 3%、等比缩放居中到白底 256×320 |

现成卡图一律走 `fit_card.py`，别手工缩。
