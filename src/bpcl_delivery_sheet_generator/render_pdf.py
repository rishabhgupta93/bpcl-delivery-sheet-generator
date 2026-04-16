# from __future__ import annotations
#
# import re
# import zipfile
# from pathlib import Path
# from typing import List
#
# from reportlab.lib import colors
# from reportlab.lib.pagesizes import A4, landscape
# from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
# from reportlab.lib.units import mm
# from reportlab.platypus import LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle
#
# from .config import PackageConfig
# from .models import DeliveryBatch, DeliveryRecord, GenerationResult
#
#
# class PDFRenderer:
#     """
#     Render grouped delivery batches into print-ready PDF outputs.
#
#     Responsibilities:
#     - create combined PDF
#     - create split PDFs
#     - optionally create ZIP bundle
#     - combine address only for final display
#
#     Non-responsibilities:
#     - no CSV reading
#     - no source column mapping
#     - no grouping logic
#     """
#
#     def __init__(
#         self,
#         *,
#         config: PackageConfig,
#         logger,
#     ) -> None:
#         self.config = config
#         self.logger = logger
#
#         styles = getSampleStyleSheet()
#         self.title_style = ParagraphStyle(
#             "bpcl_title",
#             parent=styles["Title"],
#             fontName="Helvetica-Bold",
#             fontSize=15,
#             leading=18,
#             textColor=colors.HexColor("#16324F"),
#             spaceAfter=4,
#         )
#         self.meta_style = ParagraphStyle(
#             "bpcl_meta",
#             parent=styles["BodyText"],
#             fontName="Helvetica",
#             fontSize=8.5,
#             leading=10.5,
#             textColor=colors.HexColor("#4A5568"),
#         )
#         self.cell_style = ParagraphStyle(
#             "bpcl_cell",
#             parent=styles["BodyText"],
#             fontName="Helvetica",
#             fontSize=7.4,
#             leading=8.8,
#             textColor=colors.black,
#         )
#         self.header_style = ParagraphStyle(
#             "bpcl_header",
#             parent=styles["BodyText"],
#             fontName="Helvetica-Bold",
#             fontSize=7.2,
#             leading=8.4,
#             textColor=colors.white,
#         )
#
#         # minimal but readable landscape layout
#         self.col_widths = [
#             12 * mm,  # SLNO
#             23 * mm,  # Area
#             28 * mm,  # Operator
#             18 * mm,  # Booking Date
#             18 * mm,  # Cash Memo Date
#             60 * mm,  # Full Address
#             22 * mm,  # Mobile
#             16 * mm,  # OTP
#             23 * mm,  # Customer Sign
#             14 * mm,  # Online
#         ]
#
#     def render(
#         self,
#         *,
#         batches: List[DeliveryBatch],
#         output_dir: str | Path,
#         total_input_rows: int,
#     ) -> GenerationResult:
#         """
#         Render outputs according to configured output mode.
#         """
#
#         output_path = Path(output_dir)
#         output_path.mkdir(parents=True, exist_ok=True)
#
#         result = GenerationResult(
#             total_input_rows=total_input_rows,
#             total_output_rows=sum(len(batch.records) for batch in batches),
#             total_batches=len(batches),
#         )
#
#         mode = self.config.output.mode
#         self.logger.info("Rendering output mode: %s", mode)
#
#         if mode in ("combined", "both"):
#             result.combined_pdf_path = self._render_combined_pdf(
#                 batches=batches,
#                 output_dir=output_path,
#             )
#
#         if mode in ("split", "both"):
#             result.split_pdf_paths = self._render_split_pdfs(
#                 batches=batches,
#                 output_dir=output_path,
#             )
#
#             if self.config.output.zip_split_outputs and result.split_pdf_paths:
#                 result.zip_path = self._create_zip(
#                     pdf_paths=result.split_pdf_paths,
#                     output_dir=output_path,
#                 )
#
#         self.logger.info(
#             "Render complete: combined=%s split_count=%s zip=%s",
#             result.combined_pdf_path,
#             len(result.split_pdf_paths),
#             result.zip_path,
#         )
#
#         return result
#
#     def _render_combined_pdf(
#         self,
#         *,
#         batches: List[DeliveryBatch],
#         output_dir: Path,
#     ) -> Path:
#         output_file = output_dir / "delivery_handover_all_deliverymen.pdf"
#         self.logger.info("Creating combined PDF: %s", output_file)
#
#         doc = SimpleDocTemplate(
#             str(output_file),
#             pagesize=landscape(A4),
#             leftMargin=8 * mm,
#             rightMargin=8 * mm,
#             topMargin=14 * mm,
#             bottomMargin=10 * mm,
#         )
#
#         story = []
#         for index, batch in enumerate(batches):
#             story.extend(self._build_batch_story(batch))
#             if index < len(batches) - 1:
#                 story.append(PageBreak())
#
#         doc.build(
#             story,
#             onFirstPage=self._draw_page_frame,
#             onLaterPages=self._draw_page_frame,
#         )
#         return output_file
#
#     def _render_split_pdfs(
#         self,
#         *,
#         batches: List[DeliveryBatch],
#         output_dir: Path,
#     ) -> List[Path]:
#         split_dir = output_dir / "split_pdfs"
#         split_dir.mkdir(parents=True, exist_ok=True)
#
#         output_paths: List[Path] = []
#
#         for batch in batches:
#             filename = f"delivery_handover_{self._slugify(batch.batch_name)}.pdf"
#             output_file = split_dir / filename
#             self.logger.info("Creating split PDF: %s", output_file)
#
#             doc = SimpleDocTemplate(
#                 str(output_file),
#                 pagesize=landscape(A4),
#                 leftMargin=8 * mm,
#                 rightMargin=8 * mm,
#                 topMargin=14 * mm,
#                 bottomMargin=10 * mm,
#             )
#
#             doc.build(
#                 self._build_batch_story(batch),
#                 onFirstPage=self._draw_page_frame,
#                 onLaterPages=self._draw_page_frame,
#             )
#             output_paths.append(output_file)
#
#         return output_paths
#
#     def _create_zip(
#         self,
#         *,
#         pdf_paths: List[Path],
#         output_dir: Path,
#     ) -> Path:
#         zip_path = output_dir / "delivery_handover_split_pdfs.zip"
#         self.logger.info("Creating ZIP bundle: %s", zip_path)
#
#         with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
#             for pdf_path in pdf_paths:
#                 zf.write(pdf_path, arcname=pdf_path.name)
#
#         return zip_path
#
#     def _build_batch_story(self, batch: DeliveryBatch) -> List:
#         story: List = []
#
#         story.append(Spacer(1, 6 * mm))
#         story.append(Paragraph(self._escape(self.config.render.title), self.title_style))
#         story.append(
#             Paragraph(
#                 self._escape(
#                     f"Delivery person: {batch.batch_name} | Total records: {len(batch.records)}"
#                 ),
#                 self.meta_style,
#             )
#         )
#         story.append(Spacer(1, 3 * mm))
#         story.append(self._build_table(batch))
#         story.append(Spacer(1, 3 * mm))
#         story.append(
#             Paragraph(self._escape(self.config.render.footer_note), self.meta_style)
#         )
#
#         return story
#
#     def _build_table(self, batch: DeliveryBatch) -> LongTable:
#         headers = [
#             "SLNO",
#             "Area",
#             "eKYC Operator",
#             "Booking Date",
#             "Cash Memo Date",
#             "Address",
#             "Mobile Number",
#             "OTP",
#             "Customer Sign",
#             "Online",
#         ]
#
#         table_data = [[Paragraph(h, self.header_style) for h in headers]]
#
#         for idx, record in enumerate(batch.records, start=1):
#             table_data.append(
#                 [
#                     self._p(str(idx)),
#                     self._p(record.area),
#                     self._p(record.operator_name),
#                     self._p(record.booking_date),
#                     self._p(record.cash_memo_date),
#                     self._p(self._build_full_address(record)),
#                     self._p(record.mobile_number),
#                     self._p(""),
#                     self._p(""),
#                     self._p(""),
#                 ]
#             )
#
#         table = LongTable(
#             table_data,
#             colWidths=self.col_widths,
#             repeatRows=1,
#         )
#
#         table.setStyle(
#             TableStyle(
#                 [
#                     ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
#                     ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
#                     ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#A0AEC0")),
#                     ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#F7FAFC")]),
#                     ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
#                     ("ALIGN", (0, 0), (0, -1), "CENTER"),
#                     ("ALIGN", (1, 0), (4, -1), "CENTER"),
#                     ("ALIGN", (6, 0), (6, -1), "CENTER"),
#                     ("ALIGN", (7, 0), (9, -1), "CENTER"),
#                     ("BACKGROUND", (7, 1), (9, -1), colors.HexColor("#FFFBEA")),
#                     ("TOPPADDING", (0, 0), (-1, -1), 5),
#                     ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
#                     ("LEFTPADDING", (0, 0), (-1, -1), 4),
#                     ("RIGHTPADDING", (0, 0), (-1, -1), 4),
#                 ]
#             )
#         )
#
#         return table
#
#     def _build_full_address(self, record: DeliveryRecord) -> str:
#         """
#         Combine address parts for final display only.
#         """
#
#         if not self.config.render.use_combined_address:
#             return record.address1
#
#         parts = [
#             part.strip()
#             for part in [record.address1, record.address2, record.address3]
#             if part and part.strip()
#         ]
#         return self.config.render.address_separator.join(parts)
#
#     def _draw_page_frame(self, canvas, doc) -> None:
#         width, height = landscape(A4)
#
#         canvas.saveState()
#         canvas.setFillColor(colors.HexColor("#16324F"))
#         canvas.rect(0, height - 14 * mm, width, 14 * mm, stroke=0, fill=1)
#
#         canvas.setFillColor(colors.white)
#         canvas.setFont("Helvetica-Bold", 10)
#         canvas.drawString(doc.leftMargin, height - 9 * mm, self.config.render.title)
#
#         canvas.setFont("Helvetica", 8)
#         canvas.drawRightString(width - doc.rightMargin, height - 9 * mm, f"Page {doc.page}")
#
#         canvas.setFillColor(colors.HexColor("#718096"))
#         canvas.setFont("Helvetica", 7)
#         canvas.drawString(
#             doc.leftMargin,
#             6 * mm,
#             "Field-use format: collect OTP, signature, and mark online delivery status.",
#         )
#         canvas.restoreState()
#
#     def _p(self, text: str) -> Paragraph:
#         return Paragraph(self._escape(text), self.cell_style)
#
#     @staticmethod
#     def _escape(text: str) -> str:
#         return (
#             str(text)
#             .replace("&", "&amp;")
#             .replace("<", "&lt;")
#             .replace(">", "&gt;")
#         )
#
#     @staticmethod
#     def _slugify(value: str) -> str:
#         value = (value or "").strip().upper()
#         value = re.sub(r"[^A-Z0-9]+", "_", value).strip("_")
#         return value or "UNASSIGNED"

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
from reportlab.platypus import LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle


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

        styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            "bpcl_title",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#16324F"),
            spaceAfter=4,
        )
        self.meta_style = ParagraphStyle(
            "bpcl_meta",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=11.2,
            textColor=colors.HexColor("#4A5568"),
        )
        self.cell_style = ParagraphStyle(
            "bpcl_cell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.6,
            leading=10.2,
            textColor=colors.black,
        )
        self.header_style = ParagraphStyle(
            "bpcl_header",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.4,
            leading=9.8,
            textColor=colors.white,
        )

        # Wider usable table by reducing page margins.
        # Column widths intentionally prioritize write-in fields:
        # OTP and Customer Sign.
        self.col_widths = [
            11 * mm,  # SLNO
            20 * mm,  # Area
            24 * mm,  # eKYC Operator
            18 * mm,  # Booking Date
            18 * mm,  # Cash Memo Date
            68 * mm,  # Address
            22 * mm,  # Mobile Number
            24 * mm,  # OTP
            30 * mm,  # Customer Sign
            15 * mm,  # Online
        ]

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

        doc = SimpleDocTemplate(
            str(output_file),
            pagesize=landscape(A4),
            leftMargin=4 * mm,
            rightMargin=4 * mm,
            topMargin=14 * mm,
            bottomMargin=10 * mm,
        )

        story = []
        for index, batch in enumerate(batches):
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

            doc = SimpleDocTemplate(
                str(output_file),
                pagesize=landscape(A4),
                leftMargin=4 * mm,
                rightMargin=4 * mm,
                topMargin=14 * mm,
                bottomMargin=10 * mm,
            )

            doc.build(
                self._build_batch_story(batch),
                onFirstPage=self._draw_page_frame,
                onLaterPages=self._draw_page_frame,
            )
            output_paths.append(output_file)

        return output_paths

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

        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph(self._escape(self.config.render.title), self.title_style))
        story.append(
            Paragraph(
                self._escape(
                    f"Delivery person: {batch.batch_name} | Total records: {len(batch.records)}"
                ),
                self.meta_style,
            )
        )
        story.append(Spacer(1, 3 * mm))
        story.append(self._build_table(batch))
        story.append(Spacer(1, 3 * mm))
        story.append(
            Paragraph(self._escape(self.config.render.footer_note), self.meta_style)
        )

        return story

    def _build_table(self, batch: DeliveryBatch) -> LongTable:
        headers = [
            "SLNO",
            "Area",
            "eKYC Operator",
            "Booking Date",
            "Cash Memo Date",
            "Address",
            "Mobile Number",
            "OTP",
            "Customer Sign",
            "Online",
        ]

        table_data = [[Paragraph(h, self.header_style) for h in headers]]

        for idx, record in enumerate(batch.records, start=1):
            table_data.append(
                [
                    self._p(str(idx)),
                    self._p(record.area),
                    self._p(record.operator_name),
                    self._p(record.booking_date),
                    self._p(record.cash_memo_date),
                    self._p(self._build_full_address(record)),
                    self._p(record.mobile_number),
                    self._p(""),
                    self._p(""),
                    self._p(""),
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
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#A0AEC0")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#F7FAFC")]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

                    # alignment
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (1, 0), (4, -1), "CENTER"),
                    ("ALIGN", (6, 0), (6, -1), "CENTER"),
                    ("ALIGN", (7, 0), (9, -1), "CENTER"),

                    # highlight writable columns
                    ("BACKGROUND", (7, 1), (9, -1), colors.HexColor("#FFFBEA")),

                    # more readable cell sizing
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )

        return table

    def _build_full_address(self, record: DeliveryRecord) -> str:
        """
        Combine address parts for final display only.
        """

        if not self.config.render.use_combined_address:
            return record.address1

        parts = [
            part.strip()
            for part in [record.address1, record.address2, record.address3]
            if part and part.strip()
        ]
        return self.config.render.address_separator.join(parts)

    def _draw_page_frame(self, canvas, doc) -> None:
        width, height = landscape(A4)
        printed_at = datetime.now().strftime("%d-%m-%Y %I:%M %p")

        canvas.saveState()

        # top band
        canvas.setFillColor(colors.HexColor("#16324F"))
        canvas.rect(0, height - 14 * mm, width, 14 * mm, stroke=0, fill=1)

        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(doc.leftMargin, height - 9 * mm, self.config.render.title)

        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(
            width - doc.rightMargin,
            height - 9 * mm,
            f"Page {doc.page} | Printed: {printed_at}",
        )

        # bottom note
        canvas.setFillColor(colors.HexColor("#718096"))
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(
            doc.leftMargin,
            6 * mm,
            "Field-use format: collect OTP, signature, and mark online delivery status.",
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