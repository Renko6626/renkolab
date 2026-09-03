# _src — 卡图用到的第三方 / 原始素材（原件 + 出处）

| 文件 | 用在 | 来源 | 处理 |
| --- | --- | --- | --- |
| `reverse_card.png` | REVERSE（反转牌，id 64） | 用户提供（UNO 反转牌图，2304×3500） | `fit_card.py REVERSE cards/_src/reverse_card.png --fill`：去白边、上下各修 3%、横向拉满 256（两侧不留白边）、白底 |

| `english_pattern/*.svg` | 黑桃 10/J/Q/K/A（id 58–62） | Wikimedia Commons，Dmitry Fomin，CC0 | 见该目录 README：渲染 640 高 → `fit_card.py --no-detect --trim 0 --bg '#ffffff'`（两侧白底填充） |

现成卡图一律走 `fit_card.py`，别手工缩。
