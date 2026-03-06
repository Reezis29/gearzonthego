"""
WhatsApp pre-filled message templates for Gearz On The Go.
Uses wa.me links with URL-encoded text — no paid API needed.
"""
from urllib.parse import quote

ADMIN_PHONE = "60124662939"  # Gearz On The Go admin WhatsApp

def wa_link(phone, text):
    """Generate a wa.me link with pre-filled text."""
    clean_phone = phone.replace('+', '').replace(' ', '').replace('-', '')
    return f"https://wa.me/{clean_phone}?text={quote(text)}"


# ═══════════════════════════════════════════════════════════════════════════════
# (a) CUSTOMER → ADMIN messages (shown on booking confirmation page)
# ═══════════════════════════════════════════════════════════════════════════════

def customer_send_payment_proof(booking):
    """Customer sends deposit payment proof to admin."""
    text = (
        f"Hi Gearz On The Go 👋\n\n"
        f"I have made a booking and paid the booking fee.\n\n"
        f"📋 *Booking Details:*\n"
        f"• Ref: *{booking.get('booking_ref', '')}*\n"
        f"• Device: {booking.get('camera_name', '')}\n"
        f"• Date: {booking.get('start_date', '')} → {booking.get('end_date', '')}\n"
        f"• Total: RM{booking.get('total_price', 0):.0f}\n"
        f"• Deposit: RM{booking.get('deposit_amount', 200):.0f}\n\n"
        f"👤 *My Details:*\n"
        f"• Name: {booking.get('customer_name', '')}\n"
        f"• Phone: {booking.get('customer_phone', '')}\n"
    )
    if booking.get('customer_email'):
        text += f"• Email: {booking['customer_email']}\n"
    text += (
        f"\n📎 *Payment proof attached below.*\n"
        f"Please confirm my booking. Thank you! 🙏"
    )
    return wa_link(ADMIN_PHONE, text)


def customer_enquiry(booking):
    """Customer asks about their booking."""
    text = (
        f"Hi Gearz On The Go 👋\n\n"
        f"I'd like to ask about my booking:\n"
        f"• Ref: *{booking.get('booking_ref', '')}*\n"
        f"• Device: {booking.get('camera_name', '')}\n"
        f"• Date: {booking.get('start_date', '')} → {booking.get('end_date', '')}\n\n"
    )
    return wa_link(ADMIN_PHONE, text)


def customer_pickup_enquiry(booking):
    """Customer asks about pickup details (for confirmed bookings)."""
    text = (
        f"Hi Gearz On The Go 👋\n\n"
        f"My booking *{booking.get('booking_ref', '')}* has been confirmed.\n\n"
        f"I'd like to ask about the equipment pickup:\n"
        f"• Device: {booking.get('camera_name', '')}\n"
        f"• Pickup Date: {booking.get('start_date', '')}\n"
    )
    if booking.get('pickup_time'):
        text += f"• Pickup Time: {booking['pickup_time']}\n"
    text += (
        f"\nCan I come pick it up at the outlet? "
        f"Thank you! 🙏"
    )
    return wa_link(ADMIN_PHONE, text)


# ═══════════════════════════════════════════════════════════════════════════════
# (b) ADMIN → CUSTOMER messages (shown on staff dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

def admin_remind_payment(booking, camera_name=''):
    """Admin reminds customer to pay deposit."""
    text = (
        f"Hi {booking.get('customer_name', '')} 👋\n\n"
        f"This is from *Gearz On The Go* 📸\n\n"
        f"We noticed your booking payment is still pending:\n\n"
        f"📋 *Booking Details:*\n"
        f"• Ref: *{booking.get('booking_ref', '')}*\n"
        f"• Device: {camera_name or booking.get('camera_name', '')}\n"
        f"• Date: {booking.get('start_date', '')} → {booking.get('end_date', '')}\n"
    )
    if booking.get('total_price'):
        text += f"• Total: RM{booking['total_price']:.0f}\n"
    text += (
        f"• Deposit: RM{booking.get('deposit_amount', 200):.0f}\n\n"
        f"🏦 *How to Pay:*\n"
        f"• Bank: Maybank\n"
        f"• Name: GEAR ETC SDN BHD\n"
        f"• Account No: 552152001924\n"
        f"• Reference: {booking.get('booking_ref', '')}\n\n"
        f"Please send proof of payment to this WhatsApp after transfer. "
        f"Thank you! 🙏"
    )
    phone = booking.get('customer_phone', '')
    return wa_link(phone, text)


def admin_confirm_booking(booking, camera_name=''):
    """Admin notifies customer that booking is confirmed."""
    text = (
        f"Hi {booking.get('customer_name', '')} 👋\n\n"
        f"*Your booking is CONFIRMED!* ✅\n\n"
        f"📋 *Booking Details:*\n"
        f"• Ref: *{booking.get('booking_ref', '')}*\n"
        f"• Device: {camera_name or booking.get('camera_name', '')}\n"
        f"• Pickup Date: {booking.get('start_date', '')}\n"
        f"• Return Date: {booking.get('end_date', '')}\n"
    )
    if booking.get('pickup_time'):
        text += f"• Pickup Time: {booking['pickup_time']}\n"
    text += (
        f"\n📍 *Pickup Location:*\n"
        f"Gearz Gadget\n"
        f"No 6 Maliwalk, Jalan Pantai Cenang\n"
        f"07000 Langkawi, Kedah\n"
        f"Google Maps: https://maps.app.goo.gl/gearz\n\n"
        f"⏰ *Operating Hours:* 2:30 PM – 11:00 PM\n\n"
        f"Please bring your IC/Passport during pickup.\n"
        f"See you soon! 😊"
    )
    phone = booking.get('customer_phone', '')
    return wa_link(phone, text)


