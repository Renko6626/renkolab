# th18_mouse —— TH18 v1.00a 鼠标控制的 thcrap 插件(32 位)
#
# 本 mod 自带 DLL(路线 C)。这是对 mods/thcrap-platform.md §5「B 的不变量」的
# 一次有意识的例外:用户侧另有游戏侧管理器统管多个 DLL,取施工便利。
#
# 工具链:llvm-mingw(msvcrt 变体,Linux 宿主)。装法见 ../README.md。

TOOLCHAIN ?= $(HOME)/Tools/llvm-mingw-20260826-msvcrt-ubuntu-22.04-x86_64
CC        := $(TOOLCHAIN)/bin/i686-w64-mingw32-gcc
OBJDUMP   := $(TOOLCHAIN)/bin/i686-w64-mingw32-objdump

TARGET := th18_mouse.dll
SRCS   := dll_main.c bp_mouse.c
OBJS   := $(SRCS:.c=.o)
DEF    := th18_mouse.def

# -mfpmath=sse -msse2:断点函数跑在游戏的线程上下文里,绝不能用 x87 ——
# 未平衡的 FPU 栈会在别处崩,是最难查的一类。thcrap 自己的 Makefile 同样这么设。
CFLAGS  := -O2 -Wall -Wextra -mfpmath=sse -msse2
LDFLAGS := -shared -static-libgcc -s -lkernel32 -luser32

all: $(TARGET)

%.o: %.c th18.h thcrap_bp.h
	$(CC) $(CFLAGS) -c -o $@ $<

$(TARGET): $(OBJS) $(DEF)
	$(CC) $(CFLAGS) -o $@ $(OBJS) $(DEF) $(LDFLAGS)

check:
	python3 check_constants.py

# 导出表必须是**无装饰名**:thcrap 在 LoadLibrary 之前就先扫 PE 导出表找
# thcrap_plugin_init(thcrap/src/pe.cpp:88);__stdcall 不经 .def 会变成
# _thcrap_plugin_init@0,插件会被静默判定为「不是插件」。
verify: $(TARGET)
	@echo "--- 位数 / 类型 ---"
	@file $(TARGET)
	@echo "--- 导出表 ---"
	@$(OBJDUMP) -p $(TARGET) | grep -A 8 '^Export Table:'
	@echo "--- 依赖的 DLL ---"
	@$(OBJDUMP) -p $(TARGET) | grep 'DLL Name'
	@echo "--- x87 自检:只看我们自己的目标文件(msvcrt 的 printf 内部有 x87,与我们无关) ---"
	@if $(OBJDUMP) -d $(OBJS) | grep -E '\sf(ld|st|add|sub|mul|div|com|ucom|nst|xch|free|incstp|decstp)[a-z]*\s'; then \
		echo "  ❌ 我们的代码里有 x87 指令 —— 断点跑在游戏线程上,未平衡的 FPU 栈会在别处崩"; \
		exit 1; \
	else echo "  无 x87 指令 ✅"; fi

clean:
	rm -f $(TARGET) $(OBJS)

.PHONY: all check verify clean
