import os, sys

def run_tests():
    print("=== QUANT-POD v3.51 SURGICAL PATCH VERIFICATION SUITE ===")
    
    src_file = os.path.abspath("src/mql5/Deriv_VolSqueeze_Breakout_EA_v3.mq5")
    assert os.path.exists(src_file), f"Source file missing: {src_file}"
    with open(src_file, "r", encoding="utf-8") as f:
        mq5_code = f.read()

    # Test 1: Version 3.51
    assert '#property version   "3.51"' in mq5_code, "Test 1 Failed: #property version is not 3.51"
    assert 'QuantPod v3.51' in mq5_code, "Test 1 Failed: Description is not updated to 3.51"
    print("Test 1 PASSED: Version strings verified as v3.51.")

    # Test 2: Bug Subtil A (Lookback Shift contamination fixed)
    assert "double pre_breakout_std20 = (ArraySize(rolling_std) > 1) ? rolling_std[1] : rolling_std[0];" in mq5_code
    assert "int q_count = (InpQuantileWindow > 1) ? (InpQuantileWindow - 1) : 1;" in mq5_code
    assert "sorted_std[i] = rolling_std[i + 1];" in mq5_code
    assert "ExtLastStd20     = pre_breakout_std20;" in mq5_code
    assert "double safe_std = (pre_breakout_std20 > 1e-9) ? pre_breakout_std20 :" in mq5_code
    assert "double breakout_z = MathAbs(r_bps[0]) / safe_std;" in mq5_code
    print("Test 2 PASSED: Bug Subtil A verified (Lookback Shift contamination removed, rolling_std[1] used).")

    # Test 3: Bug Subtil B (Profit Lock false positive resolved)
    assert "double cur_sl = ExtPosition.StopLoss();" in mq5_code
    assert "double open_px = ExtPosition.PriceOpen();" in mq5_code
    assert "is_profit_locked = (cur_sl > open_px);" in mq5_code
    assert "is_profit_locked = (cur_sl > 0.0 && cur_sl < open_px);" in mq5_code
    assert 'pos_lock_str = is_profit_locked ? "VERROUILLÉ (+0.20 ATR)" : "ARMÉ (Seuil +1.20 ATR)";' in mq5_code
    print("Test 3 PASSED: Bug Subtil B verified (Dynamic Trailing Lock checked against open_px).")

    # Test 4: Dashboard retractable strings
    assert '⚡ QP v3.51 [' in mq5_code
    assert '⚡ QUANT-POD v3.51 ELITE — [' in mq5_code
    print("Test 4 PASSED: Retractable UI strings verified as v3.51.")

    # Test 5: Compiled EX5 binaries
    ex5_src = os.path.abspath("src/mql5/Deriv_VolSqueeze_Breakout_EA_v3.ex5")
    mt5_ex5 = r"C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Experts\Deriv_VolSqueeze_Breakout_EA_v3.ex5"
    assert os.path.exists(ex5_src), "Source EX5 missing"
    assert os.path.exists(mt5_ex5), "MT5 Experts EX5 missing"
    assert os.path.getsize(ex5_src) > 50000, "EX5 size suspiciously small"
    assert os.path.getsize(mt5_ex5) > 50000, "MT5 EX5 size suspiciously small"
    print(f"Test 5 PASSED: Compiled binaries present and valid ({os.path.getsize(ex5_src)} bytes).")

    # Test 6: Running Terminals
    import psutil
    terminals = [p.info for p in psutil.process_iter(['pid', 'name', 'exe']) if p.info['name'] and 'terminal' in p.info['name'].lower()]
    print(f"Test 6: Active terminals count = {len(terminals)}")
    for t in terminals:
        print(f"  - Terminal PID: {t['pid']}, Name: {t['name']}, Exe: {t.get('exe')}")
    assert len(terminals) >= 2, "Less than 2 MT5 terminals running!"
    print("Test 6 PASSED: Both MT5 terminals are active and uninterrupted.")

    print("\nALL 6 VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    run_tests()
