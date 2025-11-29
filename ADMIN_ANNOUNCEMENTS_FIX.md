# URGENT FIX: Admin Announcements Form Not Submitting

## Problem
The admin announcements form at `/admin/announcements` cannot create or send announcements because the form submission JavaScript is missing.

## Root Cause
The form exists in the HTML (line 133: `<form id="announcementForm"...>`) but there's NO JavaScript code to handle the form submission.

## Quick Fix

Add this JavaScript code at the END of `templates/admin/announcements.html` (before the closing `</script>` tag around line 3049):

```javascript
// Handle announcement form submission
document.getElementById('announcementForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const submitButton = document.getElementById('submitButton');
    const formData = new FormData(this);
    
    // Show loading state
    submitButton.classList.add('loading');
    submitButton.disabled = true;
    
    try {
        const currentAnnouncementId = document.getElementById('announcementId').value;
        const url = currentAnnouncementId ? 
            `/admin/announcements/${currentAnnouncementId}` : 
            '/admin/announcements';
        const method = currentAnnouncementId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('success', currentAnnouncementId ? 'Announcement updated successfully!' : 'Announcement created successfully!');
            closeModal('announcementModal');
            
            // Reload page to show new announcement
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showAlert('error', result.error || 'Failed to save announcement');
            submitButton.classList.remove('loading');
            submitButton.disabled = false;
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('error', 'An error occurred while saving the announcement');
        submitButton.classList.remove('loading');
        submitButton.disabled = false;
    }
});

// Open new announcement modal
function openNewAnnouncementModal() {
    document.getElementById('modalTitle').textContent = 'New Announcement';
    document.getElementById('announcementForm').reset();
    document.getElementById('announcementId').value = '';
    document.getElementById('submitButton').querySelector('.btn-text').textContent = 'Create Announcement';
    
    // Set default date/time
    const now = new Date();
    document.getElementById('announcement_date').value = now.toISOString().split('T')[0];
    document.getElementById('announcement_time').value = now.toTimeString().slice(0, 5);
    
    document.getElementById('announcementModal').style.display = 'block';
}

// Edit announcement
async function editAnnouncement(id) {
    try {
        const response = await fetch(`/admin/announcements/${id}`);
        const result = await response.json();
        
        if (result.success) {
            const announcement = result.announcement;
            
            document.getElementById('modalTitle').textContent = 'Edit Announcement';
            document.getElementById('announcementId').value = id;
            document.getElementById('title').value = announcement.title;
            
            // Set TinyMCE content if initialized, otherwise use textarea
            if (typeof tinymce !== 'undefined' && tinymce.get('content')) {
                tinymce.get('content').setContent(announcement.content);
            } else {
                document.getElementById('content').value = announcement.content;
            }
            
            document.getElementById('announcement_date').value = announcement.scheduled_date;
            document.getElementById('announcement_time').value = announcement.scheduled_time;
            document.getElementById('timezone').value = announcement.timezone;
            document.getElementById('type').value = announcement.type;
            document.getElementById('is_pinned').checked = announcement.is_pinned || false;
            document.getElementById('send_email').checked = false; // Don't re-send by default
            
            document.getElementById('submitButton').querySelector('.btn-text').textContent = 'Update Announcement';
            document.getElementById('announcementModal').style.display = 'block';
        } else {
            showAlert('error', 'Failed to load announcement');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('error', 'An error occurred while loading the announcement');
    }
}

// Delete announcement
async function deleteAnnouncement(id) {
    if (!confirm('Are you sure you want to delete this announcement? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/admin/announcements/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('success', 'Announcement deleted successfully!');
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showAlert('error', result.error || 'Failed to delete announcement');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('error', 'An error occurred while deleting the announcement');
    }
}

// Close modal
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Show alert
function showAlert(type, message) {
    const alertHTML = `
        <div class="alert alert-${type} fade-in">
            ${message}
            <button type="button" class="close-alert" onclick="this.parentElement.remove();">×</button>
        </div>
    `;
    document.getElementById('alertContainer').innerHTML = alertHTML;
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        const alert = document.querySelector('.alert');
        if (alert) alert.remove();
    }, 5000);
}
```

## Also Need to Add

Add this hidden input field inside the form (after line 134, right after `<form id="announcementForm"...>`):

```html
<input type="hidden" id="announcementId" name="announcementId" value="">
```

## Location to Insert Code

1. Open `templates/admin/announcements.html`
2. Scroll to near the end (around line 3045-3049)
3. Find the section with `async function previewEmail()` 
4. Add the code above BEFORE the closing `</script>` tag (line 3049)

## After Applying Fix

1. Refresh the admin announcements page
2. Click "New Announcement"
3. Fill in the form
4. Click "Create Announcement"
5. It should now work!

## Why This Happened

The template had all the HTML elements but was missing the JavaScript event listeners to actually handle form submissions. This is why clicking the button did nothing - there was no code to intercept the form submit and send it to the server.
