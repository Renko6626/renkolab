# re-mcp-ghidra 本地补丁

## `re-mcp-ghidra-3.0.2-txfix.diff` — 修复 save 不落盘

**问题**:`re-mcp-ghidra` 3.0.2(PyPI 最新,上游 `jtsylve/re-mcp` main 亦同)的 `rename_function`/
`set_comment` 改动**不会可靠落盘**。根因:`GhidraProject.importProgram()`/`openProgram()` 返回的
program 上留着一个整会话不关的 **"Batch Processing" 事务**,占着工程锁 → `DomainFile.save()` 报
`Unable to lock due to active transaction`,只有第一次 `saveAs`(绕过锁)能写进去,之后全丢。
上游 commit `275887d6`("fix Ghidra save_database",3.0.1)试图修过但没修对(`_end_open_transactions`
用错事务 id)。**社区无人报告此 bug。**

**修法**(本 diff,已端到端验证 `RESULT: PASS`):open 后 round-trip 一次丢弃批处理事务——
`saveAs`(若需)→ `project.close(program)` → 用**专用 `java.lang.Object` consumer** 以可写方式
`df.getDomainObject(...)` 重开;`Session.close()` 关工程前 `release` 该 consumer 释放锁。

**应用**(目标:`.../site-packages/re_mcp_ghidra/session.py`):
```bash
cd <re-mcp-ghidra venv>/lib/python3.*/site-packages/re_mcp_ghidra
cp session.py session.py.bak                       # 备份
patch -p0 < <repo>/research/sht/disasm/patches/re-mcp-ghidra-3.0.2-txfix.diff
# 然后重启 ghidra-re MCP 服务(运行中的进程不会热加载源码改动)
```
⚠️ 这是改**已安装工具的副本**,`uv tool upgrade/reinstall` 会覆盖;升级后需重打或改走上游 PR。

**验证脚本**:`/tmp/txtest_th16fix/harness2.py`(开→注释A→存→关→重开→注释B→存→关→重开→查 A、B 皆在)。

## 另发现(独立,未修):`run_auto_analysis=True` 路径
standalone 调用 `Session.open(..., run_auto_analysis=True)` 在 Ghidra 12.1.2 报
`GhidraProgramUtilities.setAnalyzedFlag` 不存在(疑应 `resetAnalysisFlags`)。但经 MCP 开 th16 时分析
正常(得 1927 函数),故疑路径相关、未阻塞,待单独复核。
