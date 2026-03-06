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
    Send a 3-hour return reminder email to the customer.
    Called when the rental return time is within 3 hours.

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
  .badge {{ background: #f59e0b; color: white; text-align: center; padding: 12px; font-size: 18px; font-weight: bold; }}
  .body {{ padding: 30px; }}
  .ref-box {{ background: #f8f8f8; border-left: 4px solid #f59e0b; padding: 15px 20px; margin-bottom: 25px; border-radius: 4px; }}
  .ref-box .ref {{ font-size: 22px; font-weight: bold; color: #1e1e1e; letter-spacing: 2px; }}
  .ref-box .label {{ font-size: 11px; color: #888; text-transform: uppercase; }}
  .section-title {{ font-size: 13px; font-weight: bold; color: #f59e0b; text-transform: uppercase; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }}
  .info-item {{ background: #f8f8f8; padding: 10px 15px; border-radius: 6px; }}
  .info-item .label {{ font-size: 10px; color: #888; text-transform: uppercase; margin-bottom: 3px; }}
  .info-item .value {{ font-size: 14px; color: #1e1e1e; font-weight: 600; }}
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
  <div class="badge">&#x23F0; RETURN REMINDER — 3 HOURS LEFT</div>
  <div class="body">
    <p style="font-size:15px; color:#333;">Hi <strong>{name}</strong>,</p>
    <p style="font-size:14px; color:#555;">This is a friendly reminder that your camera rental is due for return in approximately <strong>3 hours</strong>. Please make sure to return the equipment on time to avoid late charges.</p>

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
        <div class="label">Return Date</div>
        <div class="value">{end}</div>
      </div>
      <div class="info-item">
        <div class="label">Return By</div>
        <div class="value">{return_time}</div>
      </div>
    </div>

    <div class="warning-box">
      <div class="title">&#x26A0;&#xFE0F; Important — Avoid Late Charges</div>
      <ul>
        <li>Please return the equipment <strong>before the deadline</strong> to avoid late fees</li>
        <li>Late returns will be charged at the daily rental rate per additional hour/day</li>
        <li>Ensure all accessories and memory cards are returned together</li>
        <li>Equipment must be returned in the same condition as received</li>
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
    <p style="font-size:12px; color:#888; text-align:center;">Thank you for choosing Gearz On The Go. We hope you captured amazing memories! 📸</p>
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
            subject=f"⏰ Return Reminder — {ref} | Gearz On The Go",
            html_content=html_content
        )

        api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Return reminder email sent to {customer_email} for booking {ref}")
        return True

    except Exception as e:
        logger.error(f"Failed to send return reminder for booking {booking_data.get('booking_ref')}: {e}")
        return False
