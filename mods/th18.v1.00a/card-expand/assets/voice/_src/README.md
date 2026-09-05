# voice/_src — 语音原始素材（原件 + 出处）

| 文件 | 用在 | 来源 | 处理 |
| --- | --- | --- | --- |
| `FIRELORD_SUMMON.ogg` | 炎魔之王（id 72）召唤语音（id `0x55`） | 用户提供（Vorbis 48 kHz 单声道 4.55 s，2026-09-06） | `convert_voice.py FIRELORD_SUMMON`：+6 dB + 软限幅 → 44.1 kHz 16-bit 单声道 wav |
| `FIRELORD_ATTACK.ogg` | 炎魔之王投火球语音（id `0x56`） | 同上（4.29 s） | 同上 |

wav 是产物（`../FIRELORD_*.wav`，入库）；改素材就重跑 `convert_voice.py` 再 `make voice`。
