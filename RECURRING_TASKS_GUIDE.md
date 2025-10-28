# Recurring Tasks Guide

## Overview

The Family AI Assistant now supports recurring task management, allowing you to create tasks that repeat on a regular schedule. This is perfect for activities like:
- Taking a child to weekly classes
- Daily chores
- Monthly bill payments
- Yearly events

## Key Concepts

### Recurring Pattern
A recurring pattern defines the rules for generating recurring tasks:
- **Frequency**: daily, weekly, monthly, or yearly
- **Interval**: Repeat every N periods (e.g., every 2 weeks)
- **By Day**: Specific days for weekly (0=Monday, 6=Sunday) or monthly (1-31) patterns
- **Time**: Start time (hour and minute)
- **Duration**: Task duration in minutes
- **Date Range**: Start date and optional end date

### Task Instances
Individual task occurrences generated from a recurring pattern. Each instance:
- Links back to its parent recurring pattern
- Has its own status and can be completed independently
- Can be edited without affecting other instances
- Has an `occurrence_date` indicating which date it's for

## Database Schema

### New Table: `recurring_patterns`
Stores the recurrence rules for generating tasks.

### Updated Table: `tasks`
Added fields:
- `recurring_pattern_id`: Foreign key to the pattern (NULL for non-recurring tasks)
- `occurrence_date`: The specific date this task instance is for

## API Endpoints

### Create Recurring Pattern
```http
POST /recurring-patterns
Content-Type: application/json

{
  "family_id": 1,
  "title": "Take Sarah to Ballet Class",
  "description": "Drive Sarah to ballet at the community center",
  "frequency": "weekly",
  "interval": 1,
  "by_day": [6],  // Sunday (0=Monday, 6=Sunday)
  "start_time_hour": 16,
  "start_time_minute": 0,
  "duration_minutes": 60,
  "start_date": "2025-10-27T00:00:00",
  "end_date": null,  // No end date
  "default_assignee_user_id": 2,
  "created_by_user_id": 1,
  "is_active": true,
  "meta": {
    "location": "Community Center",
    "notes": "Bring water bottle"
  }
}
```

**Response**: Returns the created pattern with auto-generated tasks for the next 30 days.

### Get Recurring Patterns
```http
GET /recurring-patterns?family_id=1&is_active=true
```

### Get Specific Pattern
```http
GET /recurring-patterns/{pattern_id}
```

### Update Recurring Pattern
```http
PUT /recurring-patterns/{pattern_id}
Content-Type: application/json

{
  "title": "Take Sarah to Advanced Ballet Class",
  "start_time_hour": 17,
  "is_active": true
}
```

**Note**: Updating a pattern does NOT modify existing task instances, only future generated ones.

### Delete Recurring Pattern
```http
DELETE /recurring-patterns/{pattern_id}?delete_future_tasks=true
```

- `delete_future_tasks=false` (default): Keeps existing task instances
- `delete_future_tasks=true`: Deletes all future uncompleted tasks

### Generate Task Instances
```http
POST /recurring-patterns/{pattern_id}/generate?days_ahead=60
```

Manually generate task instances for the next N days (useful for planning far ahead).

### Get Tasks for Pattern
```http
GET /recurring-patterns/{pattern_id}/tasks?include_completed=false
```

Retrieves all task instances for a specific pattern.

### Activate/Deactivate Pattern
```http
PATCH /recurring-patterns/{pattern_id}/activate
PATCH /recurring-patterns/{pattern_id}/deactivate
```

## Usage Examples

### Example 1: Weekly Class on Sunday 4-5 PM
```json
{
  "family_id": 1,
  "title": "Take child to piano class",
  "frequency": "weekly",
  "interval": 1,
  "by_day": [6],  // Sunday
  "start_time_hour": 16,
  "start_time_minute": 0,
  "duration_minutes": 60,
  "start_date": "2025-10-27T00:00:00",
  "default_assignee_user_id": 2,
  "is_active": true
}
```

### Example 2: Every Tuesday and Thursday
```json
{
  "family_id": 1,
  "title": "School pickup",
  "frequency": "weekly",
  "interval": 1,
  "by_day": [1, 3],  // Tuesday=1, Thursday=3
  "start_time_hour": 15,
  "start_time_minute": 30,
  "start_date": "2025-10-27T00:00:00",
  "default_assignee_user_id": 2,
  "is_active": true
}
```

### Example 3: Monthly on 1st and 15th
```json
{
  "family_id": 1,
  "title": "Pay rent/utilities",
  "frequency": "monthly",
  "interval": 1,
  "by_day": [1, 15],  // 1st and 15th of month
  "start_time_hour": 9,
  "start_date": "2025-11-01T00:00:00",
  "default_assignee_user_id": 1,
  "is_active": true
}
```

### Example 4: Every 2 Weeks
```json
{
  "family_id": 1,
  "title": "Grocery shopping",
  "frequency": "weekly",
  "interval": 2,  // Every 2 weeks
  "by_day": [5],  // Saturday
  "start_time_hour": 10,
  "start_date": "2025-10-27T00:00:00",
  "default_assignee_user_id": 1,
  "is_active": true
}
```

