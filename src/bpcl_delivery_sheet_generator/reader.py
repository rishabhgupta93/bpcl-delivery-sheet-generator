from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import InputConfig


class CSVReader:
    """
    Read the source CSV file and validate required source columns.

    Responsibilities:
    - read CSV using configured skip rows and encoding
    - validate required source columns
    - return raw dataframe

    Non-responsibilities:
    - no column mapping
    - no normalization
    - no grouping/sorting
    """

    def __init__(
        self,
        *,
        config: InputConfig,
        logger,
    ) -> None:
        self.config = config
        self.logger = logger

    def read(self, input_csv_path: str | Path) -> pd.DataFrame:
        """
        Read the input CSV and validate the required source columns.
        """

        input_path = Path(input_csv_path)

        self.logger.info("Reading CSV file: %s", input_path)
        self.logger.info(
            "CSV read settings: skip_rows=%s encoding=%s",
            self.config.skip_rows,
            self.config.encoding,
        )

        df = pd.read_csv(
            input_path,
            skiprows=self.config.skip_rows,
            encoding=self.config.encoding,
        )

        self.logger.info(
            "CSV read complete: rows=%s cols=%s",
            len(df),
            len(df.columns),
        )
        self.logger.debug("CSV columns found: %s", list(df.columns))

        self._validate_required_columns(df)

        return df

    def _validate_required_columns(self, df: pd.DataFrame) -> None:
        """
        Validate that all required source columns are present.
        """

        missing_columns = [
            col
            for col in self.config.required_source_columns
            if col not in df.columns
        ]

        if missing_columns:
            self.logger.error(
                "Missing required source columns: %s",
                missing_columns,
            )
            raise ValueError(
                f"Missing required source columns: {missing_columns}"
            )

        self.logger.info("Required source columns validation passed")