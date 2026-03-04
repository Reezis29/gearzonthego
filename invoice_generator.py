"""
invoice_generator.py — Generate PDF invoices for Gearz On The Go bookings.
Uses fpdf2 to create a clean, professional invoice PDF.
"""

import os
import tempfile
from fpdf import FPDF
from datetime import datetime


class InvoicePDF(FPDF):
    def header(self):
        # Brand header
        self.set_fill_color(30, 30, 30)
        self.rect(0, 0, 210, 35, 'F')
        self.set_text_color(255, 165, 0)  # Orange
        self.set_font('Helvetica', 'B', 22)
        self.set_xy(10, 8)
        self.cell(0, 10, 'GEARZ ON THE GO', ln=False)
        self.set_text_color(200, 200, 200)
        self.set_font('Helvetica', '', 9)
        self.set_xy(10, 20)
        self.cell(0, 6, 'Camera Rental Langkawi  |  www.gearzonthego.com  |  WhatsApp: +60 11-1596 3866', ln=True)
        self.ln(5)

    def footer(self):
        self.set_y(-20)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, 'Thank you for choosing Gearz On The Go! We hope you capture amazing memories in Langkawi.', align='C')


def generate_invoice(booking_data: dict) -> str:
    """
    Generate a PDF invoice for a booking and return as bytes.

    booking_data keys:
        booking_ref, camera_name, customer_name, customer_phone, customer_email,
        start_date, end_date, num_days, price_per_day, total_price,
        booking_fee (30), remaining_rental, deposit_amount (200),
        pickup_time, return_time, created_at, status
    """
    pdf = InvoicePDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── Invoice Title & Reference ──────────────────────────────────────────────
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, 'BOOKING INVOICE', ln=True, align='C')
    pdf.ln(2)

    # Status badge
    status = booking_data.get('status', 'confirmed').upper()
    if status == 'CONFIRMED':
        pdf.set_fill_color(34, 197, 94)
    else:
        pdf.set_fill_color(251, 146, 60)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 8, f'  {status}  ', ln=True, align='C', fill=True)
    pdf.ln(4)

    # Invoice meta row
    pdf.set_text_color(80, 80, 80)
    pdf.set_font('Helvetica', '', 9)
    invoice_date = datetime.now().strftime('%d %B %Y, %I:%M %p')
    pdf.cell(95, 6, f"Invoice Date: {invoice_date}", ln=False)
    pdf.cell(95, 6, f"Booking Ref: {booking_data.get('booking_ref', 'N/A')}", ln=True, align='R')
    pdf.ln(4)

    # ── Divider ────────────────────────────────────────────────────────────────
    pdf.set_draw_color(230, 230, 230)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # ── Two-column: Customer Info & Rental Info ────────────────────────────────
    col_x1 = 10
    col_x2 = 110
    row_y = pdf.get_y()

    # Customer Info box
    pdf.set_fill_color(248, 248, 248)
    pdf.rect(col_x1, row_y, 95, 52, 'F')
    pdf.set_xy(col_x1 + 3, row_y + 3)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(255, 140, 0)
    pdf.cell(89, 6, 'CUSTOMER DETAILS', ln=True)
    pdf.set_text_color(50, 50, 50)
    pdf.set_font('Helvetica', '', 9)

    def info_row(label, value, x, w=89):
        pdf.set_x(x + 3)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(30, 5, label, ln=False)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(w - 30, 5, str(value or '-'), ln=True)

    info_row('Name', booking_data.get('customer_name', '-'), col_x1)
    info_row('Phone', booking_data.get('customer_phone', '-'), col_x1)
    info_row('Email', booking_data.get('customer_email', '-'), col_x1)

    # Rental Info box
    pdf.set_fill_color(248, 248, 248)
    pdf.rect(col_x2, row_y, 95, 52, 'F')
    pdf.set_xy(col_x2 + 3, row_y + 3)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(255, 140, 0)
    pdf.cell(89, 6, 'RENTAL DETAILS', ln=True)

    info_row('Camera', booking_data.get('camera_name', '-'), col_x2)
    info_row('Pickup', booking_data.get('start_date', '-'), col_x2)
    info_row('Return', booking_data.get('end_date', '-'), col_x2)
    info_row('Duration', f"{booking_data.get('num_days', 1)} day(s)", col_x2)
    if booking_data.get('pickup_time'):
        info_row('Time', booking_data.get('pickup_time', ''), col_x2)

    pdf.set_y(row_y + 58)

    # ── Pickup Location ────────────────────────────────────────────────────────
    pdf.set_fill_color(255, 248, 230)
    pdf.set_draw_color(255, 165, 0)
    pdf.rect(10, pdf.get_y(), 190, 16, 'FD')
    pdf.set_xy(13, pdf.get_y() + 3)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(180, 100, 0)
    pdf.cell(30, 5, 'Pickup Location:', ln=False)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 5, 'Gearz On The Go, Pantai Cenang, Langkawi, Kedah, Malaysia', ln=True)
    pdf.ln(8)

    # ── Payment Breakdown ──────────────────────────────────────────────────────
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, 'PAYMENT BREAKDOWN', ln=True)
    pdf.ln(2)

    # Table header
    pdf.set_fill_color(30, 30, 30)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(100, 8, '  Description', fill=True, ln=False)
    pdf.cell(45, 8, 'Details', fill=True, ln=False, align='C')
    pdf.cell(45, 8, 'Amount (RM)', fill=True, ln=True, align='R')

    # Row helper
    def table_row(desc, detail, amount, fill=False, bold=False):
        pdf.set_fill_color(245, 245, 245) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(50, 50, 50)
        pdf.set_font('Helvetica', 'B' if bold else '', 9)
        pdf.cell(100, 7, f'  {desc}', fill=True, ln=False)
        pdf.cell(45, 7, str(detail), fill=True, ln=False, align='C')
        pdf.cell(45, 7, f'RM {amount}', fill=True, ln=True, align='R')

    num_days = booking_data.get('num_days', 1)
    price_per_day = booking_data.get('price_per_day', 0)
    total_price = booking_data.get('total_price', 0)
    booking_fee = 30
    remaining = total_price - booking_fee
    deposit = booking_data.get('deposit_amount', 200)

    table_row(f"Camera Rental - {booking_data.get('camera_name', '')}", f"{num_days} day(s) x RM{price_per_day}", f"{total_price:.0f}", fill=False)
    table_row("Booking Fee (Paid Online)", "Paid [OK]", f"{booking_fee:.0f}", fill=True)
    table_row("Remaining Rental (Pay at Pickup)", f"RM{total_price:.0f} - RM{booking_fee}", f"{remaining:.0f}", fill=False)
    table_row("Refundable Security Deposit (Pay at Pickup)", "Returned after return", f"{deposit:.0f}", fill=True)

    # Total row
    pdf.set_fill_color(30, 30, 30)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(100, 9, '  TOTAL DUE AT PICKUP', fill=True, ln=False)
    pdf.cell(45, 9, '', fill=True, ln=False)
    pdf.cell(45, 9, f'RM {(remaining + deposit):.0f}', fill=True, ln=True, align='R')
    pdf.ln(6)

    # ── Notes ─────────────────────────────────────────────────────────────────
    pdf.set_fill_color(230, 245, 255)
    pdf.set_draw_color(100, 180, 255)
    pdf.rect(10, pdf.get_y(), 190, 28, 'FD')
    pdf.set_xy(13, pdf.get_y() + 3)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(0, 100, 180)
    pdf.cell(0, 5, 'IMPORTANT REMINDERS', ln=True)
    pdf.set_x(13)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(184, 5,
        "1. Please bring your IC / Passport for verification at pickup.\n"
        "2. RM200 security deposit is fully refundable upon safe return of equipment.\n"
        "3. Please arrive on time. Contact us on WhatsApp if you need to reschedule: +60 11-1596 3866"
    )
    pdf.ln(6)

    ref = booking_data.get('booking_ref', 'invoice')
    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix='.pdf',
        prefix=f'invoice_{ref}_'
    )
    tmp.close()
    pdf.output(tmp.name, 'F')
    return tmp.name


def generate_invoice_bytes(booking_data: dict) -> bytes:
    """Generate invoice and return as bytes for email attachment."""
    ref = booking_data.get('booking_ref', 'invoice')
    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix='.pdf',
        prefix=f'invoice_{ref}_'
    )
    tmp.close()
    # We need to regenerate since pdf object is consumed
    pdf2 = InvoicePDF()
    pdf2.add_page()
    pdf2.set_auto_page_break(auto=True, margin=20)
    # Re-run generation by calling generate_invoice and reading back
    path = generate_invoice(booking_data)
    with open(path, 'rb') as f:
        data = f.read()
    os.unlink(path)
    return data
