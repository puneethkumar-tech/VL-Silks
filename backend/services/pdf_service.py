"""
VL Silks – Credit / Udhaar Statement PDF Generator Service
Authoritative PDF Generation Service for Customer Credit Statements using ReportLab.
"""

import io
import os
import re
import logging
from decimal import Decimal
from datetime import date, datetime
from flask import current_app

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from backend.services import credit_service, customer_service
from backend.services.credit_service import ValidationError, to_decimal

logger = logging.getLogger('vl_silks.pdf_service')

# ---------------------------------------------------------------------------
# Brand Color Palette Constants
# ---------------------------------------------------------------------------
COLOR_PRIMARY_MAROON = colors.HexColor('#8B0000')    # Rich Maroon
COLOR_SECONDARY_GOLD = colors.HexColor('#D4AF37')    # Royal Gold
COLOR_CREAM_BG       = colors.HexColor('#FFF8E1')    # Warm Cream
COLOR_CHARCOAL       = colors.HexColor('#333333')    # Deep Charcoal Text
COLOR_MUTED_GRAY     = colors.HexColor('#666666')    # Muted subtext
COLOR_LIGHT_BG       = colors.HexColor('#F8F9FA')    # Light Table Row BG
COLOR_BORDER_GRAY    = colors.HexColor('#E0E0E0')    # Table Border Gray
COLOR_SUCCESS_GREEN  = colors.HexColor('#198754')    # Success Green for Settlements
COLOR_DANGER_RED     = colors.HexColor('#DC3545')    # Danger Red for Outstanding

# ---------------------------------------------------------------------------
# Font Setup (with graceful fallback to Helvetica)
# ---------------------------------------------------------------------------
FONT_REGULAR = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
FONT_OBLIQUE = 'Helvetica-Oblique'

def _init_fonts():
    global FONT_REGULAR, FONT_BOLD, FONT_OBLIQUE
    candidate_fonts = [
        ('C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/arialbd.ttf', 'C:/Windows/Fonts/ariali.ttf'),
        ('C:/Windows/Fonts/segoeui.ttf', 'C:/Windows/Fonts/segoeuib.ttf', 'C:/Windows/Fonts/segoeuii.ttf'),
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf')
    ]
    for reg, bld, obl in candidate_fonts:
        if os.path.exists(reg):
            try:
                pdfmetrics.registerFont(TTFont('VLCustomFont', reg))
                FONT_REGULAR = 'VLCustomFont'
                if os.path.exists(bld):
                    pdfmetrics.registerFont(TTFont('VLCustomFont-Bold', bld))
                    FONT_BOLD = 'VLCustomFont-Bold'
                else:
                    FONT_BOLD = 'VLCustomFont'
                if os.path.exists(obl):
                    pdfmetrics.registerFont(TTFont('VLCustomFont-Oblique', obl))
                    FONT_OBLIQUE = 'VLCustomFont-Oblique'
                break
            except Exception as e:
                logger.warning(f"Failed to register custom font: {e}")

_init_fonts()


def format_currency_pdf(val):
    """Format decimal as Indian Rupee string for PDF."""
    if val is None:
        return "₹0.00"
    try:
        d = to_decimal(val)
        return f"₹{d:,.2f}"
    except Exception:
        return f"₹{val}"


