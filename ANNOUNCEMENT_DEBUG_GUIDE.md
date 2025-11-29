# Announcement Feature - Debug Guide & Fixes Applied

**Date**: October 26, 2025  
**Issue**: Announcements feature displays "Internal error"  
**Status**: FIXES APPLIED - TESTING REQUIRED

---

## Issues Identified & Fixed

### 1. ✅ **Timezone Datetime Formatting Function - FIXED**

**File**: `app.py` (lines 142-176)  
**Function**: `format_datetime_with_timezone()`

**Problems Found**:
- Function could return `None` without validation
- Invalid timezone names weren't handled gracefully
- Error messages were not detailed enough
- No fallback datetime format

**Fixes Applied**:
```python
# Added input validation
if not all([date_str, time_str, timezone_str]):
    raise ValueError(f"Missing required datetime parameters...")

# Added timezone validation with fallback
try:
    tz = pytz.timezone(timezone_str)
except Exception as tz_error:
    print(f"Warning: Invalid timezone '{timezone_str}', using UTC instead")
    tz = pytz.UTC

# Added fallback datetime format if all else fails
try:
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return dt.isoformat()
except:
    return None
```

**Enhanced Logging**:
```
Successfully formatted datetime: 2025-10-26T14:30:00+02:00
Error formatting datetime - date_str: ..., time_str: ..., tz: ..., Error: ...
```

---

### 2. ✅ **Create Announcement Function - ENHANCED ERROR HANDLING**

**File**: `app.py` (lines 2486-2680)  
**Function**: `create_announcement()`

**Problems Found**:
- No validation of formatted_datetime result
- Image save errors could crash the whole function
- Email failures not handled gracefully
- Generic error messages
- No comprehensive logging

**Fixes Applied**:

#### A. Enhanced datetime formatting validation:
```python
formatted_datetime = format_datetime_with_timezone(
    scheduled_date,
    scheduled_time,
    timezone
)

if not formatted_datetime:
    print("WARNING: formatted_datetime is None or empty, using fallback")
    formatted_datetime = f"{scheduled_date}T{scheduled_time}:00"
```

#### B. Image upload error handling:
```python
try:
    # ... save image code ...
except Exception as img_error:
    print(f"Warning: Failed to save image: {str(img_error)}")
    # Continue without image, don't fail the whole announcement
```

#### C. Firebase save with detailed error handling:
```python
try:
    announcements_ref = db.reference('announcements')
    new_announcement = announcements_ref.push(announcement)
    announcement_id = new_announcement.key
    print(f"✓ Announcement saved successfully with ID: {announcement_id}")
except Exception as firebase_error:
    print(f"✗ Firebase error: {str(firebase_error)}")
    # Return specific error to user
    error_msg = f"Firebase save error: {str(firebase_error)}"
```

#### D. Email failures don't block announcement creation:
```python
# Send email notification if requested
email_status = None
if should_send_email:
    try:
        # ... email code ...
        email_status = f"Email notifications sent successfully to {len(recipient_emails)} recipients."
    except Exception as e:
        email_status = f"Warning: {error_msg}"  # Don't fail, just warn
```

**New Logging Format**:
```
============================================================
Creating new announcement...
============================================================
Received form data: {...}
Formatting datetime: date=2025-10-26, time=14:30, tz=Africa/Johannesburg
Formatted datetime result: 2025-10-26T14:30:00+02:00
Announcement data prepared: {...}
Saving announcement to Firebase...
✓ Announcement saved successfully with ID: abc123def456
Sending email notifications...
Found 5 recipients for email notification
✓ Email notifications sent successfully to 5 recipients.
============================================================
Announcement creation COMPLETE - AJAX: true
============================================================
```

---

### 3. ✅ **Email Sending Function - ENHANCED VALIDATION**

**File**: `app.py` (lines 2435-2483)  
**Function**: `send_email()`

**Problems Found**:
- Email settings errors would crash the announcement
- No validation of email configuration
- Unclear error messages
- Missing email settings handling

**Fixes Applied**:

#### A. Email settings validation:
```python
settings = settings_ref.get()

if not settings:
    print("[EMAIL] WARNING: Email settings not configured in Firebase")
    print("[EMAIL] Email sending skipped - configure email_settings in Firebase")
    return False

# Validate required settings
required_settings = ['smtp_host', 'smtp_port', 'email', 'password']
missing_settings = [s for s in required_settings if not settings.get(s)]

if missing_settings:
    print(f"[EMAIL] ERROR: Missing email settings: {missing_settings}")
    raise ValueError(f"Missing email settings in Firebase: {missing_settings}")
```

#### B. Enhanced logging with [EMAIL] prefix:
```
[EMAIL] Starting send_email to 5 recipient(s)
[EMAIL] Subject: New Announcement: Important Update
[EMAIL] Email settings found in Firebase
[EMAIL] Configuring Flask-Mail with SMTP: smtp.gmail.com:587
[EMAIL] Message created - Recipients: ['user1@example.com', ...]
[EMAIL] Adding 1 attachments
[EMAIL] Sending via Flask-Mail...
[EMAIL] ✓ Email sent successfully to 5 recipient(s)
```

