# GIIP Conference Management System - Comprehensive Issues Report

**Generated:** December 24, 2025  
**Analysis Type:** Full Codebase Audit  
**Status Legend:**
- 🔴 **Critical** - Blocking functionality
- 🟠 **High** - Major issue affecting users
- 🟡 **Medium** - Important but not blocking
- 🔵 **Low** - Minor/cosmetic issues
- ✅ **Complete** - Fixed/Working
- ⚠️ **Needs Attention** - Partially working

---

## 📊 Executive Summary

| Category | Total | Critical | High | Medium | Low | Complete |
|----------|-------|----------|------|--------|-----|----------|
| Disconnected Pages | 5 | 1 | 2 | 2 | 0 | 0 |
| Broken Features | 7 | 1 | 3 | 2 | 1 | 0 |
| Missing Routes | 3 | 1 | 1 | 1 | 0 | 0 |
| Duplicate Files | 3 | 0 | 0 | 2 | 1 | 0 |
| Code Issues | 8 | 0 | 3 | 3 | 2 | 0 |
| **TOTAL** | **26** | **3** | **9** | **10** | **4** | **0** |

---

## 🔴 CRITICAL ISSUES

### 1. User Announcements Page - No Public Route
**Status:** 🔴 Critical  
**Priority:** P0

**Problem:** The user-facing announcements template exists at `templates/user/announcements.html` but there is NO route to access it. Users cannot view announcements from the public site.

**Location:**
- Template exists: `templates/user/announcements.html`
- Admin route exists: `/admin/announcements` (works)
- **MISSING:** Public route like `/announcements`

**Impact:** 
- Users cannot see site announcements
- Admin announcements are only visible in the admin panel
- Communication with users is broken

**Fix Required:**
```python
# Add to app.py
@app.route('/announcements')
def user_announcements():
    try:
        announcements_ref = db.reference('announcements')
        all_announcements = announcements_ref.get() or {}
        
        # Filter for published announcements
        pinned = {k: v for k, v in all_announcements.items() if v.get('is_pinned')}
        regular = {k: v for k, v in all_announcements.items() if not v.get('is_pinned')}
        
        return render_template('user/announcements.html',
                             pinned_announcements=pinned,
                             regular_announcements=regular,
                             announcements_json=json.dumps(all_announcements),
                             site_design=get_site_design())
    except Exception as e:
        return render_template('user/announcements.html',
                             pinned_announcements={},
                             regular_announcements={},
                             announcements_json='{}',
                             site_design=get_site_design())
```

**Estimated Effort:** 30 minutes

---

### 2. Firebase Service Account Key Required
**Status:** 🔴 Critical  
**Priority:** P0

**Problem:** Application cannot start without `serviceAccountKey.json` file.

**Impact:**
- Application fails to start
- All Firebase-dependent features non-functional

**Fix Required:**
1. Create `serviceAccountKey.json` from Firebase Console
2. Or set `FIREBASE_CREDENTIALS` environment variable with JSON content

---

### 3. Conference Resources Section Not Functional
**Status:** 🔴 Critical  
**Priority:** P0

**Problem:** The "Conference Resources" section on the home page shows "Coming Soon" placeholder. Users cannot access templates, guidelines, or proceedings.

**Location:** `templates/user/home.html` (line 219-263)

**Impact:**
- Users cannot download conference materials
- Paper submission process is hindered

---

## 🟠 HIGH PRIORITY ISSUES

### 4. Orphaned Downloads Template
**Status:** 🟠 High  
**Priority:** P1

**Problem:** Two different downloads templates exist:
- `templates/user/downloads.html` - Not used by any route
- `templates/user/conference/downloads.html` - Used by `/downloads` route

**Impact:**
- `templates/user/downloads.html` is orphaned (never rendered)
- Potential confusion for developers

**Fix:** Remove `templates/user/downloads.html` or consolidate

---

### 5. Video Conference Page - Non-Functional Buttons
**Status:** 🟠 High  
**Priority:** P1

**Problem:** The video conference page (`templates/user/video_conference.html`) has buttons that only show alerts:
- "Schedule Test Session" button
- "Contact Support" button

**Location:** Lines 67-74

```javascript
// Current implementation - just shows alert
button.addEventListener('click', function() {
    alert('Support team will contact you shortly.');
});
```

**Impact:** Poor user experience, no actual functionality

