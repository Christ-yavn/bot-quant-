import os, shutil

repo_root = r"C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv"
src_mq5 = os.path.join(repo_root, "src", "mql5", "Deriv_VolSqueeze_Breakout_EA_v3.mq5")
archive_legacy = os.path.join(repo_root, "archive", "mql5_legacy")
dst_v352_mq5 = os.path.join(archive_legacy, "Deriv_VolSqueeze_Breakout_EA_v3_52.mq5")

# 1. Non-destructive archive of v3.52
shutil.copy2(src_mq5, dst_v352_mq5)
print(f"Archived v3.52 to: {dst_v352_mq5} ({os.path.getsize(dst_v352_mq5)} bytes)")

with open(src_mq5, "r", encoding="utf-8") as f:
    content = f.read()

# 2. Version bump to 3.53
content = content.replace('Release        : v3.52 (Omni-Basket & Retractable UI L99 Prod - Direction Fix v3.52)', 'Release        : v3.53 (Omni-Basket & Retractable UI L99 Prod - Basket & Lot Optimization v3.53)')
content = content.replace('#property version   "3.52"', '#property version   "3.53"')
content = content.replace('QuantPod v3.52', 'QuantPod v3.53')
content = content.replace('Hardened v3.31/v3.52', 'Hardened v3.31/v3.53')
content = content.replace('//| Render Real-Time Graphical Dashboard on Chart (v3.52 Retractable)|', '//| Render Real-Time Graphical Dashboard on Chart (v3.53 Retractable)|')
content = content.replace('⚡ QP v3.52 [', '⚡ QP v3.53 [')
content = content.replace('⚡ QUANT-POD v3.52 ELITE — [', '⚡ QUANT-POD v3.53 ELITE — [')
content = content.replace('//| Position Management & Strict Time-Stop Engine (v3.52)            |', '//| Position Management & Strict Time-Stop Engine (v3.53)            |')
content = content.replace('[v3.52 ', '[v3.53 ')

# 3. Optimize V25 (1s) block: support M30 as well as H1
old_v25_block = """      if(StringFind(_Symbol, "25 (1s)") >= 0)
      {
         ExtEffRole         = "ALPHA_KING_V25";
         ExtEffTimeframe    = PERIOD_H1;
         ExtEffStrategyMode = STRAT_S1_VOL_SQUEEZE_BREAKOUT;
         ExtEffSqueezeQ     = 0.30;
         ExtEffBreakoutZ    = 1.25;
         ExtEffMaxHoldBars  = 4;
         ExtEffLotCap       = 0.050;
         ExtEffMagic        = 20261021;
         ExtIsSymbolPaused  = false;
      }"""

new_v25_block = """      if(StringFind(_Symbol, "25 (1s)") >= 0)
      {
         ExtEffRole         = "ALPHA_KING_V25";
         ExtEffTimeframe    = (_Period == PERIOD_M30 ? PERIOD_M30 : PERIOD_H1);
         ExtEffStrategyMode = STRAT_S1_VOL_SQUEEZE_BREAKOUT;
         ExtEffSqueezeQ     = 0.30;
         ExtEffBreakoutZ    = 1.25;
         ExtEffMaxHoldBars  = (ExtEffTimeframe == PERIOD_M30 ? 8 : 4);
         ExtEffLotCap       = 0.050;
         ExtEffMagic        = 20261021;
         ExtIsSymbolPaused  = false;
      }"""

assert old_v25_block in content, "old_v25_block not found!"
content = content.replace(old_v25_block, new_v25_block)

# 4. Optimize V15 (1s) block: reduce lot cap to 0.050
old_v15_block = """      else if(StringFind(_Symbol, "15 (1s)") >= 0)
      {
         ExtEffRole         = "STABILIZER_V15";
         ExtEffTimeframe    = PERIOD_M30;
         ExtEffStrategyMode = STRAT_S1_VOL_SQUEEZE_BREAKOUT;
         ExtEffSqueezeQ     = 0.30;
         ExtEffBreakoutZ    = 1.25;
         ExtEffMaxHoldBars  = 8;
         ExtEffLotCap       = 0.500;
         ExtEffMagic        = 20261015;
         ExtIsSymbolPaused  = false;
      }"""

new_v15_block = """      else if(StringFind(_Symbol, "15 (1s)") >= 0)
      {
         ExtEffRole         = "STABILIZER_V15";
         ExtEffTimeframe    = PERIOD_M30;
         ExtEffStrategyMode = STRAT_S1_VOL_SQUEEZE_BREAKOUT;
         ExtEffSqueezeQ     = 0.30;
         ExtEffBreakoutZ    = 1.25;
         ExtEffMaxHoldBars  = 8;
         ExtEffLotCap       = 0.050; // v3.53: Reduced from 0.500 to 0.050 to avoid over-weighting low net expectancy
         ExtEffMagic        = 20261015;
         ExtIsSymbolPaused  = false;
      }"""

assert old_v15_block in content, "old_v15_block not found!"
content = content.replace(old_v15_block, new_v15_block)

# 5. Disable Volatility 10 Index: ExtIsSymbolPaused = true
old_v10_block = """      else if(StringFind(_Symbol, "Volatility 10 Index") >= 0 || (StringFind(_Symbol, "10 Index") >= 0 && StringFind(_Symbol, "1s") < 0))
      {
         ExtEffRole         = "V10_STD_ALPHA";
         ExtEffTimeframe    = PERIOD_H1;
         ExtEffStrategyMode = STRAT_S1_VOL_SQUEEZE_BREAKOUT;
         ExtEffSqueezeQ     = 0.30;
         ExtEffBreakoutZ    = 1.25;
         ExtEffMaxHoldBars  = 4;
         ExtEffLotCap       = 0.500;
         ExtEffMagic        = 20261010;
         ExtIsSymbolPaused  = false;
      }"""

new_v10_block = """      else if(StringFind(_Symbol, "Volatility 10 Index") >= 0 || (StringFind(_Symbol, "10 Index") >= 0 && StringFind(_Symbol, "1s") < 0))
      {
         ExtEffRole         = "V10_STD_PAUSED";
         ExtEffTimeframe    = PERIOD_H1;
         ExtEffStrategyMode = STRAT_S1_VOL_SQUEEZE_BREAKOUT;
         ExtEffSqueezeQ     = 0.30;
         ExtEffBreakoutZ    = 1.25;
         ExtEffMaxHoldBars  = 4;
         ExtEffLotCap       = 0.050;
         ExtEffMagic        = 20261010;
         ExtIsSymbolPaused  = true; // v3.53: Paused due to negative net expectancy (-0.561 bps, Quarter-Kelly = 0.00%)
      }"""

assert old_v10_block in content, "old_v10_block not found!"
content = content.replace(old_v10_block, new_v10_block)

with open(src_mq5, "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully applied v3.53 basket and lot optimizations to MQ5!")

# 6. Update V15 Preset file
v15_preset_repo = os.path.join(repo_root, "presets_v3_50", "QuantPod_v350_03_V15_1s_M30_Stabilizer.set")
v15_preset_mt5 = r"C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Presets\QuantPod_v350_03_V15_1s_M30_Stabilizer.set"

for p in [v15_preset_repo, v15_preset_mt5]:
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            pset = f.read()
        pset = pset.replace("InpMaxLotCap=0.50", "InpMaxLotCap=0.05")
        with open(p, "w", encoding="utf-8") as f:
            f.write(pset)
        print(f"Updated V15 preset InpMaxLotCap=0.05 in: {p}")
