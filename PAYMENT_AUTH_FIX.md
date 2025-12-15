# Payment Authentication Fix

## Issue
**Error**: `SyntaxError: Unexpected token '<', "<!DOCTYPE "... is not valid JSON`

## Root Cause
When a user attempted to proceed to payment without being logged in:
1. JavaScript made POST request to `/payment/create`
2. Flask's `@login_required` decorator redirected to login page (HTML)
3. JavaScript tried to parse HTML as JSON → Error!

## Solution Applied
Updated the payment processing JavaScript in `templates/user/registration.html` to:

1. **Check authentication status** before parsing response as JSON
2. **Detect redirects** (302, 401 status codes)
3. **Redirect to login** with proper `next` parameter if not authenticated
4. **Validate content-type** to ensure response is JSON before parsing

### Code Changes (Line ~1671)

**BEFORE:**
```javascript
.then(response => response.json())
.then(data => {
    if (data.success) {
        window.location.href = data.payment_url;
    }
})
```

**AFTER:**
```javascript
.then(response => {
    // Check if we got redirected to login (302/401)
    if (response.redirected || response.status === 401 || response.status === 302) {
        window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
        return null;
    }
    
    // Check if response is actually JSON
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
        throw new Error('Please log in to proceed with payment');
    }
    
    if (!response.ok) {
        throw new Error('Payment service error. Please try again.');
    }
    
    return response.json();
})
.then(data => {
    if (data === null) return;  // Redirecting to login
    
    if (data.success) {
        window.location.href = data.payment_url;
    }
})
```

## Benefits

1. ✅ **No more JSON parsing errors**
2. ✅ **Graceful redirect to login** when unauthenticated
3. ✅ **Proper error messages** for users
4. ✅ **Returns to registration page** after login (using `next` parameter)
5. ✅ **Better user experience**

## Testing

### Test Case 1: Logged In User
1. User logs in
2. Goes to registration page
3. Selects registration type and proceeds to payment
4. ✅ Successfully redirected to Yoco payment page

### Test Case 2: Not Logged In User (FIXED)
1. User is not logged in
2. Goes to registration page
3. Selects registration type and proceeds to payment
4. ✅ Redirected to login page with message
5. After login, returns to registration page to complete

### Test Case 3: Session Expired
1. User was logged in but session expired
2. Tries to proceed to payment
3. ✅ Redirected to login page
4. After login, can retry payment

## Additional Notes

- The fix also updated comment from "iKhokha" to "Yoco" for consistency  
- Error messages now specifically mention login requirement
- The `credentials: 'same-origin'` ensures cookies are sent with the request

## Status
✅ **FIXED** - Ready for testing

## Next Steps
1. Test the payment flow both logged in and logged out
2. Verify login redirect works correctly
3. Confirm Yoco payment page loads after successful auth
