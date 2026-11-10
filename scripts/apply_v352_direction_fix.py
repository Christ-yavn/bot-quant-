import os, shutil

repo_root = r"C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv"
src_mq5 = os.path.join(repo_root, "src", "mql5", "Deriv_VolSqueeze_Breakout_EA_v3.mq5")
archive_legacy = os.path.join(repo_root, "archive", "mql5_legacy")
dst_v351_mq5 = os.path.join(archive_legacy, "Deriv_VolSqueeze_Breakout_EA_v3_51.mq5")

# 1. Non-destructive archive of v3.51
shutil.copy2(src_mq5, dst_v351_mq5)
print(f"Archived v3.51 to: {dst_v351_mq5} ({os.path.getsize(dst_v351_mq5)} bytes)")

with open(src_mq5, "r", encoding="utf-8") as f:
    content = f.read()

# 2. Version bump to 3.52
content = content.replace('Release        : v3.51 (Omni-Basket & Retractable UI L99 Prod - Surgical Patch v3.51)', 'Release        : v3.52 (Omni-Basket & Retractable UI L99 Prod - Direction Fix v3.52)')
content = content.replace('#property version   "3.51"', '#property version   "3.52"')
content = content.replace('QuantPod v3.51', 'QuantPod v3.52')
content = content.replace('Hardened v3.31/v3.51', 'Hardened v3.31/v3.52')
content = content.replace('//| Render Real-Time Graphical Dashboard on Chart (v3.51 Retractable)|', '//| Render Real-Time Graphical Dashboard on Chart (v3.52 Retractable)|')
content = content.replace('⚡ QP v3.51 [', '⚡ QP v3.52 [')
content = content.replace('⚡ QUANT-POD v3.51 ELITE — [', '⚡ QUANT-POD v3.52 ELITE — [')
content = content.replace('//| Position Management & Strict Time-Stop Engine (v3.51)            |', '//| Position Management & Strict Time-Stop Engine (v3.52)            |')
content = content.replace('[v3.51 ', '[v3.52 ')

# 3. Add ExtLastRetBps declaration
old_decl = """// Telemetry state (zero 0.00 bps values)
double         ExtLastStd20         = 0.0;"""

new_decl = """// Telemetry state (zero 0.00 bps values)
double         ExtLastRetBps        = 0.0; // v3.52: Signed breakout bar return in bps (Close[shift=1] - Close[shift=2])
double         ExtLastStd20         = 0.0;"""

assert old_decl in content, "old_decl not found!"
content = content.replace(old_decl, new_decl)

# 4. Assign ExtLastRetBps in UpdateMarketTelemetry
old_telemetry_assign = """   ExtLastStd20     = pre_breakout_std20; // v3.51 Surgical Patch: Evaluates true pre-breakout volatility!
   ExtLastSqueezeQ  = squeeze_threshold;"""

new_telemetry_assign = """   ExtLastRetBps    = r_bps[0];           // v3.52: Vrai rendement signé de la bougie de cassure (Close[1] - Close[2])
   ExtLastStd20     = pre_breakout_std20; // v3.51 Surgical Patch: Evaluates true pre-breakout volatility!
   ExtLastSqueezeQ  = squeeze_threshold;"""

assert old_telemetry_assign in content, "old_telemetry_assign not found!"
content = content.replace(old_telemetry_assign, new_telemetry_assign)

# 5. Replace buggy CopyClose block in OnTick()
old_direction_block = """   // Fetch latest returns for direction calculation
   double r_bps_last = 0.0;
   double last_closes[2];
   if(CopyClose(_Symbol, ExtEffTimeframe, 1, 2, last_closes) == 2 && last_closes[1] > 0.0)
      r_bps_last = (last_closes[0] - last_closes[1]) / last_closes[1] * 10000.0;"""

new_direction_block = """   // v3.52 CRITICAL FIX: Use true signed breakout return from UpdateMarketTelemetry() (No inverted AsSeries bug)
   double r_bps_last = ExtLastRetBps;"""

assert old_direction_block in content, "old_direction_block not found!"
content = content.replace(old_direction_block, new_direction_block)

with open(src_mq5, "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully applied v3.52 patch to Deriv_VolSqueeze_Breakout_EA_v3.mq5!")
