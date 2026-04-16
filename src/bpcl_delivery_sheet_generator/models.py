from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass(slots=True)
class DeliveryRecord:
    """
    Canonical delivery record used internally by the package.

    Notes:
    - Address parts are intentionally kept separate in the data model.
    - The final PDF may combine them into a single display field later.
    """

    area: str
    operator_name: str
    booking_date: str
    cash_memo_date: str
    address1: str
    address2: str
    address3: str
    mobile_number: str


@dataclass(slots=True)
class DeliveryBatch:
    """
    A grouped set of delivery records, typically one sheet per operator.
    """

    batch_name: str
    records: List[DeliveryRecord] = field(default_factory=list)


@dataclass(slots=True)
class GenerationResult:
    """
    Summary of one package execution.
    """

    total_input_rows: int = 0
    total_output_rows: int = 0
    total_batches: int = 0
    combined_pdf_path: Path | None = None
    split_pdf_paths: List[Path] = field(default_factory=list)
    zip_path: Path | None = None
    warnings: List[str] = field(default_factory=list)