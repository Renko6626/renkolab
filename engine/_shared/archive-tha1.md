# TH16 资产管线 —— THA1 归档 + ZUN 加密 + LZSS(游戏全格式通用)

> 方法:Ghidra(ghidra-re MCP)一手反编译 th16.exe(用户自有)。日期 2026-06-11。原 `sht/findings/09`,
> 因 `.dat` 归档承载 SHT/ANM/MSG/STD/ECL **全部格式、非 SHT 专属**,移入 `shared/`(可引用的格式事实)。
> 分级:✅高 / 🟡中。**仅 TH16 v1.00a**。来源:`funcs/unexplored.md` 的 "Arcfile" 子系统(ExpHP 未命名)。
> 意义:把游戏读资产的整条链(`.dat` 归档 → 查名 → 解密 → 解压)反清楚,为 IDE 资产管线铺路。
> 与社区:这是 ZUN 的 **THA1** 归档格式,thtk/thdat 已支持;本篇是**在 TH16 exe 内一手确认**(非新发现,
> 但把 exe 内的函数/数据精确定位命名了)。
> ★ **2026-06-11 对抗审计(3 个独立 agent + thtk 源码交叉)**:核心(读取链/加密/LZSS)**0 假阳性,逐项与
> thtk 逐字节吻合**;并(a)**补回了 open/头解析**(原误标"未找到",见 §1.5/§5)、(b)**收紧了 `0x458730` 的描述**
> (非 mipmap,是文本字形平滑,见 §4)、(c)限定"与 thtk 一致"为**格式层**(exe 用二叉树找匹配,thtk 用 hash 链表)。

## 0. 一句话

游戏资产打在 `th16.dat`(THA1 归档)里:**每个文件 LZSS 压缩 + 按文件名选 key 的 XOR 解密**。
读取入口 `reads_file_into_new_allocation_402440` → `Arcfile::find_entry`(按名查)→ `Arcfile::read_entry`
(读压缩字节 → `zun_decrypt` → `lzss_decompress`)。压缩器(`lzss_compress` 一族)也在,用于写出(存档/录像)。

## 1. 读取链(全部一手,已命名落盘)

```
reads_file_into_new_allocation_402440(name, &size, mode)   [ExpHP 名]
  mode==0(从归档): basename(去 \ 和 /) → 在全局表 ARCFILE_4c10b8 / 计数 DAT_004c10bc 里查
     → malloc(size) → Arcfile::read_entry(&ARCFILE_4c10b8, name, buf)
  mode!=0(散文件): CreateFileA + GetFileSize + ReadFile

Arcfile::find_entry @0x457290   this[0]=条目数组, this[1]=计数; stride 0x10; __stricmp 按名
Arcfile::read_entry @0x457120
  entry = find_entry(name)
  compressed = entry[5]-entry[1]   // 下一条偏移 - 本条偏移
  uncompressed = entry[2]
  读 compressed 字节(底层 Pbg::File,this+0xc;SetFilePointer 到 entry[1])
  ★解密:key_idx = (Σ name 字节) & 7  → DAT_0049f278[key_idx](stride 0xc:{key,step,block,limit})
          zun_decrypt(buf, compressed, key, step, block, limit)   [ExpHP 名 @0x402220]
  若 compressed != uncompressed → lzss_decompress(buf, compressed, out, uncompressed)
```

**条目记录布局**(`entry`,从 find_entry/read_entry 实证):`[0]`=文件名指针、`[1]`=归档内偏移、
`[2]`=解压后大小、`[5]`=下一条偏移(→ 压缩大小 = `[5]-[1]`)。`Arcfile` 对象:`+0`=条目数组、
`+4`=计数、`+0xc`=`Pbg::File*`(底层文件,vtable=`Pbg::File::vftable`,ExpHP 已命名)。

## 1.5 归档 OPEN + THA1 头解析(2026-06-11 审计补回,原误标"未找到")✅

**`archive_open_th16dat` @0x4572e0**(写全局 `ARCFILE_4c10b8` + 计数 `DAT_004c10bc`):
1. 经 `Pbg::File`(`DAT_004c10c4`)打开 **`"th16.dat"`**;
2. 读 **0x10 字节头** → `zun_decrypt(hdr, 0x10, key=0x1b, step=0x37, 0x10, 0x10)`;
3. 校验 **magic `local_18 == 0x31414854`**(小端 = `"THA1"`);
4. **头布局(0x10)**:`+0x00` magic、`+0x04` size(文件表解压后大小,去混淆 `+=0xf8a432eb` = −123456789)、
   `+0x08` zsize(文件表压缩大小,`+=0xc521974f` = −987654321)、`+0x0c` entry_count(`-=0x8180754` = 135792468)。
   **三个去混淆常量 = thtk 对应值的负数,逐一吻合**;
5. seek 到 `filesize - zsize`,读 zsize → `zun_decrypt(_, zsize, 0x3e, -0x65, 0x80, zsize)` → `lzss_decompress` 文件表;
6. `ARCFILE_4c10b8 = thai_build_entry_table(decompressed, count, data_offset)`。

