#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
PHASE 2 (C2) : ENTRAÎNEMENT DU FILTRE MÉTA-LABELING ONNX (ALIGNÉ EA V3)
=============================================================================
Correction de l'Audit Indépendant (25/10/2026) :
  - Délègue l'extraction des 7 features exactes de Deriv_VolSqueeze_Breakout_EA_v3.mq5
    et l'entraînement chronologique strict 60% Train / 20% Validation / 20% OOS
    (sans fuite du futur et avec zipmap=False) à `src/python/train_volatility_colab.py`.
  - Remplace l'ancien pipeline biaisé (qui utilisait atr14 * 100.0, wick_ratio au lieu de
    body_to_range, un split 75/25 sans jeu de validation et zipmap=True).
=============================================================================
"""

import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)

from train_volatility_colab import (  # noqa: E402
    FEATURE_NAMES,
    calc_levy_area,
    extract_ea_aligned_signals,
    fetch_mt5_h1_history,
    train_chronological_and_export_onnx,
)

EA_FEATURE_NAMES = FEATURE_NAMES
train_and_evaluate_strict_split = train_chronological_and_export_onnx

__all__ = [
    "FEATURE_NAMES",
    "EA_FEATURE_NAMES",
    "calc_levy_area",
    "extract_ea_aligned_signals",
    "fetch_mt5_h1_history",
    "train_chronological_and_export_onnx",
    "train_and_evaluate_strict_split",
]

if __name__ == "__main__":
    raise SystemExit(
        subprocess.call([sys.executable, os.path.join(PYTHON_DIR, "train_volatility_colab.py")] + sys.argv[1:])
    )
