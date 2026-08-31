# anm — ANM 精灵动画 VM

⚠️ **本子系统尚未系统开工。**

东方里几乎所有「显示」都挂在 `.anm` 上：创建一个显示对象 = 选一段 anm 脚本/模板，
由 anm VM 每帧驱动它的精灵、变换、特效。它因此是**图形侧的总接缝**——
MSG 的文本绘制走它（[`../msg/OVERVIEW.md`](../msg/OVERVIEW.md)）、弹幕的外观也走它。

## 断言 × 版本矩阵

| 断言 | th16 | 证据 |
| --- | :---: | --- |
| 存在 anm 脚本 VM，每帧驱动显示对象 | 🟡 | [th16/README](th16/README.md)（做弹幕时顺带掀开的口子，多为 call-site/二手） |

> **图例**：✅ 该版本一手验过（证据列给地址/出处） · 🟡 待验（从别的版本借来的假设，或单源） · ❌ 已知不同/不存在 · ❓ 存疑 · — 未看
>
> **本页不许出现没有出处的断言。** 从某作借到另一作的判断一律 🟡，在该版本 exe 上验过才能改 ✅（[`METHOD.md`](../../METHOD.md)）。

## 开工前必读

[th16/README.md](th16/README.md) 里的「起步锚点」全部是做 [`../bullet/`](../bullet/OVERVIEW.md)
时**顺带掀开的口子**，多为 🟡（call-site / 二手）。**动手时务必自己反编译复核，别当定论。**

ExpHP `th-re-data` 对 `zAnmVm` / `AnmManager` 已有大量命名（TH16 AnmVm 45 / AnmManager 38），
起步先套（[`../../tooling/ghidra/bootstrap.py`](../../tooling/ghidra/bootstrap.py)）。
