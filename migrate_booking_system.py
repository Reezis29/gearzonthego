"""
Migration script: Upgrade database for real booking system.
Adds: booking status, booking_ref, deposit tracking, blocked_dates, payments tables.
Safe to run multiple times (uses IF NOT EXISTS / try-except for ALTER).
"""
import sqlite3
import os
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'bookings.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ── 1. Add new columns to bookings table ──
    new_booking_cols = [
        "status TEXT DEFAULT 'confirmed'",       # pending, confirmed, active, returned, cancelled
        "booking_ref TEXT",                       # unique ref like GZ-XXXXXX
        "deposit_amount REAL DEFAULT 200",
        "deposit_status TEXT DEFAULT 'unpaid'",   # unpaid, pending, paid, refunded
        "total_price REAL",
        "price_per_day REAL",
        "source TEXT DEFAULT 'staff'",            # staff, online
        "customer_email TEXT",
        "customer_ic TEXT",
    ]
    for col in new_booking_cols:
        try:
            c.execute(f"ALTER TABLE bookings ADD COLUMN {col}")
            print(f"  Added column to bookings: {col.split()[0]}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    # ── 2. Generate booking_ref for existing bookings that don't have one ──
    existing = c.execute("SELECT id FROM bookings WHERE booking_ref IS NULL OR booking_ref = ''").fetchall()
    for row in existing:
        ref = f"GZ-{uuid.uuid4().hex[:6].upper()}"
        c.execute("UPDATE bookings SET booking_ref = ?, status = 'confirmed' WHERE id = ?", (ref, row[0]))
        print(f"  Generated ref {ref} for booking #{row[0]}")

    # ── 3. Create blocked_dates table ──
    c.execute('''CREATE TABLE IF NOT EXISTS blocked_dates (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        camera_id   TEXT NOT NULL,
        start_date  TEXT NOT NULL,
        end_date    TEXT NOT NULL,
        reason      TEXT DEFAULT '',
        created_at  TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    print("  Table blocked_dates: OK")

    # ── 4. Create payments table ──
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id  INTEGER,
        booking_ref TEXT,
        amount      REAL NOT NULL,
        type        TEXT DEFAULT 'deposit',
        method      TEXT DEFAULT 'bank_transfer',
        status      TEXT DEFAULT 'pending',
        reference   TEXT,
        notes       TEXT,
        created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
        verified_at TEXT,
        verified_by TEXT
    )''')
    print("  Table payments: OK")

    conn.commit()
    conn.close()
    print("\nMigration complete!")

if __name__ == '__main__':
    migrate()
