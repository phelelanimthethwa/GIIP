# Security Rules Design: Multi-Conference Access Control

## Overview

This document defines the Firebase Realtime Database security rules for the multi-conference GIIR Conference System. The rules ensure proper data isolation between conferences while maintaining appropriate access controls for users and administrators.

## Security Principles

1. **Conference Isolation**: Users can only access data for conferences they're associated with
2. **Role-Based Access**: Different permission levels for users, conference admins, and global admins
3. **Data Privacy**: Users can only access their own personal data
4. **Admin Scope**: Conference admins have limited scope to their assigned conferences
5. **Audit Trail**: All data modifications are traceable to authenticated users

## Current vs New Security Model

### Current Security Model
- Global admin permissions (`is_admin` field)
- Email-based user identification
- Simple auth-based read/write rules
- No conference-specific access control

### New Security Model
- Global admins (`is_global_admin`) with full system access
- Conference-specific admins with scoped permissions
- User-conference associations for access control
- Granular permissions for different data types

## New Security Rules Structure

### Conference Management Rules
```json
{
  "conferences": {
    ".read": "auth != null",
    "$conference_id": {
      ".write": "auth != null && (
        root.child('users').child(auth.uid).child('is_global_admin').val() === true ||
        root.child('conference_admins').child($conference_id).child(auth.uid).child('permission_level').val() === 'admin'
      )",
      "basic_info": {
        ".read": true
      }
    }
  }
}
```

### Conference-Specific Data Rules
```json
{
  "conference_registrations": {
    "$conference_id": {
      "registrations": {
        ".indexOn": ["user_id", "email", "registration_type", "payment_status"],
        "$registration_id": {
          ".read": "auth != null && (
            data.child('user_id').val() === auth.uid ||
            root.child('users').child(auth.uid).child('is_global_admin').val() === true ||
            root.child('conference_admins').child($conference_id).child(auth.uid).exists()
          )",
          ".write": "auth != null && (
            newData.child('user_id').val() === auth.uid ||
            root.child('users').child(auth.uid).child('is_global_admin').val() === true ||
            root.child('conference_admins').child($conference_id).child(auth.uid).child('permission_level').val() === 'admin'
          )"
        }
      }
    }
  }
}
```

### User-Conference Association Rules
```json
{
  "user_conferences": {
    "$user_id": {
      ".read": "auth != null && (
        auth.uid === $user_id ||
        root.child('users').child(auth.uid).child('is_global_admin').val() === true
      )",
      ".write": "auth != null && auth.uid === $user_id",
      "$conference_id": {
        ".validate": "root.child('conferences').child($conference_id).exists()"
      }
    }
  }
}
```

### Conference Admin Rules
```json
{
  "conference_admins": {
    "$conference_id": {
      ".read": "auth != null && (
        root.child('users').child(auth.uid).child('is_global_admin').val() === true ||
        root.child('conference_admins').child($conference_id).child(auth.uid).exists()
      )",
      "$admin_user_id": {
        ".write": "auth != null && (
          root.child('users').child(auth.uid).child('is_global_admin').val() === true ||
          (root.child('conference_admins').child($conference_id).child(auth.uid).child('permission_level').val() === 'admin' &&
           newData.child('permission_level').val() !== 'admin')
        )",
        ".validate": "newData.hasChildren(['permission_level', 'granted_by', 'granted_at'])"
      }
    }
  }
}
```

## Permission Levels

### Global Admin (`is_global_admin: true`)
- Full access to all conferences and system settings
- Can create/modify/delete conferences
- Can assign conference-specific admin permissions
- Access to global system settings

### Conference Admin (`permission_level: 'admin'`)
- Full access to assigned conference data
- Can manage conference settings and content
- Can assign lower-level permissions within conference
- Cannot access other conferences or global settings

### Conference Editor (`permission_level: 'editor'`)
- Read/write access to conference content
- Can manage registrations and papers
- Cannot modify conference settings or permissions
- Limited to assigned conference

### Conference Viewer (`permission_level: 'viewer'`)
- Read-only access to conference data
- Can view registrations and submissions
- Cannot modify any data
- Limited to assigned conference

