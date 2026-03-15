from flask import Flask, render_template, request, redirect, url_for, session, abort, flash, jsonify, send_from_directory
import sqlite3
import os
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from functools import wraps
from werkzeug.utils import secure_filename
import wa_messages as wa
import payment_gateways as pg
import threading

# Malaysia timezone (UTC+8)
MYT = ZoneInfo('Asia/Kuala_Lumpur')

def now_myt():
    """Return current datetime in Malaysia timezone (UTC+8)"""
    return datetime.now(MYT).replace(tzinfo=None)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'gearz_on_the_go_secret_2026')

# Use /data for Railway persistent volume, fallback to local for development
_data_dir = '/data' if os.path.isdir('/data') else os.path.dirname(__file__)
DB_PATH     = os.path.join(_data_dir, 'bookings.db')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'heic', 'webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─── Camera list ─────────────────────────────────────────────────────────────
CAMERAS = [
    {"id": "gopro11",        "name": "GoPro Hero 11 Black",            "category": "gopro",    "image": "gopro11.png",          "prices": {"1": 80,  "2": 70,  "3": 60,  "5": 50}},
    {"id": "gopro13",        "name": "GoPro Hero 13 Black",            "category": "gopro",    "image": "gopro13.png",          "prices": {"1": 85,  "2": 75,  "3": 65,  "5": 55}},
    {"id": "insta360x3",     "name": "Insta360 X3",                    "category": "insta360", "image": "insta360x3.jpg",       "prices": {"1": 85,  "2": 75,  "3": 65,  "5": 55}},
    {"id": "insta360x5",     "name": "Insta360 X5",                    "category": "insta360", "image": "insta360x5.jpg",       "prices": {"1": 100, "2": 90,  "3": 80,  "5": 70}},
    {"id": "insta360ace2",   "name": "Insta360 Ace Pro 2",             "category": "insta360", "image": "insta360acepro2.jpg",  "prices": {"1": 90,  "2": 80,  "3": 70,  "5": 60}},
    {"id": "insta360x4air",  "name": "Insta360 X4 Air",                "category": "insta360", "image": "insta360-x4-air.jpg",  "prices": {"1": 90,  "2": 80,  "3": 70,  "5": 60}},
    {"id": "dji_action5pro", "name": "DJI Osmo Action 5 Pro",          "category": "dji",      "image": "dji_action5pro.jpg",   "prices": {"1": 85,  "2": 75,  "3": 65,  "5": 55}},
    {"id": "dji_nano",       "name": "DJI Osmo Nano",                  "category": "dji",      "image": "dji_osmo_nano.jpg",    "prices": {"1": 80,  "2": 70,  "3": 60,  "5": 50}},
    {"id": "dji_360",        "name": "DJI Osmo 360",                   "category": "dji",      "image": "dji_osmo360.jpg",      "prices": {"1": 100, "2": 90,  "3": 80,  "5": 70}},
    {"id": "dji_mobile6",    "name": "DJI Osmo Mobile 6",              "category": "dji",      "image": "dji_osmo_mobile6.jpg", "prices": {"1": 30,  "2": 25,  "3": 20,  "5": 15}},
    {"id": "dji_pocket3",    "name": "DJI Osmo Pocket 3",              "category": "dji",      "image": "dji_osmo_pocket3.jpg", "prices": {"1": 110, "2": None,"3": None,"5": None}},
    {"id": "canon_t100",     "name": "Canon Rebel T100",               "category": "canon",    "image": "canon_t100.jpg",       "prices": {"1": 55,  "2": 50,  "3": 45,  "5": 40}},
    {"id": "canon_r50",      "name": "Canon R50",                      "category": "canon",    "image": "canon_r50.jpg",        "prices": {"1": 85,  "2": 75,  "3": 65,  "5": 55}},
    {"id": "canon_r7",       "name": "Canon EOS R7 + Sigma 150-600C",  "category": "canon",    "image": "canon_r7.jpg",         "prices": {"1": 320, "2": 300, "3": 280, "5": 260}},
    {"id": "dji_neo",        "name": "DJI Neo",                        "category": "drone",    "image": "dji_neo.jpg",          "prices": {"1": 70,  "2": 60,  "3": 50,  "5": 40}},
    {"id": "dji_neo2",       "name": "DJI Neo 2",                      "category": "drone",    "image": "dji_neo2.jpg",         "prices": {"1": 80,  "2": 70,  "3": 65,  "5": 55}},
    {"id": "dji_mini4pro",   "name": "DJI Mini 4 Pro",                 "category": "drone",    "image": "drone-mini4pro.jpg",   "prices": {"1": 280, "2": 260, "3": 240, "5": 220}},
    {"id": "yashica_digimate100", "name": "Yashica DigiMate 100",           "category": "compact",  "image": "yashica_digimate100.jpg", "prices": {"1": 25,  "2": 22,  "3": 19,  "5": 15}},
]
CAMERA_MAP = {c["id"]: c for c in CAMERAS}

# ─── Accessories catalogue ─────────────────────────────────────────────────
# Prices are per-day rates for tiers: 1 day / 2 days / 3-4 days / 5+ days
ACCESSORIES = [
    {"id": "x5_dive_case",      "name": "Dive Case Pro",                  "desc": "Perfect for snorkeling and underwater filming.",       "badge": "Best for snorkeling",       "image": "accessories/dive_case_360.png",  "prices": [25, 22, 19, 15], "inventory": 2, "camera_ids": ["insta360x5"],                                  "group": "Insta360"},
    {"id": "x5_moto_mount",     "name": "Motorcycle Mount",                "desc": "Secure 360° mount for motorbike handlebars.",         "badge": "Best for motorbike rides",  "image": "accessories/motorcycle_mount.jpg", "prices": [20, 18, 16, 14], "inventory": 2, "camera_ids": ["insta360x5", "insta360ace2", "dji_action5pro"], "group": "Insta360"},
    {"id": "x5_stick_1m",       "name": "1M Invisible Stick",              "desc": "Compact invisible selfie stick for 360° shots.",      "badge": "Most popular",              "image": "accessories/selfie_stick_1m.jpg",  "prices": [7, 6, 5, 4],     "inventory": 2, "camera_ids": ["insta360x5"],                                  "group": "Insta360"},
    {"id": "x5_stick_3m",       "name": "3M Long Invisible Selfie Stick",  "desc": "Extended reach for creative drone-like angles.",      "badge": "Best for creative angles",  "image": "accessories/selfie_stick_3m.jpg",  "prices": [10, 9, 7, 6],    "inventory": 2, "camera_ids": ["insta360x5"],                                  "group": "Insta360"},
    {"id": "x5_battery",        "name": "Extra Battery",                   "desc": "Spare battery for extended shooting sessions.",       "badge": "Most popular",              "image": "accessories/extra_battery.jpg",    "prices": [8, 7, 6, 5],     "inventory": 2, "camera_ids": ["insta360x5", "insta360ace2", "gopro13", "dji_action5pro"], "group": "Universal"},
    {"id": "ace2_dive_case",    "name": "Dive Case + Floaty",              "desc": "Waterproof housing with floaty for water sports.",    "badge": "Best for snorkeling",       "image": "accessories/dive_case_ace.jpg",    "prices": [15, 13, 11, 9],  "inventory": 2, "camera_ids": ["insta360ace2"],                                 "group": "Insta360"},
    {"id": "ace2_stick",        "name": "Selfie Stick",                    "desc": "Lightweight selfie stick for action cameras.",        "badge": "Most popular",              "image": "accessories/selfie_stick_1m.jpg",  "prices": [5, 4, 3, 2],     "inventory": 2, "camera_ids": ["insta360ace2", "gopro13", "dji_action5pro"],    "group": "Universal"},
    {"id": "gopro_dive_case",   "name": "Dive Case + Floaty",              "desc": "Waterproof housing with floaty for water sports.",    "badge": "Best for snorkeling",       "image": "accessories/dive_case_gopro.jpg",  "prices": [15, 13, 11, 9],  "inventory": 2, "camera_ids": ["gopro13"],                                     "group": "GoPro"},
    {"id": "gopro_chest",       "name": "Chest Mount",                     "desc": "Hands-free POV chest harness for action footage.",    "badge": "POV videos",                "image": "accessories/chest_mount.jpg",      "prices": [5, 4, 3, 2],     "inventory": 2, "camera_ids": ["gopro13"],                                     "group": "GoPro"},
    {"id": "dji_dive_case",     "name": "Dive Case + Floaty",              "desc": "Waterproof housing with floaty for water sports.",    "badge": "Best for snorkeling",       "image": "accessories/dive_case_ace.jpg",    "prices": [15, 13, 11, 9],  "inventory": 2, "camera_ids": ["dji_action5pro"],                               "group": "DJI"},
]
ACCESSORY_MAP = {a["id"]: a for a in ACCESSORIES}

def get_accessories_for_camera(camera_id):
    """Return list of accessories compatible with a given camera."""
    return [a for a in ACCESSORIES if camera_id in a.get('camera_ids', [])]

def get_accessory_price(accessory_id, days):
    """Return per-day price for an accessory based on rental duration tier."""
    acc = ACCESSORY_MAP.get(accessory_id)
    if not acc:
        return None
    prices = acc['prices']  # [tier1, tier2, tier3-4, tier5+]
    if days >= 5:
        return prices[3]
    elif days >= 3:
        return prices[2]
    elif days == 2:
        return prices[1]
    else:
        return prices[0]

