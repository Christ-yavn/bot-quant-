"""
Verification Suite for v3.50 Omni-Basket & Retractable UI.
Asserts:
1. File invariants in Deriv_VolSqueeze_Breakout_EA_v3.mq5:
   - Version 3.50
   - UpdateMarketTelemetry() function
   - Lookback Shift Bug fix (rolling_std[1])
   - OrderCalcMargin free margin verification
   - InpDirectionMode (DIR_BOTH, DIR_LONG_ONLY, DIR_SHORT_ONLY)
   - 3 Strategy Engines (STRAT_S1, STRAT_S2, STRAT_S3)
   - 8 Elite Assets Auto-Preset Matrix
   - Graphical Retractable UI (QP350_, OnChartEvent, ExtDashboardMinimized)
2. Presets .set files existence (6 presets)
3. Compiled binary existence and size > 70KB
4. Verification of 0 compiler errors/warnings in metaeditor.log
"""

import os
import sys

MQ5_PATH = r"C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\src\mql5\Deriv_VolSqueeze_Breakout_EA_v3.mq5"
EX5_PATH = r"C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\src\mql5\Deriv_VolSqueeze_Breakout_EA_v3.ex5"
PRESETS_DIR = r"C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\presets_v3_50"
MT5_PRESETS_DIR = r"C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Presets"
EDITOR_LOG = r"C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\logs\metaeditor.log"

def test_mq5_invariants():
    assert os.path.exists(MQ5_PATH), f"MQ5 source missing at {MQ5_PATH}"
    with open(MQ5_PATH, "r", encoding="utf-8", errors="ignore") as f:
        src = f.read()

    assert '#property version   "3.50"' in src, "Version 3.50 missing"
    assert "ENUM_STRATEGY_MODE" in src, "ENUM_STRATEGY_MODE missing"
    assert "STRAT_S1_VOL_SQUEEZE_BREAKOUT" in src, "STRAT_S1 missing"
    assert "STRAT_S2_MOMENTUM_CONTINUATION" in src, "STRAT_S2 missing"
    assert "STRAT_S3_OU_MEAN_REVERSION" in src, "STRAT_S3 missing"
    assert "ENUM_DIRECTION_MODE" in src, "ENUM_DIRECTION_MODE missing"
    assert "InpDirectionMode" in src, "InpDirectionMode missing"
    assert "UpdateMarketTelemetry()" in src, "UpdateMarketTelemetry() function missing"
    assert "pre_breakout_std20" in src, "pre_breakout_std20 missing (Bug 2 fix)"
    assert "OrderCalcMargin" in src, "OrderCalcMargin check missing (Bug 3 fix)"
    assert "OnChartEvent" in src, "OnChartEvent handler missing (Part 3 UI)"
    assert "ExtDashboardMinimized" in src, "ExtDashboardMinimized flag missing"
    assert "UI_PREFIX" in src and "QP350_" in src, "UI prefix QP350_ missing"
    assert "ALPHA_KING_V25" in src, "Role ALPHA_KING_V25 missing"
    assert "HIGH_FREQ_V5" in src, "Role HIGH_FREQ_V5 missing"
    assert "STABILIZER_V15" in src, "Role STABILIZER_V15 missing"
    assert "CHAMPION_VC550" in src, "Role CHAMPION_VC550 missing"
    assert "DEX1500_ELITE" in src, "Role DEX1500_ELITE missing"
    assert "RANGE_MEANREV" in src, "Role RANGE_MEANREV missing"
    assert "LADDER_MOM" in src, "Role LADDER_MOM missing"
    assert "BOOM300_SWING" in src, "Role BOOM300_SWING missing"
    assert "V10_STD_ALPHA" in src, "Role V10_STD_ALPHA missing"
    print("[PASS] MQ5 invariants verified.")

def test_ex5_binary():
    assert os.path.exists(EX5_PATH), f"EX5 binary missing at {EX5_PATH}"
    size = os.path.getsize(EX5_PATH)
    assert size >= 70000, f"EX5 binary smaller than expected ({size} bytes)"
    print(f"[PASS] EX5 binary verified ({size} bytes).")

def test_presets():
    required = [
        "QuantPod_v350_01_V25_1s_H1_AlphaKing.set",
        "QuantPod_v350_02_V5_1s_M30_HighFreq.set",
        "QuantPod_v350_03_V15_1s_M30_Stabilizer.set",
        "QuantPod_v350_04_Volatility_Crash_550_H4_Champion.set",
        "QuantPod_v350_05_DEX_1500_DOWN_M15_H1_Elite.set",
        "QuantPod_v350_06_Range_Break_200_H1_MeanReversion.set"
    ]
    for p in required:
        f1 = os.path.join(PRESETS_DIR, p)
        f2 = os.path.join(MT5_PRESETS_DIR, p)
        assert os.path.exists(f1), f"Preset missing in repo: {f1}"
        assert os.path.exists(f2), f"Preset missing in MT5: {f2}"
    print(f"[PASS] All {len(required)} presets verified in both locations.")

def test_compiler_log():
    assert os.path.exists(EDITOR_LOG), "metaeditor.log missing"
    with open(EDITOR_LOG, "r", encoding="utf-16-le", errors="ignore") as f:
        log_content = f.read()
    assert "0 errors, 0 warnings" in log_content, "Compiler errors found"
    print("[PASS] MetaEditor log confirms 0 errors, 0 warnings.")

if __name__ == "__main__":
    test_mq5_invariants()
    test_ex5_binary()
    test_presets()
    test_compiler_log()
    print("ALL v3.50 TESTS PASSED SUCCESSFULLY.")