def sanitize_filename(name):
    """Generate safe, clean ASCII filename."""
    if not name:
        return "Customer"
    cleaned = re.sub(r'[^A-Za-z0-9_-]+', '_', str(name)).strip('_')
    return cleaned or "Customer"


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to calculate total page count and draw running
    headers, footers, brand markers, and page numbers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, total_pages):
        self.saveState()
        
        # 1. Running Header for pages > 1
        if self._pageNumber > 1:
            self.setFont(FONT_BOLD, 8)
            self.setFillColor(COLOR_PRIMARY_MAROON)
            self.drawString(36, 842 - 25, "VL SILKS")
            
            self.setFont(FONT_REGULAR, 7)
            self.setFillColor(COLOR_MUTED_GRAY)
            self.drawString(85, 842 - 25, "• TRADITION MEETS FASHION • Credit / Udhaar Statement")
            
            # Gold divider line
            self.setStrokeColor(COLOR_SECONDARY_GOLD)
            self.setLineWidth(0.75)
            self.line(36, 842 - 29, 595 - 36, 842 - 29)

        # 2. Running Footer on all pages
        # Gold accent line
        self.setStrokeColor(COLOR_SECONDARY_GOLD)
        self.setLineWidth(1)
        self.line(36, 38, 595 - 36, 38)
        
        # Footer text left
        self.setFont(FONT_BOLD, 7.5)
        self.setFillColor(COLOR_PRIMARY_MAROON)
        self.drawString(36, 26, "VL SILKS")
        
        self.setFont(FONT_REGULAR, 7)
        self.setFillColor(COLOR_MUTED_GRAY)
        self.drawString(80, 26, "— Tradition Meets Fashion • Computer-generated statement")
        
        # Footer text right (Page numbers)
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.setFont(FONT_BOLD, 7.5)
        self.setFillColor(COLOR_CHARCOAL)
        self.drawRightString(595 - 36, 26, page_str)
        
        self.restoreState()


def get_logo_image_path():
    """Find the best available VL Silks logo image asset."""
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'vl-silks-logo-transparent.png'),
        os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'vl-silks-logo.png'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'branding', 'logo', 'vl-silks-logo-transparent.png'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'branding', 'logo', 'vl-silks-logo.png'),
    ]
    for p in possible_paths:
        abs_p = os.path.abspath(p)
        if os.path.exists(abs_p):
            return abs_p
    return None


def parse_statement_dates(date_from=None, date_to=None):
    """
    Validate and parse statement period dates.
    Returns (d_from_obj, d_to_obj, formatted_period_str)
    Raises ValidationError if format is invalid or date_from > date_to.
    """
    d_from = None
    d_to = None

    if date_from:
        if isinstance(date_from, str):
            date_from_str = date_from.strip()
            if date_from_str:
                try:
                    d_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
                except ValueError:
                    raise ValidationError(f"Invalid date_from format: '{date_from}'. Expected YYYY-MM-DD.")
        elif isinstance(date_from, (date, datetime)):
            d_from = date_from.date() if isinstance(date_from, datetime) else date_from

    if date_to:
        if isinstance(date_to, str):
            date_to_str = date_to.strip()
            if date_to_str:
                try:
                    d_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
                except ValueError:
                    raise ValidationError(f"Invalid date_to format: '{date_to}'. Expected YYYY-MM-DD.")
        elif isinstance(date_to, (date, datetime)):
            d_to = date_to.date() if isinstance(date_to, datetime) else date_to

    if d_from and d_to and d_from > d_to:
        raise ValidationError(f"date_from ({d_from}) cannot be later than date_to ({d_to}).")

    if d_from and d_to:
        period_str = f"{d_from.strftime('%d-%b-%Y')} to {d_to.strftime('%d-%b-%Y')}"
    elif d_from:
        period_str = f"From {d_from.strftime('%d-%b-%Y')} (to present)"
    elif d_to:
        period_str = f"Up to {d_to.strftime('%d-%b-%Y')}"
    else:
        period_str = "Full Account History (All Time)"

    return d_from, d_to, period_str


