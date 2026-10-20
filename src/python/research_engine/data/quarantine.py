"""
src.data.quarantine
===================
Hermetic Out-of-Sample Test Partition Quarantine & Cryptographic Vault (F5).

Features:
- SHA-256 cryptographic sealing of out-of-sample test datasets in manifest.json
- Tamper detection and hash integrity verification
- Token-guarded access control: requires token "OOS_EVALUATION_AUTHORIZED"
- Immutable audit trail logging into logs/quarantine_audit.log
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import polars as pl

logger = logging.getLogger("src.data.quarantine")

# Official authorization token for accessing sealed test datasets
OOS_AUTHORIZATION_TOKEN = "OOS_EVALUATION_AUTHORIZED"
DEFAULT_AUDIT_LOG_PATH = Path("logs/quarantine_audit.log")


class QuarantineViolationError(Exception):
    """Raised when an unauthorized or corrupted attempt to access quarantined test data occurs."""
    pass


def compute_sha256(path: Union[str, Path]) -> str:
    """
    Computes the SHA-256 hexadecimal hash digest of a file.

    Parameters
    ----------
    path : str or Path
        Target file path.

    Returns
    -------
    str
        Hexadecimal SHA-256 hash.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found for SHA-256 computation: {path}")

    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def log_quarantine_event(
    file_path: Union[str, Path],
    status: str,
    action: str = "READ_TEST_QUARANTINE",
    caller: str = "",
    reason: str = "",
    log_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Appends an immutable audit log entry into the quarantine access log.

    Parameters
    ----------
    file_path : str or Path
        Target partition file path.
    status : str
        "GRANTED" or "DENIED".
    action : str, default "READ_TEST_QUARANTINE"
        Action being attempted.
    caller : str
        Context or name of the calling module/function.
    reason : str
        Justification or error reason.
    log_path : Path or str, optional
        Target log file. Defaults to logs/quarantine_audit.log.

    Returns
    -------
    dict
        The recorded audit entry.
    """
    p = Path(file_path)
    audit_file = Path(log_path) if log_path is not None else DEFAULT_AUDIT_LOG_PATH
    audit_file.parent.mkdir(parents=True, exist_ok=True)

    sha = None
    if p.exists() and p.is_file():
        try:
            sha = compute_sha256(p)
        except Exception:
            sha = "UNREADABLE"

    entry: Dict[str, Any] = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "action": action,
        "file": str(p.name),
        "sha256": sha,
        "status": status,
        "caller": caller or "unknown",
        "reason": reason,
    }

    with open(audit_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def create_quarantine_manifest(
    test_path: Union[str, Path],
    manifest_path: Union[str, Path],
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Creates a single-file cryptographic manifest sealing a test partition.
    Conforms to PROJECT.md § 5.A and contract_harness.py specifications.

    Parameters
    ----------
    test_path : Path or str
        Path to the test Parquet dataset to seal.
    manifest_path : Path or str
        Destination path for manifest.json.
    metadata : dict, optional
        Additional metadata (symbol, tick count, DGP model, etc.).

    Returns
    -------
    dict
        Manifest dictionary.
    """
    tp = Path(test_path)
    mp = Path(manifest_path)
    if not tp.is_file():
        raise FileNotFoundError(f"Cannot seal non-existent test file: {tp}")

    sha = compute_sha256(tp)
    manifest = {
        "test_file": str(tp.name),
        "sha256": sha,
        "sealed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "file_size_bytes": os.path.getsize(tp),
        "metadata": metadata or {},
    }

    mp.parent.mkdir(parents=True, exist_ok=True)
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Sealed quarantine manifest for {tp.name} -> {mp} (SHA-256: {sha[:12]}...)")
    return manifest


def create_global_quarantine_manifest(
    test_files: List[Union[str, Path]],
    manifest_path: Union[str, Path],
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Creates a comprehensive global cryptographic manifest sealing multiple test partitions.

    Parameters
    ----------
    test_files : list of Path or str
        List of test Parquet datasets to seal.
    manifest_path : Path or str
        Destination path for global manifest.json (e.g. data/partitioned/manifest.json).
    metadata : dict, optional
        Project-wide metadata.

    Returns
    -------
    dict
        Global manifest dictionary.
    """
    mp = Path(manifest_path)
    files_catalog: Dict[str, Dict[str, Any]] = {}

    for tf in test_files:
        p = Path(tf)
        if not p.is_file():
            raise FileNotFoundError(f"Cannot seal non-existent partition file: {p}")
        sha = compute_sha256(p)
        files_catalog[p.name] = {
            "sha256": sha,
            "file_size_bytes": os.path.getsize(p),
            "relative_path": str(p.name),
        }

    manifest = {
        "manifest_version": "1.0",
        "sealed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_test_partitions": len(files_catalog),
        "files": files_catalog,
        "metadata": metadata or {},
    }

    mp.parent.mkdir(parents=True, exist_ok=True)
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Created global quarantine manifest at {mp} sealing {len(files_catalog)} partitions.")
    return manifest


def verify_quarantine_manifest(
    test_path: Union[str, Path],
    manifest_path: Union[str, Path],
) -> bool:
    """
    Verifies that a test partition matches its cryptographic SHA-256 seal.
    Supports both single-file manifests and global multi-file manifests.

    Parameters
    ----------
    test_path : Path or str
        Path to the test Parquet dataset to verify.
    manifest_path : Path or str
        Path to the manifest.json file.

    Returns
    -------
    bool
        True if the file exists and matches the recorded SHA-256 digest; False otherwise.
    """
    tp = Path(test_path)
    mp = Path(manifest_path)

    if not mp.is_file() or not tp.is_file():
        return False

    try:
        with open(mp, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read manifest at {mp}: {e}")
        return False

    if not isinstance(manifest, dict):
        logger.error(f"Invalid manifest structure at {mp}: expected dict, got {type(manifest).__name__}")
        return False

    try:
        current_sha = compute_sha256(tp)

        # 1. Single-file manifest format: {"test_file": ..., "sha256": ...}
        if "sha256" in manifest and ("test_file" not in manifest or manifest.get("test_file") == tp.name):
            expected_sha = manifest.get("sha256")
            if isinstance(expected_sha, str):
                return current_sha == expected_sha

        # 2. Multi-file global manifest format: {"files": {filename: {"sha256": ...}}}
        files_catalog = manifest.get("files")
        if isinstance(files_catalog, dict) and tp.name in files_catalog:
            file_entry = files_catalog.get(tp.name)
            if isinstance(file_entry, dict):
                expected_sha = file_entry.get("sha256")
                if isinstance(expected_sha, str):
                    return current_sha == expected_sha

        # 3. Alternative partitions key
        partitions_catalog = manifest.get("partitions")
        if isinstance(partitions_catalog, dict) and tp.name in partitions_catalog:
            part_entry = partitions_catalog.get(tp.name)
            if isinstance(part_entry, dict):
                expected_sha = part_entry.get("sha256")
                if isinstance(expected_sha, str):
                    return current_sha == expected_sha

        return False
    except Exception as e:
        logger.error(f"Error during manifest verification at {mp}: {e}")
        return False


def load_test_partition(
    test_path: Union[str, Path],
    manifest_path: Union[str, Path],
    token: str,
    reason: str = "",
    caller: str = "",
    audit_log_path: Optional[Union[str, Path]] = None,
) -> pl.DataFrame:
    """
    Guarded loader for out-of-sample test datasets.
    Strictly enforces:
    1. Authorization token check: token must equal "OOS_EVALUATION_AUTHORIZED"
    2. Cryptographic integrity check: SHA-256 must match manifest.json
    3. Automatic audit logging in logs/quarantine_audit.log

    Parameters
    ----------
    test_path : Path or str
        Path to the quarantined test dataset.
    manifest_path : Path or str
        Path to manifest.json sealing the dataset.
    token : str
        Authorization token. Must be "OOS_EVALUATION_AUTHORIZED".
    reason : str, optional
        Research justification for accessing the sealed out-of-sample data.
    caller : str, optional
        Name of the calling function/module.
    audit_log_path : Path or str, optional
        Path to quarantine access log file.

    Returns
    -------
    pl.DataFrame
        Loaded Polars DataFrame.

    Raises
    -------
    QuarantineViolationError
        If authorization token is invalid or if cryptographic tamper is detected.
    """
    tp = Path(test_path)
    mp = Path(manifest_path)

    # 1. Authorization guard
    if token != OOS_AUTHORIZATION_TOKEN:
        log_quarantine_event(
            file_path=tp,
            status="DENIED",
            caller=caller or "unknown",
            reason=f"INVALID_TOKEN: Provided token '{token}' does not match required authorization.",
            log_path=audit_log_path,
        )
        raise QuarantineViolationError(
            f"ACCESS DENIED: Unauthorized attempt to read sealed test partition '{tp.name}'. "
            f"Expected token '{OOS_AUTHORIZATION_TOKEN}', received '{token}'."
        )

    # 2. Cryptographic integrity verification
    if not tp.is_file():
        log_quarantine_event(
            file_path=tp,
            status="DENIED",
            caller=caller or "unknown",
            reason="MISSING_FILE: Test partition file does not exist.",
            log_path=audit_log_path,
        )
        raise QuarantineViolationError(f"Quarantine Breach: Test file does not exist: {tp}")

    if not mp.is_file():
        log_quarantine_event(
            file_path=tp,
            status="DENIED",
            caller=caller or "unknown",
            reason="MISSING_MANIFEST: Cryptographic manifest.json is missing.",
            log_path=audit_log_path,
        )
        raise QuarantineViolationError(f"Quarantine Breach: Manifest file not found: {mp}")

    try:
        manifest_ok = verify_quarantine_manifest(tp, mp)
    except Exception as e:
        logger.error(f"Unexpected exception verifying manifest at {mp}: {e}")
        manifest_ok = False

    if not manifest_ok:
        log_quarantine_event(
            file_path=tp,
            status="DENIED",
            caller=caller or "unknown",
            reason="TAMPER_DETECTED: SHA-256 digest does not match sealed manifest.",
            log_path=audit_log_path,
        )
        raise QuarantineViolationError(
            f"CRYPTOGRAPHIC TAMPER DETECTED: SHA-256 digest of '{tp.name}' does not match "
            f"the sealed hash in '{mp.name}'. Access strictly aborted."
        )

    # 3. Log granted access
    log_quarantine_event(
        file_path=tp,
        status="GRANTED",
        caller=caller or "authorized_oos_runner",
        reason=reason or "Authorized out-of-sample quantitative evaluation",
        log_path=audit_log_path,
    )

    return pl.read_parquet(tp)
