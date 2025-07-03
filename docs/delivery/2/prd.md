# PBI-2: Multi-Conference Paper Submission Support

[View in Backlog](../backlog.md#user-content-2)

## Overview

This PBI enables researchers to submit papers to multiple conferences within the GIIR Conference System. Currently, the system supports paper submission to only one conference. This enhancement will allow researchers to submit papers to multiple conferences, track submission status across conferences, and manage conference-specific submission requirements and deadlines.

## Problem Statement

The current system's single-conference paper submission model limits researchers who want to:
- Submit the same research to multiple relevant conferences
- Submit different papers to different conferences
- Track paper status across multiple conference submissions
- Manage different submission requirements per conference
- Handle conference-specific review processes and deadlines

## User Stories

**Primary User Story:**
As a researcher, I want to submit papers to multiple conferences so that I can share my research with different audiences and increase publication opportunities.

**Additional User Stories:**
- As a researcher, I want to track the status of my papers across multiple conferences in one place
- As a researcher, I want to submit different papers to different conferences based on their focus areas
- As a researcher, I want to manage conference-specific submission guidelines and deadlines
- As an admin, I want to manage paper submissions separately for each conference
- As a reviewer, I want to review papers specific to the conference I'm assigned to

## Technical Approach

### Data Model Changes
1. **Paper Submission Model**: Restructure paper storage to be conference-specific
2. **User Paper Tracking**: Create user-centric view of papers across conferences
3. **Conference-Specific Guidelines**: Store submission requirements per conference

### Key Components
1. **Conference Selection in Submission**: Add conference targeting to paper submission flow
2. **Multi-Conference Paper Dashboard**: User view of papers across all conferences
3. **Conference-Specific Review System**: Separate review processes per conference
4. **Admin Paper Management**: Conference-specific paper administration

### Database Schema Updates
```
papers/
├── {conference_id}/
│   └── {paper_id}/
│       ├── paper_data
│       ├── review_status
│       └── conference_specific_metadata

user_papers/
├── {user_id}/
│   └── {conference_id}/
│       └── {paper_id}: {paper_summary}

conference_submission_guidelines/
├── {conference_id}/
│   ├── submission_requirements
│   ├── review_criteria
│   └── deadlines
```

## UX/UI Considerations

1. **Conference Selection**: Clear conference selection during paper submission
2. **Submission Guidelines**: Conference-specific guidelines and requirements display
3. **Paper Dashboard**: Multi-conference paper tracking with status indicators
4. **Duplicate Detection**: Warning system for potential duplicate submissions
5. **Conference Comparison**: Side-by-side comparison of submission requirements
6. **Status Tracking**: Clear visual indicators for paper status per conference

## Acceptance Criteria

1. **Conference Selection**: Users can select target conference(s) during paper submission
2. **Multi-Submission**: Users can submit papers to multiple conferences with separate tracking
3. **Conference Guidelines**: Each conference can have specific submission requirements and templates
4. **Paper Dashboard**: Users can view all paper submissions across conferences in unified interface
5. **Review Management**: Admins can manage review processes separately per conference
6. **Status Tracking**: Real-time status updates for papers in each conference
7. **Duplicate Prevention**: System warns about potential duplicate submissions (configurable)

## Dependencies

- Multi-conference infrastructure from PBI-1
- Firebase schema migration for paper storage
- Email notification system for conference-specific paper updates
- File storage system updates for conference-specific paper organization
- Review system updates for conference-specific workflows

## Open Questions

1. Should we allow exact duplicate paper submissions to multiple conferences?
2. How should we handle withdrawal of papers from specific conferences?
3. Should there be bulk submission features for submitting to multiple conferences at once?
4. How should we handle conference-specific paper formats and templates?
5. Should we implement paper versioning for conference-specific modifications?
6. How should we handle co-author permissions across multiple conference submissions?

## Related Tasks

[View Task List](./tasks.md) - Complete breakdown of implementation tasks for this PBI. 