### Example 5: Daily Task
```json
{
  "family_id": 1,
  "title": "Morning medication reminder",
  "frequency": "daily",
  "interval": 1,
  "start_time_hour": 8,
  "start_time_minute": 0,
  "start_date": "2025-10-27T00:00:00",
  "default_assignee_user_id": 3,
  "is_active": true
}
```

## Task Generation Logic

### Automatic Generation
- When creating a pattern, tasks are auto-generated for the next 30 days
- Tasks are generated with status `todo`
- Each task links back to the pattern via `recurring_pattern_id`

### Manual Generation
Use the generate endpoint to create tasks further into the future:
```http
POST /recurring-patterns/{pattern_id}/generate?days_ahead=90
```

### Generation Algorithm
The service intelligently generates tasks based on:
1. **Frequency**: How often to repeat (daily, weekly, monthly, yearly)
2. **Interval**: Every N periods
3. **By Day**: Specific days to include
4. **Date Range**: Only within start_date and end_date (if set)

The algorithm avoids creating duplicate tasks by checking `occurrence_date`.

## Managing Task Instances

### Editing Individual Instances
Each generated task can be edited independently:
```http
PUT /tasks/{task_id}
Content-Type: application/json

{
  "assignee_user_id": 3,
  "due_at": "2025-11-03T17:00:00",
  "status": "in_progress"
}
```

This only affects the specific task instance, not the pattern or other instances.

### Completing Tasks
```http
POST /tasks/{task_id}/complete
```

### Viewing All Instances
```http
GET /recurring-patterns/{pattern_id}/tasks
```

### Filtering Tasks
Regular task endpoints still work and include recurring task instances:
```http
GET /tasks?family_id=1&assignee_user_id=2&status=todo
```

## Best Practices

### 1. Use Descriptive Titles
Include enough context in the title:
- ✅ "Take Sarah to Ballet Class at Community Center"
- ❌ "Class"

### 2. Set Duration for Time-Bound Activities
Use `duration_minutes` for activities with a specific duration:
```json
{
  "duration_minutes": 60,
  "meta": {
    "end_time": "17:00"
  }
}
```

### 3. Use Meta for Additional Context
Store extra information in the `meta` field:
```json
{
  "meta": {
    "location": "123 Main St",
    "contact": "+1234567890",
    "preparation_time": 15,
    "notes": "Bring soccer cleats"
  }
}
```

### 4. Set End Dates for Seasonal Activities
For activities that end after a certain date:
```json
{
  "start_date": "2025-09-01T00:00:00",
  "end_date": "2026-06-30T00:00:00",  // School year
  "title": "After-school program"
}
```

### 5. Deactivate Instead of Delete
When a recurring activity is temporarily paused:
```http
PATCH /recurring-patterns/{pattern_id}/deactivate
```

Later, reactivate it:
```http
PATCH /recurring-patterns/{pattern_id}/activate
```

### 6. Generate Tasks Ahead of Time
For better planning, generate tasks 60-90 days ahead:
```http
POST /recurring-patterns/{pattern_id}/generate?days_ahead=90
```

## Database Migration

To apply the schema changes, run:
```bash
# Apply the migration
alembic upgrade head

# Or if using Docker
docker-compose exec app alembic upgrade head
```

## Technical Details

### Weekday Convention
- **0** = Monday
- **1** = Tuesday
- **2** = Wednesday
- **3** = Thursday
- **4** = Friday
- **5** = Saturday
- **6** = Sunday

This follows Python's `datetime.weekday()` convention.

### Task Generation Performance
- Tasks are generated in batches (max 100 per call by default)
- Generation is tracked via `last_generated_until` to avoid duplicates
- Inactive patterns do not generate new tasks

### Timezone Handling
- All datetimes are stored as naive (no timezone)
- Times are stored as separate hour/minute fields
- The application should handle timezone conversion at the API layer

## Future Enhancements

Potential features for future development:
- [ ] Recurring exceptions (skip specific dates)
- [ ] Multiple assignees per pattern
- [ ] Notification preferences per pattern
- [ ] Pattern templates (common use cases)
- [ ] Bulk edit of future instances
- [ ] Pattern analytics (completion rates)
- [ ] Smart scheduling suggestions

## Troubleshooting

### Tasks Not Generating
1. Check if pattern is active: `is_active: true`
2. Verify date range includes current date
3. Check `last_generated_until` field
4. Manually trigger generation

### Duplicate Tasks
- The system prevents duplicates by checking `occurrence_date`
- If duplicates occur, check database constraints

### Wrong Days Generated
- Verify `by_day` values match your intention
- Remember: 0=Monday, 6=Sunday
- For monthly, use 1-31 (day of month)

## Support

For issues or questions about recurring tasks, please refer to:
- API documentation at `/docs` endpoint
- Model definitions in `app/models/recurring_pattern.py`
- Service logic in `app/services/recurring_pattern_service.py`


