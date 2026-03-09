"""
Payment Gateways for Gearz On The Go
=====================================
Three options:
  Option 1: ToyyibPay — FPX / Online Banking (Malaysian banks)
  Option 2: Stripe    — Visa / Mastercard / Amex
  Option 3: Billplz   — FPX / DuitNow (Malaysian banks)

Configuration is via environment variables.
"""

import os
import hmac
import hashlib
import json
import requests
from urllib.parse import urlencode

# ─── Configuration ───────────────────────────────────────────────────────────

# Stripe config (sandbox by default)
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_PLACEHOLDER')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'pk_test_PLACEHOLDER')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', 'whsec_PLACEHOLDER')

# ToyyibPay config (live)
TOYYIBPAY_SECRET_KEY = os.environ.get('TOYYIBPAY_SECRET_KEY', '3v0bo8n2-p1km-ds7o-sz2x-8wi0lkkekjhs')
TOYYIBPAY_CATEGORY_CODE = os.environ.get('TOYYIBPAY_CATEGORY_CODE', '1q1z5uee')
TOYYIBPAY_BASE_URL = 'https://toyyibpay.com'  # Live

# Billplz config (sandbox by default)
BILLPLZ_API_KEY = os.environ.get('BILLPLZ_API_KEY', 'sandbox_PLACEHOLDER')
BILLPLZ_COLLECTION_ID = os.environ.get('BILLPLZ_COLLECTION_ID', 'sandbox_collection')
BILLPLZ_X_SIGNATURE_KEY = os.environ.get('BILLPLZ_X_SIGNATURE_KEY', 'sandbox_xsig')

# Billplz sandbox vs production
BILLPLZ_SANDBOX = os.environ.get('BILLPLZ_SANDBOX', 'true').lower() == 'true'
BILLPLZ_BASE_URL = 'https://www.billplz-sandbox.com/api' if BILLPLZ_SANDBOX else 'https://www.billplz.com/api'

# Dev mode: when True, simulates payment without calling real APIs
DEV_MODE = os.environ.get('PAYMENT_DEV_MODE', 'false').lower() == 'true'


def is_configured(gateway):
    """Check if a gateway has real API keys configured (not placeholder)."""
    if gateway == 'stripe':
        return 'PLACEHOLDER' not in STRIPE_SECRET_KEY
    elif gateway == 'billplz':
        return 'PLACEHOLDER' not in BILLPLZ_API_KEY
    elif gateway == 'toyyibpay':
        return TOYYIBPAY_SECRET_KEY and 'PLACEHOLDER' not in TOYYIBPAY_SECRET_KEY
    return False


# ─── Stripe Integration ─────────────────────────────────────────────────────

