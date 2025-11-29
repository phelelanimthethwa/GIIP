# Issue 17: Announcements System Improvement - Progress Report

**Date**: November 29, 2025  
**Status**: 🚧 In Progress  
**Priority**: 🟡 Medium

---

## 📋 Summary

Working on improving the announcements system for GIIP conference management. The system exists but lacks public-facing features for users.

---

## ✅ What We Accomplished

### 1. **Created Public Announcements Page**
- ✅ **File Created**: `templates/user/announcements.html`
- **Features**:
  - Modern, responsive design with filtering and search
  - Separates pinned and regular announcements
  - Type-based filtering (Important, Event, Update, Info)
  - Search functionality
  - Modal view for full announcement details
  - Dynamic badges for announcement types
  - Mobile-responsive grid layout

### 2. **Analyzed Existing System**
- ✅ Admin interface exists and is comprehensive (`templates/admin/announcements.html`)
- ✅ Backend routes implemented:
  - `GET /admin/announcements` - List announcements
  - `POST /admin/announcements` - Create announcement
  - `PUT /admin/announcements/<id>` - Update announcement  
  - `DELETE /admin/announcements/<id>` - Delete announcement
  - `GET /admin/announcements/<id>` - Get single announcement

---

## ⚠️ What Still Needs To Be Done

### 1. **Add Public Route in app.py** ⚠️ URGENT
**File**: `app.py`  
**Location**: After `delete_announcement` function (around line 3004)

```python
# Public announcements route for users
@app.route('/announcements')
def public_announcements():
    """Public-facing page for users to view all announcements"""
    try:
        # Get all announcements from Firebase
        announcements_ref = db.reference('announcements')
        all_announcements = announcements_ref.get() or {}
        
        # Filter and separate pinned and regular announcements
        pinned_announcements = {}
        regular_announcements = {}
        
        for ann_id, announcement in all_announcements.items():
            # Check if announcement should be visible (scheduled date has passed)
            if announcement.get('scheduled_date'):
                try:
                    scheduled_dt = datetime.fromisoformat(announcement.get('formatted_datetime', ''))
                    if scheduled_dt > datetime.now():
                        continue  # Skip future announcements
                except:
                    pass  # If parsing fails, show the announcement anyway
            
            if announcement.get('is_pinned'):
                pinned_announcements[ann_id] = announcement
            else:
                regular_announcements[ann_id] = announcement
        
        # Sort pinned announcements by date (most recent first)
        pinned_announcements = dict(sorted(
            pinned_announcements.items(),
            key=lambda x: x[1].get('scheduled_date', x[1].get('created_at', '')),
            reverse=True
        ))
        
        # Sort regular announcements by date (most recent first)
        regular_announcements = dict(sorted(
            regular_announcements.items(),
            key=lambda x: x[1].get('scheduled_date', x[1].get('created_at', '')),
            reverse=True
        ))
        
        return render_template(
            'user/announcements.html',
            pinned_announcements=pinned_announcements,
            regular_announcements=regular_announcements,
            site_design=get_site_design()
        )
    except Exception as e:
        print(f"Error loading public announcements: {str(e)}")
        flash(f'Error loading announcements: {str(e)}', 'error')
        return render_template(
            'user/announcements.html',
            pinned_announcements={},
            regular_announcements={},
            site_design=get_site_design()
        )
```

**⚠️ NOTE**: There's a syntax error in `app.py` around line 2999. You'll need to fix the `delete_announcement` function first - it's missing the completion of its exception handler.

### 2. **Add Navigation Links**

#### a. **Main Navigation** (`templates/base.html`)
Add to navigation menu:
```html
<li><a href="{{ url_for('public_announcements') }}">
    <i class="fas fa-bullhorn"></i> Announcements
</a></li>
```

#### b. **User Dashboard** (`templates/user/dashboard.html`)
Add announcements widget to show latest 3 announcements

#### c. **Homepage** (`templates/user/home.html`)
Add announcements section showing latest pinned announcements

### 3. **Optional Enhancements**

#### a. **Announcement Notifications Badge**
Show unread announcement count in navigation

#### b. **Email Digest**
Weekly email digest of announcements for subscribed users

#### c. **RSS Feed**
Create `/announcements/feed` route for RSS subscriptions

#### d. **View Analytics**  
Track how many users viewed each announcement

---

## 🐛 Known Issues

### 1. **Syntax Error in app.py**
- **Line**: ~2999
- **Issue**: Incomplete `delete_announcement` function - missing closing lines for exception handler
-  **Fix**: Complete the function properly

### 2. **Lint Warnings in announcements.html**
- Minor JavaScript syntax warnings (doesn't affect functionality)
- Related to Jinja2 template variables in JavaScript

---

## 📝 Testing Checklist

Once the route is added, test these scenarios:

-  [ ] Navigate to `/announcements` as non-logged-in user
- [ ] Navigate to `/announcements` as logged-in user  
- [ ] Filter announcements by type
- [ ] Search for specific announcement
- [ ] Click "Read More" to open modal
- [ ] Verify pinned announcements show at top
- [ ] Verify future announcements are hidden
- [ ] Test on mobile device

---

## 🎯 Success Criteria

Issue 17 will be considered complete when:

1. ✅ Public announcements page created
2. ⏳ Public route `/announcements` is accessible
3. ⏳ Navigation links added to website
4. ⏳ Announcements display correctly with filtering
5. ⏳ Scheduled announcements only show when date has passed
6. ⏳ Mobile-responsive design works

---

## 📦 Files Modified/Created

### Created
- `templates/user/announcements.html` ✅

### Need to Modify
- `app.py` - Add public route ⏳
- `templates/base.html` - Add navigation link ⏳
- `templates/user/dashboard.html` - Add announcements widget (optional) ⏳
- `templates/user/home.html` - Add announcements section (optional) ⏳

---

## 💡 Recommendations

1. **Fix app.py syntax error first** - The delete_announcement function is incomplete
2. **Add the public route** - This is the critical missing piece
3. **Update navigation** - Make announcements easily discoverable
4. **Test thoroughly** - Ensure scheduled announcements work correctly
5. **Consider analytics** - Track announcement engagement

---

## Related Issues

- **GIIP_ISSUES_TRACKING.md #8** - Original issue about announcements system
- **INCOMPLETE_FEATURES_TRACKING.md #17** - This issue

---

*Report Generated: November 29, 2025*  
*Next Steps: Fix app.py syntax error, add public route, update navigation*
