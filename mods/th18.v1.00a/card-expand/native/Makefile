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
