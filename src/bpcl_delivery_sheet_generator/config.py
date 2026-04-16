from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal


OutputMode = Literal["combined", "split", "both"]


@dataclass(slots=True)
class InputConfig:
    """
    Configuration for reading and validating the source CSV file.
    """

    skip_rows: int = 3
    encoding: str = "utf-8"

    column_mapping: Dict[str, str] = field(
        default_factory=lambda: {
            "AreaDescription": "area",
            "eKYCOperatorName": "operator_name",
            "BookDate": "booking_date",
            "CashMemoDate": "cash_memo_date",
            "Address1": "address1",
            "Address2": "address2",
            "Address3": "address3",
            "MobileNumber": "mobile_number",
        }
    )

    required_source_columns: List[str] = field(
        default_factory=lambda: [
            "AreaDescription",
            "eKYCOperatorName",
            "BookDate",
            "CashMemoDate",
            "Address1",
            "Address2",
            "Address3",
            "MobileNumber",
        ]
    )


@dataclass(slots=True)
class TransformConfig:
    """
    Configuration for record grouping and sorting.
    """

    group_by: str = "operator_name"
    sort_by: List[str] = field(
        default_factory=lambda: [
            "area",
            "address1",
            "address2",
            "address3",
        ]
    )


@dataclass(slots=True)
class RenderConfig:
    """
    Configuration for PDF rendering and visible output columns.
    Notes:
    - Internal model keeps address1/address2/address3 separate.
    - Final PDF can optionally render them as a single combined address.
    """

    title: str = "BPCL Delivery Handover Sheet"
    footer_note: str = (
        "Blank fields are intentionally provided for OTP, Sign, and Online status."
    )

    visible_columns: List[str] = field(
        default_factory=lambda: [
            "slno",
            "area",
            "operator_name",
            "booking_date",
            "cash_memo_date",
            "full_address",
            "mobile_number",
            "otp",
            "sign",
            "online_status",
        ]
    )

    use_combined_address: bool = True
    address_separator: str = ", "


@dataclass(slots=True)
class OutputConfig:
    """
    Configuration for output file generation.
    """

    mode: OutputMode = "both"
    zip_split_outputs: bool = True


@dataclass(slots=True)
class LoggingConfig:
    """
    Configuration for package-wide logging.
    """

    logger_name: str = "bpcl_delivery_sheet_generator"
    log_level: str = "INFO"
    log_to_file: bool = False
    log_file_path: str | None = None


@dataclass(slots=True)
class PackageConfig:
    """
    Top-level package configuration.
    """

    input: InputConfig = field(default_factory=InputConfig)
    transform: TransformConfig = field(default_factory=TransformConfig)
    render: RenderConfig = field(default_factory=RenderConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)