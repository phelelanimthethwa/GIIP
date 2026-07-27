# GIIR Conference Management System - Codebase Index

## Project Overview
**GIIR** is a comprehensive conference management system built with Flask and Firebase, designed to handle multiple conferences with features for registration, paper submissions, gallery management, and administrative functions.

## Architecture Summary
- **Backend**: Flask (Python) with Firebase integration
- **Database**: Firebase Realtime Database + Firestore
- **Storage**: Firebase Storage for file uploads
- **Frontend**: Jinja2 templates with Bootstrap CSS
- **Authentication**: Firebase Auth + Flask-Login
- **Deployment**: Render.com with Gunicorn
- **Email**: Flask-Mail with SMTP configuration

## Core Technologies
- **Flask 3.0.0** - Web framework
- **Firebase Admin SDK 6.6.0** - Database and authentication
- **Google Cloud Storage** - File storage
- **Flask-Mail** - Email functionality
- **Google Generative AI** - AI-powered features
- **Pillow** - Image processing
- **Gunicorn** - Production WSGI server

---

## Directory Structure

### Root Level Files
```
GIIP/
├── app.py                    # Main Flask application (13,819 lines)
├── config.py                 # Configuration management & Yoco credentials
├── requirements.txt          # Python dependencies
├── firebase.json            # Firebase configuration
├── database.rules.json      # Firebase security rules
├── render.yaml              # Render.com deployment config
├── Procfile                 # Process configuration
├── utils.py                 # Utility functions and Jinja filters
└── INCOMPLETE_FEATURES_TRACKING.md  # Feature status tracking
```

### Core Application Modules & Services
```
models/
├── __init__.py
├── email_service.py         # Email sending service (Flask-Mail integration)
└── email_templates.py       # HTML email templates definition

routes/
└── user_routes.py           # User profile and paper submission blueprints

services/
├── __init__.py
├── yoco_service.py          # Yoco Payment Gateway integration (card processing)
└── exchange_rate_service.py # Live USD -> ZAR exchange rate caching service
```

### Database & Schema
```
dataconnect/
├── dataconnect.yaml         # Firebase Data Connect config
├── connector/
│   ├── connector.yaml
│   ├── mutations.gql       # GraphQL mutations
│   └── queries.gql         # GraphQL queries
└── schema/
    └── schema.gql          # Database schema (commented example)
```

### Static Assets
```
static/
├── css/
│   ├── style.css           # Main stylesheet
│   └── admin_registration.css
├── js/
│   └── main.js            # Client-side JavaScript
├── images/                # Static images and logos
└── uploads/              # User-uploaded files
```

### Templates (Frontend)
```
templates/
├── base.html                        # Base template
├── admin/                           # Admin interface templates
│   ├── base_admin.html
│   ├── dashboard.html
│   ├── conferences.html
│   ├── conference_details.html
│   ├── admin_registration_fees.html # Registration fees & pricing config (1110 lines)
│   ├── admin_venue.html             # Venue details management
│   ├── manage_registrations.html    # Registration records management
│   ├── submissions.html             # Paper submission review
│   ├── speakers.html                # Speaker management
│   ├── announcements.html           # Announcements management
│   ├── home_content.html            # Home page content management
│   └── [20+ more admin templates]
├── user/                            # User-facing templates
│   ├── base.html
│   ├── home.html
│   ├── auth/                        # Authentication templates
│   ├── account/                     # User account templates
│   ├── conference/                  # Conference-specific templates
│   ├── papers/                      # Paper submission templates
│   └── components/                  # Reusable components
├── conferences/                     # Conference discovery templates
└── [various other templates]
```

### Scripts, Population & Migration
```
./
├── add_all_conferences_2026_2027.py  # Bulk 2026-2027 conference populator
├── add_conferences_2026_2027.py      # Conference setup script
├── add_conferences_direct.py         # Direct database injection for conferences
├── add_organizing_committee.py       # Committee members generator
├── add_registration_fees.py          # Pricing structure initializers
├── clean_database.py                 # Utility to scrub test data & orphaned entries
├── fix_template.py                   # Quick syntax patch tool for HTML templates
├── migrate_registration_fees.py      # Fee schema migration script
├── purge_firebase_users.py           # Test user account purging script
└── send_acceptance_letter.py         # Batch acceptance email dispatch tool
```                  # Reusable components
├── conferences/                     # Conference discovery templates
└── [various other templates]
```

### Scripts & Migration
```
scripts/
└── migration/
    ├── backups/          # Database backups
    ├── *.js             # Node.js migration scripts
    ├── *.bat            # Windows batch scripts
    └── *.sh             # Shell scripts
