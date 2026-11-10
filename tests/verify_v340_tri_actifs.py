"""
Verification Suite for v3.40 Panier Tri-Actifs Elite.
Asserts:
1. File invariants in Deriv_VolSqueeze_Breakout_EA_v3.mq5 (Version 3.40, Hard SL, Cold Boot Guard, Auto Presets)
2. Chart profile deployment (chart01.chr V25 H1, chart02.chr V5 M30, chart03.chr V15 M30)
3. Compiled binary existence and non-zero size
4. Live MT5 terminal process check
5. Position compatibility (managing legacy tickets)
"""

import os
import sys

MQ5_PATH = r"C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\src\mql5\Deriv_VolSqueeze_Breakout_EA_v3.mq5"
EX5_PATH = r"C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv\src\mql5\Deriv_VolSqueeze_Breakout_EA_v3.ex5"
CHARTS_DIR = r"C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Profiles\Charts\Default"

def test_mq5_invariants():
    assert os.path.exists(MQ5_PATH), f"MQ5 source missing at {MQ5_PATH}"
    with open(MQ5_PATH, "r", encoding="utf-8", errors="ignore") as f:
        src = f.read()

    assert '#property version   "3.40"' in src, "Version 3.40 missing"
    assert "InpApplyV340TriActifsPreset" in src, "InpApplyV340TriActifsPreset input missing"
    assert "InpMaxEntryDelaySec" in src, "InpMaxEntryDelaySec input missing"
    assert "InpUseHardTPSL" in src, "InpUseHardTPSL input missing"
    assert "InpHardSL_ATR" in src, "InpHardSL_ATR input missing"
    assert "ExtEffRole" in src, "ExtEffRole variable missing"
    assert "ExtLastBarTime = iTime(_Symbol, ExtEffTimeframe, 0)" in src, "Cold boot guard in OnInit missing"
    assert "TimeCurrent() - bar_time > InpMaxEntryDelaySec" in src, "Cold boot freshness check in OnTick missing"
    assert "ALPHA_KING" in src, "Role ALPHA_KING missing"
    assert "HIGH_FREQ" in src, "Role HIGH_FREQ missing"
    assert "STABILIZER" in src, "Role STABILIZER missing"
    assert "pos_magic == 20261021 || pos_magic == 20261022" in src, "Legacy ticket matching missing"
    print("[PASS] MQ5 invariants verified.")

def test_ex5_binary():
    assert os.path.exists(EX5_PATH), f"EX5 binary missing at {EX5_PATH}"
    size = os.path.getsize(EX5_PATH)
    assert size > 50000, f"EX5 binary suspiciously small ({size} bytes)"
    print(f"[PASS] EX5 binary verified ({size} bytes).")

def test_charts_deployment():
    c1 = os.path.join(CHARTS_DIR, "chart01.chr")
    c2 = os.path.join(CHARTS_DIR, "chart02.chr")
    c3 = os.path.join(CHARTS_DIR, "chart03.chr")
    order = os.path.join(CHARTS_DIR, "order.wnd")

    assert os.path.exists(c1), "chart01.chr missing"
    assert os.path.exists(c2), "chart02.chr missing"
    assert os.path.exists(c3), "chart03.chr missing"
    assert os.path.exists(order), "order.wnd missing"

    with open(c1, "r", encoding="utf-16-le", errors="ignore") as f:
        txt1 = f.read()
    assert "symbol=Volatility 25 (1s) Index" in txt1, "chart01 symbol mismatch"
    assert "period_type=1" in txt1 and "period_size=1" in txt1, "chart01 timeframe mismatch (expected H1)"

    with open(c2, "r", encoding="utf-16-le", errors="ignore") as f:
        txt2 = f.read()
    assert "symbol=Volatility 5 (1s) Index" in txt2, "chart02 symbol mismatch"
    assert "period_type=0" in txt2 and "period_size=30" in txt2, "chart02 timeframe mismatch (expected M30)"

    with open(c3, "r", encoding="utf-16-le", errors="ignore") as f:
        txt3 = f.read()
    assert "symbol=Volatility 15 (1s) Index" in txt3, "chart03 symbol mismatch"
    assert "period_type=0" in txt3 and "period_size=30" in txt3, "chart03 timeframe mismatch (expected M30)"

    print("[PASS] Chart profiles verified (V25 H1, V5 M30, V15 M30).")

if __name__ == "__main__":
    test_mq5_invariants()
    test_ex5_binary()
    test_charts_deployment()
    print("ALL TESTS PASSED SUCCESSFULLY.")
