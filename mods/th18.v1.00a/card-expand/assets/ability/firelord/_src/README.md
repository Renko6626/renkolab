# ability/firelord/_src — 炎魔之王场上贴图的原始素材

| 文件 | 用在 | 来源 | 处理 |
| --- | --- | --- | --- |
| `FIRELORD_TOPDOWN.png` | 场上本体 `RAGNAROS.png`（entry `FIRELORD_BODY`，script91） | 用户提供（1189×1323 RGB，白底正面像，2026-09-06） | `../make_firelord_art.py`：四角泛洪抠白底 + 边缘 alpha 斜坡 → 裁包围盒 → 等比缩到 256 高、居中 256×256 |

火球 / 爆炸贴图没有源图，同一个脚本程序生成（固定种子）。卡图的源图在 `cards/_src/FIRELORD.png`。
