# tooling/thtk — 标准 thtk（thanm / thdat / thecl）编译与解包

版本无关的资产工具链：把游戏 `.dat` 解开、把 `.anm` 反成 thanm spec + 贴图，
以及（在 mod 侧）用 thanm 把改过的 spec 编回去。**只用标准 thtk**，不用 truanm——
产物要和社区生态（thcrap 补丁、其他人的 thanm 脚本）互通。

```bash
bash tooling/thtk/build.sh               # 编 thanm + thdat → local/vendor/thtk/build/（幂等）
python3 tooling/thtk/unpack.py th18.v1.00a   # 解 dat → local/th18.v1.00a/{dat,anm}/
source tooling/env.sh                    # 顺带导出 THANM / THDAT / THTK_ANMMAP_DIR
python3 tooling/doctor.py                # 自检里有 thtk 一组
```

## 为什么自己编

- thtk 发布页（release 12）**只有 Windows exe**；Linux 上没 wine 就跑不了。
- thanm 的语法解析器是 bison + flex 现场生成的，源码树里没有预生成的 `.c`。
- 这台机器没 sudo。`build.sh` 在系统缺 bison/flex/m4 时用 `apt-get download` 拉发行版 .deb，
  `dpkg -x` 解到 `local/vendor/bisonflex/` 直接用——零编译、零安装。
  **坑**：bison 搬家后找不到自己的 skeleton，必须 `BISON_PKGDATADIR=<bisonflex>/usr/share/bison`，
  `build.sh` 已经处理。非 apt 系统自己装好三件再跑。

## 解包布局（全部在 `local/`，不入库）

```
local/<版本>/
  thXX.dat            用户放（版权）
  dat/                thdat -x 的全部文件
  anm/<名>/
    <名>.anm.txt      thanm -l 的 spec（带 anmmap 助记符）
    <entry 路径>.png  thanm -x 的贴图，按 entry 的 name 落地（如 ability/BLANK_max.png）
    <名>.err          应为空
```

一个 anm 一个目录：spec 和它自己的贴图放一起，重编时 `cd` 进去 `thanm -c` 路径就对。

## anmmap（指令助记符）

`thanm -l` 默认只给 `ins_NNN`；加 `-m <anmmap>` 才有 `pos` / `alpha` / `scriptNew` 这类名字。
用的是 thpages（ExpHP 指令参考站）的 `static/mapfile/v8.anmm`（TH13–TH18 通用，含 th18 新加的
439 `fadeNearCamera` / 614 `drawArc`）；`any.anmm` 是版本 → 文件的映射。备份源是 ExpHP `truth`
仓库的 `map/`（Apache-2.0），内容几乎一致（thpages 多一条 432 `slowdownImmune`）。

⚠️ **`thanm -c` 编译时必须用和 `-l` 同一份 anmmap**，否则助记符解析不了。

## thecl（ECL）

`thecl -d 18 -m local/vendor/eclmap/eclmap/th18.eclm x.ecl x.txt` 反编译、`-c` 编回；指令名靠 Priw8 的 eclmap
（`git clone https://github.com/Priw8/eclmap local/vendor/eclmap`）。th18 的 `st01.ecl` / `st01bs.ecl` 往返字节一致（2026-09-04）。
⚠️ 反编译文本里的字符串是 Shift-JIS，Python 处理要 `errors="surrogateescape"`。

## thanm 速查

```
thanm -l 18 x.anm -m v8.anmm        列出 spec（entry / sprite / script）
thanm -x 18 x.anm                   按 entry name 解出贴图（相对 cwd）
thanm -c 18 out.anm spec.txt -m v8.anmm   从 spec + 贴图编回（贴图路径相对 cwd）
thanm -r 18 x.anm NAME file.png     只换一张贴图
```

th18 上 `-l` → `-c` 往返**字节一致**（2026-09-04 在 `abcard.anm` 上验过）。

## 已知规模（th18，2026-09-04 一手解包）

56 个 anm、529 张贴图、139 MB。大头：`front.anm` 382 脚本、`bullet.anm` 328、`enemy.anm` 261、
`effect.anm` 195、`title.anm` 174。卡牌三件：`abcard.anm` 118 entry / 18 脚本（卡图），
`ability.anm` 7 entry / 68 脚本（场上特效），`abmenu.anm` 3 entry / 19 脚本（编成 / 图鉴 UI）。
