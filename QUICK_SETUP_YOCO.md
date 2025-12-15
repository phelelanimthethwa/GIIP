# Quick Setup Guide - Yoco Payment Gateway

## Immediate Next Steps

### 1. Update Your .env File

Add these lines to your `.env` file:

```env
# Yoco Payment Gateway Configuration
YOCO_SECRET_KEY=demo
YOCO_PUBLIC_KEY=demo
YOCO_WEBHOOK_SECRET=demo_webhook_secret

# Optional - defaults provided (uncomment to customize)
# YOCO_BASE_URL=https://payments.yoco.com
# YOCO_RETURN_URL=https://globalconference.co.za/payment/callback
# YOCO_CANCEL_URL=https://globalconference.co.za/payment/cancelled
```

**Note**: Using `demo` as values will enable demo mode for testing without real API keys.

### 2. Test the Integration

Restart your application and test the payment flow:

```powershell
# Stop your current Flask app (Ctrl+C if running)

# Start the Flask app again
python app.py
```

### 3. Try a Test Payment

1. Navigate to the registration page
2. Select a conference and registration type
3. Proceed to payment
4. In **demo mode**, you'll see a test payment page where you can simulate success or failure
5. Click "Simulate Successful Payment" to test the complete flow

---

## When Ready for Production

### Get Real Yoco API Keys

#### Development/Testing (Test Mode)
1. Visit https://developer.yoco.com/
2. Sign in or create a Yoco developer account
3. Navigate to **API Keys** section
4. Copy your **Test Secret Key** (starts with `sk_test_`)
5. Copy your **Test Public Key** (starts with `pk_test_`)

#### Production (Live Mode)
1. Ensure you have a verified Yoco business account
2. In the same API Keys section
3. Copy your **Live Secret Key** (starts with `sk_live_`)
4. Copy your **Live Public Key** (starts with `pk_live_`)

### Update .env for Production

Replace the demo values with real keys:

```env
YOCO_SECRET_KEY=sk_live_your_actual_secret_key
YOCO_PUBLIC_KEY=pk_live_your_actual_public_key
YOCO_WEBHOOK_SECRET=your_webhook_secret_from_yoco_dashboard
```

### Configure Webhooks

1. Go to Yoco Developer Dashboard → **Webhooks**
2. Click "Create Webhook"
3. Set webhook URL: `https://globalconference.co.za/payment/webhook`
4. Select events to monitor:
   - `payment.succeeded`
   - `payment.failed`
   - `payment.cancelled`
5. Save and copy the **Webhook Secret**
6. Update `YOCO_WEBHOOK_SECRET` in your `.env`

---

## Verification Checklist

- [ ] `.env` file updated with Yoco credentials (demo or real)
- [ ] Application restarted successfully
- [ ] Can access registration page without errors
- [ ] Can initiate payment flow
- [ ] Demo payment page works (if using demo mode)
- [ ] Payment success flow completes and creates registration
- [ ] Payment failure is handled gracefully
- [ ] Logs show Yoco-related messages (not iKhokha)

---

## Test Cards (When Using Real Test Keys)

When using Yoco test API keys, use these test card numbers:

### Successful Payment
- **Card Number**: 4242 4242 4242 4242
- **Expiry**: Any future date (e.g., 12/25)
- **CVV**: Any 3 digits (e.g., 123)

### Failed Payment
- **Card Number**: 4000 0000 0000 0002
- **Expiry**: Any future date
- **CVV**: Any 3 digits

### Requires 3D Secure
- **Card Number**: 4000 0027 6000 3184
- **Expiry**: Any future date
- **CVV**: Any 3 digits

More test cards: https://developer.yoco.com/online/resources/test-cards-and-bank-accounts

---

## Common Commands

### Restart Application
```powershell
# Stop current process (Ctrl+C)
python app.py
```

### Check Logs for Payment Activity
Your application will log:
- Payment creation requests
- API responses from Yoco
- Verification results
- Webhook events

Look for lines like:
```
Making Yoco payment request for amount: R500.00
Yoco API Response: 200
Yoco payment checkout created successfully
```

### View Environment Variables (to verify)
```powershell
Get-Content .env | Select-String "YOCO"
```

---

## Troubleshooting

### "Payment service not configured"
- Check that `YOCO_SECRET_KEY` and `YOCO_PUBLIC_KEY` are set in `.env`
- Restart the application after updating `.env`

### Payment creation returns 401/403
- Verify your API keys are correct
- Check you're using test keys for testing, live keys for production
- The system will automatically fall back to demo mode if authentication fails

### Webhook not receiving events
- Ensure webhook URL is publicly accessible
- Verify `YOCO_WEBHOOK_SECRET` matches the value in Yoco dashboard
- Check Yoco dashboard webhook logs for delivery status

### Amount shown incorrectly
- Yoco uses cents internally but the service converts automatically
- Verify `registration_fees` are configured correctly in Firebase
- Check that amounts in database are in rands (not cents)

---

## Files Changed

✅ **New Files:**
- `services/yoco_service.py` - Yoco payment integration
- `PAYMENT_GATEWAY_MIGRATION.md` - Detailed migration guide
- `QUICK_SETUP_YOCO.md` - This file

✅ **Modified Files:**
- `config.py` - Updated to use Yoco configuration
- `app.py` - Import and references updated to Yoco

✅ **Preserved Files:**
- `services/ikhokha_service.py` - Kept for reference/rollback

---

## Demo Mode Features

When using `YOCO_SECRET_KEY=demo`:
- No real API calls are made
- Payment redirects to `/payment/demo` page
- You can simulate success/failure/cancellation
- Perfect for development and testing UI/UX
- No Yoco account needed

---

## Need Help?

- **Yoco Documentation**: https://developer.yoco.com/
- **Yoco Support**: https://www.yoco.com/support/
- **Migration Guide**: See `PAYMENT_GATEWAY_MIGRATION.md` for detailed information

---

**Status**: ✅ Migration Complete  
**Ready to Test**: Yes (with demo mode)  
**Ready for Production**: Update `.env` with real keys
