# iKhokha Payment Gateway Integration

This document describes the iKhokha payment gateway integration that replaces the previous proof-of-payment file upload system.

## Overview

The system now uses iKhokha's secure payment gateway to process conference registration payments in real-time. Users no longer need to upload proof of payment files - payments are processed instantly through the secure payment gateway.

## Features

- **Secure Online Payments**: SSL-encrypted payment processing through iKhokha
- **Real-time Payment Processing**: Instant payment confirmation and registration completion
- **Multiple Payment Methods**: Credit cards, debit cards, and EFT supported
- **Automatic Registration**: Successful payments automatically complete registration
- **Transaction Tracking**: All payments tracked with unique transaction IDs
- **Admin Dashboard**: Enhanced admin interface showing payment transaction details

## Configuration

### 1. iKhokha Account Setup

1. Sign up for an iKhokha merchant account at https://www.ikhokha.com/
2. Complete the merchant verification process
3. Obtain your API credentials from the merchant dashboard:
   - App ID
   - Secret Key  
   - Webhook Secret

### 2. Environment Variables

Copy `.env.example` to `.env` and configure the following variables:

```bash
# iKhokha Configuration
IKHOKHA_APP_ID=your_app_id_here
IKHOKHA_SECRET_KEY=your_secret_key_here
IKHOKHA_BASE_URL=https://api.ikhokha.com/v2
IKHOKHA_WEBHOOK_SECRET=your_webhook_secret_here

# Callback URLs (adjust for your domain)
IKHOKHA_RETURN_URL=https://yourdomain.com/payment/callback
IKHOKHA_CANCEL_URL=https://yourdomain.com/payment/cancelled
```

### 3. Dependencies Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## How It Works

### Registration Flow

1. **User Registration**: User selects conference, registration type, and additional options
2. **Payment Initiation**: User clicks "Proceed to Payment" button
3. **Payment Session**: System creates secure payment session with iKhokha
4. **Payment Processing**: User is redirected to iKhokha's secure payment page
5. **Payment Completion**: After successful payment, user is redirected back to the site
6. **Registration Completion**: System automatically creates registration record with payment details

### Payment States

- **Pending**: Payment session created but not completed
- **Paid**: Payment successfully processed through iKhokha
- **Failed**: Payment failed or was cancelled
- **Refunded**: Payment was refunded (manual process)

### Database Schema Changes

New fields added to registration records:

```json
{
  "payment_method": "ikhokha",
  "payment_id": "ikhokha_payment_id",
  "transaction_reference": "REG_USER123_1234567890",
  "payment_date": "2024-01-01T12:00:00.000Z",
  "payment_status": "paid"
}
```

Legacy `payment_proof` field is maintained for backward compatibility with existing registrations.

## API Endpoints

### Payment Creation
- **POST** `/payment/create`
- Creates iKhokha payment session
- Requires authentication
- Returns payment URL for redirection

### Payment Callbacks
- **GET** `/payment/callback` - Success/failure callback from iKhokha
- **GET** `/payment/cancelled` - User cancelled payment
- **POST** `/payment/webhook` - iKhokha webhook notifications

## Admin Interface Changes

### Registration Management

The admin interface now shows:
- **Payment Method**: Online Payment vs Legacy File Upload
- **Transaction Details**: Transaction reference, payment ID, payment date
- **Payment Status**: Real-time payment status from iKhokha
- **Legacy Support**: Still displays old payment proof files for existing records

### Export Functionality

CSV exports now include:
- Payment method (Online Payment vs File Uploaded)
- Transaction reference for online payments
- Payment processing date

## Testing

### Development Testing

For development, you can:
1. Use iKhokha's sandbox/test environment (if available)
2. Configure test callback URLs pointing to your local development server
3. Use tools like ngrok to expose local server for webhook testing

### Production Deployment

1. Ensure all production URLs are configured correctly
2. Test webhook endpoints are accessible from iKhokha servers
3. Verify SSL certificates are valid for callback URLs
4. Test the complete payment flow with small amounts

## Security Considerations

1. **Webhook Verification**: All webhooks are verified using HMAC signatures
2. **HTTPS Required**: All callback URLs must use HTTPS in production
3. **Secure Session Storage**: Payment session data is stored securely in Flask sessions
4. **Input Validation**: All payment amounts are validated against registration fees
5. **Transaction Logging**: All payment activities are logged for audit trails

## Troubleshooting

### Common Issues

1. **Payment Not Completing**: Check webhook URLs are accessible
2. **Invalid Signature Errors**: Verify webhook secret configuration
3. **Session Expired**: Increase Flask session timeout if needed
4. **Amount Mismatch**: Ensure registration fees are properly configured

### Logs and Monitoring

- Payment creation attempts are logged in application logs
- Webhook processing is logged for debugging
- Failed payments generate error logs with details
- Email notifications may fail independently of payment processing

## Migration from File Upload System

The new system is backward compatible:
- Existing registrations with payment proof files are preserved
- Admin interface shows both payment methods appropriately
- No data migration is required
- New registrations automatically use iKhokha payment flow

## Support

For iKhokha-specific issues:
- Contact iKhokha merchant support
- Check iKhokha developer documentation
- Verify merchant account status and limits

For implementation issues:
- Check application logs for error details
- Verify environment variable configuration
- Test webhook endpoints manually
- Confirm Firebase database permissions