**Fix Required:** 
- Either remove buttons or implement actual functionality
- Add contact form integration

---

### 6. Schedule Feature - Disabled but Routes Exist
**Status:** 🟠 High  
**Priority:** P1

**Problem:** Schedule feature is disabled (hidden from menu) but routes still exist and are accessible via direct URL:
- `/admin/schedule` - Still accessible
- `/schedule` - Still accessible

**Documentation:** Per ISSUES.md #3, schedule was intentionally disabled due to functionality issues.

**Impact:**
- Security risk - hidden features still accessible
- Confusion for users who discover the routes

**Fix Required:** Either:
- Remove routes entirely
- Add proper access control
- Fix the feature

**Related Files:**
- `app.py` lines 3427-3561 (schedule routes)
- `templates/admin/schedule.html`
- `templates/user/conference/schedule.html`

---

### 7. Duplicate Site Design Templates
**Status:** 🟠 High  
**Priority:** P1

**Problem:** Two templates exist for the same purpose:
- `templates/admin/design.html` - Currently used
- `templates/admin/site_design.html` - Orphaned duplicate

**Impact:**
- Code maintenance overhead
- Potential for feature drift

**Fix:** Delete `templates/admin/site_design.html`

---

### 8. Navigation Header Links - Missing "Announcements"
**Status:** 🟠 High  
**Priority:** P1

**Problem:** The navigation header (`templates/user/components/header.html`) does not include a link to announcements, even though the template exists.

**Fix Required:** Add announcements link to navigation:
```html
<li class="nav-item">
    <a href="{{ url_for('user_announcements') }}" class="nav-link">
        <i class="fas fa-bullhorn"></i> Announcements
    </a>
</li>
```

---

### 9. User Dashboard - Broken Schedule Link
**Status:** 🟠 High  
**Priority:** P1

**Problem:** User account dashboard (`templates/user/account/dashboard.html`) has a link to `admin_schedule` which:
1. Requires admin privileges
2. The schedule feature is disabled

**Location:** Line 61
```html
<a href="{{ url_for('admin_schedule') }}" class="action-button">
```

**Impact:** Regular users clicking this will get access denied

**Fix:** Remove or fix this link for regular users

---

## 🟡 MEDIUM PRIORITY ISSUES

### 10. Downloads Route Template Mismatch
**Status:** 🟡 Medium  
**Priority:** P2

**Problem:** The `/downloads` route renders `user/conference/downloads.html` but user dashboard links to `downloads` expecting different template structure.

**Impact:** Potential display issues

---

### 11. Guest Speaker Applications - Admin Review Incomplete
**Status:** 🟡 Medium  
**Priority:** P2

**Problem:** Guest speaker application form exists but admin review workflow is basic.

**Current State:**
- `/guest-speaker-application` - Form works
- `/admin/guest-speaker-applications` - List view exists
- Status update exists but notification system unclear

**Missing:**
- Email notifications for applicants
- Automated speaker profile creation upon approval

---

### 12. Registration Form Route Naming Inconsistency
**Status:** 🟡 Medium  
**Priority:** P2

**Problem:** Two similar routes exist:
- `/registration` → `registration()` 
- `/registration-form` → `registration_form()`

**Impact:** Confusing navigation, potential broken links

---

### 13. Backup Files in Repository
**Status:** 🟡 Medium  
**Priority:** P2

**Problem:** Backup files exist in root directory:
- `app.py.backup` (202KB)
- `app.py.bak` (182KB)

**Impact:**
- Repository bloat
- Sensitive information exposure risk

**Fix:** Delete files, add to `.gitignore`

---

### 14. Accidental Git Files in Repository
**Status:** 🟡 Medium  
**Priority:** P2

**Problem:** Files that appear to be redirected git command output:
- `h origin master` (git branch output)
- `tatus -s` (git status output)
- `er.name` (git config output)

**Fix:** Delete these files immediately

---

### 15. Conference Proceedings - User Access Limited
**Status:** 🟡 Medium  
**Priority:** P2

**Problem:** Conference proceedings admin interface exists but user access to download proceedings may be limited.

**Location:** 
- Admin: `/admin/conference-proceedings`
- User: `/conference-proceedings`

---

### 16. Email Template Customization UI
**Status:** 🟡 Medium  
**Priority:** P2

