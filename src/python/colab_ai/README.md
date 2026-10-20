# GOOGLE COLAB AI TRAINING & SERIALIZATION SUITE

Contains the deep learning pipeline designed to train zero-leakage neural networks on Google Colab GPU/TPU and export optimized ONNX computation graphs.

## Contents:
* `train_boom_crash_l99_onnx.py`: The production training script integrating Adam optimization, cosine annealing learning rate schedule, intra-symbol Z-score scaling, and standalone binary ONNX serialization.
* `boom_crash_meta_brain.onnx`: The serialized multi-layer perceptron (14 -> 128 -> 64 -> 32 -> 2) ready for MT5.
* `onnx_model_metadata.json`: Feature normalization constants and decision thresholds.
* `real_live_spreads_mt5.json`: Real-market spread values for the entire Boom & Crash asset class.
* `boom_crash_10M_events.npz`: Compressed dataset containing 10,000,000 historical ticks and 18,268 spike events.
* `INSTRUCTIONS_GOOGLE_COLAB.md`: Step-by-step user guide for executing the training run in Colab.
