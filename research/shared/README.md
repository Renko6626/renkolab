# research/shared — 东方 modding 社区知识库

这里沉淀**来自东方 modding 社区、我们已核实可信的结论**——格式事实、工具/人物、运行时模型、
逆向所得的语义表等。它是跨会话稳定的"共享底料",既供研究引用,也供 IDE 实现取用。

## 与其他目录的区别

- `sht/findings/` = **我们自己的研究/逆向报告**(过程 + 结论,带可信度分级,可能含未解项)。
- `shared/` = **已沉淀、可直接引用的知识**(去掉过程,只留结论 + 出处),按主题组织。
- `docs/` = 面向 IDE **实现**的设计沉淀。

经验法则:一条结论在 findings 里被验证清楚后,把"干货 + 出处"提炼进 `shared/` 的对应主题文件;
真正要驱动写代码时再进 `docs/`。

## 当前文件

- `touhou-modding-sources.md` — 社区工具链、关键人物、权威来源速查(谁做了什么、哪里查什么最准)。
- `th16-engine-math.md` — **TH16 引擎数学/CRT 模块**逆向语义表(角度/向量几何、CRT 浮点 atan2/fmod/floor/sin/cos/sqrt、
  ZUN 16 位 PRNG 算法+周期、数学常量实测)。是首个跨主题(非 SHT)引擎子系统结论。配套脚本:
  `../sht/disasm/scripts/apply_th16_math_names.py`(命名落盘)、`th16_prng_model.py`(PRNG 参考模型)。

## 待积累(随逆向推进新建)

- `sht-field-semantics.md` — SHT 各字段确证语义(尤其反汇编解出的 `func_*` 索引→行为表、`flags` 位表)。
- `sht-version-matrix.md` — 逐版本 schema 差异的稳定速查(从 `docs/sht-webedit-and-shmupcc-analysis.md` 提炼)。
- 其他格式(ECL/ANM/MSG/STD)若有社区结论也可入这里。

## 录入规范(保证可信、可追溯)

每条结论尽量标注:
- **出处**:一手优先(Priw8 sht-webedit 源码 / pytouhou 源码 / thtk / ExpHp truth),二手注明
  (touhouwiki Mddass 等)。
- **可信度**:✅确证 / 🟡单源或推断 / ❓社区未解。
- **适用范围**:哪些版本(SHT 逐版本差异大,别把某版结论当通用)。
- 反汇编得到的结论标注**游戏 + 地址/函数**,便于复核。