**Problem:** Email templates system exists but admin UI for customization is basic.

**Missing:**
- Rich text editor for templates
- Preview functionality
- Variable documentation

---

## 🔵 LOW PRIORITY ISSUES

### 17. Test Files Not Organized
**Status:** 🔵 Low  
**Priority:** P3

**Problem:** Test files are in root directory instead of `tests/` folder:
- `test_admin_menu.py`
- `test_firebase.py`
- `test_gallery_upload.py`
- `test_jquery_fix.py`
- `test_storage_upload.py`
- `test_user_gallery_visibility.py`
- `quick_test.py`

**Fix:** Create `tests/` directory and move files

---

### 18. Debug Print Statements in Production
**Status:** 🔵 Low  
**Priority:** P3

**Problem:** Extensive `print()` statements throughout `app.py` instead of proper logging.

**Impact:**
- Log pollution
- Potential information exposure
- Performance impact

**Fix:** Replace with Python logging module

---

### 19. Large Monolithic app.py File
**Status:** 🔵 Low  
**Priority:** P3

**Problem:** `app.py` is 9,352 lines - extremely large and difficult to maintain.

**Recommended Structure:**
```
routes/
├── auth_routes.py
├── admin_routes.py
├── conference_routes.py
├── registration_routes.py
├── gallery_routes.py
└── api_routes.py

services/
├── email_service.py (exists)
├── yoco_service.py (exists)
├── ikhokha_service.py (exists)
├── firebase_service.py (new)
└── user_service.py (new)
```

---

### 20. Instance Directory with SQLite Database
**Status:** 🔵 Low  
**Priority:** P3

**Problem:** `instance/conference.db` exists but application uses Firebase exclusively.

**Fix:** Delete if not used, or document if needed for migration

---

## 📋 PAGES & ROUTES STATUS

### User-Facing Pages

| Page | Route | Template | Status |
|------|-------|----------|--------|
| Home | `/` | `user/home.html` | ✅ Working |
| About | `/about` | `user/about.html` | ✅ Working |
| Call for Papers | `/call-for-papers` | `user/call_for_papers.html` | ✅ Working |
| Paper Submission | `/paper-submission` | `user/papers/submit.html` | ✅ Working |
| Author Guidelines | `/author-guidelines` | `user/author_guidelines.html` | ✅ Working |
| Venue | `/venue` | `user/venue.html` | ✅ Working |
| Guest Speakers | `/guest-speakers` | `user/guest_speakers.html` | ✅ Working |
| Video Conference | `/video-conference` | `user/video_conference.html` | ⚠️ Buttons non-functional |
| Login | `/login` | `user/auth/login.html` | ✅ Working |
| Register | `/register` | `user/register.html` | ✅ Working |
| Registration | `/registration` | `user/registration.html` | ✅ Working |
| Schedule | `/schedule` | `user/conference/schedule.html` | ⚠️ Disabled feature |
| Downloads | `/downloads` | `user/conference/downloads.html` | ✅ Working |
| Contact | `/contact` | `user/contact.html` | ✅ Working |
| Galleries | `/galleries` | `galleries.html` | ✅ Working |
| Conferences | `/conferences` | `conferences/discover.html` | ✅ Working |
| Dashboard | `/dashboard` | `user/dashboard.html` | ✅ Working |
| Profile | `/profile` | `user/account/profile.html` | ✅ Working |
| Announcements | ❌ Missing Route | `user/announcements.html` | 🔴 **NOT ACCESSIBLE** |
| Forgot Password | `/forgot-password` | `user/auth/forgot_password.html` | ✅ Working |
| Conference Proceedings | `/conference-proceedings` | `user/conference_proceedings.html` | ✅ Working |
| Guest Speaker App | `/guest-speaker-application` | `user/guest_speaker_application.html` | ✅ Working |

### Admin Pages

