# research/sht — SHT 格式逆向工程工作区

这是 SHT（自机 / shoot type）格式的**独立研究工作区**,用于在动手写 IDE 支持之前彻底搞懂原理。
与 `docs/` 的区别:`docs/` 放沉淀后的结论(`sht-format-research.md`、
`sht-webedit-and-shmupcc-analysis.md`),这里放**研究过程、原始材料、逆向草稿**。

## 目录结构

- `vendor/`(**已 gitignore,不入库**)— 第三方参考仓库的本地克隆
  - `sht-webedit/` — Priw8 浏览器编辑器,真实东方逐版本二进制 schema
    - 上游:<https://github.com/Priw8/sht-webedit> @ `98b8cca` (2023-09-20)
  - `shmupcc-sht/` — Priw8 quickjs CLI 编译器,声明式 struct + JSON 互转架构
    - 上游:<https://github.com/Priw8/shmupcc-sht> @ `dcf1f91` (2023-09-12)
  - ⚠️ 两个仓库都无 LICENSE 文件;按社区公开资料 + 作者允许进行研究/移植,正式发布前需确认授权。
  - 重新获取:`git clone <url> research/sht/vendor/<name>`
- `findings/` — 逆向工程的产出(deep research 报告、字段语义草稿、运行时模型笔记)

## 研究目标(为什么还要更深一层)

源码级布局已在 `docs/sht-webedit-and-shmupcc-analysis.md` 搞清。仍有一批**语义黑洞**需要逆向:

1. `flags` 段(各版本 0x20 / 0x3c 字节)到底控制什么?(sht-webedit README 自列为 TODO)
2. 行为函数索引 `func_on_init/tick/draw/hit`(TH19 变成 4× `func_?`)各自对应游戏里的什么行为
   (寻的、溅射、命中音效…)?各版本函数表是否有社区整理?
3. main 头部与 shooter 里的 `unknown_*` 字段含义。
4. 运行时模型:游戏是怎么按 power/focus 选 shooterset、怎么用 fire_rate 计时器发弹的
   (各版本计时器帧数差异、LoLK 的 120 帧 bug 根因)。
5. shmupcc-sht 的 `"shmupcc"` 归一化格式对应哪个引擎/中间表示,能否作为我们的统一中间层。

## 方法

- 用 deep research(多源网络检索 + 对抗验证)逆向上述语义,产出写入 `findings/`。
- 与 `vendor/` 源码、pytouhou 实现、touhouwiki 规范交叉印证。
- 结论稳定后再回填到 `docs/` 的两篇沉淀文档。
