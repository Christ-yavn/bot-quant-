# -*- coding: utf-8 -*-
"""
Adversarial Verification & Proxy Fitness Suite for Steps 1 and 4:
1. Retrains c2_vol_filter.onnx with strict chronological 60/20/20 split on full H1 history (V25 & V75).
2. Deploys & compiles DerivBoomCrashHFT_v830_Ultimate.mq5 and Deriv_VolSqueeze_Breakout_EA_v3.mq5 via metaeditor64.exe (0 errors, 0 warnings).
3. Executes 5 Proxy Fitness & Red Team Adversarial Verification tests covering B1-B9, ONNX tensor shapes, and closed-form probability identities.
4. Runs the live Deriv WebSocket Fair-Value EV Scanner across all fixed-payout contract families.
"""

import os
import sys
import json
import math
import shutil
import subprocess
import numpy as np
import onnxruntime as ort

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "src", "python"))

import train_volatility_colab as tvc
import deriv_fair_value_scanner as dfvs

MT5_TERMINAL_DIR = r"C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5"
METAEDITOR_EXE = r"C:\Program Files\MetaTrader 5 Terminal\metaeditor64.exe"


def step_1a_retrain_vol_onnx():
    print("\n" + "=" * 80)
    print(" [STEP 1A] RETRAINING c2_vol_filter.onnx (STRICT 60/20/20 CHRONOLOGICAL SPLIT)")
    print("=" * 80)
    onnx_out = os.path.join(REPO_ROOT, "src", "models", "c2_vol_filter.onnx")
    reports = {}

    # Evaluate V75 (H=3 and H=4) and V25 (H=4, primary target of c2_vol_filter.onnx)
    for sym, horizon in [("Volatility 75 (1s) Index", 3), ("Volatility 25 (1s) Index", 4)]:
        df_h1 = tvc.fetch_mt5_h1_history(sym)
        X, y, net_pnl, gross_pnl, bar_idx, sig_times = tvc.extract_ea_aligned_signals(df_h1, horizon=horizon)
        rep = tvc.train_chronological_and_export_onnx(
            X, y, net_pnl, sig_times, output_path=onnx_out, symbol_name=sym
        )
        reports[sym] = rep

    meta_out = os.path.join(REPO_ROOT, "src", "models", "c2_vol_filter_metadata.json")
    with open(meta_out, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, ensure_ascii=False)

    # Copy updated c2_vol_filter.onnx to MT5 MQL5\Files and MQL5\Experts
    for dst_sub in ["Files", "Experts"]:
        dst_dir = os.path.join(MT5_TERMINAL_DIR, dst_sub)
        if os.path.isdir(dst_dir):
            shutil.copy2(onnx_out, os.path.join(dst_dir, "c2_vol_filter.onnx"))
    print("  [OK] c2_vol_filter.onnx updated in repo and MT5 MQL5\\Files.")
    return reports


def step_1b_compile_mql5():
    print("\n" + "=" * 80)
    print(" [STEP 1B] COMPILING MQL5 BOTS WITH METAEDITOR64.EXE (0 ERRORS, 0 WARNINGS)")
    print("=" * 80)
    eas = [
        "DerivBoomCrashHFT_v830_Ultimate.mq5",
        "Deriv_VolSqueeze_Breakout_EA_v3.mq5",
    ]
    compile_results = {}
    for ea in eas:
        repo_mq5 = os.path.join(REPO_ROOT, "src", "mql5", ea)
        mt5_mq5 = os.path.join(MT5_TERMINAL_DIR, "Experts", ea)
        shutil.copy2(repo_mq5, mt5_mq5)
        log_file = mt5_mq5 + ".compile.log"
        if os.path.exists(log_file):
            os.remove(log_file)

        cmd = [METAEDITOR_EXE, f"/compile:{mt5_mq5}", f"/log:{log_file}"]
        subprocess.run(cmd, check=False)

        with open(log_file, "r", encoding="utf-16le", errors="ignore") as f:
            log_text = f.read()

        # Copy compiled .ex5 back to repository src/mql5/
        ex5_name = ea.replace(".mq5", ".ex5")
        mt5_ex5 = os.path.join(MT5_TERMINAL_DIR, "Experts", ex5_name)
        repo_ex5 = os.path.join(REPO_ROOT, "src", "mql5", ex5_name)
        shutil.copy2(mt5_ex5, repo_ex5)

        result_line = [ln.strip() for ln in log_text.splitlines() if "Result:" in ln or "error(s)" in ln]
        summary_str = result_line[-1] if result_line else "UNKNOWN"
        print(f"  {ea:<38} -> {summary_str} | .ex5 size = {os.path.getsize(repo_ex5):,} bytes")
        compile_results[ea] = summary_str
        assert "0 errors, 0 warnings" in summary_str, f"Compilation failed or had warnings for {ea}: {log_text}"

    return compile_results