**`thai_build_entry_table` @0x4574b0**:分配 `(count+1)*0x10`,逐条:拷 NUL 结尾文件名(malloc)、4 字节对齐越过名字、
读 3 个 dword `{offset, uncompressed_size, ?}` 填入 0x10-stride 记录;末条 sentinel 存 data 段偏移。
即 §1 里 `find_entry`/`read_entry` 消费的那张表。**与 thtk `thdat95` 逐字节吻合**。

## 2. 加密:`zun_decrypt` @0x402220(ExpHP 名;参数本篇坐实)✅

`zun_decrypt(data, size, key, step, block, limit)`:分块异或——每 `block` 字节一段(上限 `limit`),
段内字节 `^= key`,`key += step`(逐字节递增),并做了交错(前半从段尾倒写、后半正写)。
**key/step/block/limit 由 8 项表 `DAT_0049f278`(stride 0xc)按 `(name 字节和)&7` 选**——即**逐文件、
按文件名哈希选密钥**。`zun_encrypt`(0x402330)是其逆。

## 3. 压缩:LZSS(经典 Okumura 二叉树实现)✅

| 函数 | 地址 | 作用 |
| --- | --- | --- |
| `lzss_decompress` | 0x457f00 | 解压:bit 标志流,1=字面字节 / 0=回引(**13-bit 偏移 + 4-bit 长度,最小匹配 3**),写入 0x2000 环形缓冲 `DAT_004bef40` |
| `lzss_compress` | 0x457b20 | 压缩(解压的逆):8192 窗口、**最大匹配 0x12(18)** |
| `lzss_insert_node` | 0x458130 | 二叉搜索树找最长匹配 + 插入(树 `DAT_004a6f30`,stride 3:{parent,left,right}) |
| `lzss_delete_node` | 0x458370 | 树删除(递归,配 successor 0x4584b0) |
| `lzss_init` | 0x4580e0 | 清环形缓冲 + 清树 |

参数:窗口 **8192(0x2000)**、最小匹配 **3**、最大匹配 **18(0x12)**、偏移 13 位、长度 4 位、bit 序 MSB-first、
0 偏移=终止符。**位宽/窗口/参数与 thtk 的 THA1 LZSS 逐项吻合**(审计逐位核对,flag=1=字面非反向)。
⚠️ **仅格式层一致**:exe 用**二叉搜索树**找最长匹配(本节函数),thtk 用 **hash + 链表**——产出兼容、内部算法不同。
`lzss_compress` 的调用方经审计实证写 `scoreth16.dat`(`FUN_00449a00`)与 `replay/%s`(`FUN_00448400`)→ "存档/录像"为证据非推断。

## 4. ★ 一处 hint 误导(已澄清,防后人再追)

`funcs/unexplored.md` 把 **`0x458730`** 标了 "Arcfile" 线索(nearest-named 邻居),但它**不是归档代码**:
**唯一调用方 = `draw_text`(0x459240)**,处理喂给 `D3DXLoadSurfaceFromMemory` 的 GDI 文本渲染表面
`DAT_004a5d80`(先 memset + `TextOutA`)。对相邻像素做 RGB 半字节(`&0xf`/`>>4`/`>>8`)平均再 `>>1`,
format 0x15/0x1a → **文本字形表面的平滑/抗锯齿 pass**(★审计修正:**不是 mipmap/降采样**,我先前措辞过头了)。已加 DB 注释。
**教训**:unexplored.md 的子系统线索是"最近已命名邻居",非真实归属,反编译时须自行判断(文档已提示)。

## 5. 落盘 / 可信度 / 开放

- 已命名 + 加 [TH16] plate 注释:`Arcfile__read_entry`(0x457120)、`Arcfile__find_entry`(0x457290)、
  `lzss_decompress`(0x457f00)、`lzss_compress`(0x457b20)、`lzss_insert_node`(0x458130)、
  `lzss_delete_node`(0x458370)、`lzss_init`(0x4580e0)。`0x458730` 加了"非归档"澄清注释。
- ✅ 一手:读取链、条目布局、解密 key 选择、LZSS 参数,均来自反编译且自洽(解压=压缩的逆)。
- 🟡 数据符号 `DAT_0049f278`(key 表)/`DAT_004bef40`(环形缓冲)/`DAT_004a6f30`(LZSS 树)/
  `ARCFILE_4c10b8`(条目表)未改名(MCP 不持久化数据符号,需 driver;语义见上)。
- ✅(原 ❓,2026-06-11 审计补回):归档 **OPEN / THA1 头解析 = `archive_open_th16dat`(0x4572e0)** +
  表构建 `thai_build_entry_table`(0x4574b0),见 §1.5。(`Arcfile__constructor` 0x456fb0 只清零,是另一回事。)
- 🟡 **未做**:8 项解密 key 表 `DAT_0049f278` 的**具体数值**未逐字节读出比对 thtk 的 `th14_crypt_params`
  (选择算法/表布局已坐实,值待 PE 字节读)。
- 复核入口:Ghidra DB `th16`;格式对照 thtk/thdat(THA1)。

## 6. 对 IDE 的意义

THTK-Studio 已用 thtk(thdat)做 `.dat` 解包,故本篇主要价值是**确认 exe 内格式 + 命名落库**,
为将来"IDE 内置资产浏览/回写"或诊断 thdat 兼容性提供一手参照(尤其逐文件 key 选择 = `(name和)&7`)。