| Page | Route | Template | Status |
|------|-------|----------|--------|
| Dashboard | `/admin/dashboard` | `admin/dashboard.html` | ✅ Working |
| Users | `/admin/users` | `admin/users.html` | ✅ Working |
| Conferences | `/admin/conferences` | `admin/conferences.html` | ✅ Working |
| Registrations | `/admin/registrations` | `admin/manage_registrations.html` | ✅ Working |
| Submissions | `/admin/submissions` | `admin/submissions.html` | ✅ Working |
| Speakers | `/admin/speakers` | `admin/speakers.html` | ✅ Working |
| Announcements | `/admin/announcements` | `admin/announcements.html` | ✅ Working |
| Schedule | `/admin/schedule` | `admin/schedule.html` | ⚠️ Disabled (hidden from menu) |
| Downloads | `/admin/downloads` | `admin/downloads.html` | ✅ Working |
| Venue | `/admin/venue` | `admin/admin_venue.html` | ✅ Working |
| Registration Fees | `/admin/registration-fees` | `admin/admin_registration_fees.html` | ✅ Working |
| Design | `/admin/design` | `admin/design.html` | ✅ Working |
| Home Content | `/admin/home-content` | `admin/home_content.html` | ✅ Working |
| About Content | `/admin/about-content` | `admin/about_content.html` | ✅ Working |
| Call for Papers | `/admin/call-for-papers-content` | `admin/call_for_papers_content.html` | ✅ Working |
| Author Guidelines | `/admin/author-guidelines` | `admin/author_guidelines.html` | ✅ Working |
| Email Templates | `/admin/email-templates` | `admin/email_templates.html` | ✅ Working |
| Email Settings | `/admin/email-settings` | `admin/email_settings.html` | ✅ Working |
| Conference Galleries | `/admin/conference-galleries` | `admin/conference_galleries.html` | ✅ Working |
| Conference Proceedings | `/admin/conference-proceedings` | `admin/conference_proceedings.html` | ✅ Working |
| Conference Codes | `/admin/conference-codes` | `admin/conference_codes.html` | ✅ Working |
| Paper Settings | `/admin/paper-submission-settings` | `admin/paper_submission_settings.html` | ✅ Working |
| Guest Speaker Apps | `/admin/guest-speaker-applications` | `admin/guest_speaker_applications.html` | ✅ Working |

### Orphaned Templates (No Route)

| Template | Issue |
|----------|-------|
| `templates/user/announcements.html` | 🔴 **No public route** |
| `templates/user/downloads.html` | Route uses different template |
| `templates/admin/site_design.html` | Duplicate of `design.html` |

---

## 🔧 RECOMMENDED FIX PRIORITY

### Immediate (Today)
1. ✅ Add `/announcements` route for user announcements
2. ✅ Add announcements link to navigation header
3. ✅ Delete duplicate/orphaned templates

### Short-term (This Week)
4. Fix video conference page buttons
5. Remove or properly disable schedule routes
6. Fix user dashboard admin links for regular users
7. Delete backup and git files

### Medium-term (Next Sprint)
8. Refactor app.py into smaller modules
9. Implement proper logging
10. Complete guest speaker workflow
11. Improve email template management

---

## 📁 FILES TO DELETE

```bash
# Backup files
rm app.py.backup
rm app.py.bak

# Accidental git outputs  
rm "h origin master"
rm "tatus -s"
rm "er.name"

# Duplicate templates
rm templates/admin/site_design.html

# Orphaned template (or create route for it)
# rm templates/user/downloads.html  # Review first
```

---

## 📝 NOTES

- This report focuses on **structural issues** (routes, templates, connections)
- For **functional bugs**, see `GIIP_ISSUES_TRACKING.md`
- For **incomplete features**, see `INCOMPLETE_FEATURES_TRACKING.md`
- For **previously resolved issues**, see `ISSUES.md`

---

---

## 🔴 ADMIN TEMPLATE ISSUES

### 21. Missing JavaScript Libraries in Admin Templates
**Status:** 🔴 Critical  
**Priority:** P0

**Problem:** Admin templates use `jQuery`, `toastr`, and `DataTables` but these libraries are NOT loaded in `base_admin.html`. This causes JavaScript errors.

**Affected Templates:**
- `admin/speakers.html` - Uses `toastr` and `DataTables`
- `admin/speaker_form.html` - Uses `toastr`
- `admin/submissions.html` - Uses `DataTables` and `$()` jQuery syntax

**Current `base_admin.html` (line 276) ONLY includes:**
```html
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
```

**Missing Libraries - Add to `<head>` section:**
```html
<!-- CSS Libraries -->
<link rel="stylesheet" href="https://cdn.datatables.net/1.11.5/css/dataTables.bootstrap5.min.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/toastr.js/latest/toastr.min.css">
```