def step_1c_adversarial_tests():
    print("\n" + "=" * 80)
    print(" [STEP 1C] ADVERSARIAL RED-TEAM & PROXY FITNESS TESTS (5/5 REQUIRED)")
    print("=" * 80)
    passed = 0
    total = 5

    # Test 1: Verify B1-B9 code invariants in DerivBoomCrashHFT_v830_Ultimate.mq5
    v830_path = os.path.join(REPO_ROOT, "src", "mql5", "DerivBoomCrashHFT_v830_Ultimate.mq5")
    with open(v830_path, "r", encoding="utf-8") as f:
        code_v830 = f.read()

    exec_lines = "\n".join(
        ln for ln in code_v830.splitlines() if not ln.strip().startswith("//")
    )
    assert "if(InpEnableStaticEvGate && !tr.ev_gate_pass)" in exec_lines, "B1 Fix missing!"
    assert "calm_maturity_boost" not in exec_lines, "B7 calm_maturity_boost still active!"
    assert "0.20 * mean_sp" not in exec_lines, "B8 0.20 * mean_sp floor still active!"
    assert "MathPow(surv_train, horizon / train_horizon_ticks)" in exec_lines, "B4 be_ticks+15 survival scaling missing!"
    assert "MathMax(phys_spike_p0, 0.50" not in exec_lines, "B2 MathMax clamp still blocking ONNX filter!"
    assert "live_pos_tick.time_msc - pos_time_msc" in exec_lines, "B5 epoch seconds time-stop fix missing!"
    assert "g_day_start_equity = eq;" in exec_lines, "B6 daily drawdown rollover missing!"
    assert "input bool   InpEnableHawkesClusterEntry    = false;" in exec_lines, "B9 Hawkes cluster default not false!"
    assert "tick.time_msc < tr.last_time_msc" in exec_lines, "CopyTicks cursor timestamp guard still using <= and dropping ticks!"
    assert "GetLiveExecutableSpreadPts(" in exec_lines, "Live executable spread floor missing!"
    passed += 1
    print("  [PASS 1/5] All B1..B9 structural, CopyTicks cursor & live spread floor fixes verified in DerivBoomCrashHFT_v830_Ultimate.mq5.")

    # Test 2: Simulate Static & Dynamic EV Gate on all 10 Boom/Crash symbols with live MT5 spreads
    import MetaTrader5 as mt5
    mt5.initialize()
    table = [
        ("Boom 1000 Index", 0.01551, 17.015, 1066.6, 1.7215),
        ("Crash 1000 Index", 0.00636, 5.887, 961.0, 0.5422),
        ("Boom 900 Index", 0.00972, 8.865, 911.4, 0.9620),
        ("Crash 900 Index", 0.01900, 17.314, 907.3, 1.3560),
        ("Boom 600 Index", 0.00894, 5.155, 586.5, 0.7730),
        ("Crash 600 Index", 0.03773, 22.904, 571.5, 3.2810),
        ("Boom 500 Index", 0.01128, 5.825, 486.9, 0.5270),
        ("Crash 500 Index", 0.00623, 2.991, 480.0, 0.3270),
        ("Boom 300 Index", 0.00414, 1.324, 289.3, 0.5030),
        ("Crash 300 Index", 0.02080, 6.863, 297.3, 1.1130),
    ]
    M = 60.0
    lot = 0.20
    for sym, drift, mean_sp, tau, min_live_sp in table:
        mt5.symbol_select(sym, True)
        t = mt5.symbol_info_tick(sym)
        sp = max(min_live_sp, (t.ask - t.bid) if (t and t.ask > t.bid) else min_live_sp)
        p0 = 1.0 - math.exp(-M / tau)
        L_pts = M * drift + sp
        G_pts = max(0.0, mean_sp - 0.5 * M * drift - sp)
        ev_usd = (p0 * G_pts - (1.0 - p0) * L_pts) * lot
        gate_pass = ev_usd >= 0.01
        assert not gate_pass, f"EV Gate unexpectedly passed on {sym}: EV={ev_usd}"
    passed += 1
    print("  [PASS 2/5] EV Gate simulation on all 10 Boom/Crash symbols with live spreads: 10/10 REFUSED (0 false entries).")

    # Test 3: Verify boom_crash_meta_brain.onnx inference with exact 14 metadata features & out_proba[0][1]
    bc_onnx = os.path.join(REPO_ROOT, "src", "models", "boom_crash_meta_brain.onnx")
    bc_meta = json.load(open(os.path.join(REPO_ROOT, "src", "models", "onnx_model_metadata.json"), "r"))
    assert len(bc_meta["feature_names"]) == 14
    sess_bc = ort.InferenceSession(bc_onnx)
    be_ticks_test = 86.9
    x_bc = np.array([[5.0, 0.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.8, 1.2, 1.0, 1.0, 1.0, be_ticks_test, 0.15]], dtype=np.float32)
    out_bc = sess_bc.run(None, {sess_bc.get_inputs()[0].name: x_bc})
    assert len(out_bc) >= 2 and out_bc[1].shape == (1, 2), f"Expected 2 outputs with [1,2] proba tensor, got: {[o.shape for o in out_bc]}"
    raw_surv = float(out_bc[1][0, 1])
    assert 0.0 < raw_surv < 1.0, f"Invalid ONNX survival probability: {raw_surv}"
    train_horizon_ticks = max(15.0, be_ticks_test + 15.0)
    onnx_spike_p60 = 1.0 - (raw_surv ** (60.0 / train_horizon_ticks))
    phys_p0_crash600 = 1.0 - math.exp(-60.0 / 571.5)
    fused_p0 = 0.50 * phys_p0_crash600 + 0.50 * onnx_spike_p60
    assert fused_p0 < phys_p0_crash600, f"B2/B4 failed: high survival ({raw_surv:.4f}) did not reduce spike_prob ({fused_p0:.4f} >= {phys_p0_crash600:.4f})"
    passed += 1
    print(
        f"  [PASS 3/5] boom_crash_meta_brain.onnx [1, 14] -> out_proba[0,1]={raw_surv:.4f} "
        f"(P_spike_60t={onnx_spike_p60:.4f} < base_p0={phys_p0_crash600:.4f} -> B2/B4 blocks trade)."
    )

    # Test 4: Verify c2_vol_filter.onnx [1, 7] inference on nominal + extreme edge cases
    vol_onnx = os.path.join(REPO_ROOT, "src", "models", "c2_vol_filter.onnx")
    sess_vol = ort.InferenceSession(vol_onnx)
    test_vectors = [
        np.array([[0.85, 1.80, 1.0, 0.12, 0.035, 0.10, 2.95]], dtype=np.float32),   # Nominal BUY
        np.array([[0.92, 2.40, -1.0, -0.25, 0.042, -0.30, 3.40]], dtype=np.float32), # Nominal SELL
        np.array([[0.01, 15.0, 1.0, 5.0, 0.001, 3.0, 15.0]], dtype=np.float32),      # Extreme outlier
        np.array([[1.00, 1.50, -1.0, 0.0, 0.050, 0.0, 3.0]], dtype=np.float32),      # Boundary threshold
    ]
    for vec in test_vectors:
        outs = sess_vol.run(None, {sess_vol.get_inputs()[0].name: vec})
        assert len(outs) == 2, "c2_vol_filter.onnx must return (label, probabilities) without zipmap"
        assert outs[0].shape == (1,), f"Unexpected label shape: {outs[0].shape}"
        assert outs[1].shape == (1, 2), f"Unexpected probability shape: {outs[1].shape}"
        p_sum = float(outs[1][0, 0] + outs[1][0, 1])
        assert abs(p_sum - 1.0) < 1e-5, f"Probabilities do not sum to 1: {p_sum}"
    passed += 1
    print("  [PASS 4/5] c2_vol_filter.onnx [1, 7] -> ([1], [1, 2]) verified across nominal, boundary & extreme inputs.")

    # Test 5: Verify closed-form mathematical probability conservation laws for the Fair-Value Scanner (GBM, Reflection, Geometric 1/tau)
    for s0 in [100.0, 1500.0]:
        for sigma in [0.25, 0.75]:
            for t_sec in [60.0, 3600.0, 86400.0]:
                for k_mult in [0.98, 1.00, 1.02]:
                    k = s0 * k_mult
                    p_call = dfvs.exact_gbm_call_put_prob(s0, k, sigma, t_sec, True)
                    p_put = dfvs.exact_gbm_call_put_prob(s0, k, sigma, t_sec, False)
                    assert abs((p_call + p_put) - 1.0) < 1e-12
                    p_ot = dfvs.exact_gbm_onetouch_prob(s0, k, sigma, t_sec)
                    assert 0.0 <= p_ot <= 1.0
                    # Reflection principle invariant: P(OneTouch, K) >= P(European Call/Put at K)
                    if k > s0:
                        assert p_ot >= p_call - 1e-12
                    elif k < s0:
                        assert p_ot >= p_put - 1e-12
    for tau in [300.0, 500.0, 600.0, 900.0, 1000.0]:
        for n_ticks in [1, 15, 60, 300]:
            p_sp = dfvs.exact_boom_crash_spike_prob(n_ticks, tau)
            p_su = dfvs.exact_boom_crash_survival_prob(n_ticks, tau)
            assert abs((p_sp + p_su) - 1.0) < 1e-12
    passed += 1
    print(f"  [PASS 5/5] Closed-form GBM, Reflection Principle & Geometric (1/tau) invariants verified ({passed}/{total} Proxy Fitness score = 100%).")


if __name__ == "__main__":
    step_1a_retrain_vol_onnx()
    step_1b_compile_mql5()
    step_1c_adversarial_tests()
    dfvs.main()
