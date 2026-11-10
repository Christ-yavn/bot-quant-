import os, shutil, subprocess

mt5_experts_dir = r"C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Experts"
src_mq5 = os.path.abspath("src/mql5/Deriv_VolSqueeze_Breakout_EA_v3.mq5")
dst_mq5 = os.path.join(mt5_experts_dir, "Deriv_VolSqueeze_Breakout_EA_v3.mq5")
dst_ex5 = os.path.join(mt5_experts_dir, "Deriv_VolSqueeze_Breakout_EA_v3.ex5")
src_ex5 = os.path.abspath("src/mql5/Deriv_VolSqueeze_Breakout_EA_v3.ex5")

print("1. Copying MQ5 to MT5 Experts directory...")
shutil.copy2(src_mq5, dst_mq5)
print(f"Copied {src_mq5} -> {dst_mq5}")

compiler = r"C:\Program Files\MetaTrader 5 Terminal\metaeditor64.exe"
log_file = os.path.join(mt5_experts_dir, "metaeditor_compile.log")

if os.path.exists(log_file):
    os.remove(log_file)

print("2. Compiling with metaeditor64.exe...")
# Run compiler without affecting terminal64.exe
res = subprocess.run([compiler, f"/compile:{dst_mq5}", f"/log:{log_file}"], timeout=30)
print(f"Compiler process exited with code: {res.returncode}")

if os.path.exists(log_file):
    with open(log_file, "r", encoding="utf-16", errors="ignore") as f:
        log_content = f.read()
    print("Compilation Log:")
    print(log_content.strip())
else:
    print("Log file not found.")

if os.path.exists(dst_ex5):
    sz = os.path.getsize(dst_ex5)
    print(f"3. Compiled EX5 generated successfully! Size: {sz} bytes")
    shutil.copy2(dst_ex5, src_ex5)
    print(f"Copied {dst_ex5} -> {src_ex5}")
else:
    print("ERROR: EX5 was not generated!")