# ─── DB init ──────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Bookings table
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        camera_id       TEXT NOT NULL,
        start_date      TEXT NOT NULL,
        end_date        TEXT NOT NULL,
        customer_name   TEXT,
        customer_phone  TEXT,
        notes           TEXT,
        customer_id     INTEGER,
        created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
        nationality     TEXT,
        customer_photo  TEXT,
        booking_mode    TEXT,
        pickup_time     TEXT,
        return_time     TEXT,
        status          TEXT DEFAULT 'pending',
        booking_ref     TEXT,
        deposit_amount  REAL DEFAULT 200,
        deposit_status  TEXT DEFAULT 'unpaid',
        total_price     REAL,
        price_per_day   REAL,
        source          TEXT DEFAULT 'staff',
        customer_email  TEXT,
        customer_ic     TEXT
    )''')

    # Blocked dates table
    c.execute('''CREATE TABLE IF NOT EXISTS blocked_dates (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        camera_id       TEXT NOT NULL,
        start_date      TEXT NOT NULL,
        end_date        TEXT NOT NULL,
        reason          TEXT,
        created_at      TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Payments table
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id      INTEGER,
        booking_ref     TEXT,
        amount          REAL,
        type            TEXT DEFAULT 'deposit',
        method          TEXT,
        status          TEXT DEFAULT 'pending',
        reference       TEXT,
        notes           TEXT,
        created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
        verified_at     TEXT,
        verified_by     TEXT
    )''')

    # Customers table
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name       TEXT NOT NULL,
        phone           TEXT NOT NULL,
        email           TEXT,
        nationality     TEXT,
        id_type         TEXT,
        id_number       TEXT,
        id_photo        TEXT,
        agreement_signed INTEGER DEFAULT 0,
        agreement_date  TEXT,
        notes           TEXT,
        created_at      TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Agreements table
    c.execute('''CREATE TABLE IF NOT EXISTS agreements (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name   TEXT NOT NULL,
        customer_phone  TEXT NOT NULL,
        ic_number       TEXT,
        equipment       TEXT NOT NULL,
        accessories     TEXT,
        pickup_date     TEXT NOT NULL,
        return_date     TEXT NOT NULL,
        deposit         REAL DEFAULT 200,
        signature_data  TEXT,
        signed_at       TEXT DEFAULT CURRENT_TIMESTAMP,
        booking_id      INTEGER,
        customer_id     INTEGER
    )''')

    # Units table — tracks individual physical units per product model
    c.execute('''CREATE TABLE IF NOT EXISTS units (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id      TEXT NOT NULL,
        serial_number   TEXT,
        label           TEXT NOT NULL,
        condition       TEXT DEFAULT 'good',
        status          TEXT DEFAULT 'available',
        notes           TEXT,
        created_at      TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Accessory bookings table (standalone accessory-only rentals)
    c.execute('''CREATE TABLE IF NOT EXISTS accessory_bookings (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_ref     TEXT NOT NULL,
        start_date      TEXT NOT NULL,
        end_date        TEXT NOT NULL,
        customer_name   TEXT,
        customer_phone  TEXT,
        customer_email  TEXT,
        customer_ic     TEXT,
        accessories_json TEXT,
        total_price     REAL,
        status          TEXT DEFAULT 'pending',
        deposit_amount  REAL DEFAULT 200,
        deposit_status  TEXT DEFAULT 'unpaid',
        created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
        source          TEXT DEFAULT 'online',
        customer_id     INTEGER
    )''')

    # Accessory inventory units table
    c.execute('''CREATE TABLE IF NOT EXISTS accessory_units (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        accessory_id    TEXT NOT NULL,
        label           TEXT NOT NULL,
        status          TEXT DEFAULT 'available',
        created_at      TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Safe migration: add unit_id to bookings if not present
    for col_def in [
        'unit_id INTEGER',
        'return_reminder_sent INTEGER DEFAULT 0',
        'actual_pickup_datetime TEXT',
        'accessories_json TEXT',
        'booking_type TEXT DEFAULT "ONLINE"',
        'payment_status TEXT DEFAULT "Paid Online"',
        'rental_status TEXT DEFAULT "Pending Pickup"',
        'pickup_confirmed_at TEXT',
        'return_processed_at TEXT',
        'checklist_json TEXT',
        'return_reminder_24h_sent INTEGER DEFAULT 0',
    ]:
        try:
            c.execute(f"ALTER TABLE bookings ADD COLUMN {col_def}")
        except:
            pass

    # Safe migration: add unit_id to blocked_dates if not present
    for col_def in ['unit_id INTEGER']:
        try:
            c.execute(f"ALTER TABLE blocked_dates ADD COLUMN {col_def}")
        except:
            pass

    # Safe migration: add pickup_time and return_time to agreements if not present
    for col_def in ['pickup_time TEXT', 'return_time TEXT']:
        try:
            c.execute(f"ALTER TABLE agreements ADD COLUMN {col_def}")
        except:
            pass

    # Seed 1 unit per product — also handles cameras added after initial seeding
    existing_product_ids = {row[0] for row in c.execute("SELECT DISTINCT product_id FROM units").fetchall()}
    for cam in CAMERAS:
        if cam['id'] not in existing_product_ids:
            c.execute(
                "INSERT INTO units (product_id, label, condition, status) VALUES (?, ?, 'good', 'available')",
                (cam['id'], 'Unit A')
            )

    # Seed 2 units per accessory if accessory_units table is empty
    existing_acc_units = c.execute("SELECT COUNT(*) FROM accessory_units").fetchone()[0]
    if existing_acc_units == 0:
        for acc in ACCESSORIES:
            for i in range(acc.get('inventory', 2)):
                c.execute(
                    "INSERT INTO accessory_units (accessory_id, label, status) VALUES (?, ?, 'available')",
                    (acc['id'], f'Unit {chr(65+i)}')
                )

    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)  # 10s timeout to avoid blocking
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')  # WAL mode allows concurrent reads
    conn.execute('PRAGMA busy_timeout=5000')  # 5s busy timeout
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

# ─── Auth ─────────────────────────────────────────────────────────────────────
STAFF_PASSWORD = "gearz2026"
STAFF_WALKIN_PIN = os.environ.get('STAFF_WALKIN_PIN', '1234')  # Walk-in booking authorization PIN

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('staff_login'))
        return f(*args, **kwargs)
    return decorated

# ─── Helper: unit-aware availability ──────────────────────────────────────────

def _date_range(start_str, end_str):
    """Return list of date strings between start and end (inclusive)."""
    start = datetime.strptime(start_str, '%Y-%m-%d')
    end   = datetime.strptime(end_str,   '%Y-%m-%d')
    dates = []
    d = start
    while d <= end:
        dates.append(d.strftime('%Y-%m-%d'))
        d += timedelta(days=1)
    return dates

def _get_unit_booked_dates(conn, unit_id):
    """Get all booked dates for a specific unit (from bookings + blocked_dates)."""
    rows = conn.execute(
        """SELECT start_date, end_date FROM bookings
           WHERE unit_id = ? AND (status IS NULL OR status NOT IN ('cancelled','returned'))""",
        (unit_id,)
    ).fetchall()
    dates = set()
    for row in rows:
        dates.update(_date_range(row['start_date'], row['end_date']))
    return dates

def _get_product_blocked_dates(conn, product_id, unit_id=None):
    """Get blocked dates. If unit_id is None on the block, it blocks ALL units."""
    if unit_id:
        blocks = conn.execute(
            "SELECT start_date, end_date FROM blocked_dates WHERE camera_id = ? AND (unit_id IS NULL OR unit_id = ?)",
            (product_id, unit_id)
        ).fetchall()
    else:
        blocks = conn.execute(
            "SELECT start_date, end_date FROM blocked_dates WHERE camera_id = ?",
            (product_id,)
        ).fetchall()
    dates = set()
    for row in blocks:
        dates.update(_date_range(row['start_date'], row['end_date']))
    return dates

def get_available_units(product_id, start_date, end_date):
    """Return list of unit dicts that are free for the requested date range.
    Each dict: {id, label, serial_number, condition}
    """
    conn = get_db()
    units = conn.execute(
        "SELECT * FROM units WHERE product_id = ? AND status = 'available'",
        (product_id,)
    ).fetchall()
    requested_dates = set(_date_range(start_date, end_date))
    available = []
    for unit in units:
        booked = _get_unit_booked_dates(conn, unit['id'])
        blocked = _get_product_blocked_dates(conn, product_id, unit['id'])
        unavailable = booked | blocked
        if not requested_dates & unavailable:
            available.append(dict(unit))
    conn.close()
    return available

def get_booked_dates(camera_id):
    """Legacy compatibility: return all dates where ALL units are booked.
    A date is 'booked' only if every available unit is occupied on that date.
    Used by the calendar view / simple availability check.
    """
    conn = get_db()
    units = conn.execute(
        "SELECT id FROM units WHERE product_id = ? AND status = 'available'",
        (camera_id,)
    ).fetchall()
    total_units = len(units)
    if total_units == 0:
        # No units registered — fall back to legacy booking-level check
        rows = conn.execute(
            """SELECT start_date, end_date FROM bookings
               WHERE camera_id = ? AND (status IS NULL OR status NOT IN ('cancelled','returned'))""",
            (camera_id,)
        ).fetchall()
        blocked = conn.execute(
            "SELECT start_date, end_date FROM blocked_dates WHERE camera_id = ?",
            (camera_id,)
        ).fetchall()
        conn.close()
        dates = set()
        for row in list(rows) + list(blocked):
            dates.update(_date_range(row['start_date'], row['end_date']))
        return list(dates)

    # Count bookings per date across all units
    from collections import Counter
    date_counts = Counter()
    for unit in units:
        booked = _get_unit_booked_dates(conn, unit['id'])
        blocked = _get_product_blocked_dates(conn, camera_id, unit['id'])
        for d in booked | blocked:
            date_counts[d] += 1
    conn.close()
    # A date is fully booked only if ALL units are occupied
    fully_booked = [d for d, count in date_counts.items() if count >= total_units]
    return fully_booked

def generate_booking_ref():
    """Generate unique booking reference like GZ-A1B2C3"""
    return f"GZ-{uuid.uuid4().hex[:6].upper()}"

def get_accessory_booked_count(accessory_id, start_date, end_date):
    """Return how many units of an accessory are booked for the given date range.
    Checks both camera bookings (add-ons) and standalone accessory bookings."""
    import json
    conn = get_db()
    requested = set(_date_range(start_date, end_date))
    count = 0

    # Check camera bookings with accessories_json
    rows = conn.execute(
        """SELECT accessories_json, start_date, end_date FROM bookings
           WHERE accessories_json IS NOT NULL AND accessories_json != ''
           AND (status IS NULL OR status NOT IN ('cancelled','returned'))"""
    ).fetchall()
    for row in rows:
        try:
            accs = json.loads(row['accessories_json'])
        except:
            continue
        for acc in accs:
            if acc.get('id') == accessory_id:
                booked_dates = set(_date_range(row['start_date'], row['end_date']))
                if requested & booked_dates:
                    count += 1
                break

    # Check standalone accessory bookings
    acc_rows = conn.execute(
        """SELECT accessories_json, start_date, end_date FROM accessory_bookings
           WHERE (status IS NULL OR status NOT IN ('cancelled','returned'))"""
    ).fetchall()
    for row in acc_rows:
        try:
            accs = json.loads(row['accessories_json'])
        except:
            continue
        for acc in accs:
            if acc.get('id') == accessory_id:
                booked_dates = set(_date_range(row['start_date'], row['end_date']))
                if requested & booked_dates:
                    count += 1
                break

    conn.close()
    return count

def get_accessory_availability(accessory_id, start_date, end_date):
    """Return dict with available_units and total_units for an accessory."""
    acc = ACCESSORY_MAP.get(accessory_id)
    if not acc:
        return {'available_units': 0, 'total_units': 0}
    total = acc.get('inventory', 2)
    booked = get_accessory_booked_count(accessory_id, start_date, end_date)
    available = max(0, total - booked)
    return {'available_units': available, 'total_units': total}

def calculate_price(camera_id, days):
    """Calculate price per day and total based on tier pricing"""
    camera = CAMERA_MAP.get(camera_id, {})
    prices = camera.get('prices', {})
    if days >= 5:
        price_key = '5'
    else:
        price_key = str(days)
    ppd = prices.get(price_key)
    if ppd is None:
        return None, None
    return ppd, ppd * days

# ─── Public Routes ────────────────────────────────────────────────────────────
@app.route('/')
def index():
    # Build availability_map for urgency indicators (units available today)
    today = now_myt().strftime('%Y-%m-%d')
    tomorrow = (now_myt() + timedelta(days=1)).strftime('%Y-%m-%d')
    availability_map = {}
    try:
        conn = get_db()
        for cam in CAMERAS:
            avail_units = get_available_units(cam['id'], today, tomorrow)
            total_units = conn.execute(
                "SELECT COUNT(*) FROM units WHERE product_id = ? AND status = 'available'",
                (cam['id'],)
            ).fetchone()[0]
            availability_map[cam['id']] = {
                'available_units': len(avail_units),
                'total_units': total_units
            }
        conn.close()
    except Exception:
        pass
    return render_template('index.html', cameras=CAMERAS, availability_map=availability_map)

@app.route('/api/availability/<camera_id>')
def api_availability(camera_id):
    if camera_id not in CAMERA_MAP:
        return jsonify({'error': 'Camera not found'}), 404
    return jsonify({'camera_id': camera_id, 'booked_dates': get_booked_dates(camera_id)})

@app.route('/api/accessories/<camera_id>')
def api_accessories_for_camera(camera_id):
    """Return accessories available for a camera model with pricing for given days."""
    days = request.args.get('days', 1, type=int)
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    accs = get_accessories_for_camera(camera_id)
    result = []
    for a in accs:
        ppd = get_accessory_price(a['id'], days)
        avail = {'available_units': a.get('inventory', 2), 'total_units': a.get('inventory', 2)}
        if start_date and end_date:
            avail = get_accessory_availability(a['id'], start_date, end_date)
        result.append({
            'id': a['id'],
            'name': a['name'],
            'desc': a['desc'],
            'badge': a['badge'],
            'image': a['image'],
            'prices': a['prices'],
            'price_per_day': ppd,
            'total': ppd * days if ppd else 0,
            'available_units': avail['available_units'],
            'total_units': avail['total_units'],
        })
    return jsonify({'accessories': result, 'days': days, 'camera_id': camera_id})

@app.route('/api/accessories/all')
def api_all_accessories():
    """Return all accessories grouped by compatibility."""
    days = request.args.get('days', 1, type=int)
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    result = []
    for a in ACCESSORIES:
        ppd = get_accessory_price(a['id'], days)
        avail = {'available_units': a.get('inventory', 2), 'total_units': a.get('inventory', 2)}
        if start_date and end_date:
            avail = get_accessory_availability(a['id'], start_date, end_date)
        result.append({
            'id': a['id'],
            'name': a['name'],
            'desc': a['desc'],
            'badge': a['badge'],
            'image': a['image'],
            'prices': a['prices'],
            'price_per_day': ppd,
            'total': ppd * days if ppd else 0,
            'group': a.get('group', ''),
            'camera_ids': a.get('camera_ids', []),
            'available_units': avail['available_units'],
            'total_units': avail['total_units'],
        })
    return jsonify({'accessories': result, 'days': days})

@app.route('/accessories')
def accessories_page():
    """Standalone accessories rental page."""
    return render_template('accessories.html', accessories=ACCESSORIES, accessory_map=ACCESSORY_MAP)

@app.route('/api/accessory-bookings', methods=['POST'])
def api_create_accessory_booking():
    """Create a standalone accessory-only booking."""
    import json as _json
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    start_date = data.get('start_date', '').strip()
    end_date   = data.get('end_date', '').strip()
    cust_name  = data.get('customer_name', '').strip()
    cust_phone = data.get('customer_phone', '').strip()
    cust_email = data.get('customer_email', '').strip()
    cust_ic    = data.get('customer_ic', '').strip()
    accessories_list = data.get('accessories', [])

    if not all([start_date, end_date, cust_name, cust_phone]):
        return jsonify({'error': 'Required: start_date, end_date, customer_name, customer_phone'}), 400
    if not cust_email:
        return jsonify({'error': 'Email address is required.'}), 400
    if not accessories_list:
        return jsonify({'error': 'At least one accessory must be selected.'}), 400

    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end   = datetime.strptime(end_date,   '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format.'}), 400
    if end < start:
        return jsonify({'error': 'End date must be after start date'}), 400

    days = (end - start).days
    if days < 1:
        days = 1

    # Validate and price accessories
    validated_accs = []
    total = 0
    for acc_item in accessories_list:
        acc_id = acc_item.get('id', '')
        acc_data = ACCESSORY_MAP.get(acc_id)
        if acc_data:
            ppd_acc = get_accessory_price(acc_id, days)
            if ppd_acc is not None:
                avail = get_accessory_availability(acc_id, start_date, end_date)
                if avail['available_units'] <= 0:
                    return jsonify({'error': f'{acc_data["name"]} is not available for selected dates.'}), 409
                acc_total = ppd_acc * days
                validated_accs.append({
                    'id': acc_id,
                    'name': acc_data['name'],
                    'price_per_day': ppd_acc,
                    'days': days,
                    'total': acc_total
                })
                total += acc_total

    if not validated_accs:
        return jsonify({'error': 'No valid accessories selected.'}), 400

    booking_ref = generate_booking_ref()
    accessories_json = _json.dumps(validated_accs)

    conn = get_db()

    # Auto-create customer record
    customer_id = None
    if cust_name and cust_phone:
        existing = conn.execute(
            "SELECT id FROM customers WHERE phone = ? AND LOWER(full_name) = LOWER(?)",
            (cust_phone, cust_name)
        ).fetchone()
        if existing:
            customer_id = existing['id']
        else:
            cur = conn.execute(
                "INSERT INTO customers (full_name, phone, email, created_at) VALUES (?, ?, ?, ?)",
                (cust_name, cust_phone, cust_email, now_myt().strftime('%Y-%m-%d %H:%M'))
            )
            customer_id = cur.lastrowid
        conn.commit()

    conn.execute(
        """INSERT INTO accessory_bookings
           (booking_ref, start_date, end_date, customer_name, customer_phone,
            customer_email, customer_ic, accessories_json, total_price,
            status, deposit_amount, deposit_status, source, customer_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (booking_ref, start_date, end_date, cust_name, cust_phone,
         cust_email, cust_ic, accessories_json, total,
         'pending', 200, 'unpaid', 'online', customer_id)
    )
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'booking_ref': booking_ref,
        'total_price': total,
        'accessories': validated_accs,
        'days': days,
        'booking_fee': 30,
        'message': f'Accessory booking {booking_ref} created. Pay RM30 to confirm.'
    }), 201

@app.route('/api/check')
def api_check():
    camera_id  = request.args.get('camera_id')
    start_date = request.args.get('start_date')
    end_date   = request.args.get('end_date')
    if not all([camera_id, start_date, end_date]):
        return jsonify({'error': 'Missing parameters'}), 400

    try:
        # Unit-aware availability check
        avail_units = get_available_units(camera_id, start_date, end_date)
        available = len(avail_units) > 0

        start = datetime.strptime(start_date, '%Y-%m-%d')
        end   = datetime.strptime(end_date,   '%Y-%m-%d')
        days = (end - start).days
        if days < 1:
            days = 1
        camera = CAMERA_MAP.get(camera_id, {})
        price_key = "5" if days >= 5 else str(days)
        price_per_day = camera.get('prices', {}).get(price_key)
        total = price_per_day * days if price_per_day else None

        # Get total units for this product
        conn = get_db()
        try:
            total_units = conn.execute(
                "SELECT COUNT(*) FROM units WHERE product_id = ? AND status = 'available'",
                (camera_id,)
            ).fetchone()[0]
        finally:
            conn.close()

        # Build conflicts list when not available
        conflicts = []
        if not available:
            booked_dates = get_booked_dates(camera_id)
            requested = set(_date_range(start_date, end_date))
            conflict_dates = sorted(requested & set(booked_dates))
            # Format dates nicely for display
            conflicts = [datetime.strptime(d, '%Y-%m-%d').strftime('%d %b %Y') for d in conflict_dates]
            if not conflicts:
                # Fallback: show the full requested range
                conflicts = [f"{datetime.strptime(start_date, '%Y-%m-%d').strftime('%d %b')} - {datetime.strptime(end_date, '%Y-%m-%d').strftime('%d %b %Y')}"]

        return jsonify({
            'available': available,
            'available_units': len(avail_units),
            'total_units': total_units,
            'days': days,
            'price_per_day': price_per_day,
            'total_price': total,
            'camera_name': camera.get('name', ''),
            'conflicts': conflicts
        })
    except Exception as e:
        app.logger.error(f'api_check error: {e}')
        return jsonify({'error': 'Server error', 'message': str(e)}), 500

# ─── Staff Login/Logout ───────────────────────────────────────────────────────
@app.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == STAFF_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('staff_dashboard'))
        error = "Password salah. Cuba lagi."
    return render_template('staff_login.html', error=error)

@app.route('/staff/logout')
def staff_logout():
    session.clear()
    return redirect(url_for('staff_login'))

# ─── Staff Dashboard (Bookings) ───────────────────────────────────────────────
@app.route('/staff')
@login_required
def staff_dashboard():
    import json as _json
    conn = get_db()
    bookings = conn.execute(
        """SELECT b.*, c.full_name as cust_name, c.phone as cust_phone2,
                  u.label as unit_label, u.serial_number as unit_serial,
                  ag.id as agreement_id
           FROM bookings b
           LEFT JOIN customers c ON b.customer_id = c.id
           LEFT JOIN units u ON b.unit_id = u.id
           LEFT JOIN agreements ag ON (
               ag.customer_phone = b.customer_phone
               AND ag.pickup_date = b.start_date
           )
           ORDER BY b.start_date ASC"""
    ).fetchall()
    customers = conn.execute("SELECT id, full_name, phone FROM customers ORDER BY full_name ASC").fetchall()

    # Due today: bookings where end_date is today and rental_status is Picked Up
    today_str = now_myt().strftime('%Y-%m-%d')
    due_today = conn.execute(
        """SELECT b.*, c.full_name as cust_name, c.phone as cust_phone2
           FROM bookings b
           LEFT JOIN customers c ON b.customer_id = c.id
           WHERE b.end_date = ? AND b.rental_status = 'Picked Up'
           ORDER BY b.start_date ASC""",
        (today_str,)
    ).fetchall()

    # Overdue: rental_status = Overdue OR (status=active and end_date < today)
    overdue = conn.execute(
        """SELECT b.*, c.full_name as cust_name, c.phone as cust_phone2
           FROM bookings b
           LEFT JOIN customers c ON b.customer_id = c.id
           WHERE b.rental_status = 'Overdue'
              OR (b.status = 'active' AND b.end_date < ? AND b.rental_status NOT IN ('Returned','Cancelled'))
           ORDER BY b.end_date ASC""",
        (today_str,)
    ).fetchall()

    conn.close()
    return render_template('staff_dashboard.html', bookings=bookings, cameras=CAMERAS,
                           camera_map=CAMERA_MAP, customers=customers, wa=wa,
                           due_today=due_today, overdue_bookings=overdue)

@app.route('/staff/add', methods=['POST'])
@login_required
def staff_add_booking():
    camera_id      = request.form.get('camera_id')
    start_date     = request.form.get('start_date')
    end_date       = request.form.get('end_date')
    customer_name  = request.form.get('customer_name', '').strip()
    customer_phone = request.form.get('customer_phone', '').strip()
    nationality    = request.form.get('nationality', '').strip()
    id_number      = request.form.get('id_number', '').strip()
    pickup_time    = request.form.get('pickup_time', '').strip()
    return_time    = request.form.get('return_time', '').strip()
    notes          = request.form.get('notes', '')
    booking_mode   = request.form.get('booking_mode', 'walkin')
    redirect_sign  = request.args.get('redirect') == 'sign'

    if not all([camera_id, start_date, end_date]):
        return redirect(url_for('staff_dashboard'))

    # Unit-aware availability check
    avail_units = get_available_units(camera_id, start_date, end_date)
    if not avail_units:
        return redirect(url_for('staff_dashboard') + '?error=conflict')
    assigned_unit_id = avail_units[0]['id']

    # Handle photo ID upload
    id_photo_filename = None
    if 'id_photo' in request.files:
        file = request.files['id_photo']
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            id_photo_filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(UPLOAD_FOLDER, id_photo_filename))

    # Handle customer photo with device upload
    customer_photo_filename = None
    if 'customer_photo' in request.files:
        cfile = request.files['customer_photo']
        if cfile and cfile.filename and allowed_file(cfile.filename):
            ext2 = cfile.filename.rsplit('.', 1)[1].lower()
            customer_photo_filename = f"cust_{uuid.uuid4().hex}.{ext2}"
            cfile.save(os.path.join(UPLOAD_FOLDER, customer_photo_filename))

    conn = get_db()

    # Ensure bookings table has extra columns
    for col in ['nationality TEXT', 'customer_photo TEXT', 'booking_mode TEXT', 'pickup_time TEXT', 'return_time TEXT']:
        try:
            conn.execute(f"ALTER TABLE bookings ADD COLUMN {col}")
            conn.commit()
        except:
            pass

    # Auto-create or update customer record if customer name exists
    customer_id = None
    if customer_name:
        existing = None
        if customer_phone:
            # Cari customer dengan nama DAN telefon yang sama
            existing = conn.execute(
                "SELECT id FROM customers WHERE phone = ? AND LOWER(full_name) = LOWER(?)", 
                (customer_phone, customer_name)
            ).fetchone()
            if not existing:
                # Cuba cari dengan telefon sahaja — jika nama berbeza, cipta baru
                phone_match = conn.execute(
                    "SELECT id, full_name FROM customers WHERE phone = ?", (customer_phone,)
                ).fetchone()
                if phone_match and phone_match['full_name'].lower().strip() == customer_name.lower().strip():
                    existing = phone_match
        if existing:
            customer_id = existing['id']
            updates = []
            params = []
            if id_photo_filename:
                updates.append("id_photo=?")
                params.append(id_photo_filename)
            if nationality:
                updates.append("nationality=?")
                params.append(nationality)
            if id_number:
                updates.append("id_number=?")
                params.append(id_number)
            if updates:
                params.append(customer_id)
                conn.execute(f"UPDATE customers SET {', '.join(updates)} WHERE id=?", params)
        else:
            cur = conn.execute(
                """INSERT INTO customers (full_name, phone, id_photo, nationality, id_number, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (customer_name, customer_phone, id_photo_filename, nationality, id_number,
                 now_myt().strftime('%Y-%m-%d %H:%M'))
            )
            customer_id = cur.lastrowid
        conn.commit()

    cur2 = conn.execute(
        """INSERT INTO bookings (camera_id, start_date, end_date, customer_name, customer_phone,
           notes, customer_id, nationality, customer_photo, booking_mode, pickup_time, return_time, unit_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (camera_id, start_date, end_date, customer_name, customer_phone,
         notes, customer_id, nationality, customer_photo_filename, booking_mode, pickup_time, return_time, assigned_unit_id)
    )
    booking_id = cur2.lastrowid
    conn.commit()
    conn.close()

    # Walk-in: redirect terus ke sign agreement
    if redirect_sign:
        cam = CAMERA_MAP.get(camera_id, {})
        cam_name = cam.get('name', camera_id)
        params = f'booking_id={booking_id}'
        return redirect(url_for('agreement_new') + '?' + params)

    return redirect(url_for('staff_dashboard') + '?success=1')

@app.route('/staff/booking/<int:booking_id>/update', methods=['GET', 'POST'])
@login_required
def booking_update(booking_id):
    conn = get_db()
    booking = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not booking:
        conn.close()
        abort(404)

    if request.method == 'GET':
        # Prepare booking dict with photo URLs
        b = dict(booking)
        if b.get('customer_photo'):
            b['customer_photo_url'] = url_for('serve_upload', filename=b['customer_photo'])
        # Check if customer has id_photo and id_number
        if b.get('customer_id'):
            cust = conn.execute("SELECT id_photo, id_number FROM customers WHERE id = ?", (b['customer_id'],)).fetchone()
            if cust:
                if cust['id_photo']:
                    b['id_photo_url'] = url_for('serve_upload', filename=cust['id_photo'])
                if cust['id_number'] and not b.get('id_number'):
                    b['id_number'] = cust['id_number']
        conn.close()
        return render_template('booking_update.html', booking=b, camera_map=CAMERA_MAP)

    # POST — update booking and customer
    booking_dict = dict(booking)  # Convert sqlite3.Row to dict
    customer_name  = request.form.get('customer_name', '').strip()
    customer_phone = request.form.get('customer_phone', '').strip()
    nationality    = request.form.get('nationality', '').strip()
    id_number      = request.form.get('id_number', '').strip()
    notes          = request.form.get('notes', '')
    redirect_sign  = request.form.get('redirect_sign') == '1'

    # Handle photo ID upload
    id_photo_filename = None
    if 'id_photo' in request.files:
        file = request.files['id_photo']
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            id_photo_filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(UPLOAD_FOLDER, id_photo_filename))

    # Handle customer photo
    customer_photo_filename = booking_dict.get('customer_photo')
    if 'customer_photo' in request.files:
        cfile = request.files['customer_photo']
        if cfile and cfile.filename and allowed_file(cfile.filename):
            ext2 = cfile.filename.rsplit('.', 1)[1].lower()
            customer_photo_filename = f"cust_{uuid.uuid4().hex}.{ext2}"
            cfile.save(os.path.join(UPLOAD_FOLDER, customer_photo_filename))

    # Update booking record
    conn.execute(
        """UPDATE bookings SET customer_name=?, customer_phone=?, nationality=?,
           customer_photo=?, notes=? WHERE id=?""",
        (customer_name, customer_phone, nationality, customer_photo_filename, notes, booking_id)
    )

    # Auto-create or update customer record
    customer_id = booking_dict.get('customer_id')
    if customer_name:
        existing = None
        if customer_phone:
            # Cari customer dengan nama DAN telefon yang sama
            existing = conn.execute(
                "SELECT id FROM customers WHERE phone = ? AND LOWER(full_name) = LOWER(?)",
                (customer_phone, customer_name)
            ).fetchone()
        if existing:
            customer_id = existing['id']
            updates = ['nationality=?']
            params = [nationality]
            if id_photo_filename:
                updates.append('id_photo=?')
                params.append(id_photo_filename)
            if id_number:
                updates.append('id_number=?')
                params.append(id_number)
            params.append(customer_id)
            conn.execute(f"UPDATE customers SET {', '.join(updates)} WHERE id=?", params)
        elif customer_id:
            # Update existing linked customer
            updates = ['nationality=?', 'full_name=?', 'phone=?']
            params = [nationality, customer_name, customer_phone]
            if id_photo_filename:
                updates.append('id_photo=?')
                params.append(id_photo_filename)
            if id_number:
                updates.append('id_number=?')
                params.append(id_number)
            params.append(customer_id)
            conn.execute(f"UPDATE customers SET {', '.join(updates)} WHERE id=?", params)
        else:
            cur = conn.execute(
                """INSERT INTO customers (full_name, phone, id_photo, nationality, id_number, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (customer_name, customer_phone, id_photo_filename, nationality, id_number,
                 now_myt().strftime('%Y-%m-%d %H:%M'))
            )
            customer_id = cur.lastrowid

    # Update customer_id in booking
    if customer_id:
        conn.execute("UPDATE bookings SET customer_id=? WHERE id=?", (customer_id, booking_id))

    conn.commit()
    conn.close()

    if redirect_sign:
        return redirect(url_for('agreement_new') + f'?booking_id={booking_id}')

    return redirect(url_for('staff_dashboard') + '?updated=1')

@app.route('/staff/delete/<int:booking_id>', methods=['POST'])
@login_required
def staff_delete_booking(booking_id):
    conn = get_db()
    conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('staff_dashboard') + '?deleted=1')

# ─── Customer Database ────────────────────────────────────────────────────────
@app.route('/staff/customers')
@login_required
def customer_list():
    search = request.args.get('q', '').strip()
    conn = get_db()
    if search:
        customers = conn.execute(
            "SELECT * FROM customers WHERE full_name LIKE ? OR phone LIKE ? OR id_number LIKE ? ORDER BY created_at DESC",
            (f'%{search}%', f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        customers = conn.execute("SELECT * FROM customers ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template('customer_list.html', customers=customers, search=search)

@app.route('/staff/customers/add', methods=['GET', 'POST'])
@login_required
def customer_add():
    if request.method == 'POST':
        full_name   = request.form.get('full_name', '').strip()
        phone       = request.form.get('phone', '').strip()
        email       = request.form.get('email', '').strip()
        nationality = request.form.get('nationality', '').strip()
        id_type     = request.form.get('id_type', '').strip()
        id_number   = request.form.get('id_number', '').strip()
        notes       = request.form.get('notes', '').strip()
        agreement_signed = 1 if request.form.get('agreement_signed') else 0
        agreement_date   = now_myt().strftime('%Y-%m-%d %H:%M') if agreement_signed else None

        # Handle ID photo upload
        id_photo_filename = None
        if 'id_photo' in request.files:
            file = request.files['id_photo']
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                id_photo_filename = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(UPLOAD_FOLDER, id_photo_filename))

        conn = get_db()
        conn.execute(
            """INSERT INTO customers (full_name, phone, email, nationality, id_type, id_number,
               id_photo, agreement_signed, agreement_date, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (full_name, phone, email, nationality, id_type, id_number,
             id_photo_filename, agreement_signed, agreement_date, notes)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('customer_list') + '?added=1')
    return render_template('customer_add.html')

@app.route('/staff/customers/<int:cust_id>')
@login_required
def customer_detail(cust_id):
    conn = get_db()
    customer = conn.execute("SELECT * FROM customers WHERE id = ?", (cust_id,)).fetchone()
    if not customer:
        conn.close()
        abort(404)
    bookings = conn.execute(
        "SELECT * FROM bookings WHERE customer_id = ? ORDER BY start_date DESC",
        (cust_id,)
    ).fetchall()
    # Get customer photos from bookings
    customer_photos = []
    for b in bookings:
        if b['customer_photo']:
            customer_photos.append({
                'filename': b['customer_photo'],
                'camera': CAMERA_MAP.get(b['camera_id'], {}).get('name', b['camera_id']),
                'date': b['start_date']
            })
    # Get agreements for this customer
    cust_phone = customer['phone']
    agreements = []
    if cust_phone:
        agreements = conn.execute(
            "SELECT * FROM agreements WHERE customer_phone = ? ORDER BY signed_at DESC",
            (cust_phone,)
        ).fetchall()
    conn.close()
    return render_template('customer_detail.html', customer=customer, bookings=bookings,
                           customer_photos=customer_photos, agreements=agreements, camera_map=CAMERA_MAP)

@app.route('/staff/customers/<int:cust_id>/edit', methods=['GET', 'POST'])
@login_required
def customer_edit(cust_id):
    conn = get_db()
    customer = conn.execute("SELECT * FROM customers WHERE id = ?", (cust_id,)).fetchone()
    if not customer:
        conn.close()
        abort(404)
    if request.method == 'POST':
        full_name   = request.form.get('full_name', '').strip()
        phone       = request.form.get('phone', '').strip()
        email       = request.form.get('email', '').strip()
        nationality = request.form.get('nationality', '').strip()
        id_type     = request.form.get('id_type', '').strip()
        id_number   = request.form.get('id_number', '').strip()
        notes       = request.form.get('notes', '').strip()
        agreement_signed = 1 if request.form.get('agreement_signed') else 0
        agreement_date   = customer['agreement_date']
        if agreement_signed and not customer['agreement_signed']:
            agreement_date = now_myt().strftime('%Y-%m-%d %H:%M')

        id_photo_filename = customer['id_photo']
        if 'id_photo' in request.files:
            file = request.files['id_photo']
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                id_photo_filename = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(UPLOAD_FOLDER, id_photo_filename))

        conn.execute(
            """UPDATE customers SET full_name=?, phone=?, email=?, nationality=?, id_type=?,
               id_number=?, id_photo=?, agreement_signed=?, agreement_date=?, notes=?
               WHERE id=?""",
            (full_name, phone, email, nationality, id_type, id_number,
             id_photo_filename, agreement_signed, agreement_date, notes, cust_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('customer_detail', cust_id=cust_id) + '?updated=1')
    conn.close()
    return render_template('customer_edit.html', customer=customer)

@app.route('/staff/customers/<int:cust_id>/delete', methods=['POST'])
@login_required
def customer_delete(cust_id):
    conn = get_db()
    customer = conn.execute("SELECT id_photo FROM customers WHERE id = ?", (cust_id,)).fetchone()
    if customer and customer['id_photo']:
        photo_path = os.path.join(UPLOAD_FOLDER, customer['id_photo'])
        if os.path.exists(photo_path):
            os.remove(photo_path)
    conn.execute("DELETE FROM customers WHERE id = ?", (cust_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('customer_list') + '?deleted=1')

@app.route('/staff/uploads/<filename>')
@login_required
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ─── Digital Agreements ───────────────────────────────────────────────────────
@app.route('/staff/agreements')
@login_required
def agreement_list():
    search = request.args.get('q', '').strip()
    conn = get_db()
    if search:
        agreements = conn.execute(
            "SELECT * FROM agreements WHERE customer_name LIKE ? OR customer_phone LIKE ? ORDER BY signed_at DESC",
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        agreements = conn.execute("SELECT * FROM agreements ORDER BY signed_at DESC").fetchall()
    conn.close()
    return render_template('agreement_list.html', agreements=agreements, search=search)

@app.route('/staff/agreements/new')
@login_required
def agreement_new():
    booking_id = request.args.get('booking_id')
    booking = None
    if booking_id:
        conn = get_db()
        b = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if b:
            b_dict = dict(b)
            cam = CAMERA_MAP.get(b_dict['camera_id'], {})
            # Cari ic_number dari customer record
            ic_number = ''
            if b_dict.get('customer_id'):
                cust = conn.execute("SELECT id_number FROM customers WHERE id = ?", (b_dict['customer_id'],)).fetchone()
                if cust and cust['id_number']:
                    ic_number = cust['id_number']
            booking = {
                'camera_name': cam.get('name', b_dict['camera_id']),
                'start_date': b_dict['start_date'],
                'end_date': b_dict['end_date'],
                'pickup_time': b_dict.get('pickup_time', '') or '',
                'return_time': b_dict.get('return_time', '') or '',
                'customer_name': b_dict['customer_name'] or '',
                'customer_phone': b_dict['customer_phone'] or '',
                'ic_number': ic_number
            }
        conn.close()
    else:
        # Read from URL params (sent from booking form)
        name  = request.args.get('name', '')
        phone = request.args.get('phone', '')
        equip = request.args.get('equipment', '')
        pickup = request.args.get('pickup', '')
        ret   = request.args.get('return', '')
        ic    = request.args.get('ic', '')
        pickup_time = request.args.get('pickup_time', '')
        return_time = request.args.get('return_time', '')
        if any([name, phone, equip, pickup, ret]):
            booking = {
                'customer_name': name,
                'customer_phone': phone,
                'camera_name': equip,
                'start_date': pickup,
                'end_date': ret,
                'ic_number': ic,
                'pickup_time': pickup_time,
                'return_time': return_time
            }
    return render_template('agreement_sign.html', signed=False, booking=booking)

@app.route('/staff/agreements/save', methods=['POST'])
@login_required
def agreement_save():
    from flask import jsonify
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Data tidak diterima'}), 400
    required = ['customer_name', 'customer_phone', 'equipment', 'pickup_date', 'return_date']
    for field in required:
        if not data.get(field, '').strip():
            return jsonify({'success': False, 'error': f'Medan {field} diperlukan'}), 400
    cust_name  = data['customer_name'].strip()
    cust_phone = data['customer_phone'].strip()
    ic_number  = data.get('ic_number', '').strip()

    conn = get_db()

    # Auto-create or link customer record
    customer_id = None
    if cust_name:
        existing = None
        if cust_phone:
            # Cari customer dengan nama DAN telefon yang sama
            existing = conn.execute(
                "SELECT id FROM customers WHERE phone = ? AND LOWER(full_name) = LOWER(?)",
                (cust_phone, cust_name)
            ).fetchone()
        if existing:
            customer_id = existing['id']
            # Update ic_number if available and not yet set
            if ic_number:
                conn.execute(
                    "UPDATE customers SET id_number=? WHERE id=? AND (id_number IS NULL OR id_number='')",
                    (ic_number, customer_id)
                )
        else:
            cur2 = conn.execute(
                """INSERT INTO customers (full_name, phone, id_number, created_at)
                   VALUES (?, ?, ?, ?)""",
                (cust_name, cust_phone, ic_number,
                 now_myt().strftime('%Y-%m-%d %H:%M'))
            )
            customer_id = cur2.lastrowid
        conn.commit()

    cur = conn.execute(
        """INSERT INTO agreements
           (customer_name, customer_phone, ic_number, equipment, accessories,
            pickup_date, return_date, deposit, signature_data, signed_at,
            pickup_time, return_time)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            cust_name,
            cust_phone,
            ic_number,
            data['equipment'].strip(),
            data.get('accessories', ''),
            data['pickup_date'],
            data['return_date'],
            float(data.get('deposit', 200) or 200),
            data.get('signature_data', ''),
            now_myt().strftime('%Y-%m-%d %H:%M'),
            data.get('pickup_time', ''),
            data.get('return_time', '')
        )
    )
    agreement_id = cur.lastrowid

    # Update customer record — mark agreement as signed
    if customer_id:
        conn.execute(
            "UPDATE customers SET agreement_signed=1, agreement_date=? WHERE id=?",
            (now_myt().strftime('%Y-%m-%d %H:%M'), customer_id)
        )

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': agreement_id})

@app.route('/staff/agreements/<int:ag_id>')
@login_required
def agreement_detail(ag_id):
    conn = get_db()
    ag = conn.execute("SELECT * FROM agreements WHERE id = ?", (ag_id,)).fetchone()
    conn.close()
    if not ag:
        abort(404)
    return render_template('agreement_sign.html', signed=True, agreement=ag)

@app.route('/staff/agreements/<int:ag_id>/delete', methods=['POST'])
@login_required
def agreement_delete(ag_id):
    conn = get_db()
    conn.execute("DELETE FROM agreements WHERE id = ?", (ag_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('agreement_list') + '?deleted=1')

# ═══════════════════════════════════════════════════════════════════════════════
# ─── PUBLIC BOOKING API ──────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/products')
def api_products():
    """GET /api/products — return all cameras with availability summary and unit counts"""
    conn = get_db()
    products = []
    today = now_myt().strftime('%Y-%m-%d')
    for cam in CAMERAS:
        booked = get_booked_dates(cam['id'])
        total_units = conn.execute(
            "SELECT COUNT(*) FROM units WHERE product_id = ? AND status = 'available'",
            (cam['id'],)
        ).fetchone()[0]
        avail_today = get_available_units(cam['id'], today, today)
        products.append({
            'id': cam['id'],
            'name': cam['name'],
            'category': cam['category'],
            'image': cam['image'],
            'prices': cam['prices'],
            'booked_dates': booked,
            'available_today': len(avail_today) > 0,
            'total_units': total_units,
            'available_units_today': len(avail_today)
        })
    conn.close()
    return jsonify({'products': products})

@app.route('/api/availability')
def api_availability_check():
    """GET /api/availability?productId=xxx&start=YYYY-MM-DD&end=YYYY-MM-DD"""
    camera_id  = request.args.get('productId') or request.args.get('camera_id')
    start_date = request.args.get('start')
    end_date   = request.args.get('end')
    if not all([camera_id, start_date, end_date]):
        return jsonify({'error': 'Missing parameters: productId, start, end'}), 400
    if camera_id not in CAMERA_MAP:
        return jsonify({'error': 'Product not found'}), 404

    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end   = datetime.strptime(end_date,   '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    if end < start:
        return jsonify({'error': 'End date must be after start date'}), 400

    # Unit-aware availability
    avail_units = get_available_units(camera_id, start_date, end_date)
    available = len(avail_units) > 0

    days = (end - start).days
    if days < 1:
        days = 1
    camera = CAMERA_MAP[camera_id]
    ppd, total = calculate_price(camera_id, days)

    # Get total units count
    conn = get_db()
    total_units = conn.execute(
        "SELECT COUNT(*) FROM units WHERE product_id = ? AND status = 'available'",
        (camera_id,)
    ).fetchone()[0]
    conn.close()

    return jsonify({
        'available': available,
        'available_units': len(avail_units),
        'total_units': total_units,
        'days': days,
        'price_per_day': ppd,
        'total_price': total,
        'deposit': 200,
        'camera_id': camera_id,
        'camera_name': camera['name'],
        'camera_image': camera['image'],
        'start_date': start_date,
        'end_date': end_date
    })

@app.route('/api/bookings', methods=['POST'])
def api_create_booking():
    """POST /api/bookings — create a pending booking and lock date range.
    Body JSON: { camera_id, start_date, end_date, customer_name, customer_phone,
                 customer_email (optional), customer_ic (optional),
                 pickup_time (optional), return_time (optional), notes (optional) }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    camera_id  = data.get('camera_id', '').strip()
    start_date = data.get('start_date', '').strip()
    end_date   = data.get('end_date', '').strip()
    cust_name  = data.get('customer_name', '').strip()
    cust_phone = data.get('customer_phone', '').strip()

    if not all([camera_id, start_date, end_date, cust_name, cust_phone]):
        return jsonify({'error': 'Required: camera_id, start_date, end_date, customer_name, customer_phone'}), 400
    if camera_id not in CAMERA_MAP:
        return jsonify({'error': 'Product not found'}), 404

    # Validate dates
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end   = datetime.strptime(end_date,   '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    if end < start:
        return jsonify({'error': 'End date must be after start date'}), 400

    # Unit-aware availability check (double-booking prevention)
    avail_units = get_available_units(camera_id, start_date, end_date)
    if not avail_units:
        return jsonify({'error': 'Date not available — all units are booked for selected dates',
                        'available': False}), 409

    # Auto-assign first available unit
    assigned_unit = avail_units[0]
    assigned_unit_id = assigned_unit['id']

    # Calculate price
    days = (end - start).days
    if days < 1:
        days = 1
    ppd, total = calculate_price(camera_id, days)
    if ppd is None:
        return jsonify({'error': 'Pricing not available for this duration'}), 400

    booking_ref = generate_booking_ref()
    cust_email  = data.get('customer_email', '').strip()
    cust_ic     = data.get('customer_ic', '').strip()

    # Validate email format on backend
    if cust_email:
        import re
        email_regex = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}$')
        if not email_regex.match(cust_email) or '..' in cust_email:
            return jsonify({'error': 'Invalid email address format. Please enter a valid email.'}), 400
    else:
        return jsonify({'error': 'Email address is required to receive your booking confirmation.'}), 400
    pickup_time = data.get('pickup_time', '').strip()
    return_time = data.get('return_time', '').strip()
    notes       = data.get('notes', '').strip()

    # Process accessories add-ons
    import json as _json
    accessories_list = data.get('accessories', [])
    accessories_json = None
    accessories_total = 0
    if accessories_list and isinstance(accessories_list, list):
        validated_accs = []
        for acc_item in accessories_list:
            acc_id = acc_item.get('id', '')
            acc_data = ACCESSORY_MAP.get(acc_id)
            if acc_data:
                ppd_acc = get_accessory_price(acc_id, days)
                if ppd_acc is not None:
                    # Check availability
                    avail = get_accessory_availability(acc_id, start_date, end_date)
                    if avail['available_units'] > 0:
                        acc_total = ppd_acc * days
                        validated_accs.append({
                            'id': acc_id,
                            'name': acc_data['name'],
                            'price_per_day': ppd_acc,
                            'days': days,
                            'total': acc_total
                        })
                        accessories_total += acc_total
        if validated_accs:
            accessories_json = _json.dumps(validated_accs)
            total += accessories_total  # Add accessories to total price

    conn = get_db()

    # Auto-create customer record
    customer_id = None
    if cust_name and cust_phone:
        existing = conn.execute(
            "SELECT id FROM customers WHERE phone = ? AND LOWER(full_name) = LOWER(?)",
            (cust_phone, cust_name)
        ).fetchone()
        if existing:
            customer_id = existing['id']
            if cust_ic:
                conn.execute("UPDATE customers SET id_number=? WHERE id=? AND (id_number IS NULL OR id_number='')",
                             (cust_ic, customer_id))
            if cust_email:
                conn.execute("UPDATE customers SET email=? WHERE id=? AND (email IS NULL OR email='')",
                             (cust_email, customer_id))
        else:
            cur = conn.execute(
                """INSERT INTO customers (full_name, phone, email, id_number, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (cust_name, cust_phone, cust_email, cust_ic,
                 now_myt().strftime('%Y-%m-%d %H:%M'))
            )
            customer_id = cur.lastrowid
        conn.commit()

    # Insert booking with status=pending and assigned unit_id
    cur2 = conn.execute(
        """INSERT INTO bookings
           (camera_id, start_date, end_date, customer_name, customer_phone,
            notes, customer_id, booking_ref, status, deposit_amount, deposit_status,
            total_price, price_per_day, source, customer_email, customer_ic,
            pickup_time, return_time, booking_mode, unit_id, accessories_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (camera_id, start_date, end_date, cust_name, cust_phone,
         notes, customer_id, booking_ref, 'pending', 200, 'unpaid',
         total, ppd, 'online', cust_email, cust_ic,
         pickup_time, return_time, 'online', assigned_unit_id, accessories_json)
    )
    booking_id = cur2.lastrowid
    conn.commit()
    conn.close()

    camera = CAMERA_MAP[camera_id]

    # Build booking dict for WhatsApp message generation
    booking_data = {
        'booking_ref': booking_ref,
        'camera_name': camera['name'],
        'start_date': start_date,
        'end_date': end_date,
        'total_price': total,
        'deposit_amount': 200,
        'customer_name': cust_name,
        'customer_phone': cust_phone,
        'customer_email': cust_email,
    }
    admin_wa_link = wa.admin_new_booking_alert(booking_data, camera['name'])

    return jsonify({
        'success': True,
        'booking_id': booking_id,
        'booking_ref': booking_ref,
        'status': 'pending',
        'camera_name': camera['name'],
        'start_date': start_date,
        'end_date': end_date,
        'days': days,
        'price_per_day': ppd,
        'total_price': total,
        'accessories_total': accessories_total,
        'booking_fee': 30,
        'deposit': 200,
        'admin_wa_link': admin_wa_link,
        'message': f'Booking {booking_ref} has been created. Please pay the RM30 booking fee to confirm your booking.'
    }), 201

@app.route('/api/bookings/<booking_ref>')
def api_booking_status(booking_ref):
    """GET /api/bookings/<ref> — check booking status by reference"""
    conn = get_db()
    b = conn.execute("SELECT * FROM bookings WHERE booking_ref = ?", (booking_ref,)).fetchone()
    conn.close()
    if not b:
        return jsonify({'error': 'Booking not found'}), 404
    bd = dict(b)
    camera = CAMERA_MAP.get(bd['camera_id'], {})
    return jsonify({
        'booking_ref': bd['booking_ref'],
        'status': bd.get('status', 'confirmed'),
        'camera_name': camera.get('name', bd['camera_id']),
        'camera_image': camera.get('image', ''),
        'start_date': bd['start_date'],
        'end_date': bd['end_date'],
        'pickup_time': bd.get('pickup_time', ''),
        'return_time': bd.get('return_time', ''),
        'customer_name': bd['customer_name'],
        'customer_phone': bd['customer_phone'],
        'days': max((datetime.strptime(bd['end_date'], '%Y-%m-%d') - datetime.strptime(bd['start_date'], '%Y-%m-%d')).days, 1),
        'price_per_day': bd.get('price_per_day'),
        'total_price': bd.get('total_price'),
        'deposit_amount': bd.get('deposit_amount', 200),
        'deposit_status': bd.get('deposit_status', 'unpaid')
    })

@app.route('/api/payments/deposit', methods=['POST'])
def api_payment_deposit():
    """POST /api/payments/deposit — record deposit payment intent.
    Body JSON: { booking_ref, method (bank_transfer/cash), reference (optional) }
    For MVP: records payment as 'pending' for staff to verify.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    booking_ref = data.get('booking_ref', '').strip()
    method      = data.get('method', 'bank_transfer').strip()
    reference   = data.get('reference', '').strip()

    if not booking_ref:
        return jsonify({'error': 'booking_ref required'}), 400

    conn = get_db()
    b = conn.execute("SELECT id, status, deposit_amount FROM bookings WHERE booking_ref = ?",
                     (booking_ref,)).fetchone()
    if not b:
        conn.close()
        return jsonify({'error': 'Booking not found'}), 404

    bd = dict(b)
    if bd.get('status') == 'cancelled':
        conn.close()
        return jsonify({'error': 'Booking has been cancelled'}), 400

    deposit = bd.get('deposit_amount', 200) or 200

    # Record payment
    conn.execute(
        """INSERT INTO payments (booking_id, booking_ref, amount, type, method, status, reference)
           VALUES (?, ?, ?, 'deposit', ?, 'pending', ?)""",
        (bd['id'], booking_ref, deposit, method, reference)
    )
    # Update booking deposit status
    conn.execute("UPDATE bookings SET deposit_status = 'pending' WHERE id = ?", (bd['id'],))
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'booking_ref': booking_ref,
        'deposit_amount': deposit,
        'payment_status': 'pending',
        'message': 'Payment recorded. Staff will verify shortly.'
    })

@app.route('/api/bookings/confirm', methods=['POST'])
def api_booking_confirm():
    """POST /api/bookings/confirm — confirm booking after payment verified.
    Body JSON: { booking_ref }
    This is called by staff or auto after payment verification.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    booking_ref = data.get('booking_ref', '').strip()
    if not booking_ref:
        return jsonify({'error': 'booking_ref required'}), 400

    conn = get_db()
    b = conn.execute("SELECT id, status FROM bookings WHERE booking_ref = ?",
                     (booking_ref,)).fetchone()
    if not b:
        conn.close()
        return jsonify({'error': 'Booking not found'}), 404

    conn.execute(
        "UPDATE bookings SET status = 'confirmed', deposit_status = 'paid' WHERE id = ?",
        (b['id'],)
    )
    conn.execute(
        "UPDATE payments SET status = 'verified', verified_at = ? WHERE booking_ref = ? AND type = 'deposit'",
        (now_myt().strftime('%Y-%m-%d %H:%M'), booking_ref)
    )
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'booking_ref': booking_ref,
        'status': 'confirmed',
        'message': f'Booking {booking_ref} has been confirmed!'
    })

# ═══════════════════════════════════════════════════════════════════════════════
# ─── ADMIN / STAFF BOOKING MANAGEMENT API ────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/staff/booking/<int:booking_id>/confirm', methods=['POST'])
@login_required
def staff_confirm_booking(booking_id):
    """Staff confirms payment and booking, generates WhatsApp confirmation link"""
    conn = get_db()
    b = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not b:
        conn.close()
        return jsonify({'error': 'Booking not found'}), 404

    conn.execute(
        "UPDATE bookings SET status = 'confirmed', deposit_status = 'paid' WHERE id = ?",
        (booking_id,)
    )
    bd = dict(b)
    ref = bd.get('booking_ref', '')
    if ref:
        conn.execute(
            "UPDATE payments SET status = 'verified', verified_at = ?, verified_by = 'staff' WHERE booking_ref = ? AND type = 'deposit'",
            (now_myt().strftime('%Y-%m-%d %H:%M'), ref)
        )
    conn.commit()
    conn.close()

    # Generate WhatsApp confirmation message link for staff to send to customer
    camera = CAMERA_MAP.get(bd.get('camera_id', ''), {})
    camera_name = camera.get('name', bd.get('camera_id', ''))
    wa_link = wa.admin_confirm_booking(bd, camera_name)
    from urllib.parse import quote
    return redirect(url_for('staff_dashboard') + '?confirmed=1&wa_confirm=' + quote(wa_link, safe=''))

@app.route('/staff/booking/<int:booking_id>/returned', methods=['POST'])
@login_required
def staff_mark_returned(booking_id):
    """Staff marks equipment as returned, generates thank-you WhatsApp link"""
    conn = get_db()
    b = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    conn.execute("UPDATE bookings SET status = 'returned' WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()
    if b:
        bd = dict(b)
        camera = CAMERA_MAP.get(bd.get('camera_id', ''), {})
        camera_name = camera.get('name', bd.get('camera_id', ''))
        wa_link = wa.admin_thank_you(bd, camera_name)
        from urllib.parse import quote
        return redirect(url_for('staff_dashboard') + '?returned=1&wa_thankyou=' + quote(wa_link, safe=''))
    return redirect(url_for('staff_dashboard') + '?returned=1')

@app.route('/staff/booking/<int:booking_id>/cancel', methods=['POST'])
@login_required
def staff_cancel_booking(booking_id):
    """Staff cancels a booking — frees up dates"""
    conn = get_db()
    conn.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('staff_dashboard') + '?cancelled=1')

@app.route('/staff/booking/<int:booking_id>/active', methods=['POST'])
@login_required
def staff_mark_active(booking_id):
    """Staff marks booking as active (equipment picked up) — records actual pickup datetime"""
    import json as _json
    now_str = now_myt().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db()
    conn.execute(
        """UPDATE bookings SET
           status = 'active',
           rental_status = 'Picked Up',
           actual_pickup_datetime = ?,
           pickup_confirmed_at = ?
           WHERE id = ?""",
        (now_str, now_str, booking_id)
    )
    conn.commit()

    # Re-fetch booking for email
    b_updated = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    conn.close()

    # Send pickup confirmation email in background thread
    if b_updated:
        bd = dict(b_updated)
        camera = CAMERA_MAP.get(bd.get('camera_id', ''), {})
        bd['camera_name'] = camera.get('name', bd.get('camera_id', 'Camera'))
        bd['actual_pickup_datetime'] = now_str

        # Parse accessories
        accessories = []
        if bd.get('accessories_json'):
            try:
                accessories = _json.loads(bd['accessories_json'])
            except Exception:
                pass
        bd['accessories'] = accessories

        # Calculate days
        try:
            sd = datetime.strptime(bd['start_date'], '%Y-%m-%d')
            ed = datetime.strptime(bd['end_date'], '%Y-%m-%d')
            bd['days'] = max((ed - sd).days, 1)
        except Exception:
            bd['days'] = 1

        # Calculate return deadline = actual pickup time + (num_days × 24h)
        try:
            pickup_dt_obj = datetime.strptime(now_str, '%Y-%m-%d %H:%M:%S')
            return_deadline_dt = pickup_dt_obj + timedelta(hours=24 * bd['days'])
            bd['return_deadline_display'] = return_deadline_dt.strftime('%d %b %Y (%A) %I:%M %p')
            bd['return_time_for_agreement'] = return_deadline_dt.strftime('%H:%M')
        except Exception:
            bd['return_deadline_display'] = f"{bd.get('end_date', '')} same time as pickup"

        def _send_pickup_email(booking_dict):
            try:
                from email_sender import send_pickup_confirmation_email
                send_pickup_confirmation_email(booking_dict)
            except Exception as e:
                app.logger.error(f"Pickup email error for {booking_dict.get('booking_ref')}: {e}")

        import threading
        threading.Thread(target=_send_pickup_email, args=(bd,), daemon=True).start()
        app.logger.info(f"Pickup confirmation email queued for {bd.get('booking_ref')}")

    return redirect(url_for('staff_dashboard') + '?active=1')

@app.route('/staff/block-dates', methods=['POST'])
@login_required
def staff_block_dates():
    """Staff blocks date range for a camera (maintenance, reserved, etc.)"""
    camera_id  = request.form.get('camera_id', '').strip()
    start_date = request.form.get('start_date', '').strip()
    end_date   = request.form.get('end_date', '').strip()
    reason     = request.form.get('reason', '').strip()

    if not all([camera_id, start_date, end_date]):
        return redirect(url_for('staff_dashboard') + '?error=missing')

    conn = get_db()
    conn.execute(
        "INSERT INTO blocked_dates (camera_id, start_date, end_date, reason) VALUES (?,?,?,?)",
        (camera_id, start_date, end_date, reason)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('staff_dashboard') + '?blocked=1')

@app.route('/staff/block-dates/<int:block_id>/delete', methods=['POST'])
@login_required
def staff_unblock_dates(block_id):
    """Staff removes a date block"""
    conn = get_db()
    conn.execute("DELETE FROM blocked_dates WHERE id = ?", (block_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('staff_dashboard') + '?unblocked=1')

@app.route('/staff/blocked-dates')
@login_required
def staff_blocked_dates_list():
    """View all blocked dates"""
    conn = get_db()
    blocks = conn.execute("SELECT * FROM blocked_dates ORDER BY start_date DESC").fetchall()
    conn.close()
    return jsonify({'blocked_dates': [dict(b) for b in blocks]})

@app.route('/staff/online-bookings')
@login_required
def staff_online_bookings():
    """View all online bookings with status management"""
    import json as _json
    conn = get_db()
    bookings = conn.execute(
        """SELECT b.*, c.full_name as cust_name,
                  u.label as unit_label, u.serial_number as unit_serial
           FROM bookings b
           LEFT JOIN customers c ON b.customer_id = c.id
           LEFT JOIN units u ON b.unit_id = u.id
           WHERE b.source = 'online'
           ORDER BY b.created_at DESC"""
    ).fetchall()
    # Also fetch standalone accessory bookings
    acc_bookings = conn.execute(
        "SELECT * FROM accessory_bookings ORDER BY created_at DESC"
    ).fetchall()
    payments = conn.execute(
        "SELECT * FROM payments ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    # Parse accessories_json for display
    def parse_accessories(booking_dict):
        if booking_dict.get('accessories_json'):
            try:
                return _json.loads(booking_dict['accessories_json'])
            except:
                pass
        return []

    return render_template('staff_online_bookings.html', bookings=bookings,
                           acc_bookings=acc_bookings, payments=payments,
                           camera_map=CAMERA_MAP, wa=wa,
                           parse_accessories=parse_accessories)

# ─── Walk-in Booking API ─────────────────────────────────────────────────────

@app.route('/api/verify-walkin-pin', methods=['POST'])
def api_verify_walkin_pin():
    """Verify staff PIN for walk-in booking authorization"""
    data = request.get_json() or {}
    pin = data.get('pin', '').strip()
    if pin == STAFF_WALKIN_PIN:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Invalid PIN'}), 401


@app.route('/api/walkin-booking', methods=['POST'])
def api_create_walkin_booking():
    """Create a walk-in booking directly (no payment required, Pay at Counter).
    Requires staff PIN verification.
    Body JSON: { pin, camera_id, start_date, end_date, customer_name, customer_phone,
                 customer_email (optional), customer_ic (optional),
                 pickup_time (optional), return_time (optional), notes (optional) }
    """
    import json as _json
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    # Verify PIN
    pin = data.get('pin', '').strip()
    if pin != STAFF_WALKIN_PIN:
        return jsonify({'error': 'Invalid staff PIN'}), 401

    camera_id  = data.get('camera_id', '').strip()
    start_date = data.get('start_date', '').strip()
    end_date   = data.get('end_date', '').strip()
    cust_name  = data.get('customer_name', '').strip()
    cust_phone = data.get('customer_phone', '').strip()
    cust_email = data.get('customer_email', '').strip()
    cust_ic    = data.get('customer_ic', '').strip()
    pickup_time = data.get('pickup_time', '').strip()
    return_time = data.get('return_time', '').strip()
    notes       = data.get('notes', '').strip()

    if not all([camera_id, start_date, end_date]):
        return jsonify({'error': 'camera_id, start_date, end_date are required'}), 400

    if camera_id not in CAMERA_MAP:
        return jsonify({'error': f'Unknown camera: {camera_id}'}), 400

    # Validate dates
    try:
        sd = datetime.strptime(start_date, '%Y-%m-%d')
        ed = datetime.strptime(end_date, '%Y-%m-%d')
        days = max((ed - sd).days, 1)
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    # Check availability
    avail_units = get_available_units(camera_id, start_date, end_date)
    if not avail_units:
        return jsonify({'error': 'No units available for selected dates'}), 409

    assigned_unit_id = avail_units[0]['id']
    ppd, total = calculate_price(camera_id, days)
    if ppd is None:
        return jsonify({'error': f'No pricing available for {days} days'}), 400

    # Process accessories
    accessories_list = data.get('accessories', [])
    accessories_json = None
    accessories_total = 0
    if accessories_list and isinstance(accessories_list, list):
        validated_accs = []
        for acc_item in accessories_list:
            acc_id = acc_item.get('id', '')
            acc_data = ACCESSORY_MAP.get(acc_id)
            if acc_data:
                ppd_acc = get_accessory_price(acc_id, days)
                if ppd_acc is not None:
                    avail = get_accessory_availability(acc_id, start_date, end_date)
                    if avail['available_units'] > 0:
                        acc_total = ppd_acc * days
                        validated_accs.append({
                            'id': acc_id,
                            'name': acc_data['name'],
                            'price_per_day': ppd_acc,
                            'days': days,
                            'total': acc_total
                        })
                        accessories_total += acc_total
        if validated_accs:
            accessories_json = _json.dumps(validated_accs)
            total += accessories_total

    booking_ref = generate_booking_ref()

    conn = get_db()
    # Auto-create customer record
    customer_id = None
    if cust_name and cust_phone:
        existing = conn.execute(
            "SELECT id FROM customers WHERE phone = ? AND LOWER(full_name) = LOWER(?)",
            (cust_phone, cust_name)
        ).fetchone()
        if existing:
            customer_id = existing['id']
            if cust_ic:
                conn.execute("UPDATE customers SET id_number=? WHERE id=? AND (id_number IS NULL OR id_number='')",
                             (cust_ic, customer_id))
            if cust_email:
                conn.execute("UPDATE customers SET email=? WHERE id=? AND (email IS NULL OR email='')",
                             (cust_email, customer_id))
        else:
            cur = conn.execute(
                """INSERT INTO customers (full_name, phone, email, id_number, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (cust_name, cust_phone, cust_email, cust_ic,
                 now_myt().strftime('%Y-%m-%d %H:%M'))
            )
            customer_id = cur.lastrowid
        conn.commit()

    # Insert walk-in booking — status=confirmed, payment_status=Pay at Counter
    cur2 = conn.execute(
        """INSERT INTO bookings
           (camera_id, start_date, end_date, customer_name, customer_phone,
            notes, customer_id, booking_ref, status, deposit_amount, deposit_status,
            total_price, price_per_day, source, customer_email, customer_ic,
            pickup_time, return_time, booking_mode, unit_id, accessories_json,
            booking_type, payment_status, rental_status)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (camera_id, start_date, end_date, cust_name, cust_phone,
         notes, customer_id, booking_ref, 'confirmed', 200, 'unpaid',
         total, ppd, 'walkin', cust_email, cust_ic,
         pickup_time, return_time, 'walkin', assigned_unit_id, accessories_json,
         'WALK-IN', 'Pay at Counter', 'Pending Pickup')
    )
    booking_id = cur2.lastrowid
    conn.commit()
    conn.close()

    camera = CAMERA_MAP[camera_id]
    return jsonify({
        'success': True,
        'booking_id': booking_id,
        'booking_ref': booking_ref,
        'status': 'confirmed',
        'booking_type': 'WALK-IN',
        'payment_status': 'Pay at Counter',
        'camera_name': camera['name'],
        'start_date': start_date,
        'end_date': end_date,
        'days': days,
        'price_per_day': ppd,
        'total_price': total,
        'accessories_total': accessories_total,
        'message': f'Walk-in booking {booking_ref} created. Payment to be collected at counter.'
    }), 201


# ─── Unified Booking List (Staff) ─────────────────────────────────────────────

@app.route('/staff/bookings')
@login_required
def staff_bookings_list():
    """Unified booking list for all bookings (online + walk-in) with search."""
    import json as _json
    conn = get_db()
    search = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    type_filter = request.args.get('type', '').strip()

    query = """
        SELECT b.*, c.full_name as cust_name, c.phone as cust_phone2,
               c.id_photo as cust_id_photo, c.id_number as cust_id_number,
               u.label as unit_label, u.serial_number as unit_serial
        FROM bookings b
        LEFT JOIN customers c ON b.customer_id = c.id
        LEFT JOIN units u ON b.unit_id = u.id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (b.customer_name LIKE ? OR b.customer_phone LIKE ? OR b.booking_ref LIKE ? OR c.id_number LIKE ?)"
        s = f'%{search}%'
        params.extend([s, s, s, s])

    if status_filter:
        query += " AND b.rental_status = ?"
        params.append(status_filter)

    if type_filter:
        query += " AND b.booking_type = ?"
        params.append(type_filter)

    query += " ORDER BY b.created_at DESC"
    bookings = conn.execute(query, params).fetchall()

    # Compute overdue status
    now = now_myt()
    booking_list = []
    for row in bookings:
        bd = dict(row)
        # Auto-detect overdue
        if bd.get('rental_status') == 'Picked Up':
            try:
                end_dt = datetime.strptime(bd['end_date'], '%Y-%m-%d').replace(hour=23, minute=59)
                if now > end_dt:
                    bd['rental_status'] = 'Overdue'
                    conn.execute("UPDATE bookings SET rental_status='Overdue' WHERE id=?", (bd['id'],))
            except Exception:
                pass
        # Parse accessories
        bd['accessories'] = []
        if bd.get('accessories_json'):
            try:
                bd['accessories'] = _json.loads(bd['accessories_json'])
            except Exception:
                pass
        booking_list.append(bd)
    conn.commit()
    conn.close()

    return render_template('staff_bookings_list.html',
                           bookings=booking_list,
                           camera_map=CAMERA_MAP,
                           search=search,
                           status_filter=status_filter,
                           type_filter=type_filter)


@app.route('/staff/bookings/<int:booking_id>')
@login_required
def staff_booking_detail(booking_id):
    """Comprehensive booking detail page."""
    import json as _json
    conn = get_db()
    b = conn.execute(
        """SELECT b.*, c.full_name as cust_name, c.phone as cust_phone2,
                  c.id_photo as cust_id_photo, c.id_number as cust_id_number,
                  c.nationality as cust_nationality, c.email as cust_email2,
                  u.label as unit_label, u.serial_number as unit_serial
           FROM bookings b
           LEFT JOIN customers c ON b.customer_id = c.id
           LEFT JOIN units u ON b.unit_id = u.id
           WHERE b.id = ?""",
        (booking_id,)
    ).fetchone()
    if not b:
        conn.close()
        abort(404)

    bd = dict(b)
    conn.close()

    # Parse accessories
    bd['accessories'] = []
    if bd.get('accessories_json'):
        try:
            bd['accessories'] = _json.loads(bd['accessories_json'])
        except Exception:
            pass

    # Parse checklist
    bd['checklist'] = []
    if bd.get('checklist_json'):
        try:
            bd['checklist'] = _json.loads(bd['checklist_json'])
        except Exception:
            pass

    # Auto-detect overdue
    if bd.get('rental_status') == 'Picked Up':
        try:
            now = now_myt()
            end_dt = datetime.strptime(bd['end_date'], '%Y-%m-%d').replace(hour=23, minute=59)
            if now > end_dt:
                bd['rental_status'] = 'Overdue'
        except Exception:
            pass

    camera = CAMERA_MAP.get(bd.get('camera_id', ''), {})
    bd['camera_name'] = camera.get('name', bd.get('camera_id', ''))
    bd['camera_image'] = camera.get('image', '')
    try:
        bd['days'] = max((datetime.strptime(bd['end_date'], '%Y-%m-%d') - datetime.strptime(bd['start_date'], '%Y-%m-%d')).days, 1)
    except Exception:
        bd['days'] = 1

    # Generate default checklist items based on camera
    default_checklist = _generate_checklist(bd.get('camera_id', ''), bd.get('accessories', []))

    return render_template('staff_booking_detail.html',
                           booking=bd,
                           camera_map=CAMERA_MAP,
                           default_checklist=default_checklist)


def _generate_checklist(camera_id, accessories):
    """Generate default equipment checklist items for a camera rental."""
    camera = CAMERA_MAP.get(camera_id, {})
    cam_name = camera.get('name', camera_id)

    # Base items for all cameras
    items = [
        {'item': f'{cam_name} body', 'checked': False},
        {'item': 'Charging cable / adapter', 'checked': False},
        {'item': 'Battery (in camera)', 'checked': False},
        {'item': 'Memory card', 'checked': False},
        {'item': 'Carry bag / pouch', 'checked': False},
    ]

    # Category-specific items
    cat = camera.get('category', '')
    if cat == 'gopro':
        items.append({'item': 'Mounting accessories (clips/mounts)', 'checked': False})
    elif cat == 'insta360':
        items.append({'item': 'Lens cap / lens guard', 'checked': False})
        items.append({'item': 'Invisible selfie stick', 'checked': False})
    elif cat == 'dji':
        items.append({'item': 'Gimbal stabilizer / mount', 'checked': False})
    elif cat == 'drone':
        items.append({'item': 'Propellers (set)', 'checked': False})
        items.append({'item': 'Remote controller', 'checked': False})
        items.append({'item': 'Drone carry case', 'checked': False})
    elif cat == 'canon':
        items.append({'item': 'Lens cap', 'checked': False})
        items.append({'item': 'Lens (if separate)', 'checked': False})
        items.append({'item': 'Camera strap', 'checked': False})

    # Add accessories to checklist
    for acc in accessories:
        items.append({'item': acc.get('name', ''), 'checked': False})

    return items


@app.route('/api/booking/<int:booking_id>/confirm-pickup', methods=['POST'])
@login_required
def api_confirm_pickup(booking_id):
    """Staff confirms equipment pickup. Updates rental_status to Picked Up.
    Body JSON: { checklist: [{item, checked}, ...], notes (optional) }
    """
    import json as _json
    data = request.get_json() or {}
    checklist = data.get('checklist', [])
    notes = data.get('notes', '').strip()
    now_str = now_myt().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db()
    b = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not b:
        conn.close()
        return jsonify({'error': 'Booking not found'}), 404

    checklist_json = _json.dumps(checklist) if checklist else None
    update_notes = notes if notes else dict(b).get('notes', '')

    conn.execute(
        """UPDATE bookings SET
           rental_status = 'Picked Up',
           status = 'active',
           actual_pickup_datetime = ?,
           pickup_confirmed_at = ?,
           checklist_json = ?,
           notes = ?
           WHERE id = ?""",
        (now_str, now_str, checklist_json, update_notes, booking_id)
    )
    conn.commit()

    # Re-fetch booking after update for email
    b_updated = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    conn.close()

    # Send pickup confirmation email in background thread
    if b_updated:
        import threading
        bd = dict(b_updated)
        camera = CAMERA_MAP.get(bd.get('camera_id', ''), {})
        bd['camera_name'] = camera.get('name', bd.get('camera_id', 'Camera'))
        bd['actual_pickup_datetime'] = now_str

        # Parse accessories
        accessories = []
        if bd.get('accessories_json'):
            try:
                accessories = _json.loads(bd['accessories_json'])
            except Exception:
                pass
        bd['accessories'] = accessories

        # Calculate days
        try:
            sd = datetime.strptime(bd['start_date'], '%Y-%m-%d')
            ed = datetime.strptime(bd['end_date'], '%Y-%m-%d')
            bd['days'] = max((ed - sd).days, 1)
        except Exception:
            bd['days'] = 1

        # Calculate return deadline = actual pickup time + (num_days × 24h)
        try:
            pickup_dt = datetime.strptime(now_str, '%Y-%m-%d %H:%M:%S')
            return_deadline_dt = pickup_dt + timedelta(hours=24 * bd['days'])
            bd['return_deadline_display'] = return_deadline_dt.strftime('%d %b %Y (%A) %I:%M %p')
            bd['return_time_for_agreement'] = return_deadline_dt.strftime('%H:%M')
        except Exception:
            bd['return_deadline_display'] = f"{bd.get('end_date', '')} same time as pickup"

        def _send_pickup_email(booking_dict):
            try:
                from email_sender import send_pickup_confirmation_email
                send_pickup_confirmation_email(booking_dict)
            except Exception as e:
                app.logger.error(f"Pickup email error for {booking_dict.get('booking_ref')}: {e}")

        threading.Thread(target=_send_pickup_email, args=(bd,), daemon=True).start()
        app.logger.info(f"Pickup confirmation email queued for {bd.get('booking_ref')}")

    return jsonify({'success': True, 'rental_status': 'Picked Up', 'pickup_confirmed_at': now_str})


@app.route('/api/booking/<int:booking_id>/process-return', methods=['POST'])
@login_required
def api_process_return(booking_id):
    """Staff processes equipment return. Updates rental_status to Returned.
    Body JSON: { condition_ok: bool, notes (optional), deposit_refunded: bool }
    """
    import json as _json
    data = request.get_json() or {}
    condition_ok = data.get('condition_ok', True)
    notes = data.get('notes', '').strip()
    deposit_refunded = data.get('deposit_refunded', False)
    now_str = now_myt().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db()
    b = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not b:
        conn.close()
        return jsonify({'error': 'Booking not found'}), 404

    bd = dict(b)
    new_notes = notes if notes else bd.get('notes', '')
    deposit_status = 'refunded' if deposit_refunded else bd.get('deposit_status', 'unpaid')

    conn.execute(
        """UPDATE bookings SET
           rental_status = 'Returned',
           status = 'returned',
           return_processed_at = ?,
           deposit_status = ?,
           notes = ?
           WHERE id = ?""",
        (now_str, deposit_status, new_notes, booking_id)
    )
    conn.commit()
    conn.close()

    # Generate WhatsApp thank-you link
    camera = CAMERA_MAP.get(bd.get('camera_id', ''), {})
    camera_name = camera.get('name', bd.get('camera_id', ''))
    wa_link = wa.admin_thank_you(bd, camera_name)

    return jsonify({
        'success': True,
        'rental_status': 'Returned',
        'return_processed_at': now_str,
        'wa_thankyou_link': wa_link
    })


@app.route('/api/booking/<int:booking_id>/update-payment-status', methods=['POST'])
@login_required
def api_update_payment_status(booking_id):
    """Update payment status for a booking (e.g., mark as paid at counter)."""
    data = request.get_json() or {}
    payment_status = data.get('payment_status', '').strip()
    deposit_status = data.get('deposit_status', '').strip()

    if not payment_status and not deposit_status:
        return jsonify({'error': 'payment_status or deposit_status required'}), 400

    conn = get_db()
    updates = []
    params = []
    if payment_status:
        updates.append('payment_status = ?')
        params.append(payment_status)
    if deposit_status:
        updates.append('deposit_status = ?')
        params.append(deposit_status)
    params.append(booking_id)
    conn.execute(f"UPDATE bookings SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/booking/<int:booking_id>/update-rental-status', methods=['POST'])
@login_required
def api_update_rental_status(booking_id):
    """Update rental status for a booking."""
    data = request.get_json() or {}
    rental_status = data.get('rental_status', '').strip()
    valid_statuses = ['Pending Pickup', 'Picked Up', 'Returned', 'Overdue', 'Cancelled']
    if rental_status not in valid_statuses:
        return jsonify({'error': f'Invalid rental_status. Must be one of: {valid_statuses}'}), 400

    conn = get_db()
    conn.execute("UPDATE bookings SET rental_status = ? WHERE id = ?", (rental_status, booking_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'rental_status': rental_status})


# ─── Payment Gateway Routes ──────────────────────────────────────────────────

def _get_base_url():
    """Get the public base URL for callbacks/redirects."""
    return request.host_url.rstrip('/')

def _get_booking_for_payment(booking_ref):
    """Fetch booking and enrich with camera info."""
    conn = get_db()
    b = conn.execute("SELECT * FROM bookings WHERE booking_ref = ?", (booking_ref,)).fetchone()
    conn.close()
    if not b:
        return None
    bd = dict(b)
    camera = CAMERA_MAP.get(bd['camera_id'], {})
    bd['camera_name'] = camera.get('name', bd['camera_id'])
    bd['days'] = max((datetime.strptime(bd['end_date'], '%Y-%m-%d') - datetime.strptime(bd['start_date'], '%Y-%m-%d')).days, 1)
    return bd

def _send_booking_notifications(booking_ref):
    """Send email and log WhatsApp link for confirmed booking (runs in background thread)."""
    try:
        from email_sender import send_booking_confirmation_email
        conn = get_db()
        b = conn.execute('SELECT * FROM bookings WHERE booking_ref = ?', (booking_ref,)).fetchone()
        conn.close()
        if not b:
            return
        bd = dict(b)
        camera = CAMERA_MAP.get(bd['camera_id'], {})
        bd['camera_name'] = camera.get('name', bd['camera_id'])
        bd['num_days'] = max((datetime.strptime(bd['end_date'], '%Y-%m-%d') - datetime.strptime(bd['start_date'], '%Y-%m-%d')).days, 1)
        bd['price_per_day'] = bd.get('price_per_day') or 0
        bd['total_price'] = bd.get('total_price') or 0
        bd['deposit_amount'] = bd.get('deposit_amount') or 200

        # Send confirmation email with PDF invoice
        if bd.get('customer_email'):
            send_booking_confirmation_email(bd)
            app.logger.info(f'Confirmation email sent for {booking_ref}')
        else:
            app.logger.info(f'No email for {booking_ref}, skipping email')

        # Log WhatsApp link for customer notification
        wa_link = wa.customer_booking_confirmed_with_invoice(bd, bd['camera_name'])
        app.logger.info(f'Customer WA link for {booking_ref}: {wa_link}')

    except Exception as e:
        app.logger.error(f'Notification error for {booking_ref}: {e}')


def _mark_booking_paid(booking_ref, method, transaction_id=''):
    """Mark a booking as confirmed after successful RM30 booking fee payment."""
    conn = get_db()
    now = now_myt().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        "UPDATE bookings SET status='confirmed', deposit_status='paid' WHERE booking_ref=? AND status='pending'",
        (booking_ref,)
    )
    conn.execute(
        "INSERT INTO payments (booking_ref, amount, type, method, status, reference, created_at, verified_at, verified_by) "
        "VALUES (?, 30, 'booking_fee', ?, 'verified', ?, ?, ?, 'auto')",
        (booking_ref, method, transaction_id, now, now)
    )
    conn.commit()
    conn.close()

    # Send notifications in background thread (non-blocking)
    t = threading.Thread(target=_send_booking_notifications, args=(booking_ref,), daemon=True)
    t.start()

@app.route('/api/payment/gateway-status')
def api_gateway_status():
    """GET /api/payment/gateway-status — check which gateways are available."""
    return jsonify(pg.get_gateway_status())

# --- ToyyibPay routes ---

@app.route('/api/payment/toyyibpay/create', methods=['POST'])
def api_toyyibpay_create():
    """POST /api/payment/toyyibpay/create — create ToyyibPay Bill for FPX payment.
    Body JSON: { booking_ref }
    """
    data = request.get_json(force=True)
    booking_ref = data.get('booking_ref')
    if not booking_ref:
        return jsonify({'success': False, 'error': 'booking_ref required'}), 400

    bd = _get_booking_for_payment(booking_ref)
    if not bd:
        return jsonify({'success': False, 'error': 'Booking not found'}), 404
    if bd.get('status') != 'pending':
        return jsonify({'success': False, 'error': 'Booking is not pending payment'}), 400

    result = pg.toyyibpay_create_bill(bd, _get_base_url())
    return jsonify(result)


@app.route('/payment/toyyibpay/return')
def toyyibpay_return():
    """ToyyibPay redirect after payment (return URL).
    GET params: status_id (1=success, 2=pending, 3=fail), billcode, order_id, transaction_id
    """
    status_id = request.args.get('status_id', '')
    billcode = request.args.get('billcode', '')
    order_id = request.args.get('order_id', '')
    transaction_id = request.args.get('transaction_id', '')

    app.logger.info(f'ToyyibPay return: status={status_id}, billcode={billcode}, order_id={order_id}')

    if status_id == '1' and order_id:
        # Payment successful — order_id is our booking_ref (billExternalReferenceNo)
        _mark_booking_paid(order_id, 'toyyibpay_fpx', transaction_id or billcode)
        return redirect(f'/booking/{order_id}?payment=success')
    elif status_id == '2':
        # Pending
        if order_id:
            return redirect(f'/booking/{order_id}?payment=pending')
        return redirect('/?payment=pending')
    else:
        # Failed or cancelled
        if order_id:
            return redirect(f'/booking/{order_id}?payment=cancelled')
        return redirect('/?payment=error')


@app.route('/payment/toyyibpay/callback', methods=['POST'])
def toyyibpay_callback():
    """ToyyibPay server-side callback (backend-to-backend).
    POST params: refno, status, reason, billcode, order_id, amount, transaction_time
    Status: 1=success, 2=pending, 3=fail
    """
    result = pg.toyyibpay_verify_callback(request.form.to_dict())
    app.logger.info(f'ToyyibPay callback: {result}')

    if result.get('paid'):
        booking_ref = result.get('order_id', '')
        if booking_ref:
            _mark_booking_paid(booking_ref, 'toyyibpay_fpx', result.get('refno', result.get('billcode', '')))
            app.logger.info(f'ToyyibPay payment confirmed for {booking_ref}')

    return 'OK', 200


# --- Stripe routes ---

@app.route('/api/payment/stripe/create', methods=['POST'])
def api_stripe_create():
    """POST /api/payment/stripe/create — create Stripe Checkout Session.
    Body JSON: { booking_ref }
    """
    data = request.get_json(force=True)
    booking_ref = data.get('booking_ref')
    if not booking_ref:
        return jsonify({'success': False, 'error': 'booking_ref required'}), 400

    bd = _get_booking_for_payment(booking_ref)
    if not bd:
        return jsonify({'success': False, 'error': 'Booking not found'}), 404
    if bd.get('status') != 'pending':
        return jsonify({'success': False, 'error': 'Booking is not pending payment'}), 400

    result = pg.stripe_create_checkout(bd, _get_base_url())
    return jsonify(result)

@app.route('/payment/stripe/success')
def stripe_success():
    """Stripe redirect after successful payment."""
    session_id = request.args.get('session_id', '')
    booking_ref = request.args.get('booking_ref', '')

    if session_id and booking_ref:
        result = pg.stripe_get_session(session_id)
        if result.get('paid'):
            _mark_booking_paid(booking_ref, 'stripe_card', session_id)

    return redirect(f'/booking/{booking_ref}?payment=success')

@app.route('/payment/stripe/cancel')
def stripe_cancel():
    """Stripe redirect after cancelled payment."""
    booking_ref = request.args.get('booking_ref', '')
    return redirect(f'/booking/{booking_ref}?payment=cancelled')

@app.route('/payment/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Stripe webhook for payment events (backup to redirect)."""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature', '')

    result = pg.stripe_verify_webhook(payload, sig_header)
    if not result.get('success'):
        return 'Invalid signature', 400

    event = result['event']
    if isinstance(event, dict):
        event_type = event.get('type', '')
        event_data = event.get('data', {}).get('object', {})
    else:
        event_type = event.type
        event_data = event.data.object

    if event_type == 'checkout.session.completed':
        metadata = event_data.get('metadata', {}) if isinstance(event_data, dict) else dict(event_data.metadata)
        booking_ref = metadata.get('booking_ref', '')
        if booking_ref:
            _mark_booking_paid(booking_ref, 'stripe_card', event_data.get('id', '') if isinstance(event_data, dict) else event_data.id)

    return 'OK', 200

# --- Billplz routes ---

@app.route('/api/payment/billplz/create', methods=['POST'])
def api_billplz_create():
    """POST /api/payment/billplz/create — create Billplz Bill for FPX/DuitNow.
    Body JSON: { booking_ref }
    """
    data = request.get_json(force=True)
    booking_ref = data.get('booking_ref')
    if not booking_ref:
        return jsonify({'success': False, 'error': 'booking_ref required'}), 400

    bd = _get_booking_for_payment(booking_ref)
    if not bd:
        return jsonify({'success': False, 'error': 'Booking not found'}), 404
    if bd.get('status') != 'pending':
        return jsonify({'success': False, 'error': 'Booking is not pending payment'}), 400

    result = pg.billplz_create_bill(bd, _get_base_url())
    return jsonify(result)

@app.route('/payment/billplz/redirect')
def billplz_redirect():
    """Billplz redirect after payment (client-side, not guaranteed)."""
    result = pg.billplz_verify_redirect(request.args.to_dict())

    # Find booking ref from bill
    bill_id = result.get('bill_id', '')
    booking_ref = ''

    if result.get('paid') and result.get('verified'):
        # Look up booking ref from payments or try to get from bill
        conn = get_db()
        p = conn.execute("SELECT booking_ref FROM payments WHERE reference LIKE ?", (f"%{bill_id}%",)).fetchone()
        if p:
            booking_ref = p['booking_ref']
        else:
            # Try to get from Billplz bill reference_1
            bill_info = pg.billplz_get_bill(bill_id)
            if bill_info.get('success'):
                booking_ref = bill_info.get('reference_1', '')
        conn.close()

        if booking_ref:
            _mark_booking_paid(booking_ref, 'billplz_fpx', bill_id)
            return redirect(f'/booking/{booking_ref}?payment=success')

    # Fallback: try to find booking from recent payments
    return redirect(f'/booking/{booking_ref}?payment=pending' if booking_ref else '/?payment=error')

@app.route('/payment/billplz/callback', methods=['POST'])
def billplz_callback():
    """Billplz server-side callback (guaranteed, backend-to-backend)."""
    result = pg.billplz_verify_callback(request.form.to_dict())

    if result.get('paid') and result.get('verified'):
        bill_id = result.get('bill_id', '')
        # Get booking ref from Billplz bill
        bill_info = pg.billplz_get_bill(bill_id)
        booking_ref = bill_info.get('reference_1', '') if bill_info.get('success') else ''

        if booking_ref:
            _mark_booking_paid(booking_ref, 'billplz_fpx', result.get('transaction_id', bill_id))

    return 'OK', 200

# --- Dev mode checkout simulation pages ---

@app.route('/payment/stripe/dev-checkout')
def stripe_dev_checkout():
    """Dev mode: simulated Stripe checkout page."""
    booking_ref = request.args.get('booking_ref', '')
    bd = _get_booking_for_payment(booking_ref)
    if not bd:
        abort(404)
    return render_template('payment_dev_checkout.html',
                           booking=bd, gateway='stripe',
                           gateway_label='Stripe (Card Payment)',
                           gateway_icon='💳')

@app.route('/payment/billplz/dev-checkout')
def billplz_dev_checkout():
    """Dev mode: simulated Billplz FPX/DuitNow checkout page."""
    booking_ref = request.args.get('booking_ref', '')
    bd = _get_booking_for_payment(booking_ref)
    if not bd:
        abort(404)
    return render_template('payment_dev_checkout.html',
                           booking=bd, gateway='billplz',
                           gateway_label='Billplz (FPX / DuitNow)',
                           gateway_icon='🏦')

@app.route('/payment/dev-simulate', methods=['POST'])
def dev_simulate_payment():
    """Dev mode: simulate successful or failed payment."""
    booking_ref = request.form.get('booking_ref', '')
    gateway = request.form.get('gateway', 'stripe')
    action = request.form.get('action', 'success')

    if action == 'success' and booking_ref:
        method = 'stripe_card' if gateway == 'stripe' else 'billplz_fpx'
        _mark_booking_paid(booking_ref, method, f"dev_sim_{booking_ref}")
        return redirect(f'/booking/{booking_ref}?payment=success')
    else:
        return redirect(f'/booking/{booking_ref}?payment=cancelled')

# ─── Public booking confirmation page ────────────────────────────────────────
@app.route('/booking/<booking_ref>')
def booking_confirmation(booking_ref):
    """Public page: booking confirmation / status check"""
    import json as _json
    conn = get_db()
    b = conn.execute("SELECT * FROM bookings WHERE booking_ref = ?", (booking_ref,)).fetchone()
    is_accessory_booking = False
    if not b:
        # Check accessory_bookings table
        b = conn.execute("SELECT * FROM accessory_bookings WHERE booking_ref = ?", (booking_ref,)).fetchone()
        is_accessory_booking = True if b else False
    conn.close()
    if not b:
        abort(404)
    bd = dict(b)

    if is_accessory_booking:
        bd['camera_name'] = 'Accessories Rental'
        bd['camera_image'] = 'accessories/selfie_stick_1m.jpg'
        bd['days'] = max((datetime.strptime(bd['end_date'], '%Y-%m-%d') - datetime.strptime(bd['start_date'], '%Y-%m-%d')).days, 1)
    else:
        camera = CAMERA_MAP.get(bd['camera_id'], {})
        bd['camera_name'] = camera.get('name', bd['camera_id'])
        bd['camera_image'] = camera.get('image', '')
        bd['days'] = max((datetime.strptime(bd['end_date'], '%Y-%m-%d') - datetime.strptime(bd['start_date'], '%Y-%m-%d')).days, 1)

    # Parse accessories
    bd['accessories'] = []
    if bd.get('accessories_json'):
        try:
            bd['accessories'] = _json.loads(bd['accessories_json'])
        except:
            pass

    # Generate WhatsApp links
    wa_links = {
        'send_proof': wa.customer_send_payment_proof(bd),
        'enquiry': wa.customer_enquiry(bd),
        'pickup_enquiry': wa.customer_pickup_enquiry(bd),
    }

    # Payment status from redirect
    payment_status = request.args.get('payment', '')

    # Gateway status
    gateway_status = pg.get_gateway_status()

    return render_template('booking_confirmation.html', booking=bd, wa_links=wa_links,
                           payment_status=payment_status, gateway_status=gateway_status,
                           is_accessory_booking=is_accessory_booking)

# ─── SEO Landing Pages ───────────────────────────────────────────────────────
@app.route('/gopro-rental-langkawi')
def seo_gopro_rental():
    return render_template('seo_gopro_rental_langkawi.html')

@app.route('/insta360-rental-langkawi')
def seo_insta360_rental():
    return render_template('seo_insta360_rental_langkawi.html')

@app.route('/dji-action-camera-rental-langkawi')
def seo_dji_rental():
    return render_template('seo_dji_action_camera_rental_langkawi.html')

@app.route('/camera-rental-pantai-cenang')
def seo_pantai_cenang():
    return render_template('seo_camera_rental_pantai_cenang.html')

@app.route('/things-to-do-in-langkawi-with-gopro')
def seo_things_to_do():
    return render_template('seo_things_to_do_langkawi_gopro.html')

# ─── Blog Routes ─────────────────────────────────────────────────────────────
from blog_engine import load_all_posts, load_post, get_related_posts

@app.route('/blog')
def blog_hub():
    posts = load_all_posts()
    return render_template('blog.html', posts=posts)

@app.route('/blog/<slug>')
def blog_post(slug):
    post = load_post(slug)
    if not post:
        abort(404)
    all_posts = load_all_posts()
    related = get_related_posts(slug, all_posts, count=3)
    return render_template(
        'blog_post.html',
        post=post,
        content=post['content_html'],
        toc=post['toc'],
        related_posts=related
    )

# ─── Sitemap & Robots ───────────────────────────────────────────────────────
from flask import make_response
from blog_engine import get_all_slugs as get_blog_slugs

@app.route('/sitemap.xml')
def sitemap():
    base = 'https://www.gearzonthego.com'
    pages = [
        ('/', '1.0', 'daily'),
        ('/blog', '0.9', 'weekly'),
        ('/gopro-rental-langkawi', '0.8', 'monthly'),
        ('/insta360-rental-langkawi', '0.8', 'monthly'),
        ('/dji-action-camera-rental-langkawi', '0.8', 'monthly'),
        ('/camera-rental-pantai-cenang', '0.8', 'monthly'),
        ('/things-to-do-in-langkawi-with-gopro', '0.8', 'monthly'),
    ]
    for slug in get_blog_slugs():
        pages.append((f'/blog/{slug}', '0.7', 'monthly'))

    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, priority, freq in pages:
        xml_lines.append(f'  <url>')
        xml_lines.append(f'    <loc>{base}{path}</loc>')
        xml_lines.append(f'    <changefreq>{freq}</changefreq>')
        xml_lines.append(f'    <priority>{priority}</priority>')
        xml_lines.append(f'  </url>')
    xml_lines.append('</urlset>')
    resp = make_response('\n'.join(xml_lines))
    resp.headers['Content-Type'] = 'application/xml'
    return resp

@app.route('/robots.txt')
def robots():
    content = 'User-agent: *\nAllow: /\nSitemap: https://www.gearzonthego.com/sitemap.xml\n'
    resp = make_response(content)
    resp.headers['Content-Type'] = 'text/plain'
    return resp

## ─── 3-Hour Return Reminder Scheduler ───────────────────────────────────────
import time as _time

def _parse_return_datetime(end_date_str, return_time_str):
    """Parse end_date + return_time into a datetime object.
    Tries multiple time formats. Falls back to 11:00 PM."""
    rt_clean = (return_time_str or '').strip()
    for fmt in ('%I:%M %p', '%H:%M', '%I %p', '%I:%M%p', '%I%p'):
        try:
            t = datetime.strptime(rt_clean.upper(), fmt)
            d = datetime.strptime(end_date_str, '%Y-%m-%d')
            return d.replace(hour=t.hour, minute=t.minute, second=0)
        except ValueError:
            continue
    # Default: 11:00 PM on end_date
    d = datetime.strptime(end_date_str, '%Y-%m-%d')
    return d.replace(hour=23, minute=0, second=0)


def _return_reminder_scheduler():
    """Background thread: checks every 5 minutes for active bookings.
    1. Sends 24-hour return reminder email before return deadline.
    2. Sends 2-hour return reminder email before return deadline.
    3. Auto-marks overdue bookings."""
    _time.sleep(30)  # Wait 30s after startup before first check
    while True:
        try:
            with app.app_context():
                from email_sender import send_return_reminder_email
                now = now_myt()
                conn = get_db()
                active_bookings = conn.execute(
                    """SELECT * FROM bookings
                       WHERE status = 'active'
                         AND customer_email IS NOT NULL
                         AND customer_email != ''"""
                ).fetchall()
                conn.close()

                for row in active_bookings:
                    bd = dict(row)

                    actual_pickup_str = bd.get('actual_pickup_datetime', '') or ''
                    start_date_str = bd.get('start_date', '')
                    end_date_str = bd.get('end_date', '')

                    try:
                        start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
                        end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
                        num_days = max((end_dt - start_dt).days, 1)
                    except Exception:
                        num_days = 1

                    if actual_pickup_str:
                        try:
                            pickup_dt = datetime.strptime(actual_pickup_str, '%Y-%m-%d %H:%M:%S')
                        except Exception:
                            try:
                                pickup_dt = datetime.strptime(actual_pickup_str, '%Y-%m-%d %H:%M')
                            except Exception:
                                pickup_dt = None
                    else:
                        pickup_dt = None

                    if pickup_dt:
                        # Return deadline = pickup time + (num_days × 24 hours)
                        return_deadline = pickup_dt + timedelta(hours=24 * num_days)
                    else:
                        # Fallback: end_date at same time as booking pickup_time, or 11:00 PM
                        return_time_str = bd.get('return_time', '') or '23:00'
                        return_deadline = _parse_return_datetime(end_date_str, return_time_str)

                    minutes_until_return = (return_deadline - now).total_seconds() / 60

                    # Auto-mark overdue if past return deadline
                    if minutes_until_return < 0 and bd.get('rental_status') == 'Picked Up':
                        conn2 = get_db()
                        conn2.execute(
                            "UPDATE bookings SET rental_status='Overdue' WHERE id=?",
                            (bd['id'],)
                        )
                        conn2.commit()
                        conn2.close()
                        app.logger.info(f"Booking {bd.get('booking_ref')} marked as Overdue")

                    camera = CAMERA_MAP.get(bd.get('camera_id', ''), {})
                    bd['camera_name'] = camera.get('name', bd.get('camera_id', ''))
                    bd['return_time'] = return_deadline.strftime('%I:%M %p')
                    bd['return_date_display'] = return_deadline.strftime('%d %b %Y (%A), %I:%M %p')

                    # Send 24-hour reminder (23h to 25h before return)
                    if (bd.get('return_reminder_24h_sent') or 0) == 0 and 1380 <= minutes_until_return <= 1500:
                        ok = send_return_reminder_email(bd)
                        if ok:
                            conn2 = get_db()
                            conn2.execute(
                                "UPDATE bookings SET return_reminder_24h_sent = 1 WHERE id = ?",
                                (bd['id'],)
                            )
                            conn2.commit()
                            conn2.close()
                            app.logger.info(
                                f"24h return reminder sent for booking {bd.get('booking_ref')}"
                            )

                    # Parse accessories for reminder email
                    import json as _json2
                    bd_accessories = []
                    if bd.get('accessories_json'):
                        try:
                            bd_accessories = _json2.loads(bd['accessories_json'])
                        except Exception:
                            pass
                    bd['accessories'] = bd_accessories

                    # Send 2-hour reminder (1h45m to 2h15m before return)
                    if (bd.get('return_reminder_sent') or 0) == 0 and 105 <= minutes_until_return <= 135:
                        ok = send_return_reminder_email(bd)
                        if ok:
                            conn2 = get_db()
                            conn2.execute(
                                "UPDATE bookings SET return_reminder_sent = 1 WHERE id = ?",
                                (bd['id'],)
                            )
                            conn2.commit()
                            conn2.close()
                            app.logger.info(
                                f"2h return reminder sent for booking {bd.get('booking_ref')} "
                                f"(return deadline: {return_deadline})"
                            )
        except Exception as e:
            try:
                app.logger.error(f"Return reminder scheduler error: {e}")
            except Exception:
                pass
        _time.sleep(300)  # Check every 5 minutes


# ─── Initialise DB ────────────────────────────────────────────────────────────
with app.app_context():
    init_db()

# Start return reminder scheduler in background thread
_reminder_thread = threading.Thread(target=_return_reminder_scheduler, daemon=True)
_reminder_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
