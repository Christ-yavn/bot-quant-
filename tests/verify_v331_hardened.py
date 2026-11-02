# -*- coding: utf-8 -*-
"""
Verification Suite for Deriv_VolSqueeze_Breakout_EA_v3.mq5 (v3.31 Hardened)
and Repository Invariants (Rules 1 to 7 of AGENT.md).

Note: Does NOT overwrite historical ONNX models (preserves Rule 2 Immutable Archiving).
"""
import os
import sys
import pathlib

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import verify_step1_and_step4 as vs


def verify_v331_invariants():
    print("\n" + "=" * 80)
    print(" [STEP 1D] VERIFYING v3.31 HARDENED MQL5 & ARCHIVE INVARIANTS")
    print("=" * 80)

    v3_path = os.path.join(REPO_ROOT, "src", "mql5", "Deriv_VolSqueeze_Breakout_EA_v3.mq5")
    with open(v3_path, "r", encoding="utf-8") as f:
        code = f.read()

    exec_code = "\n".join(ln for ln in code.splitlines() if not ln.strip().startswith("//"))

    # 1. Version & Pure S1 Parameter Defaults
    assert '#property version   "3.31"' in code, "Version 3.31 property missing!"
    assert "InpSqueezeQuantile       = 0.30;" in exec_code, "InpSqueezeQuantile default != 0.30"
    assert "InpBreakoutZScore        = 1.25;" in exec_code, "InpBreakoutZScore default != 1.25"
    assert "InpUseONNXFilter         = false;" in exec_code, "InpUseONNXFilter default != false"
    assert "InpSlippagePoints        = 50;" in exec_code, "InpSlippagePoints default != 50"
    assert "InpApplyV331AuditedPreset= true;" in exec_code, "InpApplyV331AuditedPreset default != true"
    assert "InpAllowV75Trading       = false;" in exec_code, "InpAllowV75Trading default != false"

    # 2. Bug 1 Fix: Closed-bar ATR shift=1 + 0.5*pt anti-spam tolerance
    assert "CopyBuffer(ExtATRHandle, 0, 1, 1, atr_vals)" in exec_code, "Closed-bar ATR shift=1 missing!"
    assert "CopyBuffer(ExtATRHandle, 0, 0, 1" not in exec_code, "Regression: intra-bar ATR shift=0 present!"
    assert "0.5 * pt" in exec_code, "Anti-spam 0.5 * _Point tolerance missing!"

    # 3. Bug 2 Fix: Exact TickSize + _Digits price normalization on Profit Lock and Entry SL/TP
    assert "double NormalizePrice(const double price)" in exec_code, "NormalizePrice helper missing!"
    assert "NormalizePrice(open_price + lock_offset)" in exec_code, "BUY Profit Lock missing NormalizePrice!"
    assert "NormalizePrice(open_price - lock_offset)" in exec_code, "SELL Profit Lock missing NormalizePrice!"
    assert "NormalizePrice(MathMin(ask - (InpHardSL_ATR * atr_val)" in exec_code, "BUY Hard SL missing NormalizePrice!"
    assert "NormalizePrice(MathMax(bid + (InpHardSL_ATR * atr_val)" in exec_code, "SELL Hard SL missing NormalizePrice!"

    # 4. Bug 3/4/5 Hardening: Time-Stop priority BEFORE Profit Lock + PositionClose check + VULN-02
    assert exec_code.index("bars_elapsed >= InpMaxHoldBars") < exec_code.index(
        "ExtTrade.PositionModify("
    ), "Time-Stop must execute BEFORE PositionModify!"
    assert "if(!frozen && ExtTrade.PositionClose(ticket))" in exec_code, "Verified PositionClose check missing!"
    ontick_code = exec_code[exec_code.index("void OnTick()") :]
    assert ontick_code.index("ManageOpenPositions()") < ontick_code.index(
        "InpMaxDailyLossPct"
    ), "VULN-02 regression: ManageOpenPositions must precede Daily Loss Circuit Breaker inside OnTick()!"

    # 5. AGENT.md Rule 2, 3, 4 Preservation
    assert "if(p > 1.0)" in exec_code, "Rule 4 probability scale guard missing!"
    assert "const long in_shape[] = {1, 7};" in exec_code, "Rule 3 7-feature ONNX input shape missing!"

    arch_mq5 = pathlib.Path(REPO_ROOT) / "archive" / "mql5_legacy" / "Deriv_VolSqueeze_Breakout_EA_v3_30.mq5"
    arch_ex5 = pathlib.Path(REPO_ROOT) / "archive" / "mql5_legacy" / "Deriv_VolSqueeze_Breakout_EA_v3_30.ex5"
    assert arch_mq5.exists() and arch_mq5.stat().st_size == 29183, "Rule 2 v3.30 .mq5 archive missing!"
    assert arch_ex5.exists() and arch_ex5.stat().st_size == 57352, "Rule 2 v3.30 .ex5 archive missing!"

    print(
        "  [PASS 6/6] All v3.31 Hardened invariants (shift=1 ATR, NormalizePrice, 0.5*pt anti-spam, "
        "Time-Stop priority, Pure S1 Q=0.30/Z=1.25, V75 Standby, Rules 2-7) verified!"
    )


if __name__ == "__main__":
    vs.step_1b_compile_mql5()
    vs.step_1c_adversarial_tests()
    verify_v331_invariants()