```

### Documentation
```
docs/
└── technical/
    ├── AUTO_DATE_FILTERING.md    # Date-based filtering system
    └── SECURITY_SSRF_FIX.md      # Security fixes documentation
```

---

## Key Features & Functionality

### 🔐 Authentication & Authorization
- **Firebase Authentication** integration
- **Role-based access control** (Admin, Global Admin, User)
- **Session management** with Flask-Login
- **Password reset** functionality
- **Admin dashboard** access control

### 🏢 Multi-Conference Management
- **Conference creation** with auto-generated codes
- **Conference discovery** page with filtering
- **Date-based status** auto-computation
- **Registration management** per conference
- **Paper submission** per conference
- **Gallery management** per conference

### 📝 Registration System
- **Multi-step registration** process
- **Payment proof upload** functionality
- **Registration type** management (Student, Regular, etc.)
- **Workshop and banquet** options
- **Email confirmations** for registrations

### 📄 Paper Submission
- **File upload** with validation
- **Co-author management** system
- **Status tracking** (Pending, Accepted, Rejected, Revision)
- **Admin review** workflow
- **Email notifications** for status changes

### 🖼️ Gallery System
- **Conference photo galleries**
- **Attendee photo uploads**
- **Advanced filtering** (All, Photos, Attendees)
- **Real-time search** functionality
- **Responsive design** for mobile devices

### 📧 Email System
- **Flask-Mail** integration
- **Template management** system
- **Automated notifications** for:
  - Registration confirmations
  - Paper submission confirmations
  - Status updates
  - Password resets

### 🎨 Site Customization
- **Dynamic theming** system
- **Color scheme** customization
- **Content management** for:
  - Home page content
  - About page content
  - Call for papers content
  - Author guidelines

### 👥 User Management
- **User profiles** and account management
- **Registration history** tracking
- **Paper submission** history
- **Admin user** management

---

## Database Schema (Firebase)

### Main Collections
```json
{
  "users": {
    "uid": {
      "email": "string",
      "is_admin": "boolean",
      "is_global_admin": "boolean",
      "profile_data": "object"
    }
  },
  "conferences": {
    "conference_id": {
      "conference_code": "string",
      "basic_info": "object",
      "registration_settings": "object",
      "paper_submission_settings": "object"
    }
  },
  "registrations": {
    "registration_id": {
      "email": "string",
      "user_id": "string",
      "conference_id": "string",
      "registration_type": "string",
      "payment_status": "string",
      "payment_proof": "object"
    }
  },
  "submissions": {
    "submission_id": {
      "email": "string",
      "conference_id": "string",
      "status": "string",
      "paper_data": "object"
    }
  },
  "papers": {
    "paper_id": {
      "email": "string",
      "status": "string",
      "file_data": "object"
    }
  }
}
```

### Security Rules
- **Authentication required** for all operations
- **Role-based access** control
- **User data isolation** (users can only access their own data)
- **Admin override** capabilities
- **File upload validation**

---

## API Endpoints & Routes

### Public Routes
- `/` - Home page
- `/conferences` - Conference discovery
- `/conferences/<code>` - Conference details
- `/registration` - Registration form
- `/login` - User login
- `/register` - User registration
- `/contact` - Contact form
- `/galleries` - Photo galleries

### User Routes (Authenticated)
- `/dashboard` - User dashboard
- `/account/profile` - User profile
- `/papers/submit` - Paper submission
- `/papers/guidelines` - Submission guidelines
- `/conference/schedule` - Conference schedule
- `/conference/downloads` - Conference resources

### Admin Routes
- `/admin/dashboard` - Admin dashboard
- `/admin/conferences` - Conference management
- `/admin/conferences/<id>` - Conference details
- `/admin/users` - User management
- `/admin/registrations` - Registration management
- `/admin/registration-fees` - Registration fees & pricing management (see below)
- `/admin/submissions` - Paper submissions
- `/admin/speakers` - Speaker management
- `/admin/schedule` - Schedule management
- `/admin/galleries` - Gallery management
- `/admin/settings` - System settings
- `/admin/venue` - Venue details management
- `/admin/downloads` - Downloadable resources management
- `/admin/conferences/<conference_id>/registration-fees` — Per-conference registration fees & pricing management (see below)

#### `/admin/conferences/<conference_id>/registration-fees` — Registration Fees Management
- **Route function**: `admin_registration_fees(conference_id)` ([app.py L2594](file:///c:/Users/ACE/G/GIIP/app.py#L2594-L2753))
- **Template**: [`admin/admin_registration_fees.html`](file:///c:/Users/ACE/G/GIIP/templates/admin/admin_registration_fees.html)
- **Custom CSS**: [`static/css/admin_registration.css`](file:///c:/Users/ACE/G/GIIP/static/css/admin_registration.css)
- **Access**: Admin-only (`@admin_required`)
- **Methods**: `GET`, `POST`
- **Firebase Node**: `conferences/{conference_id}/registration_fees`

**Form Sections (POST fields)**:
| Section | Fields |
|---|---|
| Currency | `currency_code` (ZAR, USD, EUR, GBP, AUD, custom), `custom_currency_symbol` |
| Early Bird | `early_bird_enabled`, `early_bird_deadline`, `early_bird_total_seats`, `early_bird_remaining_seats`, `show_remaining_seats`, `early_bird_student/regular/physical/listener`, `early_bird_benefits[]` |
| Early Registration | `early_deadline`, `early_student/regular/physical/listener`, `early_benefits[]` |
| Regular Registration | `regular_deadline`, `regular_student/regular/physical/listener`, `regular_benefits[]` |
| Late Registration | `late_deadline`, `late_student/regular/physical/listener`, `late_benefits[]` |
| Additional Items | `extra_paper_enabled`, `extra_paper_fee`, `extra_paper_description`; `workshop_enabled`, `workshop_fee`, `workshop_description`; `banquet_enabled`, `banquet_fee`, `banquet_description`, `banquet_virtual_eligible` |

**Firebase Data Structure** (`registration_fees`):
```json
{
  "currency": { "code": "ZAR", "symbol": "R" },
  "early_bird": {
    "enabled": true,
    "deadline": "YYYY-MM-DD",
    "seats": { "total": 100, "remaining": 80, "show_remaining": true },
    "fees": { "student_author": 0, "regular_author": 0, "physical_delegate": 0, "listener": 0 },
    "benefits": []
  },
  "early": { "deadline": "", "fees": { ... }, "benefits": [] },
  "regular": { "deadline": "", "fees": { ... }, "benefits": [] },
  "late": { "deadline": "", "fees": { ... }, "benefits": [] },
  "additional_items": {
    "extra_paper": { "enabled": false, "fee": 0, "description": "" },
    "workshop": { "enabled": false, "fee": 0, "description": "" },
    "banquet": { "enabled": false, "fee": 0, "description": "", "virtual_eligible": false }
  }
}
```

**Registration Types** (used across all fee tiers):
- `student_author` — Student author fee
- `regular_author` — Regular/professional author fee
- `physical_delegate` — Physical (in-person) delegate fee
- `listener` — Listener/observer fee

### API Endpoints
- `/api/conferences` - Conference data API
- `/api/registrations` - Registration data API
- `/api/submissions` - Submission data API
- `/api/gallery` - Gallery data API

---

## Configuration Management

### Environment Variables
```python
# Required
SECRET_KEY                    # Flask secret key
FIREBASE_API_KEY             # Firebase API key
FIREBASE_PROJECT_ID          # Firebase project ID
FIREBASE_CREDENTIALS        # Firebase service account (JSON)

