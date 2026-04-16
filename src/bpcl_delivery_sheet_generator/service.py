from __future__ import annotations

from pathlib import Path
from typing import Optional

from .config import PackageConfig
from .logging_utils import get_logger
from .models import GenerationResult
from .reader import CSVReader
from .render_pdf import PDFRenderer
from .transform import DeliveryTransformer


class DeliverySheetService:
    """
    Main orchestration service for generating delivery sheets.

    Responsibilities:
    - initialize configuration and logger
    - orchestrate reader -> transformer -> renderer pipeline
    - return structured execution result

    This class should remain thin.
    It should coordinate work, not contain low-level business logic.
    """

    def __init__(
        self,
        *,
        config: Optional[PackageConfig] = None,
    ) -> None:
        self.config = config or PackageConfig()

        self.logger = get_logger(
            logger_name=self.config.logging.logger_name,
            log_level=self.config.logging.log_level,
            log_to_file=self.config.logging.log_to_file,
            log_file_path=self.config.logging.log_file_path,
        )

        self.reader = CSVReader(
            config=self.config.input,
            logger=self.logger,
        )
        self.transformer = DeliveryTransformer(
            config=self.config,
            logger=self.logger,
        )
        self.renderer = PDFRenderer(
            config=self.config,
            logger=self.logger,
        )

    def generate(
        self,
        *,
        input_csv_path: str | Path,
        output_dir: str | Path,
    ) -> GenerationResult:
        """
        Generate delivery sheet outputs from the input CSV file.
        """

        input_path = Path(input_csv_path)
        output_path = Path(output_dir)

        self.logger.info("Starting delivery sheet generation")
        self.logger.info("Input file: %s", input_path)
        self.logger.info("Output directory: %s", output_path)

        if not input_path.exists():
            self.logger.error("Input CSV not found: %s", input_path)
            raise FileNotFoundError(f"Input CSV not found: {input_path}")

        output_path.mkdir(parents=True, exist_ok=True)

        try:
            # -------------------------------------------------
            # STEP 1: READ
            # -------------------------------------------------
            self.logger.info("STEP 1: Reading input CSV")
            raw_df = self.reader.read(input_path)

            # -------------------------------------------------
            # STEP 2: TRANSFORM
            # -------------------------------------------------
            self.logger.info("STEP 2: Transforming input data")
            batches = self.transformer.transform(raw_df)

            # -------------------------------------------------
            # STEP 3: RENDER
            # -------------------------------------------------
            self.logger.info("STEP 3: Rendering output PDFs")
            result = self.renderer.render(
                batches=batches,
                output_dir=output_path,
                total_input_rows=len(raw_df),
            )

            self.logger.info(
                "Generation completed successfully: total_input_rows=%s total_output_rows=%s total_batches=%s",
                result.total_input_rows,
                result.total_output_rows,
                result.total_batches,
            )
            self.logger.info(
                "Output summary: combined_pdf=%s split_pdf_count=%s zip_path=%s",
                result.combined_pdf_path,
                len(result.split_pdf_paths),
                result.zip_path,
            )

            return result

        except Exception:
            self.logger.exception("Generation failed due to error")
            raise