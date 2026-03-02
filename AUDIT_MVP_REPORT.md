# Gearz On The Go — System Audit & MVP Upgrade Plan

## PART 1: CURRENT SYSTEM AUDIT

### 1.1 Routes & Pages Inventory

| Route | Type | Purpose | Status |
|-------|------|---------|--------|
| `GET /` | Public | Landing page — catalog, availability checker, WhatsApp links | **Static-only** (no real booking) |
| `GET /api/availability/<camera_id>` | Public API | Returns booked dates for a camera | **Working** |
| `GET /api/check` | Public API | Checks if date range is available + calculates price | **Working** |
| `GET/POST /staff/login` | Staff | Password-based login (gearz2026) | **Working** |
| `GET /staff` | Staff | Dashboard — add bookings (Walk-in/Pre-book), view list | **Working** |
| `POST /staff/add` | Staff | Create new booking + auto-create customer | **Working** |
| `GET/POST /staff/booking/<id>/update` | Staff | Update pre-book with photos, then sign | **Working** |
| `POST /staff/delete/<id>` | Staff | Delete a booking | **Working** |
| `GET /staff/customers` | Staff | Customer database list | **Working** |
| `GET/POST /staff/customers/add` | Staff | Add customer manually | **Working** |
| `GET /staff/customers/<id>` | Staff | Customer profile (photos, agreements, history) | **Working** |
| `GET/POST /staff/customers/<id>/edit` | Staff | Edit customer | **Working** |
| `POST /staff/customers/<id>/delete` | Staff | Delete customer | **Working** |
| `GET /staff/agreements` | Staff | List all signed agreements | **Working** |
| `GET /staff/agreements/new` | Staff | New agreement form with signature pad | **Working** |
| `POST /staff/agreements/save` | Staff | Save signed agreement (JSON API) | **Working** |
| `GET /staff/agreements/<id>` | Staff | View signed agreement | **Working** |
| `POST /staff/agreements/<id>/delete` | Staff | Delete agreement | **Working** |

### 1.2 Database Schema (SQLite)

**3 tables exist:**
- `bookings` — 14 columns (camera_id, dates, times, customer info, photos, mode)
- `customers` — 12 columns (name, phone, ID, photos, agreement status)
- `agreements` — 15 columns (customer info, equipment, dates, signature, deposit)

### 1.3 What Is Currently STATIC ONLY (No Real Booking)

1. **Public landing page (`/`)** — Customer can only:
   - Browse catalog & prices
   - Check availability (date checker works against DB)
   - Click WhatsApp link to contact staff manually
   - **NO self-service booking form**
   - **NO payment/deposit collection**
   - **NO booking confirmation page**

2. **Availability checker** — Works correctly but result only shows "Tempah via WhatsApp" button

3. **Pricing** — Hardcoded in CAMERAS list (per-day pricing by duration tier: 1/2/3/5+ days)

### 1.4 What Already Works Well (Reusable)

- Availability checking logic (`get_booked_dates`, `/api/check`)
- Double-booking prevention (staff panel already checks conflicts)
- Camera catalog with pricing tiers
- Staff dashboard (Walk-in / Pre-book flows)
- Customer database with photos
- Digital agreement with signature pad
- Bilingual UI (Malay/English toggle)

---

## PART 2: GAP ANALYSIS — What's Missing for Real Auto-Booking

| # | Gap | Priority | Complexity |
|---|-----|----------|------------|
| 1 | **Public booking form** — Customer fills name, phone, dates, selects camera | CRITICAL | Medium |
| 2 | **Deposit payment** — RM200 online payment to confirm booking | CRITICAL | Medium-High |
| 3 | **Booking confirmation page** — Shows booking details + receipt | CRITICAL | Low |
| 4 | **WhatsApp notification** — Auto-send confirmation to customer AND admin | CRITICAL | Low |
| 5 | **Booking status tracking** — pending → confirmed → active → returned | HIGH | Medium |
| 6 | **Staff: block dates** — Manually block dates for maintenance/personal use | HIGH | Low |
| 7 | **Staff: mark returned** — Update booking status when equipment returned | HIGH | Low |
| 8 | **Deposit refund tracking** — Track deposit status (held/refunded/forfeited) | MEDIUM | Low |
| 9 | **Email confirmation** — Optional backup to WhatsApp | LOW | Low |
| 10 | **Customer login** — View own bookings (optional for MVP) | LOW | Medium |

---

## PART 3: MVP UPGRADE PLAN

### 3.1 Recommended Tech Stack (Fastest MVP)

