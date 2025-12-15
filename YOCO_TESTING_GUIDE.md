# Yoco Payment Testing Guide

## ⚠️  ISSUE IDENTIFIED

Your Yoco integration is configured but has two main issues preventing it from working:

### Issue 1: Callback URLs
Your `.env` file has production URLs:
```env
YOCO_RETURN_URL=https://globalconference.co.za/payment/callback
YOCO_CANCEL_URL=https://globalconference.co.za/payment/cancelled
```

But you're running **locally** on `http://127.0.0.1:5000`!

**Problem**: When Yoco completes payment, it tries to redirect to `https://globalconference.co.za/payment/callback`, which doesn't reach your local development server.

### Issue 2: No Logging Visibility
The Yoco service logs weren't showing in your terminal, making debugging difficult.

---

## ✅ SOLUTIONS

### Solution 1: Fix Callback URLs for Local Development

**Update your `.env` file**:

```env
# YOCO Payment Gateway
YOCO_SECRET_KEY=sk_test_d9926e213m8QpYlec6241cb92077
YOCO_PUBLIC_KEY=pk_test_b1e1db1cR4rjY2w0d214
YOCO_BASE_URL=https://payments.yoco.com
YOCO_WEBHOOK_SECRET=your-yoco-webhook-secret-here

# 🔧 FOR LOCAL DEVELOPMENT - Use localhost URLs
YOCO_RETURN_URL=http://127.0.0.1:5000/payment/callback
YOCO_CANCEL_URL=http://127.0.0.1:5000/payment/cancelled

# 🚀 FOR PRODUCTION - Use your domain
# YOCO_RETURN_URL=https://globalconference.co.za/payment/callback
# YOCO_CANCEL_URL=https://globalconference.co.za/payment/cancelled
```

### Solution 2: Better Logging (DONE ✅)

I've added print statements to `yoco_service.py` so you can see what's happening:
- 🔵 Blue messages = Normal Yoco operations
- ❌ Red messages = Errors
- ⚠️ Yellow messages = Warnings

---

## 🧪 HOW TO TEST

### Step 1: Update .env File
```env
YOCO_RETURN_URL=http://127.0.0.1:5000/payment/callback
YOCO_CANCEL_URL=http://127.0.0.1:5000/payment/cancelled
```

### Step 2: Restart Your Application
```powershell
# Stop the current app (Ctrl+C in terminal)
python app.py
```

### Step 3: Test Payment Flow

1. **Go to registration page**: http://127.0.0.1:5000/registration
2. **Select conference and type**
3. **Log in** (if not already logged in)
4. **Click "Proceed to Payment"**

Now watch your terminal for messages like:
```
🔵 YOCO: Making payment request for R500
🔵 YOCO API Response: 201
```

### Step 4: What Should Happen

#### **If Using REAL Yoco Test Keys:**
1. Terminal shows: `🔵 YOCO: Making payment request...`
2. Browser redirects to **actual Yoco payment page**
3. Use test card:
   - Card: `4242 4242 4242 4242`
   - Expiry: `12/25`
   - CVV: `123`
4. After payment, redirects back to your localhost
5. Registration is saved ✅

#### **If API Keys Are Invalid:**
1. Terminal shows: `❌ YOCO API Error 401: ...`
2. Falls back to demo mode automatically
3. Redirects to `/payment/demo`

---

## 🔍 DEBUGGING

### Check If It's Really Calling Yoco

After clicking "Proceed to Payment", look for these messages:

✅ **Good** (Real Yoco API call):
```
🔵 YOCO: Making payment request for R500
🔵 YOCO API Response: 201
```

❌ **Bad** (No API call, probably demo mode):
```
(No Yoco messages, just redirects to /payment/demo)
```

### Test Your API Keys

Run this quick test:

```powershell
# In PowerShell
$headers = @{
    "Authorization" = "Bearer sk_test_d9926e213m8QpYlec6241cb92077"
    "Content-Type" = "application/json"
}

$body = @{
    amount = 50000
    currency = "ZAR"
    successUrl = "http://127.0.0.1:5000/payment/callback"
    cancelUrl = "http://127.0.0.1:5000/payment/cancelled"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "https://payments.yoco.com/api/checkouts" -Method POST -Headers $headers -Body $body

$response.StatusCode
```

**Expected**:
- `200` or `201` = ✅ Keys are valid!
- `401` or `403` = ❌ Invalid keys

---

## 🎯 EXPECTED BEHAVIOR

### Scenario 1: Valid Yoco API Keys
1. Click "Proceed to Payment"
2. See blue Yoco messages in terminal
3. Redirect to Yoco payment page (https://pay.yoco.com/...)
4. Complete payment with test card
5. Redirect back to http://127.0.0.1:5000/payment/callback
6. Registration saved successfully

### Scenario 2: Invalid/Demo Keys
1. Click "Proceed to Payment"
2. See warning message in terminal
3. Redirect to demo payment page
4. Simulate success/failure
5. Works but doesn't show in Yoco dashboard

---

## 🚀 FOR PRODUCTION DEPLOYMENT

When deploying to production:

1. **Use localhost URLs during development**
2. **Switch to production URLs before deployment**:
   ```env
   YOCO_RETURN_URL=https://globalconference.co.za/payment/callback
   YOCO_CANCEL_URL=https://globalconference.co.za/payment/cancelled
   ```
3. **Configure webhooks in Yoco dashboard** pointing to your production URL

---

## ❓ TROUBLESHOOTING

### "Payment session expired"
- This is expected in demo mode
- With real Yoco, the session lasts longer
- Make sure you're clicking through the payment quickly

### "Never shows in Yoco dashboard"
- If using demo mode → Won't show (it's simulated)
- If using test keys → Check Yoco test dashboard
- If using live keys → Check Yoco live dashboard

### "Can't redirect back after payment"
- Check callback URLs are set to localhost during development
- Ensure your Flask app is running on the same port (5000)

---

## 📝 QUICK CHECKLIST

- [ ] `.env` has `YOCO_RETURN_URL=http://127.0.0.1:5000/payment/callback`
- [ ] `.env` has `YOCO_CANCEL_URL=http://127.0.0.1:5000/payment/cancelled`
- [ ] Yoco keys are real test keys (starting with `sk_test_` and `pk_test_`)
- [ ] Flask app is running (`python app.py`)
- [ ] Logged in to the application
- [ ] Can see blue Yoco messages in terminal when clicking "Proceed to Payment"
- [ ] Redirects to actual Yoco payment page (not `/payment/demo`)

---

**Created**: Dec 14, 2025  
**Status**: Ready to test with updated configuration
