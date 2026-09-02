# card-expand —— 没有 C 代码要编，全部产物由 sites.py 从真 exe 生成。
ROWS ?= 58
PATCH := ../patch/th18.v1.00a.js

.PHONY: all check gen verify files clean

all: gen verify dll

## step1 —— 第 1 步交付态：58 行，行为零变化（仓库里 patch/ 提交的就是这个）
step1:
	$(MAKE) ROWS=58 gen verify dll dllx87 files

## step3 —— 战线 B 验证态：255 行 + 分配器搬迁 + patch-test（空槽→id 58 + 追踪断点）
step3:
	$(MAKE) ROWS=255 gen verify dll dllx87 files

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
LDFLAGS   := -shared -static-libgcc -s -lkernel32 -Wl,--no-insert-timestamp

## dll    —— 编 DLL（依赖 gen 出的 sites_gen.h）
dll: $(DLL)
SRCS      := dll_main.c selfcheck.c unlocked.c bp_trace.c
OBJS      := $(SRCS:.c=.o)
%.o: %.c card_expand.h sites_gen.h thcrap_bp.h
	$(CC) $(CFLAGS) -c -o $@ $<
$(DLL): $(OBJS) th18_card_expand.def
	$(CC) $(CFLAGS) -o $@ $(OBJS) th18_card_expand.def $(LDFLAGS)

## x87 自检 —— 只看我们自己的目标文件
dllx87: $(OBJS)
	@n=$$($(OBJDUMP) -d $(OBJS) | grep -cE '^\s+[0-9a-f]+:\s+[0-9a-f ]+\s+f(ld|st|add|sub|mul|div|ild|ist|xch|com)' || true); \
	 echo "x87 in our objects: $$n"; test "$$n" = 0

## dllverify —— 位数 / 导出表 / 依赖
dllverify: $(DLL)
	@file $(DLL)
	@$(OBJDUMP) -p $(DLL) | grep -A 6 '^Export Table:' | sed -n '1,8p'
	@echo "--- 依赖 ---"; $(OBJDUMP) -p $(DLL) | grep 'DLL Name'

## dist —— 在 ../dist/ 摆出可直接安装的整套：一个 DLL + patch-step1 / patch-step3 / patch-test
##         （dist/ 已 gitignore：DLL 是构建产物，不入库；随时 make dist 重建）
DIST := ../dist
dist:
	rm -rf $(DIST) && mkdir -p $(DIST)/bin $(DIST)/patch-step1 $(DIST)/patch-step3 $(DIST)/patch-test
	$(MAKE) -s ROWS=58  gen dll files >/dev/null
	cp $(DLL) $(DIST)/bin/ && cp ../patch/*.js $(DIST)/patch-step1/ && cp ../patch-test/*.js $(DIST)/patch-test/
	$(MAKE) -s ROWS=255 gen files >/dev/null
	cp ../patch/*.js $(DIST)/patch-step3/
	$(MAKE) -s ROWS=58  gen files >/dev/null
	cp ../DIST-README.txt $(DIST)/README.txt
	cd $(DIST) && rm -f th18_card_expand_bundle.zip && zip -qr th18_card_expand_bundle.zip bin patch-step1 patch-step3 patch-test README.txt
	@echo "dist/ 就绪："; ls $(DIST)

## release —— 构建 dist，同步进发布仓库 local/vendor/th18_modkit 并提交；PUSH=1 再推
release: dist
	python3 release.py