### Regular User
- Can register for conferences
- Can submit papers to conferences
- Can view their own data across conferences
- Cannot access other users' data

## Implementation Strategy

### Phase 1: Rule Preparation
1. **Test Environment Deployment**
   - Deploy new rules to development environment
   - Test with sample multi-conference data
   - Validate permission inheritance

2. **Rule Validation**
   - Unit tests for each permission scenario
   - Integration tests with real user workflows
   - Performance testing for rule evaluation

### Phase 2: Gradual Rollout
1. **Backward Compatibility**
   - Maintain existing rule functionality
   - Add new conference-specific rules
   - Implement graceful fallbacks

2. **User Migration**
   - Migrate existing admins to global admin status
   - Create default conference associations
   - Test user access patterns

### Phase 3: Full Implementation
1. **Complete Rule Deployment**
   - Remove backward compatibility rules
   - Implement full conference isolation
   - Monitor for access issues

2. **Performance Optimization**
   - Optimize rule evaluation performance
   - Add caching where appropriate
   - Monitor rule execution times

## Security Validation

### Access Control Tests
```javascript
// Test: Regular user can only access own data
function testUserDataAccess() {
  const userId = 'user123';
  const otherUserId = 'user456';
  
  // Should succeed
  assert(canRead(`user_conferences/${userId}`, { uid: userId }));
  
  // Should fail
  assert(!canRead(`user_conferences/${otherUserId}`, { uid: userId }));
}

// Test: Conference admin can access conference data
function testConferenceAdminAccess() {
  const adminId = 'admin123';
  const conferenceId = 'conf2025';
  
  // Setup admin permission
  setData(`conference_admins/${conferenceId}/${adminId}`, {
    permission_level: 'admin',
    granted_by: 'global_admin',
    granted_at: Date.now()
  });
  
  // Should succeed
  assert(canWrite(`conferences/${conferenceId}/settings`, { uid: adminId }));
}
```

### Data Validation Tests
```javascript
// Test: Conference registration validation
function testRegistrationValidation() {
  const userId = 'user123';
  const conferenceId = 'conf2025';
  const registrationData = {
    user_id: userId,
    email: 'user@example.com',
    registration_type: 'regular',
    payment_status: 'pending'
  };
  
  // Should succeed with valid data
  assert(canWrite(
    `conference_registrations/${conferenceId}/registrations/reg123`,
    { uid: userId },
    registrationData
  ));
}
```

## Performance Considerations

### Rule Optimization
1. **Early Authentication Checks**: Place `auth != null` checks first
2. **Minimize Database Lookups**: Cache permission lookups where possible
3. **Efficient Permission Checking**: Use indexed fields for permission validation

### Index Strategy
```json
{
  "users": {
    ".indexOn": ["email", "is_global_admin"]
  },
  "conference_admins": {
    "$conference_id": {
      ".indexOn": ["permission_level", "granted_at"]
    }
  },
  "user_conferences": {
    "$user_id": {
      ".indexOn": ["last_activity"]
    }
  }
}
```

### Caching Strategy
- Cache permission lookups for frequently accessed conferences
- Implement client-side permission caching with TTL
- Use Firebase Auth custom claims for global admin status

## Migration from Current Rules

### Step 1: Add New Rules Alongside Existing
- Deploy new conference-specific rules
- Maintain existing global rules for backward compatibility
- Test new rules with development data

### Step 2: Migrate User Permissions
- Convert existing `is_admin` users to `is_global_admin`
- Create default conference admin associations
- Validate user access patterns

### Step 3: Remove Legacy Rules
- Remove old global permission patterns
- Implement full conference isolation
- Monitor for access issues and performance impact

## Security Best Practices

### Rule Design Principles
1. **Principle of Least Privilege**: Grant minimum necessary permissions
2. **Defense in Depth**: Multiple validation layers
3. **Explicit Deny**: Default to denying access unless explicitly granted
4. **Audit Trail**: All rule evaluations are logged

### Monitoring and Alerting
1. **Access Pattern Monitoring**: Track unusual access patterns
2. **Permission Escalation Alerts**: Alert on admin permission changes
3. **Failed Access Logging**: Log and monitor failed access attempts
4. **Performance Monitoring**: Track rule evaluation performance 