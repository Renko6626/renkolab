# ghidra-re MCP 工具目录(pinned vs hidden,给逆向 agent)

> 我们用的是**自维护 fork** `Renko6626/re-mcp` 分支 `thtk-patches`(上游 `jtsylve/ida-mcp` 基本不维护)。
> 装:`uv tool install --force "git+https://github.com/Renko6626/re-mcp@thtk-patches#subdirectory=packages/re-mcp-ghidra"`。
> ★ **核心认知**:这个 MCP 有 ~90 个工具,但只 **pin 一小撮**给客户端。**harness 的 ToolSearch 只看得到 pinned 的**;
> 其余是 **hidden** —— 不在 ToolSearch 里 ≠ 不存在,用 **`search_tools(关键词)` 发现 + `batch`/`call`/`execute` 按名调**。
> (血泪:我们一度以为"没有数据符号改名工具/没有读字节工具"去绕 driver/手解析 PE——其实 `rename_address`、`read_bytes` 一直都在,只是 hidden。)

## A. 已 pin(ToolSearch 直接可见,= 高频骨干)
- **探索**:`get_database_info` `list_functions` `list_names` `decompile_function` `disassemble_function`
  `get_xrefs_to` `get_xrefs_from` `get_call_graph` `get_strings` `find_code_by_string` `read_bytes`
- **改名/注释**:`rename_function` `rename_address`(数据符号/标签)`list_decompiler_variables`
  `rename_decompiler_variable` `retype_decompiler_variable` `set_comment` `set_decompiler_comment`
- **函数签名**:`set_function_type` `set_function_calling_convention`(改原型/调用约定 → 修 thiscall、VM handler)
- **结构体**:`list_structures` `get_structure` `create_structure` `add_struct_member` `retype_struct_member`
- **类型**:`list_local_types` `parse_type_declaration` `apply_type_at_address` `get_type_info` `set_type`
- **管理/元**(框架自带常驻):`open_database` `close_database` `wait_for_analysis` `save_database` `list_databases`
  / `search_tools` `get_schema` `call` `batch` `execute`

> ★ 落盘:rename/comment/类型改完**每批必 `save_database`**(返回 `{"status":"saved"}`),否则 DB 超时回收会丢未存的。

## B. Hidden 但**路线图会用到的金子**(按需 `search_tools` 拉 + batch/call 调)
> 这些不在 ToolSearch,但做 ECL/ANM/MSG 解析器、弹幕/玩家系统时很可能要——**先知道它们存在**:
- `get_switch_info` / `list_switches`(switches)— ★ **ECL 字节码派发大 switch**(那个 ~4500 指令的 ins dispatcher)。
- `make_data` / `make_string` / `make_array`(makedata)— 给 ANM/MSG/弹幕的**文件字段/表标数据类型**。
- `get_cfg_edges` / `get_basic_blocks`(cfg)— VM/复杂函数的控制流。
- `get_ctree` / `find_ctree_calls`(ctree)— 在反编译树里精确找调用点。
- `demangle_name` / `demangle_at_address` / `list_demangled_names`(demangle)— ★ **RTTI/C++ 真名还原**(`.?AV*Inf@@` → ZUN 类名)。
- `search_bytes` / `search_text`(search)— 字节模式扫(如按结构偏移找 disp32 xref,过去靠手写 Python)。
- `create_function` / `make_code` / `undefine`(patching)— ★ **把裸码变成函数**(我们遇到的 init2/init4 裸码 Ghidra 没建函数,这个能建)。
- `get_imports` / `get_exports` / `get_entry_points`(imports_exports)— Win32 API 边界 / 入口。
- `get_stack_frame` / `get_function_vars`(frames)、`decode_instruction(s)` / `get_operand_value`(operands)— 精确操作数/栈帧。
- `export_all_pseudocode` / `export_all_disassembly`(export)— 大批量导出(喂 subagent / 离线分析)。
- `parse_source_declarations`(srclang)— 一次性吃一坨 C 声明建多类型。
- 结构体/枚举补全:`rename_struct_member` `delete_struct_member` `delete_structure`(structs)、enums 全套 CRUD。

## C. Hidden 且**我们基本不会碰**(知道有就行)
`assemble_instruction`/`patch_asm`/`patch_bytes`、`bookmarks`、`colors`、`chunks`、`dirtree`(项目文件夹)、
`segments`、`rebase`、`snapshots`、`undo`/`redo`、`regvars`、`regfinder`、`sig_gen`/`apply_function_id`、
`entry_manip`、`func_flags`、`operand_repr`、`processor`、`nalt`、`utility`、`xref_manip`、`load_bytes_from_memory`。

## 怎么发现/调隐藏工具
```
search_tools("switch")            # 关键词找隐藏工具(覆盖全部 ~90 个)
get_schema(tools=["get_switch_info"])   # 取参数
batch operations=[{tool:"get_switch_info", params:{address:"0x..."}}]   # 调用(或 call / execute)
```

## pin 集怎么改(以后想增减)
编辑 fork 的 `packages/re-mcp-ghidra/src/re_mcp_ghidra/transforms.py` 的 `PINNED_TOOLS` → commit/push 到
`thtk-patches` → `uv tool install --force` 重装 → 重启 ghidra-re MCP/开新会话生效。pin 有上下文成本(每个 schema
都进客户端),所以**只 pin 跨子系统高频的**;单子系统才用的留 hidden,按需拉。
