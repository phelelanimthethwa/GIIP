# Auto Date-Based Conference Filtering

## Overview
This document describes the auto date-based filtering system implemented for conferences. This system ensures that past conferences are automatically marked correctly even if administrators forget to update the status manually.

## Problem Statement
Previously, if an administrator set a conference status to "active" or "upcoming" but forgot to change it after the event ended, the system would continue to show it with the incorrect status. This could lead to:
- Users trying to register for past events
- Confusion about which conferences are actually available
- Poor user experience

## Solution
Implemented automatic date-based status computation that **always prioritizes date logic over admin-provided status**, with special rules for past events.

## Implementation Details

### Date-Based Status Logic

The system uses the following logic to determine conference status:

```
1. IF conference end_date has passed:
   → ALWAYS mark as 'past' (overrides admin status)
   
2. ELSE IF current time is before start_date:
   → Mark as 'upcoming' (unless admin explicitly set as 'active' for early registration)
   
3. ELSE IF current time is between start_date and end_date:
   → Mark as 'active' (conference is ongoing)
   
4. ELSE (if no dates available):
   → Use admin-provided status
```

### Key Features

1. **Forced Past Status**: Once a conference's end date passes, it is **always** marked as 'past', regardless of what the admin set.

2. **Draft Privacy**: Draft conferences are automatically excluded from the public `/conferences` page. They only appear in the admin dashboard.

3. **Timezone-Aware**: All date comparisons use South African Standard Time (SAST - UTC+02:00) for consistency.

4. **Auto-Disable Registration**: Past conferences automatically have:
   - `registration_enabled` set to `false`
   - `paper_submission_enabled` set to `false`

5. **Early Registration Support**: Admins can set upcoming conferences as 'active' to enable early registration/submissions.

6. **Synonym Normalization**: The system normalizes common status synonyms:
   - 'future', 'scheduled', 'soon' → 'upcoming'
   - 'open', 'live' → 'active'
   - 'closed', 'ended', 'finished' → 'past'

## Affected Routes

The auto date-based filtering has been implemented in the following routes:

### 1. `/conferences` (Public Conference Discovery)
**File**: `app.py` - `conference_discover()` function (lines 6769-7007)

**Behavior**:
- Displays all conferences with accurate, date-based status
- **Draft conferences are automatically hidden from public view** (only visible to admins)
- Filters can show: All, Active (Open for Registration), Upcoming, or Past Events
- Past conferences show "🔴 Past Event" badge

### 2. `/admin/conferences` (Admin Dashboard)
**File**: `app.py` - `admin_conferences()` function (lines 7312-7419)

**Behavior**:
- Categorizes conferences into Active, Upcoming, and Past sections
- Each conference's status is auto-computed based on dates
- Shows registration counts for each conference
- Past conferences are automatically moved to the "Past" section

### 3. `/registration` (Public Registration Page)
**File**: `app.py` - `registration()` function (lines 1203-1330)

**Behavior**:
- Only shows conferences that are 'active' or 'upcoming'
- Automatically filters out past conferences
- Auto-disables registration for past events
- Provides debug logging for conference filtering

## Date Parsing

The system supports multiple date formats:
- ISO 8601 format: `2025-07-15T09:00:00Z`
- Simple date format: `2025-07-15`
- Timezone-aware and timezone-naive inputs (defaults to SAST if no timezone)

## User Interface Updates

### Conference Badges
Added proper styling for all status types:
- 🟢 **Open** (active) - Green badge
- 🟡 **Upcoming** - Yellow badge
- 🔴 **Past Event** - Red badge
- ⚪ **Draft** - Gray badge

### Frontend Filtering
The `/conferences` page includes JavaScript-based filters:
- All Conferences
- Open for Registration
- Upcoming
- Past Events

These filters work with the `data-status` attribute on conference cards.

## Benefits

1. **No Manual Status Updates Required**: Conferences automatically transition to 'past' status after their end date
2. **Prevents User Confusion**: Users cannot attempt to register for past events
3. **Consistent Experience**: Status is always accurate across all pages
4. **Admin Override Where Needed**: Admins can still enable early registration by setting status to 'active'
5. **Timezone Consistency**: All date comparisons use the same timezone (SAST)
6. **Draft Privacy**: Draft conferences are automatically hidden from public view, only visible in admin dashboard

## Testing Recommendations

To test this feature:

### Test 1: Past Conference Auto-Detection
1. **Create a test conference** with dates that have passed
2. **Set its status** to 'active' or 'upcoming' in the admin panel
3. **View the conference** on `/conferences` - it should show as "🔴 Past Event"
4. **Check registration page** (`/registration`) - it should NOT appear
5. **Check admin dashboard** (`/admin/conferences`) - it should appear in the "Past" section

### Test 2: Draft Conference Privacy
1. **Create a draft conference** (set status to 'draft' or leave dates empty)
2. **View the public conferences page** (`/conferences`) - draft should NOT appear
3. **Check admin dashboard** (`/admin/conferences`) - draft should appear
4. **Try to access the draft directly** via URL - should work for admins only

### Test 3: Status Synonym Normalization
1. **Create a conference** and set status to 'open', 'closed', or 'future'
2. **View the conference** - status should be normalized to 'active', 'past', or 'upcoming'

### Test 4: Early Registration for Upcoming Events
1. **Create an upcoming conference** (start date in future)
2. **Set status to 'active'** manually
3. **Enable registration**
4. **Check registration page** - it should appear and allow registration

## Code References

### Main Implementation Locations

1. **Conference Discovery Route**:
   - File: `app.py`
   - Function: `conference_discover()`
   - Lines: 6956-7007

2. **Admin Conferences Route**:
   - File: `app.py`
   - Function: `admin_conferences()`
   - Lines: 7366-7413

3. **Registration Route**:
   - File: `app.py`
   - Function: `registration()`
   - Lines: 1260-1292

4. **Template Updates**:
   - File: `templates/conferences/discover.html`
   - Lines: 34-46 (status badges)
   - Lines: 252-256 (status styling)

## Future Enhancements

Potential improvements for future versions:

1. **Admin Notifications**: Show a warning in the admin panel when a conference status has been auto-corrected
2. **Status History**: Log when status changes occur (manual vs automatic)
3. **Configurable Grace Period**: Allow admins to set a grace period after end_date before auto-marking as past
4. **Email Notifications**: Notify admins when conferences automatically transition to 'past' status
5. **Bulk Status Update Tool**: Admin tool to review and update multiple conference statuses

## Maintenance Notes

- The date parsing logic is duplicated in three routes. Consider extracting to a utility function for easier maintenance.
- The SAST timezone is hardcoded. If the system needs to support multiple timezones, this should be made configurable.
- Debug logging is extensive in the registration route. Consider reducing verbosity in production.

## Version
- **Implementation Date**: October 11, 2025
- **Version**: 1.0
- **Author**: AI Assistant

