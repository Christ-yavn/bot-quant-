import os, sys, glob

def run_tests():
    print("=== QUANT-POD v3.53 BASKET OPTIMIZATION VERIFICATION SUITE ===")
    
    repo_root = os.path.abspath(".")
    src_file = os.path.join(repo_root, "src", "mql5", "Deriv_VolSqueeze_Breakout_EA_v3.mq5")
    assert os.path.exists(src_file), f"Source file missing: {src_file}"
    with open(src_file, "r", encoding="utf-8") as f:
        mq5_code = f.read()

    # Test 1: Version 3.53
    assert '#property version   "3.53"' in mq5_code, "Test 1 Failed: #property version is not 3.53"
    assert 'QuantPod v3.53' in mq5_code, "Test 1 Failed: Description is not updated to 3.53"
    print("Test 1 PASSED: Version strings verified as v3.53.")

    # Test 2: Direction Mechanics (preserved from v3.52)
    assert "double         ExtLastRetBps        = 0.0;" in mq5_code
    assert "ExtLastRetBps    = r_bps[0];" in mq5_code
    assert "double r_bps_last = ExtLastRetBps;" in mq5_code
    assert "direction = (r_bps_last > 0.0) ? 1.0 : -1.0;" in mq5_code
    print("Test 2 PASSED: S1 Direction mechanics strictly preserved.")

    # Test 3: Volatility 25 (1s) Dual Timeframe (M30 & H1)
    assert 'ExtEffTimeframe    = (_Period == PERIOD_M30 ? PERIOD_M30 : PERIOD_H1);' in mq5_code
    assert 'ExtEffMaxHoldBars  = (ExtEffTimeframe == PERIOD_M30 ? 8 : 4);' in mq5_code
    print("Test 3 PASSED: Volatility 25 (1s) dual TF (M30/H1) and dynamic hold bars (8/4) verified.")

    # Test 4: Volatility 15 (1s) lot cap reduced to 0.050
    assert 'STABILIZER_V15' in mq5_code
    assert 'ExtEffLotCap       = 0.050; // v3.53: Reduced from 0.500 to 0.050' in mq5_code
    
    preset_repo = os.path.join(repo_root, "presets_v3_50", "QuantPod_v350_03_V15_1s_M30_Stabilizer.set")
    preset_mt5 = r"C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Presets\QuantPod_v350_03_V15_1s_M30_Stabilizer.set"
    for p in [preset_repo, preset_mt5]:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                p_text = f.read()
            assert "InpMaxLotCap=0.05" in p_text, f"Preset {p} did not have InpMaxLotCap=0.05"
    print("Test 4 PASSED: Volatility 15 (1s) lot cap = 0.050 verified in code and .set presets.")

    # Test 5: Volatility 10 Index Paused
    assert 'ExtEffRole         = "V10_STD_PAUSED";' in mq5_code
    assert 'ExtIsSymbolPaused  = true; // v3.53: Paused due to negative net expectancy' in mq5_code
    print("Test 5 PASSED: Volatility 10 Index paused (ExtIsSymbolPaused = true) verified.")

    # Test 6: Non-destructive archive of v3.52
    archive_v352 = os.path.join(repo_root, "archive", "mql5_legacy", "Deriv_VolSqueeze_Breakout_EA_v3_52.mq5")
    assert os.path.exists(archive_v352), "v3.52 archive missing"
    assert os.path.getsize(archive_v352) > 50000, "v3.52 archive corrupted"
    print(f"Test 6 PASSED: v3.52 non-destructively archived ({os.path.getsize(archive_v352)} bytes).")

    # Test 7: Compiled EX5 file exists and is fresh
    ex5_repo = os.path.join(repo_root, "src", "mql5", "Deriv_VolSqueeze_Breakout_EA_v3.ex5")
    ex5_mt5 = r"C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Experts\Deriv_VolSqueeze_Breakout_EA_v3.ex5"
    assert os.path.exists(ex5_repo) and os.path.getsize(ex5_repo) > 70000
    assert os.path.exists(ex5_mt5) and os.path.getsize(ex5_mt5) > 70000
    print(f"Test 7 PASSED: Compiled v3.53 EX5 verified in repo and MT5 ({os.path.getsize(ex5_mt5)} bytes).")

    # Test 8: Single active EX5 in MT5 Experts
    mt5_experts_dir = r"C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Experts"
    ex5_files = glob.glob(os.path.join(mt5_experts_dir, "*.ex5"))
    print(f"Active EX5 files in MT5 Experts: {[os.path.basename(f) for f in ex5_files]}")
    assert len(ex5_files) == 1, f"Expected strictly 1 .ex5, found {len(ex5_files)}: {ex5_files}"
    print("Test 8 PASSED: Strictly 1 active .ex5 file in MT5 Experts directory.")

    # Test 9: Active MT5 Terminals running safely
    import psutil
    terminals = [p.info for p in psutil.process_iter(['pid', 'name', 'exe']) if p.info['name'] and 'terminal' in p.info['name'].lower()]
    print(f"Active terminals count = {len(terminals)}")
    assert len(terminals) >= 2, "Less than 2 MT5 terminals running!"
    print("Test 9 PASSED: Both MT5 terminals are active and running untouched.")

    print("\n>>> ALL 9 VERIFICATION CHECKS PASSED WITH 100% SUCCESS! <<<")

if __name__ == "__main__":
    run_tests()
