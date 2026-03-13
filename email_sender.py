"""
email_sender.py — Send booking confirmation emails with PDF invoice via Brevo.
Uses Brevo (Sendinblue) transactional email API.
"""

import os
import base64
import logging
from invoice_generator import generate_invoice_bytes

logger = logging.getLogger(__name__)

BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')
SENDER_EMAIL  = 'orders@gearzonthego.com'
SENDER_NAME   = 'Gearz On The Go'
REPLY_TO_EMAIL = os.environ.get('REPLY_TO_EMAIL', 'gearetconline@gmail.com')
REPLY_TO_NAME  = 'Gearz On The Go Support'


def send_booking_confirmation_email(booking_data: dict) -> bool:
    """
    Send a booking confirmation email with PDF invoice to the customer.

    Returns True if sent successfully, False otherwise.
    """
    customer_email = booking_data.get('customer_email', '').strip()
    if not customer_email:
        logger.warning(f"No customer email for booking {booking_data.get('booking_ref')}. Skipping email.")
        return False

    if not BREVO_API_KEY:
        logger.error("BREVO_API_KEY not set. Cannot send email.")
        return False

    try:
        import sib_api_v3_sdk
        from sib_api_v3_sdk.rest import ApiException

        # Configure API key
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = BREVO_API_KEY

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        # Generate PDF invoice
        pdf_bytes = generate_invoice_bytes(booking_data)
        pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')

        ref = booking_data.get('booking_ref', 'N/A')
        camera = booking_data.get('camera_name', 'Camera')
        name = booking_data.get('customer_name', 'Customer')
        start = booking_data.get('start_date', '')
        end = booking_data.get('end_date', '')
        num_days = booking_data.get('num_days', 1)
        total_price = booking_data.get('total_price', 0)
        remaining = total_price - 30
        deposit = booking_data.get('deposit_amount', 200)
        pickup_time = booking_data.get('pickup_time', 'As arranged')

        # Build HTML email body
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 0; }}
  .container {{ max-width: 600px; margin: 20px auto; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
  .header {{ background: #1e1e1e; padding: 25px 30px; text-align: center; }}
  .header h1 {{ color: #FFA500; margin: 0; font-size: 24px; letter-spacing: 1px; }}
  .header p {{ color: #aaa; margin: 5px 0 0; font-size: 13px; }}
  .badge {{ background: #22c55e; color: white; text-align: center; padding: 12px; font-size: 18px; font-weight: bold; }}
  .body {{ padding: 30px; }}
  .ref-box {{ background: #f8f8f8; border-left: 4px solid #FFA500; padding: 15px 20px; margin-bottom: 25px; border-radius: 4px; }}
  .ref-box .ref {{ font-size: 22px; font-weight: bold; color: #1e1e1e; letter-spacing: 2px; }}
  .ref-box .label {{ font-size: 11px; color: #888; text-transform: uppercase; }}
  .section-title {{ font-size: 13px; font-weight: bold; color: #FFA500; text-transform: uppercase; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }}
  .info-item {{ background: #f8f8f8; padding: 10px 15px; border-radius: 6px; }}
  .info-item .label {{ font-size: 10px; color: #888; text-transform: uppercase; margin-bottom: 3px; }}
  .info-item .value {{ font-size: 14px; color: #1e1e1e; font-weight: 600; }}
  .payment-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
  .payment-table th {{ background: #1e1e1e; color: white; padding: 10px 12px; text-align: left; font-size: 12px; }}
  .payment-table td {{ padding: 10px 12px; font-size: 13px; border-bottom: 1px solid #eee; }}
  .payment-table tr:nth-child(even) td {{ background: #f8f8f8; }}
  .payment-table .total td {{ background: #1e1e1e; color: white; font-weight: bold; font-size: 14px; }}
  .paid-badge {{ background: #22c55e; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px; }}
  .location-box {{ background: #fff8e6; border: 1px solid #FFA500; border-radius: 8px; padding: 15px 20px; margin-bottom: 20px; }}
  .location-box .title {{ font-weight: bold; color: #b45309; margin-bottom: 5px; }}
  .reminder-box {{ background: #e6f4ff; border: 1px solid #64b4ff; border-radius: 8px; padding: 15px 20px; margin-bottom: 20px; }}
  .reminder-box .title {{ font-weight: bold; color: #0064b4; margin-bottom: 8px; }}
  .reminder-box ul {{ margin: 0; padding-left: 20px; font-size: 13px; color: #333; }}
  .reminder-box li {{ margin-bottom: 5px; }}
  .wa-btn {{ display: block; background: #25D366; color: white; text-align: center; padding: 14px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 15px; margin-bottom: 20px; }}
  .footer {{ background: #1e1e1e; padding: 20px 30px; text-align: center; }}
  .footer p {{ color: #888; font-size: 12px; margin: 5px 0; }}
  .footer a {{ color: #FFA500; text-decoration: none; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>GEARZ ON THE GO</h1>
    <p>Camera Rental Langkawi &bull; www.gearzonthego.com</p>
  </div>
  <div class="badge">&#x2705; BOOKING CONFIRMED!</div>
  <div class="body">
    <p style="font-size:15px; color:#333;">Hi <strong>{name}</strong>,</p>
    <p style="font-size:14px; color:#555;">Your camera rental booking has been confirmed. Your invoice is attached to this email as a PDF.</p>

    <div class="ref-box">
      <div class="label">Booking Reference</div>
      <div class="ref">{ref}</div>
    </div>

    <div class="section-title">Rental Details</div>
    <div class="info-grid">
      <div class="info-item">
        <div class="label">Camera</div>
        <div class="value">{camera}</div>
      </div>
      <div class="info-item">
        <div class="label">Duration</div>
        <div class="value">{num_days} day(s)</div>
      </div>
      <div class="info-item">
        <div class="label">Pickup Date</div>
        <div class="value">{start}</div>
      </div>
      <div class="info-item">
        <div class="label">Return Date</div>
        <div class="value">{end}</div>
      </div>
    </div>

    <div class="section-title">Payment Summary</div>
    <table class="payment-table">
      <tr><th>Description</th><th>Amount</th><th>Status</th></tr>
      <tr><td>Booking Fee (Online)</td><td>RM 30</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td>Remaining Rental (Pay at Pickup)</td><td>RM {remaining:.0f}</td><td>Due at Pickup</td></tr>
      <tr><td>Refundable Security Deposit</td><td>RM {deposit:.0f}</td><td>Due at Pickup</td></tr>
      <tr class="total"><td><strong>Total Due at Pickup</strong></td><td><strong>RM {(remaining + deposit):.0f}</strong></td><td></td></tr>
    </table>

    <div class="location-box">
      <div class="title">&#x1F4CD; Pickup Location</div>
      <p style="margin:0; font-size:13px; color:#555;">Gearz On The Go, Pantai Cenang, Langkawi, Kedah, Malaysia<br>
      <a href="https://maps.google.com/?q=Gearz+On+The+Go+Langkawi" style="color:#b45309;">View on Google Maps &rarr;</a></p>
    </div>

    <div class="reminder-box">
      <div class="title">&#x1F4CB; Important Reminders</div>
      <ul>
        <li>Bring your <strong>IC / Passport</strong> for verification at pickup</li>
        <li>RM200 security deposit is <strong>fully refundable</strong> upon safe return</li>
        <li>Contact us if you need to reschedule or have any questions</li>
      </ul>
    </div>

    <a href="https://wa.me/601115963866?text=Hi%2C+I+have+a+question+about+my+booking+{ref}" class="wa-btn">
      &#x1F4AC; WhatsApp Us for Support
    </a>

    <p style="font-size:12px; color:#888; text-align:center;">Your invoice PDF is attached to this email. Please keep it for your records.</p>
  </div>
  <div class="footer">
    <p><a href="https://www.gearzonthego.com">www.gearzonthego.com</a> &bull; WhatsApp: +60 11-1596 3866</p>
    <p>Pantai Cenang, Langkawi, Kedah, Malaysia</p>
    <p style="color:#555; font-size:11px;">This is an automated email. To reply, contact us via WhatsApp.</p>
  </div>
</div>
</body>
</html>
"""

        # Build email object
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": customer_email, "name": name}],
            sender={"email": SENDER_EMAIL, "name": SENDER_NAME},
            reply_to={"email": REPLY_TO_EMAIL, "name": REPLY_TO_NAME},
            subject=f"Booking Confirmed - {ref} | Gearz On The Go",
            html_content=html_content,
            attachment=[{
                "content": pdf_b64,
                "name": f"Invoice_{ref}_GearzOnTheGo.pdf"
            }]
        )

        api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Confirmation email sent to {customer_email} for booking {ref}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email for booking {booking_data.get('booking_ref')}: {e}")
        return False


def send_return_reminder_email(booking_data: dict) -> bool:
    """
    Send a 2-hour return reminder email to the customer.
    Called when the rental return time is within 2 hours.

    Returns True if sent successfully, False otherwise.
    """
    customer_email = booking_data.get('customer_email', '').strip()
    if not customer_email:
        logger.warning(f"No customer email for booking {booking_data.get('booking_ref')}. Skipping reminder.")
        return False

    if not BREVO_API_KEY:
        logger.error("BREVO_API_KEY not set. Cannot send reminder email.")
        return False

    try:
        import sib_api_v3_sdk
        from sib_api_v3_sdk.rest import ApiException

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = BREVO_API_KEY
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        ref    = booking_data.get('booking_ref', 'N/A')
        name   = booking_data.get('customer_name', 'Customer')
        camera = booking_data.get('camera_name', 'Camera')
        end    = booking_data.get('end_date', '')
        return_time = booking_data.get('return_time', '11:00 PM')
        # Use the full formatted return deadline if available
        return_date_display = booking_data.get('return_date_display', f'{end} at {return_time}')

        # Build accessories checklist rows
        accessories = booking_data.get('accessories', [])
        if not accessories and booking_data.get('accessories_json'):
            import json as _json
            try:
                accessories = _json.loads(booking_data['accessories_json'])
            except Exception:
                accessories = []

        accessories_checklist_html = ''
        if accessories:
            items_html = ''.join(
                f'<li style="margin-bottom:6px;">&#x2705; <strong>{acc.get("name", "")}</strong></li>'
                for acc in accessories
            )
            accessories_checklist_html = f"""
    <div class="section-title">&#x1F9E9; Return Checklist — Accessories</div>
    <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:15px 20px;margin-bottom:20px;">
      <p style="margin:0 0 8px;font-size:13px;color:#166534;font-weight:bold;">Please ensure ALL items below are returned:</p>
      <ul style="margin:0;padding-left:20px;font-size:13px;color:#333;">
        <li style="margin-bottom:6px;">&#x1F4F7; <strong>{camera}</strong> (main unit)</li>
        {items_html}
      </ul>
    </div>"""
        else:
            accessories_checklist_html = f"""
    <div class="section-title">&#x1F9E9; Return Checklist</div>
    <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:15px 20px;margin-bottom:20px;">
      <ul style="margin:0;padding-left:20px;font-size:13px;color:#333;">
        <li style="margin-bottom:6px;">&#x1F4F7; <strong>{camera}</strong> (main unit + all included accessories)</li>
      </ul>
    </div>"""

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 0; }}
  .container {{ max-width: 600px; margin: 20px auto; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
  .header {{ background: #1e1e1e; padding: 25px 30px; text-align: center; }}
  .header h1 {{ color: #FFA500; margin: 0; font-size: 24px; letter-spacing: 1px; }}
  .header p {{ color: #aaa; margin: 5px 0 0; font-size: 13px; }}
  .badge {{ background: #dc2626; color: white; text-align: center; padding: 12px; font-size: 18px; font-weight: bold; }}
  .body {{ padding: 30px; }}
  .ref-box {{ background: #f8f8f8; border-left: 4px solid #dc2626; padding: 15px 20px; margin-bottom: 25px; border-radius: 4px; }}
  .ref-box .ref {{ font-size: 22px; font-weight: bold; color: #1e1e1e; letter-spacing: 2px; }}
  .ref-box .label {{ font-size: 11px; color: #888; text-transform: uppercase; }}
  .section-title {{ font-size: 13px; font-weight: bold; color: #dc2626; text-transform: uppercase; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }}
  .info-item {{ background: #f8f8f8; padding: 10px 15px; border-radius: 6px; }}
  .info-item .label {{ font-size: 10px; color: #888; text-transform: uppercase; margin-bottom: 3px; }}
  .info-item .value {{ font-size: 14px; color: #1e1e1e; font-weight: 600; }}
  .deadline-box {{ background: #fef2f2; border: 2px solid #dc2626; border-radius: 10px; padding: 18px 20px; margin-bottom: 20px; text-align: center; }}
  .deadline-box .title {{ font-weight: bold; color: #991b1b; font-size: 14px; margin-bottom: 6px; }}
  .deadline-box .deadline {{ font-size: 22px; font-weight: bold; color: #dc2626; }}
  .warning-box {{ background: #fff7ed; border: 1px solid #f59e0b; border-radius: 8px; padding: 15px 20px; margin-bottom: 20px; }}
  .warning-box .title {{ font-weight: bold; color: #b45309; margin-bottom: 8px; font-size: 15px; }}
  .warning-box ul {{ margin: 0; padding-left: 20px; font-size: 13px; color: #555; }}
  .warning-box li {{ margin-bottom: 5px; }}
  .location-box {{ background: #fff8e6; border: 1px solid #FFA500; border-radius: 8px; padding: 15px 20px; margin-bottom: 20px; }}
  .location-box .title {{ font-weight: bold; color: #b45309; margin-bottom: 5px; }}
  .wa-btn {{ display: block; background: #25D366; color: white; text-align: center; padding: 14px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 15px; margin-bottom: 20px; }}
  .footer {{ background: #1e1e1e; padding: 20px 30px; text-align: center; }}
  .footer p {{ color: #888; font-size: 12px; margin: 5px 0; }}
  .footer a {{ color: #FFA500; text-decoration: none; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>GEARZ ON THE GO</h1>
    <p>Camera Rental Langkawi &bull; www.gearzonthego.com</p>
  </div>
  <div class="badge">&#x23F0; URGENT — RETURN IN 2 HOURS!</div>
  <div class="body">
    <p style="font-size:15px; color:#333;">Hi <strong>{name}</strong>,</p>
    <p style="font-size:14px; color:#555;">This is an urgent reminder — your camera rental is due for return in approximately <strong>2 hours</strong>. Please head back to our shop now to avoid late charges.</p>

    <div class="ref-box">
      <div class="label">Booking Reference</div>
      <div class="ref">{ref}</div>
    </div>

    <div class="section-title">Return Details</div>
    <div class="info-grid">
      <div class="info-item">
        <div class="label">Camera</div>
        <div class="value">{camera}</div>
      </div>
      <div class="info-item">
        <div class="label">Return Deadline</div>
        <div class="value" style="color:#dc2626;">{return_date_display}</div>
      </div>
    </div>

    <div class="deadline-box">
      <div class="title">&#x1F6A8; RETURN DEADLINE</div>
      <div class="deadline">{return_date_display}</div>
      <p style="margin:8px 0 0;font-size:12px;color:#991b1b;">You have approximately <strong>2 hours</strong> remaining. Please return now.</p>
    </div>

    {accessories_checklist_html}

    <div class="warning-box">
      <div class="title">&#x26A0;&#xFE0F; Avoid Late Charges</div>
      <ul>
        <li>Return the equipment <strong>before the deadline</strong> to avoid late fees</li>
        <li>Late returns are charged at the <strong>daily rental rate per additional day</strong></li>
        <li>Ensure <strong>all accessories</strong> listed above are returned together</li>
        <li>Equipment must be returned in the same condition as received</li>
        <li>Your <strong>RM200 security deposit</strong> will be refunded upon safe return</li>
      </ul>
    </div>

    <div class="location-box">
      <div class="title">&#x1F4CD; Return Location</div>
      <p style="margin:0; font-size:13px; color:#555;">Gearz On The Go, Pantai Cenang, Langkawi, Kedah, Malaysia<br>
      <strong>Operating Hours:</strong> 2:30 PM – 11:00 PM<br>
      <a href="https://maps.google.com/?q=Gearz+On+The+Go+Langkawi" style="color:#b45309;">View on Google Maps &rarr;</a></p>
    </div>

    <a href="https://wa.me/601115963866?text=Hi%2C+I+need+help+with+my+return+for+booking+{ref}" class="wa-btn">
      &#x1F4AC; Contact Us on WhatsApp
    </a>
    <p style="font-size:12px; color:#888; text-align:center;">Thank you for choosing Gearz On The Go. We hope you captured amazing memories! &#x1F4F8;</p>
  </div>
  <div class="footer">
    <p><a href="https://www.gearzonthego.com">www.gearzonthego.com</a> &bull; WhatsApp: +60 11-1596 3866</p>
    <p>Pantai Cenang, Langkawi, Kedah, Malaysia</p>
    <p style="color:#555; font-size:11px;">This is an automated reminder email.</p>
  </div>
</div>
</body>
</html>
"""

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": customer_email, "name": name}],
            sender={"email": SENDER_EMAIL, "name": SENDER_NAME},
            reply_to={"email": REPLY_TO_EMAIL, "name": REPLY_TO_NAME},
            subject=f"⏰ URGENT: Return Camera in 2 Hours — {ref} | Gearz On The Go",
            html_content=html_content
        )

        api_instance.send_transac_email(send_smtp_email)
        logger.info(f"2-hour return reminder email sent to {customer_email} for booking {ref}")
        return True

    except Exception as e:
        logger.error(f"Failed to send return reminder for booking {booking_data.get('booking_ref')}: {e}")
        return False


def send_pickup_confirmation_email(booking_data: dict) -> bool:
    """
    Send a pickup confirmation email to the customer after staff confirms equipment pickup.
    Contains camera details, accessories list, actual pickup time, and return deadline.

    Returns True if sent successfully, False otherwise.
    """
    customer_email = booking_data.get('customer_email', '').strip()
    if not customer_email:
        logger.warning(f"No customer email for booking {booking_data.get('booking_ref')}. Skipping pickup email.")
        return False

    if not BREVO_API_KEY:
        logger.error("BREVO_API_KEY not set. Cannot send pickup email.")
        return False

    try:
        import sib_api_v3_sdk

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = BREVO_API_KEY
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        ref         = booking_data.get('booking_ref', 'N/A')
        name        = booking_data.get('customer_name', 'Customer')
        camera      = booking_data.get('camera_name', 'Camera')
        start       = booking_data.get('start_date', '')
        end         = booking_data.get('end_date', '')
        days        = booking_data.get('days', 1)
        pickup_dt   = booking_data.get('actual_pickup_datetime', '') or booking_data.get('pickup_confirmed_at', '')
        return_deadline = booking_data.get('return_deadline_display', f'{end} by 11:00 PM')
        accessories = booking_data.get('accessories', [])  # list of dicts with name, price_per_day, total

        # Format pickup datetime nicely
        pickup_display = pickup_dt
        try:
            from datetime import datetime as _dt
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
                try:
                    pickup_display = _dt.strptime(pickup_dt, fmt).strftime('%d %b %Y, %I:%M %p')
                    break
                except Exception:
                    pass
        except Exception:
            pass

        # Build accessories rows HTML
        accessories_html = ''
        accessories_total = 0
        if accessories:
            rows = ''
            for acc in accessories:
                acc_name = acc.get('name', '')
                acc_ppd  = acc.get('price_per_day', 0)
                acc_days = acc.get('days', days)
                acc_tot  = acc.get('total', acc_ppd * acc_days)
                accessories_total += acc_tot
                rows += f'<tr><td style="padding:8px 12px;font-size:13px;border-bottom:1px solid #eee;">{acc_name}</td><td style="padding:8px 12px;font-size:13px;border-bottom:1px solid #eee;color:#7c3aed;">RM{acc_ppd}/day × {acc_days}</td><td style="padding:8px 12px;font-size:13px;border-bottom:1px solid #eee;font-weight:600;">RM{acc_tot:.0f}</td></tr>'
            accessories_html = f"""
    <div class="section-title">&#x1F9E9; Add-On Accessories</div>
    <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
      <tr style="background:#1e1e1e;"><th style="padding:8px 12px;color:white;text-align:left;font-size:12px;">Item</th><th style="padding:8px 12px;color:white;text-align:left;font-size:12px;">Rate</th><th style="padding:8px 12px;color:white;text-align:left;font-size:12px;">Total</th></tr>
      {rows}
      <tr style="background:#f3e8ff;"><td colspan="2" style="padding:8px 12px;font-weight:bold;font-size:13px;color:#7c3aed;">Accessories Total</td><td style="padding:8px 12px;font-weight:bold;font-size:13px;color:#7c3aed;">RM{accessories_total:.0f}</td></tr>
    </table>"""
        else:
            accessories_html = '<p style="font-size:13px;color:#888;margin-bottom:20px;">No accessories rented.</p>'

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 0; }}
  .container {{ max-width: 600px; margin: 20px auto; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
  .header {{ background: #1e1e1e; padding: 25px 30px; text-align: center; }}
  .header h1 {{ color: #FFA500; margin: 0; font-size: 24px; letter-spacing: 1px; }}
  .header p {{ color: #aaa; margin: 5px 0 0; font-size: 13px; }}
  .badge {{ background: #2563eb; color: white; text-align: center; padding: 12px; font-size: 18px; font-weight: bold; }}
  .body {{ padding: 30px; }}
  .ref-box {{ background: #f8f8f8; border-left: 4px solid #FFA500; padding: 15px 20px; margin-bottom: 25px; border-radius: 4px; }}
  .ref-box .ref {{ font-size: 22px; font-weight: bold; color: #1e1e1e; letter-spacing: 2px; }}
  .ref-box .label {{ font-size: 11px; color: #888; text-transform: uppercase; }}
  .section-title {{ font-size: 13px; font-weight: bold; color: #FFA500; text-transform: uppercase; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }}
  .info-item {{ background: #f8f8f8; padding: 10px 15px; border-radius: 6px; }}
  .info-item .label {{ font-size: 10px; color: #888; text-transform: uppercase; margin-bottom: 3px; }}
  .info-item .value {{ font-size: 14px; color: #1e1e1e; font-weight: 600; }}
  .return-box {{ background: #fef3c7; border: 2px solid #f59e0b; border-radius: 10px; padding: 18px 20px; margin-bottom: 20px; text-align: center; }}
  .return-box .title {{ font-weight: bold; color: #92400e; font-size: 14px; margin-bottom: 6px; }}
  .return-box .deadline {{ font-size: 20px; font-weight: bold; color: #b45309; }}
  .reminder-box {{ background: #e6f4ff; border: 1px solid #64b4ff; border-radius: 8px; padding: 15px 20px; margin-bottom: 20px; }}
  .reminder-box .title {{ font-weight: bold; color: #0064b4; margin-bottom: 8px; }}
  .reminder-box ul {{ margin: 0; padding-left: 20px; font-size: 13px; color: #333; }}
  .reminder-box li {{ margin-bottom: 5px; }}
  .wa-btn {{ display: block; background: #25D366; color: white; text-align: center; padding: 14px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 15px; margin-bottom: 20px; }}
  .footer {{ background: #1e1e1e; padding: 20px 30px; text-align: center; }}
  .footer p {{ color: #888; font-size: 12px; margin: 5px 0; }}
  .footer a {{ color: #FFA500; text-decoration: none; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>GEARZ ON THE GO</h1>
    <p>Camera Rental Langkawi &bull; www.gearzonthego.com</p>
  </div>
  <div class="badge">&#x1F4F7; EQUIPMENT PICKED UP — ENJOY YOUR ADVENTURE!</div>
  <div class="body">
    <p style="font-size:15px; color:#333;">Hi <strong>{name}</strong>,</p>
    <p style="font-size:14px; color:#555;">Your equipment has been successfully picked up. Here is a summary of what you have rented. Please keep this email for your records.</p>

    <div class="ref-box">
      <div class="label">Booking Reference</div>
      <div class="ref">{ref}</div>
    </div>

    <div class="section-title">&#x1F3A5; Equipment Details</div>
    <div class="info-grid">
      <div class="info-item">
        <div class="label">Camera</div>
        <div class="value">{camera}</div>
      </div>
      <div class="info-item">
        <div class="label">Duration</div>
        <div class="value">{days} day(s)</div>
      </div>
      <div class="info-item">
        <div class="label">Pickup Date</div>
        <div class="value">{start}</div>
      </div>
      <div class="info-item">
        <div class="label">Picked Up At</div>
        <div class="value">{pickup_display}</div>
      </div>
    </div>

    {accessories_html}

    <div class="return-box">
      <div class="title">&#x1F4C5; RETURN DEADLINE</div>
      <div class="deadline">{return_deadline}</div>
      <p style="margin:8px 0 0;font-size:12px;color:#92400e;">Please return all equipment by this date and time to avoid late charges.</p>
    </div>

    <div class="reminder-box">
      <div class="title">&#x1F4CB; Important Reminders</div>
      <ul>
        <li>Return the camera and <strong>all accessories</strong> listed above</li>
        <li>Handle equipment with care — avoid drops, water damage, and extreme heat</li>
        <li>Return the <strong>RM200 security deposit</strong> will be refunded upon safe return</li>
        <li>Late returns are charged at the daily rental rate per additional day</li>
        <li>Contact us immediately if the equipment is lost or damaged</li>
      </ul>
    </div>

    <a href="https://wa.me/601115963866?text=Hi%2C+I+have+a+question+about+my+rental+{ref}" class="wa-btn">
      &#x1F4AC; WhatsApp Us for Support
    </a>

    <p style="font-size:13px; color:#555; text-align:center;">Thank you for choosing <strong>Gearz On The Go</strong>. We hope you capture amazing memories! &#x1F4F8;</p>
  </div>
  <div class="footer">
    <p><a href="https://www.gearzonthego.com">www.gearzonthego.com</a> &bull; WhatsApp: +60 11-1596 3866</p>
    <p>Pantai Cenang, Langkawi, Kedah, Malaysia</p>
    <p style="color:#555; font-size:11px;">This is an automated email. To reply, contact us via WhatsApp.</p>
  </div>
</div>
</body>
</html>
"""

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": customer_email, "name": name}],
            sender={"email": SENDER_EMAIL, "name": SENDER_NAME},
            reply_to={"email": REPLY_TO_EMAIL, "name": REPLY_TO_NAME},
            subject=f"📷 Equipment Picked Up — {ref} | Gearz On The Go",
            html_content=html_content
        )

        api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Pickup confirmation email sent to {customer_email} for booking {ref}")
        return True

    except Exception as e:
        logger.error(f"Failed to send pickup confirmation email for booking {booking_data.get('booking_ref')}: {e}")
        return False
