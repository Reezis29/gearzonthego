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
        f"Assalamualaikum / Hi Gearz On The Go 👋\n\n"
        f"Saya telah membuat tempahan dan bayar deposit.\n\n"
        f"📋 *Butiran Tempahan:*\n"
        f"• Rujukan: *{booking.get('booking_ref', '')}*\n"
        f"• Peranti: {booking.get('camera_name', '')}\n"
        f"• Tarikh: {booking.get('start_date', '')} → {booking.get('end_date', '')}\n"
        f"• Jumlah: RM{booking.get('total_price', 0):.0f}\n"
        f"• Deposit: RM{booking.get('deposit_amount', 200):.0f}\n\n"
        f"👤 *Maklumat Saya:*\n"
        f"• Nama: {booking.get('customer_name', '')}\n"
        f"• Telefon: {booking.get('customer_phone', '')}\n"
    )
    if booking.get('customer_email'):
        text += f"• Email: {booking['customer_email']}\n"
    text += (
        f"\n📎 *Bukti pembayaran dilampirkan di bawah.*\n"
        f"Mohon sahkan tempahan saya. Terima kasih! 🙏"
    )
    return wa_link(ADMIN_PHONE, text)


def customer_enquiry(booking):
    """Customer asks about their booking."""
    text = (
        f"Hai Gearz On The Go 👋\n\n"
        f"Saya nak tanya tentang tempahan saya:\n"
        f"• Rujukan: *{booking.get('booking_ref', '')}*\n"
        f"• Peranti: {booking.get('camera_name', '')}\n"
        f"• Tarikh: {booking.get('start_date', '')} → {booking.get('end_date', '')}\n\n"
    )
    return wa_link(ADMIN_PHONE, text)


def customer_pickup_enquiry(booking):
    """Customer asks about pickup details (for confirmed bookings)."""
    text = (
        f"Hai Gearz On The Go 👋\n\n"
        f"Tempahan saya *{booking.get('booking_ref', '')}* sudah disahkan.\n\n"
        f"Saya nak tanya tentang pengambilan peralatan:\n"
        f"• Peranti: {booking.get('camera_name', '')}\n"
        f"• Tarikh Ambil: {booking.get('start_date', '')}\n"
    )
    if booking.get('pickup_time'):
        text += f"• Masa Ambil: {booking['pickup_time']}\n"
    text += (
        f"\nBoleh saya datang ambil di outlet? "
        f"Terima kasih! 🙏"
    )
    return wa_link(ADMIN_PHONE, text)


# ═══════════════════════════════════════════════════════════════════════════════
# (b) ADMIN → CUSTOMER messages (shown on staff dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

def admin_remind_payment(booking, camera_name=''):
    """Admin reminds customer to pay deposit."""
    text = (
        f"Assalamualaikum {booking.get('customer_name', '')} 👋\n\n"
        f"Ini dari *Gearz On The Go* 📸\n\n"
        f"Kami perasan tempahan anda belum dibayar lagi:\n\n"
        f"📋 *Butiran Tempahan:*\n"
        f"• Rujukan: *{booking.get('booking_ref', '')}*\n"
        f"• Peranti: {camera_name or booking.get('camera_name', '')}\n"
        f"• Tarikh: {booking.get('start_date', '')} → {booking.get('end_date', '')}\n"
    )
    if booking.get('total_price'):
        text += f"• Jumlah: RM{booking['total_price']:.0f}\n"
    text += (
        f"• Deposit: RM{booking.get('deposit_amount', 200):.0f}\n\n"
        f"🏦 *Cara Bayar:*\n"
        f"• Bank: Maybank\n"
        f"• Nama: GEAR ETC SDN BHD\n"
        f"• No. Akaun: 552152001924\n"
        f"• Rujukan: {booking.get('booking_ref', '')}\n\n"
        f"Sila hantar bukti bayaran ke WhatsApp ini selepas transfer. "
        f"Terima kasih! 🙏"
    )
    phone = booking.get('customer_phone', '')
    return wa_link(phone, text)


