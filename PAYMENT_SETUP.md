# Payment Gateway Setup Guide — Gearz On The Go

## Overview

The deposit payment system supports **three payment methods**:

| Method | Gateway | Status | Fees |
|--------|---------|--------|------|
| **FPX / DuitNow** | Billplz | Dev Mode (simulated) | 1% per transaction |
| **Card (Visa/MC)** | Stripe | Dev Mode (simulated) | 2.9% + RM1.00 |
| **Manual Bank Transfer** | Maybank | Active | Free |

Currently running in **Dev/Sandbox Mode** — no real payments are processed. Both Stripe and Billplz show simulated checkout pages where you can test success/failure flows.

---

## Option 1: Billplz (FPX / DuitNow) — Recommended for Malaysia

### Why Billplz?

Billplz is a Malaysian payment gateway that supports **FPX (online banking)** and **DuitNow QR** — the two most popular payment methods in Malaysia. It is widely used by Malaysian SMEs and has simple API integration.

### Setup Steps

1. **Create a Billplz account** at [https://www.billplz.com](https://www.billplz.com)
2. **Get Sandbox API keys** from [https://www.billplz-sandbox.com](https://www.billplz-sandbox.com) for testing
3. **Create a Collection** in the Billplz dashboard (this groups your bills)
4. **Set environment variables** on your server:

```bash
# For sandbox testing
export BILLPLZ_API_KEY="your-sandbox-api-key"
export BILLPLZ_COLLECTION_ID="your-sandbox-collection-id"
export BILLPLZ_X_SIGNATURE="your-x-signature-key"
export BILLPLZ_SANDBOX=true

# For production (after testing)
export BILLPLZ_API_KEY="your-live-api-key"
export BILLPLZ_COLLECTION_ID="your-live-collection-id"
export BILLPLZ_X_SIGNATURE="your-live-x-signature-key"
export BILLPLZ_SANDBOX=false
```

5. **Restart the server** — the system will auto-detect the keys and switch from dev mode to live mode

### Billplz Pricing

- **FPX**: 1% per transaction (min RM1)
- **DuitNow QR**: 1% per transaction
- No monthly fees, no setup fees

---

## Option 2: Stripe (Card Payments)

### Setup Steps

1. **Create a Stripe account** at [https://dashboard.stripe.com/register](https://dashboard.stripe.com/register)
2. **Get API keys** from [https://dashboard.stripe.com/apikeys](https://dashboard.stripe.com/apikeys)
3. **Set environment variables**:

```bash
# For testing (use test keys from Stripe dashboard)
export STRIPE_SECRET_KEY="sk_test_..."
export STRIPE_PUBLISHABLE_KEY="pk_test_..."

# For production
export STRIPE_SECRET_KEY="sk_live_..."
export STRIPE_PUBLISHABLE_KEY="pk_live_..."
```

4. **Set up webhook** in Stripe Dashboard:
   - Go to Developers → Webhooks → Add endpoint
   - URL: `https://yourdomain.com/api/payment/stripe/webhook`
   - Events: `checkout.session.completed`
   - Copy the webhook signing secret and set:

```bash
export STRIPE_WEBHOOK_SECRET="whsec_..."
```

5. **Restart the server**

### Stripe Pricing (Malaysia)

- **Cards**: 2.9% + RM1.00 per transaction
- **International cards**: 3.9% + RM1.00
- No monthly fees

---

## How It Works (Technical Flow)

### Customer Payment Flow

```
Customer selects payment method on confirmation page
    ├── FPX/DuitNow → POST /api/payment/billplz/create
    │   └── Redirect to Billplz checkout → Callback → Auto-confirm booking
    ├── Card → POST /api/payment/stripe/create
    │   └── Redirect to Stripe Checkout → Webhook → Auto-confirm booking
    └── Bank Transfer → Shows bank details + WhatsApp proof button
        └── Staff manually confirms via dashboard
```

### Auto-Confirmation

When payment succeeds via Stripe or Billplz:
1. Payment record created in `payments` table (status: `verified`)
2. Booking status updated to `confirmed`
3. Deposit status updated to `paid`
4. Customer redirected to confirmation page with success message

### Dev Mode Behavior

When API keys are not configured:
- "DEV MODE" badges appear on payment options
- Clicking pay redirects to a simulated checkout page
- "Simulate Successful Payment" instantly confirms the booking
- "Simulate Failed/Cancelled" returns to confirmation page with error message
- No real money is charged

---

## Environment Variables Summary

| Variable | Required | Description |
|----------|----------|-------------|
| `STRIPE_SECRET_KEY` | For Stripe | Stripe secret key (sk_test_... or sk_live_...) |
| `STRIPE_PUBLISHABLE_KEY` | For Stripe | Stripe publishable key (pk_test_... or pk_live_...) |
| `STRIPE_WEBHOOK_SECRET` | For Stripe | Stripe webhook signing secret |
| `BILLPLZ_API_KEY` | For Billplz | Billplz API key |
| `BILLPLZ_COLLECTION_ID` | For Billplz | Billplz collection ID |
| `BILLPLZ_X_SIGNATURE` | For Billplz | Billplz X-Signature key for callback verification |
| `BILLPLZ_SANDBOX` | For Billplz | Set to `true` for sandbox, `false` for production |

---

## Testing Checklist

- [x] FPX/DuitNow dev checkout — successful payment
- [x] FPX/DuitNow dev checkout — failed/cancelled payment
- [x] Stripe dev checkout — successful payment
- [x] Stripe dev checkout — failed/cancelled payment
- [x] Manual bank transfer — shows bank details + WhatsApp button
- [x] Auto-confirmation after successful payment (status → confirmed)
- [x] Payment record created in database
- [x] Booking stays pending after cancelled payment
- [x] Payment selection UI with 3 options
- [x] "Dev Mode" badges visible when keys not configured

---

## Going Live Checklist

1. [ ] Sign up for Billplz and/or Stripe
2. [ ] Get production API keys
3. [ ] Set environment variables on production server
4. [x] Bank account updated: **552152001924** (Gear Etc Sdn Bhd, Maybank)
5. [ ] Test with real sandbox transactions
6. [ ] Switch to production keys
7. [ ] Set up Stripe webhook endpoint
8. [ ] Set up Billplz callback URL in dashboard
9. [ ] Monitor first few real transactions
