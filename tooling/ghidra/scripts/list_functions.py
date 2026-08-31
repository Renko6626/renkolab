# Ghidra headless 脚本环境冒烟测试(Jython / GhidraScript API)。
# 用法见 ../README.md:analyzeHeadless <proj> <name> -process <bin> -noanalysis
#   -scriptPath ./scripts -postScript list_functions.py
# @category SHT
fm = currentProgram.getFunctionManager()
funcs = list(fm.getFunctions(True))
print("[list_functions] program=%s" % currentProgram.getName())
print("[list_functions] function count=%d" % len(funcs))
for f in funcs[:10]:
    print("  %s @ %s" % (f.getName(), f.getEntryPoint()))
