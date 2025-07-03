# Database Schema Design: Multi-Conference Support

## Executive Summary

This document outlines the current Firebase Realtime Database schema for the GIIR Conference System and presents a comprehensive design for migrating to a multi-conference architecture. The current system assumes a single-conference model, which requires restructuring to support multiple independent conferences.

## Current Schema Analysis

### Database Technology
- **Platform**: Firebase Realtime Database
- **Project ID**: giir-66ae6
- **Database URL**: https://giir-66ae6-default-rtdb.firebaseio.com

### Current Schema Structure

```
root/
├── users/
│   └── {user_id}/
│       ├── email: string
│       ├── full_name: string
│       ├── is_admin: boolean
│       ├── registrations/
│       └── papers/
├── registrations/
│   └── {registration_id}/
│       ├── email: string
│       ├── user_id: string
│       ├── registration_type: string
│       ├── registration_period: string
│       ├── payment_status: string
│       └── payment_proof: object
├── papers/
│   └── {paper_id}/
│       ├── title: string
│       ├── email: string
│       ├── status: string
│       └── submission_data: object
├── registration_fees/
├── schedule/
├── announcements/
├── email_templates/
├── downloads/
├── venue_details: object
├── site_design: object
├── home_content: object
├── about_content: object
├── call_for_papers_content: object
├── author_guidelines: object
├── email_settings: object
├── contact_email_settings: object
├── contact_page_settings: object
├── contact_submissions/
├── payment_proofs/
└── speakers/
```

### Current Security Rules Analysis

**Key Security Patterns**:
1. **Authentication Required**: Most operations require `auth != null`
2. **Admin-Only Areas**: Configuration data requires admin privileges
3. **User-Specific Access**: Users can only access their own registration/submission data
4. **Public Read Access**: Some content (venue, downloads) allows public read access

### Single-Conference Assumptions Identified

1. **Global Configuration**: All settings (fees, venue, content) are global rather than conference-specific
2. **Direct References**: Code directly references collections without conference context
3. **User Associations**: Users have single registration/paper submission context
4. **Admin Scope**: Admin permissions are global rather than conference-specific
5. **Email Templates**: Templates are shared across all functionality
6. **Schedule Management**: Single schedule structure for all events

## Proposed Multi-Conference Schema Design

### Design Principles

1. **Conference Isolation**: Each conference operates independently with separate data
2. **User Flexibility**: Users can participate in multiple conferences simultaneously
3. **Admin Granularity**: Admin permissions can be conference-specific or global
4. **Backward Compatibility**: Existing data structure concepts are preserved
5. **Performance Optimization**: Schema designed for efficient queries across conferences

### New Schema Structure

```
root/
├── conferences/
│   └── {conference_id}/
│       ├── basic_info/
│       ├── registration_fees/
│       ├── settings/
│       ├── content/
│       ├── submission_guidelines/
│       └── metadata/
├── conference_registrations/
│   └── {conference_id}/
│       └── registrations/
├── conference_papers/
│   └── {conference_id}/
│       └── papers/
├── conference_schedule/
│   └── {conference_id}/
│       └── sessions/
├── conference_announcements/
│   └── {conference_id}/
│       └── announcements/
├── users/
│   └── {user_id}/
├── user_conferences/
│   └── {user_id}/
│       └── {conference_id}/
├── conference_admins/
│   └── {conference_id}/
│       └── {user_id}/
├── global_settings/
├── contact_submissions/
└── payment_proofs/
    └── {user_id}/
        └── {conference_id}/
```

## Migration Strategy

### Phase 1: Schema Preparation
1. Create new schema structure alongside existing data
2. Implement dual-write pattern for new registrations
3. Test security rules in development environment

### Phase 2: Data Migration
1. Migrate existing data to default conference structure
2. Validate data integrity and completeness
3. Update user associations and permissions

### Phase 3: Application Migration
1. Update API endpoints to be conference-aware
2. Modify UI components for multi-conference support
3. Implement conference selection mechanisms

### Phase 4: Optimization
1. Monitor query performance and adjust indexes
2. Optimize dashboard queries for multi-conference display
3. Implement caching strategies for frequently accessed data

## Security Rules Design

Conference-specific security rules will ensure proper data isolation while maintaining admin access controls and user privacy.

## Performance Considerations

Multi-conference queries will require careful index design and potential denormalization for optimal performance. 