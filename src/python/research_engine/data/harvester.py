"""
src.data.harvester
==================
Top-level tick harvester interface compliant with PROJECT.md § 5.A.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from src.data import TickRecord, harvest_ticks

__all__ = ["harvest_ticks", "TickRecord"]
