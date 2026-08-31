# _template/ — 新建 mod 的起手式

```bash
cp -r mods/_template mods/<版本>/<mod名>
```

然后：

1. 填 [`TARGET.md`](TARGET.md) —— **先填这个**。填不动说明逆向还没到位，回 `engine/` 补。
2. 写 `native/` 里的 cave 源码。
3. 组织 `patch/`：thcrap patch 根下 `patch.js` + `files.js`（CRC32 清单）+ 逐版本 `<版本>.js`。
   顶层放 `codecaves` / `binhacks` / `options`；binhack = `{addr, expected, code}`。
4. 成品脚本资产（`.ecl` / `.anm` / `.sht`）放 `assets/`，用 THTK-Studio 编辑。
5. **过 [`AUDIT-checklist.md`](AUDIT-checklist.md)**，把结果写进 `AUDIT.md`。
6. 先做**无行为改动**的加载验证，再一次只加入一个行为变化。
7. 实跑结果回写 `AUDIT.md`；新确认的地址/语义回流 `engine/`。