**Missing Libraries - Add BEFORE Bootstrap JS:**
```html
<!-- jQuery MUST come before Bootstrap and other libraries -->
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.11.5/js/dataTables.bootstrap5.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/toastr.js/latest/toastr.min.js"></script>
```

**Errors Currently Occurring:**
1. `$ is not defined` - jQuery not loaded
2. `$.DataTable is not a function` - DataTables not loaded
3. `toastr is not defined` - Toastr not loaded

**Impact:**
- Speaker management page: DataTable won't initialize, delete notifications won't work
- Submissions page: Sorting and pagination broken
- JavaScript console errors throughout admin

**Estimated Fix:** 30 minutes

---

### 22. Submissions Table Missing Data Element
**Status:** 🟠 High  
**Priority:** P1

**Problem:** `admin/submissions.html` references `#submissions-data` element for JSON data but the script tries to parse it before DOMContentLoaded, potentially causing race conditions.

**Location:** Lines 361-370, 449-451

**Impact:** Table may not load properly on slow connections

---

### 23. Hardcoded Schedule Days/Dates
**Status:** 🟡 Medium  
**Priority:** P2

**Problem:** Schedule admin template (`admin/schedule.html`) displays hardcoded conference days from `SCHEDULE_DAYS` constant instead of dynamic conference dates.

**Location:** `app.py` line ~2801
```python
SCHEDULE_DAYS = [
    'Day 1 - January 15, 2024',
    'Day 2 - January 16, 2024',
    'Day 3 - January 17, 2024'
]
```

**Impact:** Schedule shows wrong dates (January 2024), confusing for users

---

### 24. Announcements Template - Very Large File
**Status:** 🟡 Medium  
**Priority:** P2

**Problem:** `admin/announcements.html` is 90KB / 3089 lines - extremely large for a single template file.

**Impact:**
- Slow page load times
- Difficult to maintain
- Poor code organization

**Recommendation:** Split into:
- `announcements_list.html` - List view
- `announcements_form.html` - Create/Edit form partial
- `announcements_modal.html` - Modal component

---

### 25. Duplicate Design Templates
**Status:** 🟡 Medium  
**Priority:** P2

**Problem:** Two templates for site design exist:
- `admin/design.html` (12KB, 301 lines) - **Currently used**
- `admin/site_design.html` (4.2KB, 95 lines) - **Orphaned**

**Comparison:**
| Feature | design.html | site_design.html |
|---------|-------------|------------------|
| Colors | 8 color inputs | 8 color inputs |
| Preview | Yes | No |
| Reset | Yes | No |
| Hero Image | No | No |

**Fix:** Delete `admin/site_design.html`

---

### 26. Home Content Template - Massive Size
**Status:** 🟡 Medium  
**Priority:** P2

**Problem:** `admin/home_content.html` is 50KB / 1346 lines.

**Impact:** 
- Hard to maintain
- Slow to render
- Difficult to debug

---

### 27. Admin Registration Fees - Inline CSS File Reference
**Status:** 🔵 Low  
**Priority:** P3

