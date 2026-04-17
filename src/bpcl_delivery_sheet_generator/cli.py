from __future__ import annotations

import argparse
from pathlib import Path

from .config import PackageConfig
from .service import DeliverySheetService


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line parser for the package.
    """

    parser = argparse.ArgumentParser(
        prog="bpcl-delivery-sheet",
        description="Generate print-ready BPCL delivery handover PDFs from cash memo CSV files.",
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to the input cash memo CSV file.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the output directory.",
    )
    parser.add_argument(
        "--mode",
        choices=["combined", "split", "both"],
        default="both",
        help="Output mode: combined PDF, split PDFs, or both.",
    )
    parser.add_argument(
        "--price-10kg",
        type=float,
        required=False,
        help="Price of 10 KG cylinder to display in the sheet header.",
    )
    parser.add_argument(
        "--price-14-2kg",
        dest="price_14_2kg",
        type=float,
        required=False,
        help="Price of 14.2 KG cylinder to display in the sheet header.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Log level, for example: DEBUG, INFO, WARNING, ERROR.",
    )

    return parser


def main() -> None:
    """
    CLI entry point.
    """

    parser = build_parser()
    args = parser.parse_args()

    config = PackageConfig()
    config.output.mode = args.mode
    config.logging.log_level = args.log_level.upper()

    config.header.price_10kg = args.price_10kg
    config.header.price_14_2kg = args.price_14_2kg

    service = DeliverySheetService(config=config)
    result = service.generate(
        input_csv_path=Path(args.input),
        output_dir=Path(args.output),
    )

    print("Generation completed.")
    print(f"Total input rows: {result.total_input_rows}")
    print(f"Total output rows: {result.total_output_rows}")
    print(f"Total batches: {result.total_batches}")

    if result.combined_pdf_path:
        print(f"Combined PDF: {result.combined_pdf_path}")

    if result.split_pdf_paths:
        print(f"Split PDF count: {len(result.split_pdf_paths)}")

    if result.zip_path:
        print(f"ZIP file: {result.zip_path}")