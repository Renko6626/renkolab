# card-expand —— 没有 C 代码要编，全部产物由 sites.py 从真 exe 生成。
ROWS ?= 58
PATCH := ../patch/th18.v1.00a.js

.PHONY: all check gen verify files clean

all: gen verify

## check  —— 只扫描 + 校验两条不变式，不产出
check:
	python3 sites.py check

## list   —— 25 个查表实例的全表
list:
	python3 sites.py list

## gen    —— 生成 patch（ROWS=58 是「行为零变化」的第 1 步）
gen:
	python3 sites.py gen --rows $(ROWS) -o $(PATCH)

## verify —— 把已生成的 patch 拿回真 exe 逐条对账
verify:
	python3 sites.py verify

## files  —— 刷新 patch/files.js 的 crc32 清单
files:
	python3 mkfiles.py

clean:
	rm -f $(PATCH)

## conflicts —— 与同一 patch 栈里其它 patch 求交集（base_tsa 要拿装机上的文件）
##   make conflicts OTHERS="<thcrap>/repos/nmlgc/base_tsa/th18.v1.00a.js"
conflicts:
	python3 sites.py conflicts $(OTHERS)

# ---- DLL：全有或全无的门（post_init 里填表 + 回读验证 100 处）----
TOOLCHAIN ?= $(HOME)/Tools/llvm-mingw-20260826-msvcrt-ubuntu-22.04-x86_64
CC        := $(TOOLCHAIN)/bin/i686-w64-mingw32-gcc
OBJDUMP   := $(TOOLCHAIN)/bin/i686-w64-mingw32-objdump
DLL       := th18_card_expand.dll
CFLAGS    := -O2 -Wall -Wextra -mfpmath=sse -msse2
LDFLAGS   := -shared -static-libgcc -s -lkernel32

## dll    —— 编 DLL（依赖 gen 出的 sites_gen.h）
dll: $(DLL)
$(DLL): th18_card_expand.c sites_gen.h th18_card_expand.def
	$(CC) $(CFLAGS) -o $@ th18_card_expand.c th18_card_expand.def $(LDFLAGS)

## dllverify —— 位数 / 导出表 / 依赖
dllverify: $(DLL)
	@file $(DLL)
	@$(OBJDUMP) -p $(DLL) | grep -A 6 '^Export Table:' | sed -n '1,8p'
	@echo "--- 依赖 ---"; $(OBJDUMP) -p $(DLL) | grep 'DLL Name'