**Problem:** `admin_registration_fees.html` includes external CSS that may not exist:
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/admin_registration.css') }}">
```

**Verification Needed:** Check if `static/css/admin_registration.css` exists (it does - 6.5KB)

---

### 28. Inconsistent Bootstrap Versions
**Status:** 🟠 High  
**Priority:** P1

**Problem:** Admin templates use Bootstrap 5.1.3 but some templates have Bootstrap 4-style syntax:
- `data-dismiss="alert"` (Bootstrap 4) should be `data-bs-dismiss="alert"` (Bootstrap 5)
- `data-toggle` should be `data-bs-toggle`

**Location:** `admin/submissions.html` line 26:
```html
<button type="button" class="close" data-dismiss="alert">
```

**Impact:** Alert dismiss buttons won't work

---

### 29. Conference Galleries Attendees - Complex URL Building
**Status:** 🟡 Medium  
**Priority:** P2

**Problem:** `admin/conference_galleries_attendees.html` builds URLs with string replacement:
```javascript
`{{ url_for('edit_attendee_info', conference_id=conference_id, attendee_id='PLACEHOLDER') }}`.replace('PLACEHOLDER', attendeeId)
```

**Impact:** Fragile code that could break with URL changes

**Better Approach:** Pass attendee_id as parameter or use data attributes

---

### 30. Missing TinyMCE in Some Form Templates
**Status:** 🟡 Medium  
**Priority:** P2

**Problem:** Some admin templates that should have rich text editing don't include TinyMCE:
- `admin/email_templates.html` - Uses plain textarea
- `admin/about_content.html` - Mixed (some have it, some don't)

**Impact:** Inconsistent editing experience across admin pages

---

### 31. Speaker Form - Missing Cancel Confirmation
**Status:** 🔵 Low  
**Priority:** P3

**Problem:** `admin/speaker_form.html` cancel button navigates away without warning if form has unsaved changes.

---

### 32. Missing Form CSRF Protection
**Status:** 🟠 High  
**Priority:** P1

**Problem:** Many admin forms don't have visible CSRF tokens (Flask-WTF). While Flask may handle this at the application level, it should be verified.

**Affected Templates:**
- `admin/schedule.html` (modal forms)
- `admin/announcements.html` (modal forms)
- Various AJAX requests

---

## 📋 ADMIN TEMPLATE SUMMARY TABLE

| Template | Size | Lines | Issues | Priority |
|----------|------|-------|--------|----------|
| announcements.html | 90KB | 3089 | Very large | 🟡 Medium |
| home_content.html | 50KB | 1346 | Very large | 🟡 Medium |
| admin_registration_fees.html | 53KB | 1110 | OK | ✅ |
| manage_registrations.html | 45KB | 1153 | OK | ✅ |
| conference_galleries.html | 47KB | 1127 | OK | ✅ |
| guest_speaker_applications.html | 36KB | 977 | OK | ✅ |
| conference_details.html | 31KB | 662 | OK | ✅ |
| call_for_papers_content.html | 28KB | 530 | OK | ✅ |
| conference_galleries_attendees.html | 28KB | 583 | URL building | 🟡 Medium |
| about_content.html | 26KB | 514 | TinyMCE inconsistent | 🟡 Medium |
| conferences.html | 24KB | 541 | OK | ✅ |
| edit_conference.html | 22KB | 468 | OK | ✅ |
| author_guidelines.html | 21KB | 568 | OK | ✅ |
| schedule.html | 18KB | 510 | Hardcoded dates | 🟡 Medium |
| dashboard.html | 17KB | 553 | OK | ✅ |
| contact_email.html | 16KB | 363 | OK | ✅ |
| email_templates.html | 16KB | 494 | No rich text | 🟡 Medium |
| conference_proceedings.html | 16KB | 250 | OK | ✅ |
| downloads.html | 15KB | 297 | OK | ✅ |
| assign_registrations.html | 14KB | 335 | OK | ✅ |
| submissions.html | 14KB | 452 | Missing jQuery/DT | 🔴 Critical |
| users.html | 13KB | 451 | OK | ✅ |
| conference_codes.html | 13KB | 395 | OK | ✅ |
| design.html | 12KB | 301 | OK | ✅ |
| email_settings.html | 9.9KB | 218 | OK | ✅ |
| paper_submission_settings.html | 9.3KB | 167 | OK | ✅ |
| base_admin.html | 8.4KB | 297 | Missing libraries | 🔴 Critical |
| speakers.html | 6.4KB | 154 | toastr/DT missing | 🔴 Critical |
| admin_venue.html | 6.3KB | 207 | OK | ✅ |
| speaker_form.html | 5.7KB | 124 | toastr missing | 🟠 High |
| site_design.html | 4.2KB | 95 | **ORPHANED** | 🟡 Delete |

---

## 🔧 RECOMMENDED FIXES BY PRIORITY

### Immediate (Fix Today)
1. **Add missing JS libraries to `base_admin.html`**
   - jQuery 3.6+
   - DataTables 1.11+
   - Toastr notifications
   
2. **Fix Bootstrap 5 syntax** in `submissions.html`
   - Change `data-dismiss` to `data-bs-dismiss`

3. **Add `/announcements` route** for user-facing announcements

### This Week
4. Delete orphaned `site_design.html`
5. Fix hardcoded schedule dates
6. Add TinyMCE to email templates

### Next Sprint
7. Split large templates (announcements.html, home_content.html)
8. Refactor URL building in attendees template
9. Add unsaved changes warnings to forms

---

*Last Updated: December 24, 2025*  
*Analyzer: Codebase Audit Tool*  
*Next Review: January 2025*

