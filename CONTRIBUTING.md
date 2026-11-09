# Contributing to bot-quant-

Thank you for contributing to **bot-quant-**! This repository provides an open-source, zero-lookahead quantitative research, statistical validation, and ONNX Runtime inference framework for jump-diffusion and continuous-volatility processes.

---

## 1. Mandatory Mathematical & Engineering Invariants

All contributions must strictly respect the operational invariants defined in [`AGENT.md`](./AGENT.md):

1. **Zero Look-Ahead Bias (`shift=1` Rolling Window Invariant)**:
   - Historical rolling quantiles, ATR normalizers, and volatility compression ratios must be computed exclusively on closed bars $[t-W, \dots, t-1]$ excluding the trigger bar $t$.
2. **Net-of-Spread Expected Value Gate**:
   - Any execution signal on jump-diffusion processes must satisfy $\mathbb{E}[\Delta P_{\text{jump}} \mid \mathcal{F}_t] > c_{\text{spread}}(t) + \epsilon_{\text{slippage}}$.
3. **Deterministic Hold & Survival Bounds**:
   - All ONNX models (`src/models/*.onnx`) must include companion metadata JSON files specifying exact input feature order, normalization bounds, and out-of-sample validation metrics.

---

## 2. Running the Test Suite

```bash
pip install -e ".[dev]"
pytest tests/test_quantitative_mechanics.py -v
```

All unit tests in `tests/test_quantitative_mechanics.py` and `tests/verify_v331_hardened.py` must pass before opening a Pull Request.