# Optional
MAIL_SERVER                  # SMTP server
MAIL_USERNAME               # Email username
MAIL_PASSWORD               # Email password
GEMINI_API_KEY              # Google AI API key
GOOGLE_MAPS_API_KEY         # Maps API key
RECAPTCHA_SITE_KEY          # reCAPTCHA site key
RECAPTCHA_SECRET_KEY        # reCAPTCHA secret key
```

### Firebase Configuration
- **Project ID**: `giir-66ae6`
- **Database URL**: `https://giir-66ae6-default-rtdb.firebaseio.com`
- **Storage Bucket**: `giir-66ae6.firebasestorage.app`
- **Auth Domain**: Configured via environment

---

## Deployment & Infrastructure

### Production Deployment (Render.com)
- **Platform**: Render.com
- **Runtime**: Python 3.9.0
- **WSGI Server**: Gunicorn with 4 workers
- **Timeout**: 120 seconds
- **Health Check**: `/` endpoint
- **Auto Deploy**: Enabled

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run development server
python app.py
```

### File Structure for Deployment
- **Static files**: Served via Flask static folder
- **Uploads**: Stored in Firebase Storage
- **Database**: Firebase Realtime Database
- **Logs**: Application logs via Render.com

---

## Security Features

### Authentication Security
- **Firebase Auth** integration
- **Session management** with secure cookies
- **Password hashing** via Firebase
- **CSRF protection** via Flask-WTF

### Data Security
- **Firebase security rules** for data access
- **File upload validation** (type, size, signature)
- **Input sanitization** and validation
- **SQL injection prevention** (NoSQL database)

### File Security
- **File type validation** (magic number checking)
- **File size limits** (16MB max)
- **Secure filename generation**
- **Upload directory isolation**

---

## Feature Status Overview

### ✅ Completed Features
- **Gallery System** - Full functionality with filtering
- **Multi-Conference Support** - Complete UI and backend
- **User Authentication** - Firebase integration
- **Registration System** - Multi-step process
- **Paper Submission** - File upload and management
- **Admin Dashboard** - Comprehensive management interface
- **Email System** - Automated notifications
- **Site Customization** - Dynamic theming
- **Registration Fees Management** - Full admin UI at `/admin/registration-fees` with currency settings, tiered pricing (Early Bird, Early, Regular, Late), per-type fees (student/regular/physical/listener), and additional items (workshop, banquet, extra paper)
- **Guest Speaker Applications** - Admin review and approval workflow
- **Firebase User Purge** - `purge_firebase_users.py` script for bulk user cleanup
- **Acceptance Letters** - `send_acceptance_letter.py` script for email dispatch

### 🔴 Critical Incomplete Features
- **Conference Resources Access** - Users cannot access templates/guidelines
- **Payment Status Updates** - Manual verification required

### 🟠 High Priority Features
- **Schedule Public Viewing** - Admin interface complete, public viewing unclear
- **Email Template Management** - Backend complete, UI needs enhancement

### 🟡 Medium Priority Features
- **Debug Code Cleanup** - Extensive debug statements in production code (print statements throughout `admin_registration_fees()` and other routes)
- **Error Handling** - Some routes need better error handling

---

## Development Guidelines

### Code Organization
- **Main application**: `app.py` (very large, consider refactoring)
- **Utility functions**: `utils.py`
- **Email services**: `models/email_service.py`
- **User routes**: `routes/user_routes.py`

### Template Structure
- **Base templates**: `base.html`, `base_admin.html`
- **Component-based**: Reusable components in `components/`
- **Responsive design**: Bootstrap-based CSS
- **Dynamic theming**: CSS variables for customization

### Database Patterns
- **Firebase Realtime Database** for real-time features
- **Firestore** for complex queries (if needed)
- **Firebase Storage** for file uploads
- **Security rules** for access control

---

## Testing & Quality Assurance

### Current Testing Files
- `test_admin_menu.py` - Admin functionality tests
- `test_firebase.py` - Firebase integration tests
- `test_gallery_upload.py` - Gallery upload tests
- `test_storage_upload.py` - Storage upload tests
- `test_user_gallery_visibility.py` - Gallery visibility tests

### Quality Issues
- **Debug statements** throughout production code
- **Large monolithic** `app.py` file
- **Error handling** improvements needed
- **Code organization** could be better

---

## Future Development Roadmap

### Phase 1: Critical Fixes
1. **Conference Resources Access** - Implement user access to templates/guidelines
2. **Payment Status Updates** - Automated payment processing
3. **Debug Code Cleanup** - Remove debug statements

### Phase 2: Feature Completion
1. **Schedule Public Viewing** - Ensure public schedule access works
2. **Email Template Management** - Enhance admin interface
3. **Guest Speaker Workflow** - Complete end-to-end process

### Phase 3: Code Quality
1. **Refactor app.py** - Split into multiple modules
2. **Error Handling** - Comprehensive error handling
3. **Testing** - Expand test coverage

### Phase 4: Advanced Features
1. **Video Conference Integration** - If needed
2. **Advanced Analytics** - User behavior tracking
3. **Mobile App** - Native mobile application

---

## Support & Maintenance

### Key Files for Maintenance
- `app.py` - Main application logic
- `config.py` - Configuration management
- `database.rules.json` - Security rules
- `requirements.txt` - Dependencies
- `INCOMPLETE_FEATURES_TRACKING.md` - Feature status

### Common Tasks
- **Adding new conferences** - Use admin interface
- **Managing users** - Admin dashboard
- **Updating content** - Content management system
- **Monitoring** - Render.com dashboard

### Troubleshooting
- **Firebase connection issues** - Check credentials and API keys
- **Email delivery problems** - Verify SMTP configuration
- **File upload issues** - Check Firebase Storage permissions
- **Authentication problems** - Verify Firebase Auth configuration

---

*Last Updated: July 2026*
*Document Version: 1.1*
*Maintained by: Development Team*
