# Payment Gateway Migration: iKhokha to Yoco

## Overview
This document outlines the migration from iKhokha to Yoco payment gateway for the GIIP Conference application.

## Changes Made

### 1. New Files Created
- **`services/yoco_service.py`**: New Yoco payment service implementation
  - Handles payment session creation
  - Payment verification
  - Webhook processing
  - Demo mode for testing

### 2. Modified Files

#### `config.py`
**Removed (iKhokha configuration):**
```python
IKHOKHA_APP_ID = os.environ.get('IKHOKHA_APP_ID')
IKHOKHA_SECRET_KEY = os.environ.get('IKHOKHA_SECRET_KEY')
IKHOKHA_BASE_URL = os.environ.get('IKHOKHA_BASE_URL', 'https://api.ikhokha.com/v2')
IKHOKHA_WEBHOOK_SECRET = os.environ.get('IKHOKHA_WEBHOOK_SECRET')
IKHOKHA_RETURN_URL = os.environ.get('IKHOKHA_RETURN_URL', 'https://globalconference.co.za/payment/callback')
IKHOKHA_CANCEL_URL = os.environ.get('IKHOKHA_CANCEL_URL', 'https://globalconference.co.za/payment/cancelled')
```

**Added (Yoco configuration):**
```python
YOCO_SECRET_KEY = os.environ.get('YOCO_SECRET_KEY')
YOCO_PUBLIC_KEY = os.environ.get('YOCO_PUBLIC_KEY')
YOCO_BASE_URL = os.environ.get('YOCO_BASE_URL', 'https://payments.yoco.com')
YOCO_WEBHOOK_SECRET = os.environ.get('YOCO_WEBHOOK_SECRET')
YOCO_RETURN_URL = os.environ.get('YOCO_RETURN_URL', 'https://globalconference.co.za/payment/callback')
YOCO_CANCEL_URL = os.environ.get('YOCO_CANCEL_URL', 'https://globalconference.co.za/payment/cancelled')
```

#### `app.py`
- Updated import: `from services.yoco_service import ...` (was `ikhokha_service`)
- Updated payment method field in registration records: `'payment_method': 'yoco'`
- Updated comments referencing Yoco instead of iKhokha
- Updated webhook signature header: `X-Yoco-Signature` (was `X-iKhokha-Signature`)

## Environment Variables Required

Add the following to your `.env` file:

```env
# Yoco Payment Gateway
YOCO_SECRET_KEY=your_yoco_secret_key_here
YOCO_PUBLIC_KEY=your_yoco_public_key_here
YOCO_WEBHOOK_SECRET=your_yoco_webhook_secret_here

# Optional - Defaults are provided
YOCO_BASE_URL=https://payments.yoco.com
YOCO_RETURN_URL=https://globalconference.co.za/payment/callback
YOCO_CANCEL_URL=https://globalconference.co.za/payment/cancelled
```

### How to Get Yoco API Keys

1. **Sign up for Yoco Account**
   - Visit https://www.yoco.com/
   - Create a business account if you don't have one

2. **Access Developer Portal**
   - Go to https://developer.yoco.com/
   - Log in with your Yoco credentials

3. **Generate API Keys**
   - Navigate to API Keys section
   - You'll find two types of keys:
     - **Public Key** (starts with `pk_`): For client-side use
     - **Secret Key** (starts with `sk_`): For server-side use (keep this secure!)
   - Use **Test Keys** (`pk_test_` and `sk_test_`) for development
   - Use **Live Keys** (`pk_live_` and `sk_live_`) for production

4. **Webhook Secret**
   - In the Webhooks section, create a new webhook
   - Set the URL to: `https://globalconference.co.za/payment/webhook`
   - Select events to monitor (typically `payment.succeeded`, `payment.failed`)
   - Copy the generated webhook secret

## API Differences Between iKhokha and Yoco

### Payment Amount
- **iKhokha**: Amounts in rands (e.g., `100.00` for R100)
- **Yoco**: Amounts in cents (e.g., `10000` for R100)
- ✅ The Yoco service automatically converts amounts to cents

### API Endpoints
- **iKhokha**: Uses `/v2/payment/create`
- **Yoco**: Uses `/api/checkouts`

### Authentication
- **iKhokha**: Uses `X-API-Key` header with HMAC signature
- **Yoco**: Uses standard `Authorization: Bearer {secret_key}` header

