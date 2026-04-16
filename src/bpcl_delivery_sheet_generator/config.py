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
    Configuration for PDF rendering.

    Notes:
    - Internal model keeps address1/address2/address3 separate.
    - Final PDF can optionally render them as a single combined address.
    """

    title: str = "Venketeshwar Gas Service - Delivery Handover Sheet"
    footer_note: str = "Collect OTP, take signature, and mark online delivery status."

    use_combined_address: bool = True
    address_separator: str = ", "

    show_footer_note: bool = True
    show_online_checkbox: bool = True
    online_checkbox_text: str = "[ ]"

    printed_datetime_format: str = "%d-%m-%Y %I:%M %p"

    # page layout
    left_margin_mm: float = 4
    right_margin_mm: float = 4
    top_margin_mm: float = 12
    bottom_margin_mm: float = 10

    # typography
    title_font_size: float = 13.5
    meta_font_size: float = 8.5
    cell_font_size: float = 9.2
    header_font_size: float = 9.0

    # spacing
    title_leading: float = 16
    meta_leading: float = 10
    cell_leading: float = 11
    header_leading: float = 10.5

    story_top_spacer_mm: float = 4
    section_spacer_mm: float = 2.5

    row_top_padding: float = 8
    row_bottom_padding: float = 8
    cell_left_padding: float = 3
    cell_right_padding: float = 3

    # header/footer drawing
    page_header_y_mm: float = 8
    page_divider_y_mm: float = 10
    footer_y_mm: float = 6
    page_header_font_size: float = 11
    page_meta_font_size: float = 8
    page_footer_font_size: float = 7.5

    # styling
    header_background_hex: str = "#EDEDED"
    grid_color_hex: str = "#777777"
    meta_text_hex: str = "#444444"
    footer_text_hex: str = "#555555"

    base_grid_line_width: float = 0.35
    header_line_width: float = 0.8
    writable_box_line_width: float = 0.8
    divider_line_width: float = 0.5

    # column widths in mm
    col_widths_mm: List[float] = field(
        default_factory=lambda: [
            10,  # S.No.
            18,  # Area
            22,  # Operator
            17,  # Booking
            17,  # Memo
            66,  # Address
            22,  # Mobile
            28,  # OTP
            34,  # Signature
            12,  # Online
        ]
    )


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