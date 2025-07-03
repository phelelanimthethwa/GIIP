# PBI-1: Multi-Conference Registration Support

[View in Backlog](../backlog.md#user-content-1)

## Overview

This PBI implements the capability for users to register for multiple conferences within the GIIR Conference System. Currently, the system supports only single conference registration. This enhancement will allow users to discover, compare, and register for multiple conferences while maintaining separate registration records and payment tracking for each conference.

## Problem Statement

The current system architecture assumes a single conference model, which limits users who want to participate in multiple GIIR conferences throughout the year. Users currently cannot:
- View multiple available conferences
- Register for more than one conference
- Track registrations across multiple conferences
- Manage different registration types per conference

## User Stories

**Primary User Story:**
As a conference attendee, I want to register for multiple conferences so that I can participate in different events throughout the year.

**Additional User Stories:**
- As a researcher, I want to view all available conferences so that I can plan my participation strategy
- As a user, I want to see my registration status across all conferences in one dashboard
- As an admin, I want to manage multiple conferences independently with separate fee structures and settings

## Technical Approach

### Data Model Changes
1. **Conference Entity Structure**: Restructure Firebase schema to support multiple conferences
2. **Registration Model**: Update registration storage to be conference-specific
3. **User Dashboard**: Enhance to display multi-conference information

### Key Components
1. **Conference Management Service**: Handle conference discovery and selection
2. **Enhanced Registration Flow**: Add conference selection step
3. **Multi-Conference Dashboard**: Unified view of all user registrations
4. **Admin Conference Switcher**: Allow admins to manage multiple conferences

### Database Schema Updates
```
conferences/
├── {conference_id}/
│   ├── basic_info/
│   ├── registration_fees/
│   └── settings/

registrations/
├── {conference_id}/
│   └── {user_id}: {registration_data}

user_registrations/
├── {user_id}/
│   └── {conference_id}: {registration_summary}
```

## UX/UI Considerations

1. **Conference Discovery**: Clear listing of available conferences with key information
2. **Registration Flow**: Intuitive multi-step process with conference selection first
3. **Dashboard Design**: Tabbed or segmented view for multiple conference registrations
4. **Visual Indicators**: Clear status indicators for each conference registration
5. **Responsive Design**: Ensure mobile-friendly multi-conference interfaces

## Acceptance Criteria

1. **Conference Listing**: Users can view all available conferences with status (active, upcoming, past)
2. **Multi-Registration**: Users can register for multiple conferences with separate payment processes
3. **Dashboard Integration**: Users can view all their registrations in a unified dashboard
4. **Admin Management**: Admins can create and manage multiple conferences independently
5. **Data Integrity**: Each conference maintains separate registration fees, schedules, and settings
6. **Backward Compatibility**: Existing single-conference data continues to work during migration

## Dependencies

- Firebase schema migration strategy
- User authentication and session management
- Payment processing system updates
- Email notification system updates for conference-specific messages

## Open Questions

1. Should users be able to transfer registrations between conferences?
2. How should we handle bulk discounts for multi-conference registrations?
3. What is the maximum number of conferences a user should be able to register for?
4. Should we implement conference categories or tags for better organization?

## Related Tasks

[View Task List](./tasks.md) - Complete breakdown of implementation tasks for this PBI. 