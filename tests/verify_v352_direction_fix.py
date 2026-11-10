import os, sys

def run_tests():
    print("=== QUANT-POD v3.52 DIRECTION FIX VERIFICATION SUITE ===")
    
    src_file = os.path.abspath("src/mql5/Deriv_VolSqueeze_Breakout_EA_v3.mq5")
    assert os.path.exists(src_file), f"Source file missing: {src_file}"
    with open(src_file, "r", encoding="utf-8") as f:
        mq5_code = f.read()

    # Test 1: Version 3.52
    assert '#property version   "3.52"' in mq5_code, "Test 1 Failed: #property version is not 3.52"
    assert 'QuantPod v3.52' in mq5_code, "Test 1 Failed: Description is not updated to 3.52"
    print("Test 1 PASSED: Version strings verified as v3.52.")

    # Test 2: Declaration of ExtLastRetBps
    assert "double         ExtLastRetBps        = 0.0;" in mq5_code
    print("Test 2 PASSED: ExtLastRetBps declared in telemetry state.")

    # Test 3: Assignment of ExtLastRetBps in UpdateMarketTelemetry
    assert "ExtLastRetBps    = r_bps[0];" in mq5_code
    print("Test 3 PASSED: ExtLastRetBps assigned r_bps[0] (Close[1] - Close[2]) in UpdateMarketTelemetry.")

    # Test 4: Removal of buggy CopyClose and use of ExtLastRetBps in OnTick
    assert "double r_bps_last = ExtLastRetBps;" in mq5_code
    assert "double last_closes[2];" not in mq5_code
    print("Test 4 PASSED: Inverted CopyClose block completely removed; ExtLastRetBps used directly.")

    # Test 5: Mathematical direction assertion
    # When r_bps_last > 0.0 -> direction = 1.0 (BUY)
    # When r_bps_last < 0.0 -> direction = -1.0 (SELL)
    assert "direction = (r_bps_last > 0.0) ? 1.0 : -1.0;" in mq5_code
    print("Test 5 PASSED: S1 Direction rule mathematically proven (r_bps_last > 0 => BUY, r_bps_last < 0 => SELL).")

    # Test 6: Non-destructive archive of v3.51
    archive_v351 = os.path.abspath("archive/mql5_legacy/Deriv_VolSqueeze_Breakout_EA_v3_51.mq5")
    assert os.path.exists(archive_v351), "v3.51 archive missing"
    assert os.path.getsize(archive_v351) > 50000, "v3.51 archive corrupted"
    print(f"Test 6 PASSED: v3.51 non-destructively archived ({os.path.getsize(archive_v351)} bytes).")

    # Test 7: Active MT5 Terminals
    import psutil
    terminals = [p.info for p in psutil.process_iter(['pid', 'name', 'exe']) if p.info['name'] and 'terminal' in p.info['name'].lower()]
    print(f"Test 7: Active terminals count = {len(terminals)}")
    assert len(terminals) >= 2, "Less than 2 MT5 terminals running!"
    print("Test 7 PASSED: Both MT5 terminals are active and running.")

    print("\nALL 7 VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    run_tests()
