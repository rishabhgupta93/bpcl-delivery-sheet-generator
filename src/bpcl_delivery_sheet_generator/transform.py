from __future__ import annotations

from typing import List

import pandas as pd

from .config import PackageConfig
from .models import DeliveryBatch, DeliveryRecord


class DeliveryTransformer:
    """
    Transform raw source dataframe into grouped delivery batches.

    Responsibilities:
    - map source columns to canonical names
    - normalize string values
    - sort records
    - group records into delivery batches

    Non-responsibilities:
    - no CSV reading
    - no PDF rendering
    """

    def __init__(
        self,
        *,
        config: PackageConfig,
        logger,
    ) -> None:
        self.config = config
        self.logger = logger

    def transform(self, df: pd.DataFrame) -> List[DeliveryBatch]:
        """
        Convert raw dataframe into grouped delivery batches.
        """

        self.logger.info("Starting dataframe transformation")

        working_df = df.copy()

        working_df = self._map_columns(working_df)
        working_df = self._normalize_values(working_df)
        working_df = self._sort_records(working_df)

        batches = self._build_batches(working_df)

        self.logger.info(
            "Transformation complete: total_batches=%s total_rows=%s",
            len(batches),
            len(working_df),
        )

        return batches

    def _map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rename source columns to canonical internal field names.
        """

        column_mapping = self.config.input.column_mapping
        self.logger.info("Applying column mapping")
        self.logger.debug("Column mapping: %s", column_mapping)

        mapped_df = df.rename(columns=column_mapping)

        required_canonical_columns = list(column_mapping.values())
        missing_canonical_columns = [
            col for col in required_canonical_columns if col not in mapped_df.columns
        ]
        if missing_canonical_columns:
            self.logger.error(
                "Missing canonical columns after mapping: %s",
                missing_canonical_columns,
            )
            raise ValueError(
                f"Missing canonical columns after mapping: {missing_canonical_columns}"
            )

        return mapped_df[required_canonical_columns].copy()

    def _normalize_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize string values in the canonical dataframe.
        """

        self.logger.info("Normalizing canonical dataframe values")

        for col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

        return df

    def _sort_records(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sort canonical dataframe using configured sort keys.
        """

        sort_by = [self.config.transform.group_by] + self.config.transform.sort_by
        self.logger.info("Sorting records by: %s", sort_by)

        missing_sort_columns = [col for col in sort_by if col not in df.columns]
        if missing_sort_columns:
            self.logger.error("Missing sort columns: %s", missing_sort_columns)
            raise ValueError(f"Missing sort columns: {missing_sort_columns}")

        return df.sort_values(by=sort_by, kind="stable").reset_index(drop=True)

    def _build_batches(self, df: pd.DataFrame) -> List[DeliveryBatch]:
        """
        Group the canonical dataframe into delivery batches.
        """

        group_by = self.config.transform.group_by
        self.logger.info("Grouping records by: %s", group_by)

        if group_by not in df.columns:
            self.logger.error("Group-by column not found: %s", group_by)
            raise ValueError(f"Group-by column not found: {group_by}")

        batches: List[DeliveryBatch] = []

        for batch_name, batch_df in df.groupby(group_by, dropna=False, sort=False):
            records = [
                DeliveryRecord(
                    area=row["area"],
                    operator_name=row["operator_name"],
                    booking_date=row["booking_date"],
                    cash_memo_date=row["cash_memo_date"],
                    address1=row["address1"],
                    address2=row["address2"],
                    address3=row["address3"],
                    mobile_number=row["mobile_number"],
                )
                for _, row in batch_df.iterrows()
            ]

            batches.append(
                DeliveryBatch(
                    batch_name=batch_name or "UNASSIGNED",
                    records=records,
                )
            )

        self.logger.info("Built %s delivery batches", len(batches))
        return batches