def stripe_create_checkout(booking, base_url):
    """
    Create a Stripe Checkout Session for deposit payment.

    Args:
        booking: dict with booking_ref, customer_name, customer_email,
                 deposit_amount, camera_name, days, start_date, end_date
        base_url: the app's public base URL (e.g. https://example.com)

    Returns:
        dict with 'checkout_url' on success, or 'error' on failure
    """
    booking_fee = 30  # RM30 booking fee (changed from deposit)
    booking_ref = booking['booking_ref']

    # Dev mode: return a simulated checkout URL
    if DEV_MODE or not is_configured('stripe'):
        return {
            'success': True,
            'checkout_url': f"{base_url}/payment/stripe/dev-checkout?booking_ref={booking_ref}",
            'session_id': f"cs_dev_{booking_ref}",
            'mode': 'dev'
        }

    # Real Stripe integration
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'myr',
                    'product_data': {
                        'name': f"Gearz On The Go Camera Booking Fee",
                        'description': f"Booking Fee {booking_ref} | {booking.get('camera_name', 'Camera')} | {booking.get('start_date')} → {booking.get('end_date')}",
                    },
                    'unit_amount': booking_fee * 100,  # Stripe uses cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{base_url}/payment/stripe/success?session_id={{CHECKOUT_SESSION_ID}}&booking_ref={booking_ref}",
            cancel_url=f"{base_url}/payment/stripe/cancel?booking_ref={booking_ref}",
            metadata={
                'booking_ref': booking_ref,
                'type': 'deposit',
            },
            customer_email=booking.get('customer_email') or None,
        )

        return {
            'success': True,
            'checkout_url': session.url,
            'session_id': session.id,
            'mode': 'live' if 'live' in STRIPE_SECRET_KEY else 'test'
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def stripe_verify_webhook(payload, sig_header):
    """
    Verify Stripe webhook signature and extract event data.

    Returns:
        dict with event data on success, or 'error' on failure
    """
    if DEV_MODE:
        return {'success': True, 'event': json.loads(payload), 'mode': 'dev'}

    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        return {'success': True, 'event': event}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def stripe_get_session(session_id):
    """Retrieve a Stripe Checkout Session to verify payment status."""
    if DEV_MODE:
        return {
            'success': True,
            'paid': True,
            'payment_intent': f"pi_dev_{session_id}",
            'mode': 'dev'
        }

    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        session = stripe.checkout.Session.retrieve(session_id)
        return {
            'success': True,
            'paid': session.payment_status == 'paid',
            'payment_intent': session.payment_intent,
            'amount_total': session.amount_total,
            'currency': session.currency,
            'metadata': dict(session.metadata),
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ─── Billplz Integration ────────────────────────────────────────────────────

def billplz_create_bill(booking, base_url):
    """
    Create a Billplz Bill for deposit payment via FPX/DuitNow.

    Args:
        booking: dict with booking_ref, customer_name, customer_email,
                 customer_phone, deposit_amount, camera_name
        base_url: the app's public base URL

    Returns:
        dict with 'bill_url' on success, or 'error' on failure
    """
    booking_fee = 30  # RM30 booking fee only
    booking_ref = booking['booking_ref']

    # Dev mode: return a simulated bill URL
    if DEV_MODE or not is_configured('billplz'):
        return {
            'success': True,
            'bill_url': f"{base_url}/payment/billplz/dev-checkout?booking_ref={booking_ref}",
            'bill_id': f"bill_dev_{booking_ref}",
            'mode': 'dev'
        }

    # Real Billplz integration
    try:
        # Prepare phone number (Billplz requires country code format)
        phone = booking.get('customer_phone', '')
        if phone and not phone.startswith('+'):
            if phone.startswith('0'):
                phone = '+6' + phone
            elif phone.startswith('6'):
                phone = '+' + phone

        data = {
            'collection_id': BILLPLZ_COLLECTION_ID,
            'description': f"Gearz On The Go Camera Booking Fee – RM30",
            'name': booking.get('customer_name', 'Customer'),
            'amount': booking_fee * 100,  # Billplz uses cents (RM30 booking fee)
            'callback_url': f"{base_url}/payment/billplz/callback",
            'redirect_url': f"{base_url}/payment/billplz/redirect",
            'reference_1_label': 'Booking Ref',
            'reference_1': booking_ref,
            'deliver': False,
        }

        # Add email or mobile (at least one required)
        email = booking.get('customer_email')
        if email:
            data['email'] = email
        if phone:
            data['mobile'] = phone
        if not email and not phone:
            data['email'] = 'customer@gearz.my'  # Fallback

        response = requests.post(
            f"{BILLPLZ_BASE_URL}/v3/bills",
            auth=(BILLPLZ_API_KEY, ''),
            data=data,
            timeout=15
        )

        if response.status_code in (200, 201):
            bill = response.json()
            return {
                'success': True,
                'bill_url': bill['url'],
                'bill_id': bill['id'],
                'mode': 'sandbox' if BILLPLZ_SANDBOX else 'production'
            }
        else:
            return {
                'success': False,
                'error': f"Billplz API error {response.status_code}: {response.text}"
            }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def billplz_verify_x_signature(data_dict, x_signature):
    """
    Verify Billplz X Signature from callback or redirect.

    Args:
        data_dict: dict of parameters (excluding x_signature)
        x_signature: the x_signature value to verify

    Returns:
        bool: True if signature is valid
    """
    if DEV_MODE:
        return True

    try:
        # Step 1: Extract key-value pairs, sort by key (case-insensitive)
        sorted_pairs = sorted(data_dict.items(), key=lambda x: x[0].lower())

        # Step 2: Construct source string: key + value concatenated
        source_parts = []
        for key, value in sorted_pairs:
            source_parts.append(f"{key}{value}")

        # Step 3: Join with pipe
        source_string = '|'.join(source_parts)

        # Step 4: Compute HMAC-SHA256
        computed = hmac.new(
            BILLPLZ_X_SIGNATURE_KEY.encode('utf-8'),
            source_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(computed, x_signature)

    except Exception:
        return False


def billplz_verify_redirect(params):
    """
    Verify and extract data from Billplz redirect URL parameters.

    Args:
        params: dict from request.args (e.g. billplz[id], billplz[paid], etc.)

    Returns:
        dict with bill_id, paid status, and verification result
    """
    bill_id = params.get('billplz[id]', '')
    paid = params.get('billplz[paid]', 'false').lower() == 'true'
    paid_at = params.get('billplz[paid_at]', '')
    x_signature = params.get('billplz[x_signature]', '')

    # Build data dict for verification (without x_signature)
    verify_data = {}
    for key, value in params.items():
        clean_key = key  # Keep the billplz[] format for verification
        if 'x_signature' not in key:
            verify_data[clean_key] = value

    verified = billplz_verify_x_signature(verify_data, x_signature)

    return {
        'bill_id': bill_id,
        'paid': paid,
        'paid_at': paid_at,
        'verified': verified,
    }


def billplz_verify_callback(form_data):
    """
    Verify and extract data from Billplz callback POST.

    Args:
        form_data: dict from request.form

    Returns:
        dict with bill details and verification result
    """
    x_signature = form_data.get('x_signature', '')

    # Build data dict for verification (without x_signature)
    verify_data = {k: v for k, v in form_data.items() if k != 'x_signature'}

    verified = billplz_verify_x_signature(verify_data, x_signature)

    return {
        'bill_id': form_data.get('id', ''),
        'collection_id': form_data.get('collection_id', ''),
        'paid': form_data.get('paid', 'false').lower() == 'true',
        'state': form_data.get('state', ''),
        'amount': int(form_data.get('amount', 0)),
        'paid_amount': int(form_data.get('paid_amount', 0)),
        'name': form_data.get('name', ''),
        'paid_at': form_data.get('paid_at', ''),
        'transaction_id': form_data.get('transaction_id', ''),
        'transaction_status': form_data.get('transaction_status', ''),
        'verified': verified,
    }


def billplz_get_bill(bill_id):
    """Retrieve a Billplz Bill to check payment status."""
    if DEV_MODE:
        return {
            'success': True,
            'paid': True,
            'state': 'paid',
            'mode': 'dev'
        }

    try:
        response = requests.get(
            f"{BILLPLZ_BASE_URL}/v3/bills/{bill_id}",
            auth=(BILLPLZ_API_KEY, ''),
            timeout=15
        )

        if response.status_code == 200:
            bill = response.json()
            return {
                'success': True,
                'paid': bill.get('paid', False),
                'state': bill.get('state', 'due'),
                'amount': bill.get('amount', 0),
                'paid_amount': bill.get('paid_amount', 0),
                'reference_1': bill.get('reference_1', ''),
            }
        else:
            return {'success': False, 'error': f"Billplz API error: {response.status_code}"}

    except Exception as e:
        return {'success': False, 'error': str(e)}


# ─── ToyyibPay Integration ─────────────────────────────────────────────────

def toyyibpay_create_bill(booking, base_url):
    """
    Create a ToyyibPay Bill for RM30 booking fee via FPX.

    Args:
        booking: dict with booking_ref, customer_name, customer_email,
                 customer_phone, camera_name, start_date, end_date
        base_url: the app's public base URL

    Returns:
        dict with 'bill_url' on success, or 'error' on failure
    """
    booking_fee = 30  # RM30 booking fee
    booking_ref = booking['booking_ref']

    try:
        # Prepare phone number
        phone = booking.get('customer_phone', '')
        if phone:
            phone = phone.replace(' ', '').replace('-', '')
            if phone.startswith('+'):
                phone = phone[1:]  # Remove +
            if phone.startswith('0'):
                phone = '6' + phone  # 0123 -> 60123
            if not phone.startswith('6'):
                phone = '60' + phone

        data = {
            'userSecretKey': TOYYIBPAY_SECRET_KEY,
            'categoryCode': TOYYIBPAY_CATEGORY_CODE,
            'billName': f'Booking {booking_ref}',
            'billDescription': f'Camera rental booking fee - {booking.get("camera_name", "Camera")} ({booking.get("start_date", "")} to {booking.get("end_date", "")})',
            'billPriceSetting': 1,  # Fixed price
            'billPayorInfo': 1,  # Include payor info
            'billAmount': booking_fee * 100,  # In cents: 3000 = RM30
            'billReturnUrl': f'{base_url}/payment/toyyibpay/return',
            'billCallbackUrl': f'{base_url}/payment/toyyibpay/callback',
            'billExternalReferenceNo': booking_ref,
            'billTo': booking.get('customer_name', 'Customer'),
            'billEmail': booking.get('customer_email', ''),
            'billPhone': phone,
            'billPaymentChannel': 0,  # 0=FPX only, 1=CC only, 2=both
            'billChargeToCustomer': 2,  # 2=charge FPX fee to customer (optional)
            'billExpiryDays': 3,  # Bill expires in 3 days
            'billContentEmail': f'Thank you for booking with Gearz On The Go. Your booking reference is {booking_ref}.',
        }

        response = requests.post(
            f'{TOYYIBPAY_BASE_URL}/index.php/api/createBill',
            data=data,
            timeout=15
        )

        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                bill_code = result[0].get('BillCode', '')
                if bill_code:
                    return {
                        'success': True,
                        'bill_url': f'{TOYYIBPAY_BASE_URL}/{bill_code}',
                        'bill_code': bill_code,
                        'mode': 'live'
                    }
            return {
                'success': False,
                'error': f'ToyyibPay returned unexpected response: {response.text}'
            }
        else:
            return {
                'success': False,
                'error': f'ToyyibPay API error {response.status_code}: {response.text}'
            }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def toyyibpay_verify_callback(form_data):
    """
    Verify ToyyibPay callback POST data.

    Callback params: refno, status, reason, billcode, order_id, amount, transaction_time
    Status: 1=success, 2=pending, 3=fail

    Returns:
        dict with payment details
    """
    return {
        'refno': form_data.get('refno', ''),
        'status': form_data.get('status', ''),
        'reason': form_data.get('reason', ''),
        'billcode': form_data.get('billcode', ''),
        'order_id': form_data.get('order_id', ''),
        'amount': form_data.get('amount', ''),
        'transaction_time': form_data.get('transaction_time', ''),
        'paid': form_data.get('status') == '1',
    }


def toyyibpay_get_bill_status(bill_code):
    """
    Get bill payment status from ToyyibPay.

    Returns:
        dict with bill status info
    """
    try:
        response = requests.post(
            f'{TOYYIBPAY_BASE_URL}/index.php/api/getBillTransactions',
            data={
                'billCode': bill_code,
                'billpaymentStatus': '1',  # 1=successful transactions
            },
            timeout=15
        )

        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return {
                    'success': True,
                    'paid': True,
                    'transaction': result[0],
                }
            return {
                'success': True,
                'paid': False,
                'transaction': None,
            }
        else:
            return {'success': False, 'error': f'API error: {response.status_code}'}

    except Exception as e:
        return {'success': False, 'error': str(e)}


# ─── Gateway Status ──────────────────────────────────────────────────────────

def get_gateway_status():
    """Return the configuration status of all gateways."""
    return {
        'toyyibpay': {
            'configured': is_configured('toyyibpay'),
            'mode': 'live',
        },
        'stripe': {
            'configured': is_configured('stripe'),
            'mode': 'dev' if DEV_MODE else ('live' if 'live' in STRIPE_SECRET_KEY else 'test'),
            'publishable_key': STRIPE_PUBLISHABLE_KEY if is_configured('stripe') else None,
        },
        'billplz': {
            'configured': is_configured('billplz'),
            'mode': 'dev' if DEV_MODE else ('sandbox' if BILLPLZ_SANDBOX else 'production'),
            'sandbox': BILLPLZ_SANDBOX,
        },
        'dev_mode': DEV_MODE,
    }
