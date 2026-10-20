"""
src.data.partitioner
====================
Chronological Dataset Partitioner & Temporal Leak Isolation Engine (F4).

Features:
- Strict chronological 60% Train / 20% Val / 20% Test partitioning
- Mathematical assertion of ratio sum == 1.0
- Temporal barrier verification: max(Train.ts) < min(Val.ts) <= max(Val.ts) < min(Test.ts)
- Parquet serialization with zstd compression
- Batch partitioning for all harvested market tick datasets
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import polars as pl

from src.data.quarantine import (
    compute_sha256,
    create_global_quarantine_manifest,
    create_quarantine_manifest,
)

logger = logging.getLogger("src.data.partitioner")

DEFAULT_RATIOS: Tuple[float, float, float] = (0.60, 0.20, 0.20)
DEFAULT_PARTITION_DIR = Path("data/partitioned")


def split_chronological(
    df: pl.DataFrame,
    ratios: Tuple[float, float, float] = DEFAULT_RATIOS,
) -> Tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """
    Splits tick data chronologically into Train (60%), Val (20%), and Test (20%).
    Strictly prevents lookahead bias and temporal leakage.

    Invariants Enforced:
    1. sum(ratios) == 1.0 (asserts exact or floating close sum).
    2. Data is chronologically sorted by timestamp_ns.
    3. Strict temporal barrier: max(Train) < min(Val) <= max(Val) < min(Test).

    Parameters
    ----------
    df : pl.DataFrame
        Input tick DataFrame conforming to TICK_SCHEMA.
    ratios : tuple of 3 floats, default (0.60, 0.20, 0.20)
        Fractions for Train, Validation, and Test partitions.

    Returns
    -------
    Tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]
        (train_df, val_df, test_df)
    """
    assert len(ratios) == 3, f"Ratios must be a 3-element tuple, got {len(ratios)}"
    assert all(r > 0 for r in ratios), f"All partition ratios must be strictly positive: {ratios}"
    assert math.isclose(sum(ratios), 1.0, abs_tol=1e-7), "Ratios must sum to 1.0"

    n = len(df)
    if n == 0:
        return df.clone(), df.clone(), df.clone()

    if n < 5:
        raise ValueError(
            f"Dataset length {n} is too small for 3-way chronological partitioning "
            f"(minimum 5 records required)."
        )

    # Ensure chronological order
    sorted_df = df.sort("timestamp_ns")

    n_train = int(n * ratios[0])
    n_val = int(n * ratios[1])
    n_test = n - (n_train + n_val)

    if n_train == 0 or n_val == 0 or n_test == 0:
        raise ValueError(
            f"Dataset length {n} with ratios {ratios} yields empty partitions: "
            f"Train={n_train}, Val={n_val}, Test={n_test}."
        )

    train = sorted_df.slice(0, n_train)
    val = sorted_df.slice(n_train, n_val)
    test = sorted_df.slice(n_train + n_val)

    # Enforce temporal barrier invariants if partitions are non-empty
    if len(train) > 0 and len(val) > 0:
        train_max = train["timestamp_ns"].max()
        val_min = val["timestamp_ns"].min()
        assert train_max < val_min, (
            f"Chronological Barrier Violation (Train/Val leak): "
            f"train_max={train_max} >= val_min={val_min}"
        )

    if len(val) > 0 and len(test) > 0:
        val_max = val["timestamp_ns"].max()
        test_min = test["timestamp_ns"].min()
        assert val_max < test_min, (
            f"Chronological Barrier Violation (Val/Test leak): "
            f"val_max={val_max} >= test_min={test_min}"
        )

    if len(train) > 0 and len(test) > 0:
        train_max = train["timestamp_ns"].max()
        test_min = test["timestamp_ns"].min()
        assert train_max < test_min, (
            f"Chronological Barrier Violation (Train/Test leak): "
            f"train_max={train_max} >= test_min={test_min}"
        )

    return train, val, test


def partition_dataset(
    input_parquet: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    ratios: Tuple[float, float, float] = DEFAULT_RATIOS,
) -> Tuple[Path, Path, Path, str]:
    """
    Loads raw market ticks from Parquet, splits chronologically into Train/Val/Test,
    writes compressed Parquet files, and returns file paths along with the SHA-256 seal.

    Parameters
    ----------
    input_parquet : Path or str
        Path to the source Parquet file (e.g. data/raw/boom_1000_index.parquet).
    output_dir : Path or str, optional
        Destination directory. Defaults to data/partitioned.
    ratios : tuple of 3 floats, default (0.60, 0.20, 0.20)
        Split ratios.

    Returns
    -------
    Tuple[Path, Path, Path, str]
        (train_path, val_path, test_path, test_sha256)
    """
    in_path = Path(input_parquet)
    if not in_path.is_file():
        raise FileNotFoundError(f"Input dataset does not exist: {in_path}")

    out_dir = Path(output_dir) if output_dir is not None else DEFAULT_PARTITION_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pl.read_parquet(in_path)
    train, val, test = split_chronological(df, ratios=ratios)

    stem = in_path.stem
    train_path = out_dir / f"{stem}_train.parquet"
    val_path = out_dir / f"{stem}_val.parquet"
    test_path = out_dir / f"{stem}_test.parquet"

    train.write_parquet(train_path, compression="zstd")
    val.write_parquet(val_path, compression="zstd")
    test.write_parquet(test_path, compression="zstd")

    test_sha256 = compute_sha256(test_path)

    logger.info(
        f"Partitioned {in_path.name} -> Train: {len(train):,}, Val: {len(val):,}, "
        f"Test: {len(test):,} | SHA-256: {test_sha256[:12]}..."
    )

    return train_path, val_path, test_path, test_sha256


def partition_all_raw_datasets(
    raw_dir: Union[str, Path] = Path("data/raw"),
    output_dir: Union[str, Path] = Path("data/partitioned"),
    ratios: Tuple[float, float, float] = DEFAULT_RATIOS,
) -> Dict[str, Any]:
    """
    Batch partitions all Parquet files found in raw_dir into output_dir.
    Creates individual partitions and generates a global quarantine manifest.json.

    Parameters
    ----------
    raw_dir : Path or str, default data/raw
        Directory containing raw market tick datasets.
    output_dir : Path or str, default data/partitioned
        Destination directory for partitioned files and manifest.json.
    ratios : tuple of 3 floats, default (0.60, 0.20, 0.20)
        Partitioning fractions.

    Returns
    -------
    dict
        Summary of partitioned datasets and manifest information.
    """
    r_dir = Path(raw_dir)
    o_dir = Path(output_dir)
    o_dir.mkdir(parents=True, exist_ok=True)

    raw_files = sorted(r_dir.glob("*.parquet"))
    if not raw_files:
        raise FileNotFoundError(f"No .parquet datasets found in {r_dir}")

    partitions_summary: Dict[str, Dict[str, Any]] = {}
    test_paths: List[Path] = []

    for rf in raw_files:
        train_p, val_p, test_p, test_sha = partition_dataset(rf, output_dir=o_dir, ratios=ratios)
        test_paths.append(test_p)
        partitions_summary[rf.stem] = {
            "raw_file": str(rf.name),
            "train_file": str(train_p.name),
            "val_file": str(val_p.name),
            "test_file": str(test_p.name),
            "test_sha256": test_sha,
        }

    manifest_path = o_dir / "manifest.json"
    manifest = create_global_quarantine_manifest(
        test_files=test_paths,
        manifest_path=manifest_path,
        metadata={"ratios": list(ratios), "source_dir": str(r_dir.as_posix())},
    )

    summary = {
        "datasets_partitioned": len(partitions_summary),
        "output_directory": str(o_dir.as_posix()),
        "manifest_path": str(manifest_path.as_posix()),
        "partitions": partitions_summary,
    }

    logger.info(
        f"Completed batch partitioning of {len(raw_files)} datasets. "
        f"Manifest created at {manifest_path}."
    )
    return summary