#### C. Graceful error handling - doesn't break announcements:
```python
except Exception as e:
    print(f"[EMAIL] ✗ Error sending email: {str(e)}")
    traceback.print_exc()
    # Don't re-raise, just log and return False
    return False
```

---

## How to Test the Fixes

### Step 1: Check Logging in Terminal/Console

Run the Flask application in development mode:

```bash
python app.py
```

or

```bash
flask run
```

**Look for these log patterns** indicating successful operation:

```
============================================================
Creating new announcement...
============================================================
[✓] Announcement saved successfully with ID: ...
[✓] Email notifications sent successfully to ... recipients.
============================================================
Announcement creation COMPLETE
============================================================
```

### Step 2: Create a Test Announcement

1. Log in to Admin Dashboard
2. Go to **Announcements** → **New Announcement**
3. Fill in the form:
   - **Title**: "Test Announcement"
   - **Content**: "This is a test announcement"
   - **Type**: "Information"
   - **Date**: Today
   - **Time**: Current time
   - **Timezone**: "Africa/Johannesburg" (or your timezone)
   - Leave **Image** empty (optional)
   - **Uncheck "Send Email"** (for initial testing without email config)
4. Click **Save Announcement**

### Step 3: Verify in Terminal/Browser Console

#### Terminal Output Should Show:
```
============================================================
Creating new announcement...
============================================================
Received form data: {'title': 'Test Announcement', ...}
Formatting datetime: date=2025-10-26, time=14:30, tz=Africa/Johannesburg
Formatted datetime result: 2025-10-26T14:30:00+02:00
Announcement data prepared: {...}
Saving announcement to Firebase...
✓ Announcement saved successfully with ID: -NxYz1A2B3C4D5E6F7G
============================================================
Announcement creation COMPLETE - AJAX: true
============================================================
```

#### Browser Console Should Show:
```javascript
// Network tab: POST /admin/announcements
Response Status: 200 OK
Response JSON: {
    "success": true,
    "id": "-NxYz1A2B3C4D5E6F7G",
    "emailStatus": null,
    "redirect": "/admin/announcements"
}
```

#### Browser Page Should Show:
- ✅ "Announcement created successfully!" message
- ✅ Page redirects to announcements list
- ✅ New announcement appears in the grid

### Step 4: Verify in Firebase

1. Open Firebase Console
2. Navigate to **Realtime Database** → **announcements**
3. Should see new entry with structure:
```json
{
  "-NxYz1A2B3C4D5E6F7G": {
    "title": "Test Announcement",
    "content": "This is a test announcement",
    "type": "information",
    "is_pinned": false,
    "image_url": null,
    "scheduled_date": "2025-10-26",
    "scheduled_time": "14:30",
    "timezone": "Africa/Johannesburg",
    "formatted_datetime": "2025-10-26T14:30:00+02:00",
    "created_at": "2025-10-26T...",
    "created_by": "admin@example.com",
    "updated_at": "2025-10-26T..."
  }
}
```

---

## Troubleshooting Issues

### Issue: Still Getting "Internal Error"

1. **Check Terminal Output**:
   - Look for error messages with [EMAIL] prefix
   - Look for stack traces between the `=====` lines
   - Copy the full error and check logs below

2. **Common Errors & Solutions**:

#### ❌ Error: `ValueError: Missing required datetime parameters`
**Cause**: Form submitted without date/time  
**Solution**: Ensure all date/time fields are filled in the form

#### ❌ Error: `pytz.exceptions.UnknownTimeZoneError: 'Invalid/Timezone'`
**Cause**: Invalid timezone value  
**Solution**: Select a valid timezone from the dropdown (already fixed with UTC fallback)

#### ❌ Error: `Firebase save error: ...`
**Cause**: Firebase database connection issue  
**Solution**:
- Verify `serviceAccountKey.json` exists
- Check Firebase security rules allow writes to `announcements` path
- Verify `FIREBASE_DATABASE_URL` is correct in config

#### ❌ Error: `[EMAIL] Missing email settings`
**Cause**: Email settings not configured  
**Solution**: This is OK for testing - just don't check "Send Email" checkbox

---

## Configuration Checklist

### Required for Full Functionality

- [ ] **Firebase**: Database connection working
- [ ] **Static Uploads**: Directory `static/uploads/announcements/` has write permission
- [ ] **Email Settings** (optional): Configure in admin panel if you want email notifications
- [ ] **Admin User**: Must be logged in as admin

### Optional for Enhanced Features

- [ ] **Email Settings**: Configured for email notifications
- [ ] **Email Templates**: Custom templates for announcements

---

## Next Steps

1. **Test announcement creation** with the steps above
2. **Monitor logs** for any ERROR messages
3. **Check Firebase** for data persistence
4. **Test with email** enabled once basic functionality works
5. **Report any issues** with full error logs

---

## Files Modified

- `app.py`:
  - `format_datetime_with_timezone()` - Enhanced with validation and logging
  - `send_email()` - Enhanced with settings validation and logging
  - `create_announcement()` - Comprehensive error handling and logging

**Total changes**: ~200 lines added for better error handling and logging

---

**Document Version**: 1.0  
**Last Updated**: October 26, 2025  
**Status**: Ready for Testing