def generate_credit_statement_pdf(customer_id, date_from=None, date_to=None):
    """
    Generate an authoritative, branded, professional A4 Credit Statement PDF
    for the specified customer and period.
    
    Returns:
        (pdf_bytes, filename)
    Raises:
        ValidationError: if dates or customer parameters are invalid
        LookupError: if customer does not exist
    """
    # 1. Fetch Authoritative Customer Profile
    profile = credit_service.get_customer_credit_profile(customer_id)
    if not profile:
        raise LookupError(f"Customer #{customer_id} was not found.")

    # 2. Parse & Validate Dates
    d_from, d_to, period_str = parse_statement_dates(date_from, date_to)

    # 3. Fetch Full Chronological Ledger
    raw_ledger = credit_service.get_customer_credit_history(customer_id)

    # 4. Filter ledger by statement period if dates specified
    filtered_ledger = []
    period_credit = Decimal('0.00')
    period_paid = Decimal('0.00')

    for row in raw_ledger:
        tx_date = row.get('transaction_date')
        if isinstance(tx_date, str):
            try:
                tx_date = datetime.strptime(tx_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        elif isinstance(tx_date, datetime):
            tx_date = tx_date.date()

        include = True
        if d_from and tx_date and tx_date < d_from:
            include = False
        if d_to and tx_date and tx_date > d_to:
            include = False

        if include:
            filtered_ledger.append(row)
            period_credit += to_decimal(row.get('debit_amount', Decimal('0.00')))
            period_paid += to_decimal(row.get('credit_amount', Decimal('0.00')))

    # 5. Build Document Template
    buffer = io.BytesIO()
    # A4 Dimensions: 595.27 x 841.89 pt
    # Margins: Left=36, Right=36, Top=36, Bottom=48 -> Printable Width = 523.27 pt
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=32,
        bottomMargin=48
    )

    styles = getSampleStyleSheet()

    # Custom Paragraph Styles
    style_normal = ParagraphStyle('VLNormal', parent=styles['Normal'], fontName=FONT_REGULAR, fontSize=8, leading=11, textColor=COLOR_CHARCOAL)
    style_bold = ParagraphStyle('VLBold', parent=style_normal, fontName=FONT_BOLD)
    style_muted = ParagraphStyle('VLMuted', parent=style_normal, fontName=FONT_REGULAR, fontSize=7.5, leading=10, textColor=COLOR_MUTED_GRAY)
    style_title = ParagraphStyle('VLTitle', parent=styles['Heading1'], fontName=FONT_BOLD, fontSize=15, leading=18, textColor=COLOR_PRIMARY_MAROON, alignment=TA_CENTER)
    style_tagline = ParagraphStyle('VLTagline', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=8, leading=10, textColor=COLOR_SECONDARY_GOLD, alignment=TA_CENTER)
    style_doc_header = ParagraphStyle('VLDocHeader', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=11, leading=14, textColor=COLOR_PRIMARY_MAROON, alignment=TA_CENTER)

    style_th = ParagraphStyle('VLTH', parent=style_bold, fontSize=7.5, leading=9, textColor=colors.white, alignment=TA_LEFT)
    style_th_right = ParagraphStyle('VLTHRight', parent=style_th, alignment=TA_RIGHT)
    style_td = ParagraphStyle('VLTD', parent=style_normal, fontSize=7.5, leading=9.5)
    style_td_right = ParagraphStyle('VLTDRight', parent=style_td, alignment=TA_RIGHT)
    style_td_bold_right = ParagraphStyle('VLTDBoldRight', parent=style_td_right, fontName=FONT_BOLD)

    story = []

    # -----------------------------------------------------------------------
    # Section A: Header (Logo + Brand Title + Statement Banner)
    # -----------------------------------------------------------------------
    logo_path = get_logo_image_path()
    
    if logo_path:
        try:
            # Display branded logo
            img = Image(logo_path, width=150, height=45)
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Spacer(1, 4))
        except Exception as e:
            logger.warning(f"Could not insert logo image: {e}")
            story.append(Paragraph("VL SILKS", style_title))
            story.append(Paragraph("TRADITION MEETS FASHION", style_tagline))
    else:
        story.append(Paragraph("VL SILKS", style_title))
        story.append(Paragraph("TRADITION MEETS FASHION", style_tagline))

    story.append(Spacer(1, 3))
    story.append(Paragraph("CUSTOMER CREDIT / UDHAAR STATEMENT", style_doc_header))
    story.append(Spacer(1, 4))

    # Top Decorative Bar (Maroon & Gold)
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_PRIMARY_MAROON, spaceAfter=2, spaceBefore=2))
    story.append(HRFlowable(width="100%", thickness=0.75, color=COLOR_SECONDARY_GOLD, spaceAfter=6, spaceBefore=0))

    # -----------------------------------------------------------------------
    # Section B: Customer Details & Statement Info (Side-by-Side Table)
    # -----------------------------------------------------------------------
    cust_name = profile.get('customer_name', 'Customer')
    cust_phone = profile.get('phone', 'N/A')
    cust_email = profile.get('email', 'N/A') or 'N/A'
    cust_addr = profile.get('address', 'N/A') or 'N/A'
    cust_status = profile.get('status', 'ACTIVE')

    gen_time_str = datetime.now().strftime('%d-%b-%Y %I:%M %p')

    customer_info_cell = [
        Paragraph(f"<b>CUSTOMER DETAILS</b>", ParagraphStyle('SubHead', parent=style_bold, fontSize=8.5, leading=11, textColor=COLOR_PRIMARY_MAROON)),
        Spacer(1, 2),
        Paragraph(f"<b>Name:</b> {cust_name}", style_normal),
        Paragraph(f"<b>Customer ID:</b> #{profile['customer_id']} &nbsp; | &nbsp; <b>Status:</b> {cust_status}", style_normal),
        Paragraph(f"<b>Phone:</b> {cust_phone}", style_normal),
        Paragraph(f"<b>Email:</b> {cust_email}", style_normal),
        Paragraph(f"<b>Address:</b> {cust_addr}", style_normal),
    ]

    statement_info_cell = [
        Paragraph(f"<b>STATEMENT INFORMATION</b>", ParagraphStyle('SubHead2', parent=style_bold, fontSize=8.5, leading=11, textColor=COLOR_PRIMARY_MAROON)),
        Spacer(1, 2),
        Paragraph(f"<b>Statement Period:</b> {period_str}", style_normal),
        Paragraph(f"<b>Generated On:</b> {gen_time_str}", style_normal),
        Paragraph(f"<b>Store:</b> VL Silks Flagship Store", style_normal),
        Paragraph(f"<b>Currency:</b> Indian Rupee (INR / ₹)", style_normal),
        Paragraph(f"<b>Account Type:</b> Revolving Udhaar / Credit", style_normal),
    ]

    info_table = Table(
        [[customer_info_cell, statement_info_cell]],
        colWidths=[260, 263]
    )
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_CREAM_BG),
        ('BOX', (0, 0), (-1, -1), 0.75, COLOR_SECONDARY_GOLD),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8))

    # -----------------------------------------------------------------------
    # Section C: Financial Metric KPI Summary Cards
    # -----------------------------------------------------------------------
    credit_limit = profile.get('credit_limit', Decimal('0.00'))
    outstanding_bal = profile.get('outstanding_balance', Decimal('0.00'))
    available_credit = profile.get('available_credit', Decimal('0.00'))

    # Display Period Totals if date filter applied, else Lifetime Totals
    kpi_col1_title = "CREDIT LIMIT"
    kpi_col1_val = format_currency_pdf(credit_limit)

    kpi_col2_title = "PERIOD CHARGES (+)" if (d_from or d_to) else "TOTAL CREDIT (+)"
    kpi_col2_val = format_currency_pdf(period_credit if (d_from or d_to) else profile.get('total_credit_amount', Decimal('0.00')))

    kpi_col3_title = "PERIOD PAYMENTS (-)" if (d_from or d_to) else "TOTAL SETTLED (-)"
    kpi_col3_val = format_currency_pdf(period_paid if (d_from or d_to) else profile.get('total_paid_amount', Decimal('0.00')))

    kpi_col4_title = "BALANCE DUE"
    kpi_col4_val = format_currency_pdf(outstanding_bal)

    kpi_cell1 = [
        Paragraph(kpi_col1_title, ParagraphStyle('k1', parent=style_muted, alignment=TA_CENTER, fontSize=6.5, leading=8)),
        Spacer(1, 1),
        Paragraph(f"<b>{kpi_col1_val}</b>", ParagraphStyle('k1v', parent=style_bold, alignment=TA_CENTER, fontSize=10, leading=12, textColor=COLOR_CHARCOAL))
    ]
    kpi_cell2 = [
        Paragraph(kpi_col2_title, ParagraphStyle('k2', parent=style_muted, alignment=TA_CENTER, fontSize=6.5, leading=8)),
        Spacer(1, 1),
        Paragraph(f"<b>{kpi_col2_val}</b>", ParagraphStyle('k2v', parent=style_bold, alignment=TA_CENTER, fontSize=10, leading=12, textColor=COLOR_PRIMARY_MAROON))
    ]
    kpi_cell3 = [
        Paragraph(kpi_col3_title, ParagraphStyle('k3', parent=style_muted, alignment=TA_CENTER, fontSize=6.5, leading=8)),
        Spacer(1, 1),
        Paragraph(f"<b>{kpi_col3_val}</b>", ParagraphStyle('k3v', parent=style_bold, alignment=TA_CENTER, fontSize=10, leading=12, textColor=COLOR_SUCCESS_GREEN))
    ]
    kpi_cell4 = [
        Paragraph(kpi_col4_title, ParagraphStyle('k4', parent=style_muted, alignment=TA_CENTER, fontSize=6.5, leading=8)),
        Spacer(1, 1),
        Paragraph(f"<b>{kpi_col4_val}</b>", ParagraphStyle('k4v', parent=style_bold, alignment=TA_CENTER, fontSize=11, leading=13, textColor=COLOR_PRIMARY_MAROON))
    ]

    kpi_table = Table(
        [[kpi_cell1, kpi_cell2, kpi_cell3, kpi_cell4]],
        colWidths=[130, 131, 131, 131]
    )
    kpi_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (2, 0), COLOR_LIGHT_BG),
        ('BACKGROUND', (3, 0), (3, 0), COLOR_CREAM_BG),
        ('BOX', (0, 0), (-1, -1), 0.75, COLOR_BORDER_GRAY),
        ('BOX', (3, 0), (3, 0), 1.25, COLOR_PRIMARY_MAROON),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 8))

    # -----------------------------------------------------------------------
    # Section D: Chronological Transaction Ledger Table
    # -----------------------------------------------------------------------
    table_headers = [
        Paragraph("<b>Date</b>", style_th),
        Paragraph("<b>Type</b>", style_th),
        Paragraph("<b>Reference</b>", style_th),
        Paragraph("<b>Description / Notes</b>", style_th),
        Paragraph("<b>Debit (+)</b>", style_th_right),
        Paragraph("<b>Credit (-)</b>", style_th_right),
        Paragraph("<b>Balance</b>", style_th_right),
    ]

    ledger_rows = [table_headers]

    if filtered_ledger:
        for idx, row in enumerate(filtered_ledger):
            # Format Date
            tdate = row.get('transaction_date')
            if isinstance(tdate, (date, datetime)):
                date_display = tdate.strftime('%d-%b-%Y')
            elif isinstance(tdate, str):
                try:
                    dt_obj = datetime.strptime(tdate[:10], '%Y-%m-%d')
                    date_display = dt_obj.strftime('%d-%b-%Y')
                except ValueError:
                    date_display = str(tdate)
            else:
                date_display = "—"

            # Format Type
            ttype = row.get('transaction_type', '')
            if ttype == 'CREDIT_SALE':
                type_display = "CREDIT SALE"
            elif ttype == 'PAYMENT':
                type_display = "SETTLEMENT"
            elif ttype == 'RETURN_REFUND':
                type_display = "REFUND"
            else:
                type_display = ttype or "ADJUSTMENT"

            # Reference
            ref_str = row.get('invoice_number') or row.get('reference_number')
            if not ref_str:
                if row.get('sale_id'):
                    ref_str = f"Sale #{row['sale_id']}"
                elif row.get('payment_id'):
                    ref_str = f"Payment #{row['payment_id']}"
                else:
                    ref_str = f"TX #{row.get('transaction_id', '—')}"

            # Description
            notes = row.get('notes') or ''
            pay_method = row.get('payment_method')
            if pay_method and pay_method != 'None':
                desc = f"{pay_method} • {notes}" if notes else pay_method
            else:
                desc = notes or "Credit Transaction"

            # Debit / Credit / Running Balance
            debit_amt = to_decimal(row.get('debit_amount', Decimal('0.00')))
            credit_amt = to_decimal(row.get('credit_amount', Decimal('0.00')))
            running_bal = to_decimal(row.get('running_balance', Decimal('0.00')))

            debit_str = format_currency_pdf(debit_amt) if debit_amt > 0 else "—"
            credit_str = format_currency_pdf(credit_amt) if credit_amt > 0 else "—"
            bal_str = format_currency_pdf(running_bal)

            ledger_rows.append([
                Paragraph(date_display, style_td),
                Paragraph(type_display, style_td),
                Paragraph(ref_str, style_td),
                Paragraph(desc, style_td),
                Paragraph(debit_str, style_td_right),
                Paragraph(credit_str, style_td_right),
                Paragraph(bal_str, style_td_bold_right),
            ])

        # Summary Totals Row at the bottom of the table
        totals_row = [
            Paragraph("<b>TOTALS</b>", style_bold),
            Paragraph(f"<b>{len(filtered_ledger)} txs</b>", style_normal),
            Paragraph("—", style_td),
            Paragraph("<b>Period Totals</b>", style_normal),
            Paragraph(f"<b>{format_currency_pdf(period_credit)}</b>", style_td_bold_right),
            Paragraph(f"<b>{format_currency_pdf(period_paid)}</b>", style_td_bold_right),
            Paragraph(f"<b>{format_currency_pdf(outstanding_bal)}</b>", style_td_bold_right),
        ]
        ledger_rows.append(totals_row)

    else:
        # Empty Ledger Notification Row
        empty_msg = Paragraph("<i>No credit or settlement transactions found for this statement period.</i>", ParagraphStyle('EmptyMsg', parent=style_normal, alignment=TA_CENTER))
        ledger_rows.append([
            empty_msg, "", "", "", "", "", ""
        ])

    # Col Widths sum = 60 + 68 + 75 + 138 + 58 + 58 + 66 = 523 pt (Exact Printable Width)
    ledger_table = Table(
        ledger_rows,
        colWidths=[60, 68, 75, 138, 58, 58, 66],
        repeatRows=1
    )

    table_style_list = [
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY_MAROON),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER_GRAY),
    ]

    if not filtered_ledger:
        table_style_list.append(('SPAN', (0, 1), (-1, 1)))
        table_style_list.append(('BACKGROUND', (0, 1), (-1, 1), COLOR_LIGHT_BG))
        table_style_list.append(('TOPPADDING', (0, 1), (-1, 1), 12))
        table_style_list.append(('BOTTOMPADDING', (0, 1), (-1, 1), 12))
    else:
        # Alternating row background for readability
        for i in range(1, len(filtered_ledger) + 1):
            if i % 2 == 0:
                table_style_list.append(('BACKGROUND', (0, i), (-1, i), COLOR_LIGHT_BG))
        # Style Totals Row (Last Row)
        last_idx = len(ledger_rows) - 1
        table_style_list.append(('BACKGROUND', (0, last_idx), (-1, last_idx), COLOR_CREAM_BG))
        table_style_list.append(('LINEABOVE', (0, last_idx), (-1, last_idx), 1, COLOR_PRIMARY_MAROON))
        table_style_list.append(('LINEBELOW', (0, last_idx), (-1, last_idx), 1, COLOR_PRIMARY_MAROON))

    ledger_table.setStyle(TableStyle(table_style_list))
    story.append(ledger_table)
    story.append(Spacer(1, 10))

    # -----------------------------------------------------------------------
    # Section E: Terms & Settlement Instructions Box
    # -----------------------------------------------------------------------
    terms_content = [
        Paragraph("<b>PAYMENT & SETTLEMENT TERMS:</b>", ParagraphStyle('THead', parent=style_bold, fontSize=7.5, leading=9, textColor=COLOR_PRIMARY_MAROON)),
        Spacer(1, 1),
        Paragraph("1. Udhaar / Credit accounts must be settled within the agreed timeline. Payments can be made via Cash, UPI, or Card at the VL Silks billing counter.", style_muted),
        Paragraph("2. For any questions or balance reconciliation, please contact Store Management with your Customer ID and Invoice Reference.", style_muted),
        Paragraph("3. <i>This is an authentic computer-generated statement issued by the VL Silks Management System and is valid without physical signature.</i>", style_muted),
    ]
    terms_table = Table([[terms_content]], colWidths=[523])
    terms_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(KeepTogether([terms_table]))

    # 6. Build PDF with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    # 7. Generate Meaningful Filename
    clean_cust_name = sanitize_filename(cust_name)
    if d_from and d_to:
        filename = f"VL-Silks-Credit-Statement-{clean_cust_name}-ID{customer_id}-{d_from.strftime('%Y%m%d')}-{d_to.strftime('%Y%m%d')}.pdf"
    else:
        filename = f"VL-Silks-Credit-Statement-{clean_cust_name}-ID{customer_id}.pdf"

    return pdf_bytes, filename
