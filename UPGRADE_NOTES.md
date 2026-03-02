# Upgrade Notes

## Key Changes Needed in app.py:
1. Add new tables: blocked_dates, payments + upgrade bookings with status/ref/deposit columns
2. Upgrade get_booked_dates() to also include blocked_dates and filter by booking status
3. New public API: GET /api/products, POST /api/bookings, POST /api/payments/deposit, GET /api/bookings/<ref>
4. New admin API: POST /staff/block-dates, POST /staff/booking/<id>/confirm, POST /staff/booking/<id>/returned
5. Keep ALL existing routes intact

## Key Changes Needed in index.html:
1. Replace WhatsApp "Tempah Sekarang" with real booking form
2. In availability checker result: show "Book Now" button that opens booking form
3. In modal result: same — replace WhatsApp with booking form
4. Add booking form modal (name, phone, IC, pickup time)
5. Add booking confirmation page/modal
6. Keep bilingual support

## Database Migration:
- Add columns to bookings: status, booking_ref, deposit_amount, deposit_status, pickup_time, return_time (some already exist)
- New table: blocked_dates (id, camera_id, start_date, end_date, reason, created_at)
- New table: payments (id, booking_id, booking_ref, amount, type, method, status, reference, created_at)
