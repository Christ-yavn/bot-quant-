# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 3.31.x  | :white_check_mark: |
| 3.30.x  | :white_check_mark: |
| < 3.30  | :x:                |

## Credential & Broker Account Hygiene

- Never commit live broker credentials, MT5 account passwords, or API tokens to this repository.
- All ONNX model artifacts (`src/models/*.onnx`) are inspected via metadata hashes in `src/models/onnx_model_metadata.json`.

## Reporting a Vulnerability

Please report security issues or execution state-machine vulnerabilities privately to **yaochristyvan8@gmail.com**.