def admin_pickup_reminder(booking, camera_name=''):
    """Admin reminds customer about upcoming pickup."""
    text = (
        f"Hi {booking.get('customer_name', '')} 👋\n\n"
        f"This is a reminder from *Gearz On The Go* 📸\n\n"
        f"Your equipment is ready for pickup:\n"
        f"• Device: {camera_name or booking.get('camera_name', '')}\n"
        f"• Pickup Date: {booking.get('start_date', '')}\n"
    )
    if booking.get('pickup_time'):
        text += f"• Pickup Time: {booking['pickup_time']}\n"
    text += (
        f"\n📍 Gearz Gadget, Jalan Pantai Cenang, Langkawi\n"
        f"⏰ Operating Hours: 2:30 PM – 11:00 PM\n\n"
        f"Please bring your IC/Passport. See you soon! 😊"
    )
    phone = booking.get('customer_phone', '')
    return wa_link(phone, text)


def admin_return_reminder(booking, camera_name=''):
    """Admin reminds customer to return equipment."""
    text = (
        f"Hi {booking.get('customer_name', '')} 👋\n\n"
        f"This is a reminder from *Gearz On The Go* 📸\n\n"
        f"Please return your equipment:\n"
        f"• Device: {camera_name or booking.get('camera_name', '')}\n"
        f"• Return Date: {booking.get('end_date', '')}\n"
    )
    if booking.get('return_time'):
        text += f"• Return Time: {booking['return_time']}\n"
    text += (
        f"\n📍 Gearz Gadget, Jalan Pantai Cenang, Langkawi\n"
        f"⏰ Operating Hours: 2:30 PM – 11:00 PM\n\n"
        f"Thank you for renting with us! 🙏"
    )
    phone = booking.get('customer_phone', '')
    return wa_link(phone, text)


def admin_thank_you(booking, camera_name=''):
    """Admin sends thank you after equipment returned."""
    text = (
        f"Hi {booking.get('customer_name', '')} 👋\n\n"
        f"Thank you for renting with *Gearz On The Go*! 🎉\n\n"
        f"We hope you enjoyed using the {camera_name or booking.get('camera_name', '')}.\n\n"
        f"If you have any great photos/videos from your trip, "
        f"feel free to tag us on Instagram @gearzgadget 📸\n\n"
        f"See you on your next adventure! 😊\n"
        f"🌐 www.gearzgadget.com"
    )
    phone = booking.get('customer_phone', '')
    return wa_link(phone, text)


def customer_booking_confirmed_with_invoice(booking, camera_name=''):
    """Auto-send to customer after RM30 booking fee paid — booking confirmed notification."""
    total = booking.get('total_price', 0)
    remaining = total - 30
    deposit = booking.get('deposit_amount', 200)
    text = (
        f"Hi {booking.get('customer_name', '')} 👋\n\n"
        f"*Your booking is CONFIRMED!* ✅\n"
        f"RM30 booking fee payment received.\n\n"
        f"📋 *Booking Details:*\n"
        f"• Ref: *{booking.get('booking_ref', '')}*\n"
        f"• Device: {camera_name or booking.get('camera_name', '')}\n"
        f"• Pickup Date: {booking.get('start_date', '')}\n"
        f"• Return Date: {booking.get('end_date', '')}\n"
    )
    if booking.get('pickup_time'):
        text += f"• Pickup Time: {booking['pickup_time']}\n"
    text += (
        f"\n💳 *Payment at Pickup:*\n"
        f"• Remaining Rental: RM{remaining:.0f}\n"
        f"• Deposit (refundable): RM{deposit:.0f}\n"
        f"• TOTAL: RM{(remaining + deposit):.0f}\n\n"
        f"📍 *Pickup Location:*\n"
        f"Gearz On The Go, Pantai Cenang, Langkawi\n\n"
        f"📧 Invoice has been sent to your email.\n\n"
        f"Please bring your IC/Passport during pickup.\n"
        f"See you soon! 😊"
    )
    phone = booking.get('customer_phone', '')
    return wa_link(phone, text)


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN NOTIFICATION — new booking alert (admin clicks from dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

def admin_new_booking_alert(booking, camera_name=''):
    """Generate a self-notification link for admin about a new online booking."""
    text = (
        f"🔔 *NEW BOOKING RECEIVED*\n\n"
        f"📋 *Details:*\n"
        f"• Ref: *{booking.get('booking_ref', '')}*\n"
        f"• Device: {camera_name or booking.get('camera_name', '')}\n"
        f"• Date: {booking.get('start_date', '')} → {booking.get('end_date', '')}\n"
    )
    if booking.get('total_price'):
        text += f"• Total: RM{booking['total_price']:.0f}\n"
    text += (
        f"• Deposit: RM{booking.get('deposit_amount', 200):.0f}\n\n"
        f"👤 *Customer:*\n"
        f"• Name: {booking.get('customer_name', '')}\n"
        f"• Phone: {booking.get('customer_phone', '')}\n"
    )
    if booking.get('customer_email'):
        text += f"• Email: {booking['customer_email']}\n"
    text += (
        f"\n⏳ Status: Payment Pending\n"
        f"Please monitor deposit payment."
    )
    return wa_link(ADMIN_PHONE, text)