| Component | Choice | Reason |
|-----------|--------|--------|
| **Backend** | Flask (keep existing) | Already built, working well |
| **Database** | SQLite (keep existing) | Sufficient for single-shop operation |
| **Frontend** | TailwindCSS + vanilla JS (keep existing) | Mobile-first, fast, no build step |
| **Payment** | **Stripe Checkout** or **ToyyibPay** (Malaysian) | Stripe: global cards. ToyyibPay: FPX (Malaysian bank transfer) — both have simple redirect-based checkout |
| **WhatsApp** | **WhatsApp API URL scheme** (`wa.me`) | Free, no API key needed, opens WhatsApp with pre-filled message |
| **Hosting** | Render.com (keep existing plan) | Free tier sufficient |

> **Recommendation:** Start with **ToyyibPay** for Malaysian market (FPX is preferred by locals) OR **Stripe** for international tourists. Both support redirect-based payment — no complex integration needed.

> **Alternative (Simplest):** Manual bank transfer + WhatsApp confirmation. Customer books → gets bank details → sends payment proof via WhatsApp → staff confirms. This is the FASTEST to implement.

### 3.2 MVP Implementation Steps (6 Steps)

#### Step 1: Add Booking Status System
- Add `status` column to bookings: `pending` → `confirmed` → `active` → `returned` → `cancelled`
- Add `deposit_status` column: `unpaid` → `paid` → `refunded` → `forfeited`
- Add `booking_ref` column: unique reference code (e.g., GZ-20260301-001)

#### Step 2: Build Public Booking Form
- Replace "Tempah via WhatsApp" with real booking form
- Form fields: Camera (pre-selected), Dates (pre-filled from checker), Name, Phone, IC/Passport
- On submit: create booking with status=`pending`, show deposit payment instructions

#### Step 3: Deposit Payment Flow
**Option A — Manual Transfer (Fastest):**
- Show bank account details (Maybank/CIMB)
- Customer transfers RM200 and sends screenshot via WhatsApp
- Staff confirms payment in dashboard → status changes to `confirmed`

**Option B — ToyyibPay/Stripe (Auto):**
- Redirect to payment page after booking
- On successful payment callback → auto-confirm booking
- On failed/cancelled → booking stays `pending` (auto-cancel after 30 min)

#### Step 4: Booking Confirmation + WhatsApp Notification
- After booking created: show confirmation page with booking ref, details, payment instructions
- Auto-generate WhatsApp message links:
  - To customer: "Your booking GZ-xxx is confirmed! Pickup: [date] [time] at Gearz On The Go, Langkawi"
  - To admin: "New booking GZ-xxx from [name] for [camera] on [dates]"
- Button to open WhatsApp with pre-filled message

#### Step 5: Staff Panel Upgrades
- Add **status badges** on booking list (Pending/Confirmed/Active/Returned)
- Add **"Confirm Payment"** button for pending bookings
- Add **"Mark Returned"** button with deposit refund option
- Add **"Block Dates"** feature — create a booking with type=`blocked`
- Filter bookings by status

#### Step 6: Calendar View Enhancement
- Show blocked dates in red on public availability checker
- Show pending bookings as "tentatively booked" (yellow)
- Show confirmed bookings as "booked" (red)

### 3.3 Estimated Effort

| Step | Effort | Can Ship Independently? |
|------|--------|------------------------|
| Step 1: Status system | 1 hour | No (foundation) |
| Step 2: Public booking form | 2-3 hours | Yes (with manual payment) |
| Step 3A: Manual transfer | 30 min | Yes |
| Step 3B: ToyyibPay/Stripe | 3-4 hours | Yes |
| Step 4: Confirmation + WhatsApp | 1-2 hours | Yes |
| Step 5: Staff panel upgrades | 2-3 hours | Yes |
| Step 6: Calendar enhancement | 1 hour | Yes |

**Total MVP (with manual payment): ~7-8 hours**
**Total MVP (with auto payment): ~10-12 hours**

### 3.4 Recommended MVP Sequence

```
Phase 1 (Core): Steps 1 + 2 + 3A + 4
→ Customer can book online, pay via bank transfer, get WhatsApp confirmation
→ Staff can view and manage bookings

Phase 2 (Polish): Steps 5 + 6
→ Better staff workflow, calendar improvements

Phase 3 (Auto Payment): Step 3B
→ Add ToyyibPay/Stripe when ready
```

---

## PART 4: DECISION NEEDED FROM YOU

Before I start building, please confirm:

1. **Payment method for MVP:**
   - **A) Manual bank transfer** (fastest — customer transfers to your Maybank/CIMB, sends proof via WhatsApp)
   - **B) ToyyibPay** (Malaysian FPX — auto-confirm, needs ToyyibPay account)
   - **C) Stripe** (international cards — auto-confirm, needs Stripe account)

2. **Bank details** (if Option A): Account name, bank name, account number

3. **Admin WhatsApp number**: Currently using 60124662939 — is this correct?

4. **Should customers be able to cancel their own bookings?** (Yes/No)

5. **Auto-cancel unpaid bookings after how long?** (30 min / 1 hour / 24 hours / manual only)
