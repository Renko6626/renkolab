# TH18 v1.00a 只读运行时探针 —— 交叉编译成 32 位 Windows DLL
#
# 工具链：llvm-mingw（msvcrt 变体，Linux 宿主）。装法见 ../README.md。
# 目标必须是 32 位：TH18 是 32 位 PE，thcrap 会拒绝位数不符的插件
# （thcrap/src/plugin.cpp:337 WRONG_ARCH）。

TOOLCHAIN ?= $(HOME)/Tools/llvm-mingw-20260826-msvcrt-ubuntu-22.04-x86_64
CC        := $(TOOLCHAIN)/bin/i686-w64-mingw32-gcc
OBJDUMP   := $(TOOLCHAIN)/bin/i686-w64-mingw32-objdump

TARGET  := th18_probe.dll
SRC     := th18_probe.c
DEF     := th18_probe.def

CFLAGS  := -O2 -Wall -Wextra
LDFLAGS := -shared -static-libgcc -s -lkernel32

all: $(TARGET)

$(TARGET): $(SRC) $(DEF)
	$(CC) $(CFLAGS) -o $@ $(SRC) $(DEF) $(LDFLAGS)

# 导出表里必须是**无装饰**的 thcrap_plugin_init：thcrap 在 LoadLibrary 之前
# 就先扫 PE 导出表找这个名字（thcrap/src/pe.cpp:88）。__stdcall 若不经 .def
# 会被装饰成 _thcrap_plugin_init@0，插件会被静默判定为「不是插件」。
check:
	python3 check_constants.py

verify: $(TARGET)
	@echo "--- 位数 / 类型 ---"
	@file $(TARGET)
	@echo "--- 导出表 ---"
	@$(OBJDUMP) -p $(TARGET) | grep -A 6 '^Export Table:'
	@echo "--- 依赖的 DLL ---"
	@$(OBJDUMP) -p $(TARGET) | grep 'DLL Name'

clean:
	rm -f $(TARGET)

.PHONY: all check verify clean