### Payment Status
- **iKhokha**: Returns `paid` status
- **Yoco**: Returns `complete` status (converted to `paid` in our service)

### Response Structure
- **iKhokha**: Returns `paymentUrl` and `paymentId`
- **Yoco**: Returns `redirectUrl` and checkout `id`

## Testing

### Demo Mode
The Yoco service includes a demo mode for testing without real API credentials:

1. Set `YOCO_SECRET_KEY=demo` in your `.env` file
2. Payment requests will use a mock payment page at `/payment/demo`
3. You can simulate successful or failed payments

### Test with Yoco Test Keys
1. Use `sk_test_...` and `pk_test_...` keys
2. Yoco provides test card numbers for different scenarios
3. Visit https://developer.yoco.com/online/resources/test-cards-and-bank-accounts

## Migration Steps

### For Development
1. Update `.env` file with Yoco credentials (or use `demo`)
2. Restart your Flask application
3. Test the payment flow on the registration page

### For Production
1. **Before deployment:**
   - Obtain Yoco Live API keys
   - Update production environment variables
   - Test thoroughly in staging environment

2. **During deployment:**
   - Deploy updated codebase
   - Update environment variables on your hosting platform (Render, etc.)
   - Restart the application

3. **After deployment:**
   - Test payment flow with test cards
   - Monitor logs for any errors
   - Verify webhook integration

### Update Webhooks
1. In your Yoco dashboard, configure webhook URL:
   - URL: `https://globalconference.co.za/payment/webhook`
   - Events: `payment.succeeded`, `payment.failed`, `payment.cancelled`
2. Copy webhook secret to `YOCO_WEBHOOK_SECRET` environment variable

## Database Considerations

### Existing Payment Records
- Old registrations with `payment_method: 'ikhokha'` will remain in the database
- New registrations will have `payment_method: 'yoco'`
- Both are valid and can coexist
- No database migration required

### Payment ID Format
- iKhokha payment IDs: Custom format
- Yoco checkout IDs: UUID format
- Both are stored in the same `payment_id` field

## Backwards Compatibility

The old iKhokha service file (`services/ikhokha_service.py`) has been **kept** for reference and can be:
- Used to verify old payment records
- Restored if you need to rollback
- Referenced for historical data queries

To rollback to iKhokha:
1. Update `app.py` import back to `ikhokha_service`
2. Restore iKhokha configuration in `config.py`
3. Update `.env` with iKhokha credentials

## Monitoring and Logging

The Yoco service includes comprehensive logging:
```python
logger.info(f"Making Yoco payment request for amount: R{amount}")
logger.debug(f"Request Body: {json.dumps(request_data)}")
logger.info(f"Yoco API Response: {response.status_code}")
```

Monitor your application logs for:
- Payment creation requests
- API response codes
- Verification results
- Webhook events

## Security Notes

1. **Never commit API keys** to version control
2. Keep `YOCO_SECRET_KEY` and `YOCO_WEBHOOK_SECRET` secure
3. Use test keys in development, live keys only in production
4. Webhook signatures are verified to prevent fraud
5. All payment amounts are validated server-side

## Support and Documentation

- **Yoco Developer Docs**: https://developer.yoco.com/
- **Yoco Support**: https://www.yoco.com/support/
- **API Status**: https://status.yoco.com/

## Common Issues and Solutions

### Issue: "Payment service not configured"
**Solution**: Ensure `YOCO_SECRET_KEY` and `YOCO_PUBLIC_KEY` are set in `.env`

### Issue: Payment creation fails with 401/403
**Solution**: 
- Verify API keys are correct
- Check if using test keys in production or vice versa
- System automatically falls back to demo mode

### Issue: Webhook verification fails
**Solution**: 
- Ensure `YOCO_WEBHOOK_SECRET` matches the secret in Yoco dashboard
- Check webhook URL is correctly configured in Yoco

### Issue: Amount mismatch errors
**Solution**: 
- Yoco requires amounts in cents
- The service handles conversion automatically
- Verify registration fees are configured correctly in Firebase

## Next Steps

1. ✅ Update `.env` file with Yoco credentials
2. ✅ Restart application
3. ⬜ Test payment flow
4. ⬜ Configure webhooks in Yoco dashboard
5. ⬜ Update production environment variables
6. ⬜ Deploy to production
7. ⬜ Monitor first few production transactions

---

**Migration Date**: 2025-12-14  
**Status**: ✅ Completed  
**Old Gateway**: iKhokha  
**New Gateway**: Yoco
