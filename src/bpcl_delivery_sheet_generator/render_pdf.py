from __future__ import annotations

import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    TableStyle,
)

from .config import PackageConfig
from .models import DeliveryBatch, DeliveryRecord, GenerationResult


class PDFRenderer:
    """
    Render grouped delivery batches into print-ready PDF outputs.

    Responsibilities:
    - create combined PDF
    - create split PDFs
    - optionally create ZIP bundle
    - combine address only for final display

    Non-responsibilities:
    - no CSV reading
    - no source column mapping
    - no grouping logic
    """

    def __init__(
        self,
        *,
        config: PackageConfig,
        logger,
    ) -> None:
        self.config = config
        self.logger = logger
        self.header_cfg = config.header
        self.render_cfg = config.render

        styles = getSampleStyleSheet()

        self.cell_style = ParagraphStyle(
            "bpcl_cell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=self.render_cfg.cell_font_size,
            leading=self.render_cfg.cell_leading,
            textColor=colors.black,
        )
        self.header_style = ParagraphStyle(
            "bpcl_header",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=self.render_cfg.header_font_size,
            leading=self.render_cfg.header_leading,
            textColor=colors.black,
        )

        self.col_widths = [width_mm * mm for width_mm in self.render_cfg.col_widths_mm]

    def render(
        self,
        *,
        batches: List[DeliveryBatch],
        output_dir: str | Path,
        total_input_rows: int,
    ) -> GenerationResult:
        """
        Render outputs according to configured output mode.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        result = GenerationResult(
            total_input_rows=total_input_rows,
            total_output_rows=sum(len(batch.records) for batch in batches),
            total_batches=len(batches),
        )

        mode = self.config.output.mode
        self.logger.info("Rendering output mode: %s", mode)

        if mode in ("combined", "both"):
            result.combined_pdf_path = self._render_combined_pdf(
                batches=batches,
                output_dir=output_path,
            )

        if mode in ("split", "both"):
            result.split_pdf_paths = self._render_split_pdfs(
                batches=batches,
                output_dir=output_path,
            )

            if self.config.output.zip_split_outputs and result.split_pdf_paths:
                result.zip_path = self._create_zip(
                    pdf_paths=result.split_pdf_paths,
                    output_dir=output_path,
                )

        self.logger.info(
            "Render complete: combined=%s split_count=%s zip=%s",
            result.combined_pdf_path,
            len(result.split_pdf_paths),
            result.zip_path,
        )

        return result

    def _render_combined_pdf(
        self,
        *,
        batches: List[DeliveryBatch],
        output_dir: Path,
    ) -> Path:
        output_file = output_dir / "delivery_handover_all_deliverymen.pdf"
        self.logger.info("Creating combined PDF: %s", output_file)

        if not batches:
            doc = self._build_doc(output_file, batch_name="", batch_count=0)
            doc.build(
                [],
                onFirstPage=self._draw_page_frame,
                onLaterPages=self._draw_page_frame,
            )
            return output_file

        doc = self._build_doc(
            output_file,
            batch_name=batches[0].batch_name,
            batch_count=len(batches[0].records),
        )

        story = []
        for index, batch in enumerate(batches):
            doc._batch_name = batch.batch_name
            doc._batch_count = len(batch.records)

            story.extend(self._build_batch_story(batch))

            if index < len(batches) - 1:
                story.append(PageBreak())

        doc.build(
            story,
            onFirstPage=self._draw_page_frame,
            onLaterPages=self._draw_page_frame,
        )
        return output_file

    def _render_split_pdfs(
        self,
        *,
        batches: List[DeliveryBatch],
        output_dir: Path,
    ) -> List[Path]:
        split_dir = output_dir / "split_pdfs"
        split_dir.mkdir(parents=True, exist_ok=True)

        output_paths: List[Path] = []

        for batch in batches:
            filename = f"delivery_handover_{self._slugify(batch.batch_name)}.pdf"
            output_file = split_dir / filename
            self.logger.info("Creating split PDF: %s", output_file)

            doc = self._build_doc(
                output_file,
                batch_name=batch.batch_name,
                batch_count=len(batch.records),
            )

            doc.build(
                self._build_batch_story(batch),
                onFirstPage=self._draw_page_frame,
                onLaterPages=self._draw_page_frame,
            )
            output_paths.append(output_file)

        return output_paths

    def _build_doc(
        self,
        output_file: Path,
        *,
        batch_name: str,
        batch_count: int,
    ) -> SimpleDocTemplate:
        doc = SimpleDocTemplate(
            str(output_file),
            pagesize=landscape(A4),
            leftMargin=self.render_cfg.left_margin_mm * mm,
            rightMargin=self.render_cfg.right_margin_mm * mm,
            topMargin=self.render_cfg.top_margin_mm * mm,
            bottomMargin=self.render_cfg.bottom_margin_mm * mm,
        )

        doc._batch_name = batch_name
        doc._batch_count = batch_count
        return doc

    def _create_zip(
        self,
        *,
        pdf_paths: List[Path],
        output_dir: Path,
    ) -> Path:
        zip_path = output_dir / "delivery_handover_split_pdfs.zip"
        self.logger.info("Creating ZIP bundle: %s", zip_path)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for pdf_path in pdf_paths:
                zf.write(pdf_path, arcname=pdf_path.name)

        return zip_path

    def _build_batch_story(self, batch: DeliveryBatch) -> List:
        story: List = []
        story.append(Spacer(1, self.render_cfg.story_top_spacer_mm * mm))
        story.append(self._build_table(batch))
        return story

    def _build_table(self, batch: DeliveryBatch) -> LongTable:
        headers = [
            "S.No.",
            "Consumer No.",
            "Consumer Name",
            "Area",
            "Operator",
            "Booking",
            "Memo",
            "Address",
            "Mobile",
            "OTP",
            "Signature",
            "Online",
        ]

        table_data = [[Paragraph(header, self.header_style) for header in headers]]

        online_value = (
            self.render_cfg.online_checkbox_text
            if self.render_cfg.show_online_checkbox
            else ""
        )

        for idx, record in enumerate(batch.records, start=1):
            table_data.append(
                [
                    self._p(str(idx)),
                    self._p(record.consumer_number),
                    self._p(record.consumer_name),
                    self._p(record.area),
                    self._p(record.operator_name),
                    self._p(record.booking_date),
                    self._p(record.cash_memo_date),
                    self._p(self._build_full_address(record)),
                    self._p(record.mobile_number),
                    self._p(""),
                    self._p(""),
                    self._p(online_value),
                ]
            )

        table = LongTable(
            table_data,
            colWidths=self.col_widths,
            repeatRows=1,
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(self.render_cfg.header_background_hex),
                    ),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        self.render_cfg.base_grid_line_width,
                        colors.HexColor(self.render_cfg.grid_color_hex),
                    ),
                    (
                        "LINEBELOW",
                        (0, 0),
                        (-1, 0),
                        self.render_cfg.header_line_width,
                        colors.black,
                    ),
                    (
                        "BOX",
                        (9, 1),
                        (9, -1),
                        self.render_cfg.writable_box_line_width,
                        colors.black,
                    ),
                    (
                        "BOX",
                        (10, 1),
                        (10, -1),
                        self.render_cfg.writable_box_line_width,
                        colors.black,
                    ),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (1, -1), "CENTER"),
                    ("ALIGN", (3, 0), (6, -1), "CENTER"),
                    ("ALIGN", (8, 0), (9, -1), "CENTER"),
                    ("ALIGN", (11, 0), (11, -1), "CENTER"),
                    ("ALIGN", (2, 0), (2, -1), "LEFT"),
                    ("ALIGN", (7, 0), (7, -1), "LEFT"),
                    ("ALIGN", (10, 0), (10, -1), "LEFT"),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        self.render_cfg.row_top_padding,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        self.render_cfg.row_bottom_padding,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        self.render_cfg.cell_left_padding,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        self.render_cfg.cell_right_padding,
                    ),
                ]
            )
        )

        return table

    def _build_full_address(self, record: DeliveryRecord) -> str:
        """
        Combine address parts for final display only.
        """
        if not self.render_cfg.use_combined_address:
            return record.address1

        parts = [
            part.strip()
            for part in [record.address1, record.address2, record.address3]
            if part and part.strip()
        ]
        return self.render_cfg.address_separator.join(parts)

    def _draw_page_frame(self, canvas, doc) -> None:
        width, height = landscape(A4)
        printed_at = datetime.now().strftime(self.render_cfg.printed_datetime_format)

        batch_name = getattr(doc, "_batch_name", "UNKNOWN")
        batch_count = getattr(doc, "_batch_count", 0)

        left_x = doc.leftMargin
        right_x = width - doc.rightMargin

        header_top_y = height - (self.render_cfg.page_header_y_mm * mm)
        line_gap = 4.2 * mm

        title_y = header_top_y
        meta_y = title_y - line_gap
        price_y = meta_y - line_gap
        divider_y = price_y - 2.5 * mm

        canvas.saveState()

        # Title
        canvas.setFillColor(colors.black)
        canvas.setFont("Helvetica-Bold", self.render_cfg.page_header_font_size)
        canvas.drawString(left_x, title_y, self.render_cfg.title)

        # Page info
        canvas.setFont("Helvetica", self.render_cfg.page_meta_font_size)
        canvas.drawRightString(
            right_x,
            title_y,
            f"Page {doc.page} | Printed: {printed_at}",
        )

        # Delivery person line
        canvas.drawString(
            left_x,
            meta_y,
            f"Delivery person: {batch_name} | Total records: {batch_count}",
        )

        # Price line
        price_parts: List[str] = []

        if self.header_cfg.price_10kg is not None:
            price_parts.append(
                f"{self.header_cfg.price_10kg_label}: "
                f"{self.header_cfg.currency_symbol}{self.header_cfg.price_10kg:.2f}"
            )

        if self.header_cfg.price_14_2kg is not None:
            price_parts.append(
                f"{self.header_cfg.price_14_2kg_label}: "
                f"{self.header_cfg.currency_symbol}{self.header_cfg.price_14_2kg:.2f}"
            )

        if price_parts:
            canvas.setFont("Helvetica-Bold", self.render_cfg.page_meta_font_size)
            canvas.drawString(left_x, price_y, " | ".join(price_parts))
        else:
            price_y = meta_y

        # Divider
        canvas.setStrokeColor(colors.HexColor(self.render_cfg.grid_color_hex))
        canvas.setLineWidth(self.render_cfg.divider_line_width)
        canvas.line(left_x, divider_y, right_x, divider_y)

        # Footer
        if self.render_cfg.show_footer_note and self.render_cfg.footer_note.strip():
            canvas.setFillColor(colors.HexColor(self.render_cfg.footer_text_hex))
            canvas.setFont("Helvetica", self.render_cfg.page_footer_font_size)
            canvas.drawString(
                left_x,
                self.render_cfg.footer_y_mm * mm,
                self.render_cfg.footer_note,
            )

        canvas.restoreState()

    def _p(self, text: str) -> Paragraph:
        return Paragraph(self._escape(text), self.cell_style)

    @staticmethod
    def _escape(text: str) -> str:
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    @staticmethod
    def _slugify(value: str) -> str:
        value = (value or "").strip().upper()
        value = re.sub(r"[^A-Z0-9]+", "_", value).strip("_")
        return value or "UNASSIGNED"