def admin_confirm_booking(booking, camera_name=''):
    """Admin notifies customer that booking is confirmed."""
    text = (
        f"Assalamualaikum {booking.get('customer_name', '')} 👋\n\n"
        f"*Tempahan anda telah DISAHKAN!* ✅\n\n"
        f"📋 *Butiran Tempahan:*\n"
        f"• Rujukan: *{booking.get('booking_ref', '')}*\n"
        f"• Peranti: {camera_name or booking.get('camera_name', '')}\n"
        f"• Tarikh Ambil: {booking.get('start_date', '')}\n"
        f"• Tarikh Pulang: {booking.get('end_date', '')}\n"
    )
    if booking.get('pickup_time'):
        text += f"• Masa Ambil: {booking['pickup_time']}\n"
    text += (
        f"\n📍 *Lokasi Pickup:*\n"
        f"Gearz Gadget\n"
        f"No 6 Maliwalk, Jalan Pantai Cenang\n"
        f"07000 Langkawi, Kedah\n"
        f"Google Maps: https://maps.app.goo.gl/gearz\n\n"
        f"⏰ *Waktu Operasi:* 2:30 PM – 11:00 PM\n\n"
        f"Sila bawa IC/Passport semasa pengambilan.\n"
        f"Jumpa nanti! 😊"
    )
    phone = booking.get('customer_phone', '')
    return wa_link(phone, text)


def admin_pickup_reminder(booking, camera_name=''):
    """Admin reminds customer about upcoming pickup."""
    text = (
        f"Hai {booking.get('customer_name', '')} 👋\n\n"
        f"Ini peringatan dari *Gearz On The Go* 📸\n\n"
        f"Peralatan anda sedia untuk diambil:\n"
        f"• Peranti: {camera_name or booking.get('camera_name', '')}\n"
        f"• Tarikh Ambil: {booking.get('start_date', '')}\n"
    )
    if booking.get('pickup_time'):
        text += f"• Masa Ambil: {booking['pickup_time']}\n"
    text += (
        f"\n📍 Gearz Gadget, Jalan Pantai Cenang, Langkawi\n"
        f"⏰ Waktu Operasi: 2:30 PM – 11:00 PM\n\n"
        f"Sila bawa IC/Passport. Jumpa nanti! 😊"
    )
    phone = booking.get('customer_phone', '')
    return wa_link(phone, text)


def admin_return_reminder(booking, camera_name=''):
    """Admin reminds customer to return equipment."""
    text = (
        f"Hai {booking.get('customer_name', '')} 👋\n\n"
        f"Ini peringatan dari *Gearz On The Go* 📸\n\n"
        f"Sila pulangkan peralatan anda:\n"
        f"• Peranti: {camera_name or booking.get('camera_name', '')}\n"
        f"• Tarikh Pulang: {booking.get('end_date', '')}\n"
    )
    if booking.get('return_time'):
        text += f"• Masa Pulang: {booking['return_time']}\n"
    text += (
        f"\n📍 Gearz Gadget, Jalan Pantai Cenang, Langkawi\n"
        f"⏰ Waktu Operasi: 2:30 PM – 11:00 PM\n\n"
        f"Terima kasih kerana menyewa bersama kami! 🙏"
    )
    phone = booking.get('customer_phone', '')
    return wa_link(phone, text)


def admin_thank_you(booking, camera_name=''):
    """Admin sends thank you after equipment returned."""
    text = (
        f"Hai {booking.get('customer_name', '')} 👋\n\n"
        f"Terima kasih kerana menyewa bersama *Gearz On The Go*! 🎉\n\n"
        f"Kami harap anda puas hati dengan {camera_name or booking.get('camera_name', '')}.\n\n"
        f"Jika ada gambar/video best dari trip anda, "
        f"boleh tag kami di Instagram @gearzgadget 📸\n\n"
        f"Jumpa lagi di trip seterusnya! 😊\n"
        f"🌐 www.gearzgadget.com"
    )
    phone = booking.get('customer_phone', '')
    return wa_link(phone, text)


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN NOTIFICATION — new booking alert (admin clicks from dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

def admin_new_booking_alert(booking, camera_name=''):
    """Generate a self-notification link for admin about a new online booking."""
    text = (
        f"🔔 *TEMPAHAN BARU DITERIMA*\n\n"
        f"📋 *Butiran:*\n"
        f"• Rujukan: *{booking.get('booking_ref', '')}*\n"
        f"• Peranti: {camera_name or booking.get('camera_name', '')}\n"
        f"• Tarikh: {booking.get('start_date', '')} → {booking.get('end_date', '')}\n"
    )
    if booking.get('total_price'):
        text += f"• Jumlah: RM{booking['total_price']:.0f}\n"
    text += (
        f"• Deposit: RM{booking.get('deposit_amount', 200):.0f}\n\n"
        f"👤 *Pelanggan:*\n"
        f"• Nama: {booking.get('customer_name', '')}\n"
        f"• Telefon: {booking.get('customer_phone', '')}\n"
    )
    if booking.get('customer_email'):
        text += f"• Email: {booking['customer_email']}\n"
    text += (
        f"\n⏳ Status: Menunggu Bayaran\n"
        f"Sila pantau pembayaran deposit."
    )
    return wa_link(ADMIN_PHONE, text)
