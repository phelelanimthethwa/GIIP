# Schema Migration Implementation Guide

## Overview

This guide provides step-by-step technical instructions for implementing the multi-conference schema migration for the GIIR Conference System.

## Prerequisites

- Firebase Admin SDK access
- Development environment with database access
- Backup procedures in place
- Monitoring tools configured

## Migration Scripts

### 1. Database Backup Script
```bash
#!/bin/bash
# Create complete database backup before migration
BACKUP_DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="firebase-backup-${BACKUP_DATE}.json"

firebase database:get / --output ${BACKUP_FILE}
echo "Backup created: ${BACKUP_FILE}"
```

### 2. Schema Creation Script
```javascript
// create-new-schema.js
const admin = require('firebase-admin');
const db = admin.database();

async function createConferenceSchema() {
  const defaultConference = {
    basic_info: {
      name: "GIIR Conference 2025",
      description: "Global Innovation and Intellectual Research Conference",
      start_date: "2025-07-15",
      end_date: "2025-07-17",
      status: "active",
      timezone: "UTC",
      year: 2025
    },
    metadata: {
      created_at: Date.now(),
      created_by: "migration-script",
      version: "1.0"
    }
  };

  await db.ref('conferences/default-2025').set(defaultConference);
  console.log('Default conference created');
}
```

### 3. Data Migration Script
```javascript
// migrate-data.js
const admin = require('firebase-admin');
const db = admin.database();

async function migrateUsers() {
  const usersSnapshot = await db.ref('users').once('value');
  const users = usersSnapshot.val() || {};
  
  const updates = {};
  
  Object.keys(users).forEach(userId => {
    const user = users[userId];
    updates[`users/${userId}`] = {
      email: user.email,
      full_name: user.full_name,
      is_global_admin: user.is_admin || false,
      created_at: user.created_at || Date.now()
    };
  });
  
  await db.ref().update(updates);
  console.log(`Migrated ${Object.keys(users).length} users`);
}

async function migrateRegistrations() {
  const regsSnapshot = await db.ref('registrations').once('value');
  const registrations = regsSnapshot.val() || {};
  
  const updates = {};
  
  Object.keys(registrations).forEach(regId => {
    const registration = registrations[regId];
    updates[`conference_registrations/default-2025/registrations/${regId}`] = {
      ...registration,
      conference_id: 'default-2025',
      migrated_at: Date.now()
    };
  });
  
  await db.ref().update(updates);
  console.log(`Migrated ${Object.keys(registrations).length} registrations`);
}
```

## Execution Steps

### Phase 1: Preparation
1. **Create backup**: `./backup-database.sh`
2. **Deploy new schema**: `node create-new-schema.js`
3. **Verify schema creation**: Check Firebase console

### Phase 2: Data Migration
1. **Migrate users**: `node migrate-data.js users`
2. **Migrate registrations**: `node migrate-data.js registrations`
3. **Migrate papers**: `node migrate-data.js papers`
4. **Validate data integrity**: `node validate-migration.js`

### Phase 3: Security Rules Update
1. **Deploy new rules**: `firebase deploy --only database`
2. **Test rule functionality**: `node test-security-rules.js`
3. **Monitor access patterns**: Check Firebase console

### Phase 4: Application Updates
1. **Update API endpoints**: Deploy code changes
2. **Test functionality**: Run integration tests
3. **Monitor performance**: Check application metrics

## Validation Commands

```bash
# Check data counts
firebase database:get /users --shallow | jq '. | length'
firebase database:get /conference_registrations/default-2025/registrations --shallow | jq '. | length'

# Validate specific user data
firebase database:get /users/USER_ID
firebase database:get /user_conferences/USER_ID

# Test security rules
firebase database:test --rules database.rules.json
```

## Rollback Procedures

### Emergency Rollback
```bash
# Restore from backup
firebase database:set / firebase-backup-TIMESTAMP.json

# Remove new collections
firebase database:remove /conferences
firebase database:remove /conference_registrations
firebase database:remove /user_conferences
```

## Monitoring Checklist

- [ ] Database backup completed successfully
- [ ] New schema collections created
- [ ] User data migration completed
- [ ] Registration data migration completed
- [ ] Paper data migration completed
- [ ] Security rules deployed
- [ ] Application functionality tested
- [ ] Performance metrics within acceptable range
- [ ] User acceptance testing passed

## Troubleshooting

### Common Issues
1. **Permission Denied**: Check Firebase Auth token
2. **Data Not Found**: Verify collection paths
3. **Migration Timeout**: Implement batching for large datasets
4. **Rule Validation Failed**: Test rules in Firebase console

### Recovery Procedures
- Partial rollback for specific collections
- Data repair scripts for corrupted entries
- Performance optimization for slow queries 